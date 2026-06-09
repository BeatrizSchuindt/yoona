import json
from datetime import date, time, datetime, timedelta

from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q

from servicos.views import AdminStaffRequiredMixin
from servicos.models import Servico
from clientes.models import Cliente
from .models import Agendamento, BloqueioAgenda
from .forms import SolicitacaoAgendamentoForm, BloqueioAgendaForm


# ---------------------------------------------------------------------------
# Configuração dos slots de horário
# ---------------------------------------------------------------------------

HORARIO_INICIO = 9    # 09:00
HORARIO_FIM    = 18   # último slot às 18:00


def _gerar_slots():
    """Retorna lista de objetos time com todos os slots do dia."""
    return [time(h, 0) for h in range(HORARIO_INICIO, HORARIO_FIM + 1)]


def _data_bloqueada(data_escolhida):
    """True se a data está coberta por um BloqueioAgenda (dia da semana ou data específica)."""
    return BloqueioAgenda.objects.filter(
        Q(tipo='dia_semana', dia_semana=data_escolhida.weekday()) |
        Q(tipo='data', data=data_escolhida)
    ).exists()


def _dados_bloqueios():
    """
    Retorna (dias_semana_py, datas_iso) para passar ao Flatpickr.
    dias_semana_py: lista de int Python weekday (0=Seg … 6=Dom)
    datas_iso: lista de strings YYYY-MM-DD para os próximos 6 meses
    """
    dias = list(
        BloqueioAgenda.objects.filter(tipo='dia_semana', dia_semana__isnull=False)
        .values_list('dia_semana', flat=True)
    )
    hoje = date.today()
    datas = list(
        BloqueioAgenda.objects.filter(
            tipo='data', data__gte=hoje, data__lte=hoje + timedelta(days=180)
        ).values_list('data', flat=True)
    )
    return dias, [d.isoformat() for d in datas]


def _slots_disponiveis(data_escolhida):
    """
    Retorna lista de strings 'HH:MM' com os slots livres para a data informada.
    Retorna lista vazia se a data estiver bloqueada pelo admin.
    Bloqueia também slots já agendados e horários passados de hoje.
    """
    if _data_bloqueada(data_escolhida):
        return []

    todos = _gerar_slots()
    ocupados = set(
        Agendamento.objects.filter(
            data_agendamento=data_escolhida,
            status__in=['aguardando', 'confirmado'],
        ).values_list('horario_agendamento', flat=True)
    )

    hora_limite = datetime.now().time() if data_escolhida == date.today() else None

    return [
        t.strftime('%H:%M')
        for t in todos
        if t not in ocupados and (hora_limite is None or t > hora_limite)
    ]


# ---------------------------------------------------------------------------
# View principal de solicitação
# ---------------------------------------------------------------------------

