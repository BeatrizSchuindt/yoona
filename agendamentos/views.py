import json
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, time, datetime, timedelta

from django.views import View
from django.views.generic import ListView, CreateView, UpdateView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from django.urls import reverse, reverse_lazy

from servicos.views import AdminStaffRequiredMixin
from servicos.models import Servico
from clientes.models import Cliente
from terapeutas.models import Terapeuta
from .models import Agendamento, BloqueioAgenda, Comissao, Voucher
from .forms import SolicitacaoAgendamentoForm, BloqueioAgendaForm, VoucherForm


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
            status__in=Agendamento.STATUS_ATIVOS,
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
                status__in=Agendamento.STATUS_ATIVOS,
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
        return redirect('clientes:anamnese')


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


# ---------------------------------------------------------------------------
# US11 — Gestão Diária de Agendamentos
# ---------------------------------------------------------------------------

class GestaoAgendaView(AdminStaffRequiredMixin, View):
    """
    Listagem dos agendamentos do dia (filtrável por data) para o administrador.
    Permite vincular terapeuta e alterar o status de cada atendimento.
    """
    template_name = 'gestao_agenda.html'

    def get(self, request):
        data_str = request.GET.get('data', date.today().isoformat())
        try:
            data_filtro = date.fromisoformat(data_str)
        except ValueError:
            data_filtro = date.today()

        agendamentos = (
            Agendamento.objects
            .filter(data_agendamento=data_filtro)
            .select_related('cliente', 'servico', 'terapeuta')
            .order_by('horario_agendamento')
        )

        return render(request, self.template_name, {
            'agendamentos': agendamentos,
            'data_filtro': data_filtro.isoformat(),
            'terapeutas': Terapeuta.objects.filter(ativo=True).order_by('nome_terapeuta'),
            'status_choices': Agendamento.STATUS_CHOICES,
        })


class AtualizarAgendamentoView(AdminStaffRequiredMixin, View):
    """
    Salva o vínculo de terapeuta e a transição de status de um agendamento.
    Regras (US11):
      · Concluído exige terapeuta vinculado.
      · Concluir gera a comissão automaticamente (imutável).
      · Agendamento já concluído não pode ser alterado.
    """

    def post(self, request, pk):
        agendamento = get_object_or_404(Agendamento, pk=pk)

        # Mantém o filtro de data ao redirecionar de volta à lista
        base_url = reverse('agendamentos:gestao_agenda')
        data_q = request.POST.get('data_filtro', '')
        destino = f"{base_url}?data={data_q}" if data_q else base_url

        # Imutabilidade: concluído não pode mais ser alterado
        if agendamento.status == 'concluido':
            messages.error(
                request,
                'Este agendamento já foi concluído e não pode ser alterado.'
            )
            return redirect(destino)

        novo_status = request.POST.get('status', agendamento.status)
        terapeuta_id = request.POST.get('terapeuta') or None

        # Resolve o terapeuta selecionado
        terapeuta = None
        if terapeuta_id:
            terapeuta = get_object_or_404(Terapeuta, pk=terapeuta_id)

        # ── Conclusão exige terapeuta + gera comissão ─────────────────────
        if novo_status == 'concluido':
            if not terapeuta:
                messages.error(
                    request,
                    'Não é possível concluir: Terapeuta não vinculado.'
                )
                return redirect(destino)

            with transaction.atomic():
                agendamento.terapeuta = terapeuta
                agendamento.status = 'concluido'
                if agendamento.valor_final is None:
                    agendamento.valor_final = agendamento.calcular_valor_final()
                agendamento.save()

                # Gera a comissão apenas se ainda não existir
                if not hasattr(agendamento, 'comissao'):
                    valor_comissao = (
                        agendamento.valor_final * terapeuta.percentual_decimal
                    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    Comissao.objects.create(
                        agendamento=agendamento,
                        terapeuta=terapeuta,
                        valor_calculado=valor_comissao,
                    )

            messages.success(
                request,
                'Atendimento concluído e comissão registrada com sucesso.'
            )
            return redirect(destino)

        # ── Demais status (aguardando / em_andamento / confirmado / cancelado) ──
        agendamento.terapeuta = terapeuta
        agendamento.status = novo_status
        agendamento.save()
        messages.success(request, 'Agendamento atualizado com sucesso.')
        return redirect(destino)


# ---------------------------------------------------------------------------
# US08 — Gestão de Vouchers
# ---------------------------------------------------------------------------

class VoucherListView(AdminStaffRequiredMixin, ListView):
    """Lista todos os vouchers cadastrados."""
    model = Voucher
    template_name = 'gestao_vouchers.html'
    context_object_name = 'vouchers'


class VoucherCreateView(AdminStaffRequiredMixin, CreateView):
    """Cadastro de novo voucher."""
    model = Voucher
    form_class = VoucherForm
    template_name = 'novo_voucher.html'
    success_url = reverse_lazy('agendamentos:gestao_vouchers')

    def form_valid(self, form):
        messages.success(self.request, 'Voucher cadastrado com sucesso!')
        return super().form_valid(form)


class VoucherUpdateView(AdminStaffRequiredMixin, UpdateView):
    """Edição de voucher (Tipo e Valor travados se já utilizado)."""
    model = Voucher
    form_class = VoucherForm
    template_name = 'editar_voucher.html'
    success_url = reverse_lazy('agendamentos:gestao_vouchers')

    def form_valid(self, form):
        messages.success(self.request, 'Voucher atualizado com sucesso!')
        return super().form_valid(form)


class VoucherToggleStatusView(AdminStaffRequiredMixin, View):
    """Alterna o status do voucher entre ativo e inativo (botão Ativar/Inativar)."""

    def post(self, request, pk):
        voucher = get_object_or_404(Voucher, pk=pk)
        if voucher.status_voucher == 'ativo':
            voucher.status_voucher = 'inativo'
            messages.success(request, f'Voucher "{voucher.codigo_promocional}" inativado.')
        else:
            voucher.status_voucher = 'ativo'
            messages.success(request, f'Voucher "{voucher.codigo_promocional}" ativado.')
        voucher.save()
        return redirect('agendamentos:gestao_vouchers')