class SolicitacaoView(View):
    """
    US04 — Tela de agendamento:
      GET  → renderiza formulário (requer cliente_id na sessão)
      POST → valida, cria Agendamento com status 'aguardando', redireciona para anamnese
    """

    template_name = 'agendar.html'

    def _checar_sessao(self, request):
        """Retorna o Cliente da sessão ou None."""
        cliente_id = request.session.get('cliente_id')
        if not cliente_id:
            return None
        try:
            return Cliente.objects.get(pk=cliente_id)
        except Cliente.DoesNotExist:
            return None

    def _contexto_base(self, request, cliente, form, data_escolhida=None):
        if data_escolhida is None:
            data_escolhida = date.today()
        dias_semana, datas_especificas = _dados_bloqueios()
        return {
            'form': form,
            'cliente': cliente,
            'servicos': Servico.objects.filter(ativo=True).order_by('nome'),
            'slots_iniciais': json.dumps(_slots_disponiveis(data_escolhida)),
            'hoje': date.today().isoformat(),
            'pagamento_choices': Agendamento.PAGAMENTO_CHOICES,
            'dias_semana_bloqueados': json.dumps(dias_semana),
            'datas_especificas': json.dumps(datas_especificas),
        }

    def get(self, request):
        cliente = self._checar_sessao(request)
        if not cliente:
            messages.warning(
                request,
                'Primeiro identifique-se com seu CPF para acessar o agendamento.'
            )
            return redirect('clientes:identificacao')

        return render(request, self.template_name,
                      self._contexto_base(request, cliente, SolicitacaoAgendamentoForm()))

    def post(self, request):
        cliente = self._checar_sessao(request)
        if not cliente:
            return redirect('clientes:identificacao')

        form = SolicitacaoAgendamentoForm(request.POST)

        # Recupera a data escolhida para re-exibir slots corretos em caso de erro
        data_str = request.POST.get('data_agendamento', date.today().isoformat())
        try:
            data_escolhida = date.fromisoformat(data_str)
        except ValueError:
            data_escolhida = date.today()

        if not form.is_valid():
            return render(request, self.template_name,
                          self._contexto_base(request, cliente, form, data_escolhida))

        dados = form.cleaned_data

        # ── Race condition: re-verifica com lock antes de inserir ─────────
        with transaction.atomic():
            conflito = Agendamento.objects.select_for_update().filter(
                data_agendamento=dados['data_agendamento'],
                horario_agendamento=dados['horario_agendamento'],
                status__in=['aguardando', 'confirmado'],
            ).exists()

            if conflito:
                messages.error(
                    request,
                    'Desculpe, este horário acabou de ser preenchido. '
                    'Por favor, escolha outra opção.'
                )
                return render(request, self.template_name,
                              self._contexto_base(request, cliente, form,
                                                  dados['data_agendamento']))

            agendamento = Agendamento.objects.create(
                cliente=cliente,
                servico=dados['servico'],
                data_agendamento=dados['data_agendamento'],
                horario_agendamento=dados['horario_agendamento'],
                metodo_pagamento=dados['metodo_pagamento'],
                status='aguardando',
                valor_final=dados['servico'].preco_base,
            )

        # Persiste agendamento_id para a etapa de anamnese (US06)
        request.session['agendamento_id'] = agendamento.pk

        messages.success(
            request,
            'Horário reservado! Por favor, preencha sua ficha de saúde para concluirmos.'
        )
        # Redireciona para anamnese (US06) — temporariamente para home
        return redirect('servicos:home')


# ---------------------------------------------------------------------------
# Endpoint AJAX — horários disponíveis para uma data
# ---------------------------------------------------------------------------

class HorariosDisponiveisView(View):
    """
    GET /agendar/horarios/?data=YYYY-MM-DD
    Retorna JSON: {"disponiveis": ["09:00", "10:00", ...]}
    Atualiza a grade de horários dinamicamente ao trocar de data.
    """

    def get(self, request):
        data_str = request.GET.get('data', '')
        try:
            data_escolhida = date.fromisoformat(data_str)
        except ValueError:
            return JsonResponse({'erro': 'Data inválida.'}, status=400)

        if data_escolhida < date.today():
            return JsonResponse({'disponiveis': []})

        return JsonResponse({'disponiveis': _slots_disponiveis(data_escolhida)})


# ---------------------------------------------------------------------------
# Views admin — Gerenciamento de Bloqueios de Agenda
# ---------------------------------------------------------------------------

class GerenciarBloqueiosView(AdminStaffRequiredMixin, View):
    """
    Painel admin para configurar dias/datas em que o spa não atende.
    GET  → lista bloqueios + exibe formulário de adição
    POST → cria novo bloqueio e redireciona
    """
    template_name = 'gerenciar_bloqueios.html'

    def get(self, request):
        return render(request, self.template_name, {
            'bloqueios': BloqueioAgenda.objects.all(),
            'form': BloqueioAgendaForm(),
        })

    def post(self, request):
        form = BloqueioAgendaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bloqueio adicionado com sucesso.')
            return redirect('agendamentos:gerenciar_bloqueios')
        return render(request, self.template_name, {
            'bloqueios': BloqueioAgenda.objects.all(),
            'form': form,
        })


class RemoverBloqueioView(AdminStaffRequiredMixin, View):
    """Remove um BloqueioAgenda via POST."""

    def post(self, request, pk):
        bloqueio = get_object_or_404(BloqueioAgenda, pk=pk)
        bloqueio.delete()
        messages.success(request, 'Bloqueio removido com sucesso.')
        return redirect('agendamentos:gerenciar_bloqueios')
