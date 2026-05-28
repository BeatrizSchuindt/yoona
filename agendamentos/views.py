import json
from datetime import date, time

from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction

from servicos.models import Servico
from clientes.models import Cliente
from .models import Agendamento
from .forms import SolicitacaoAgendamentoForm


# ---------------------------------------------------------------------------
# Configuração dos slots de horário
# ---------------------------------------------------------------------------

HORARIO_INICIO = 9    # 09:00
HORARIO_FIM    = 18   # último slot às 18:00


def _gerar_slots():
    """Retorna lista de objetos time com todos os slots do dia."""
    return [time(h, 0) for h in range(HORARIO_INICIO, HORARIO_FIM + 1)]


def _slots_disponiveis(data_escolhida):
    """
    Retorna lista de strings 'HH:MM' com os slots livres para a data informada.
    Um slot é bloqueado se já existe Agendamento aguardando ou confirmado nele.
    """
    todos = _gerar_slots()
    ocupados = set(
        Agendamento.objects.filter(
            data_agendamento=data_escolhida,
            status__in=['aguardando', 'confirmado'],
        ).values_list('horario_agendamento', flat=True)
    )
    return [t.strftime('%H:%M') for t in todos if t not in ocupados]


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
        return {
            'form': form,
            'cliente': cliente,
            'servicos': Servico.objects.filter(ativo=True).order_by('nome'),
            'slots_iniciais': json.dumps(_slots_disponiveis(data_escolhida)),
            'hoje': date.today().isoformat(),
            'pagamento_choices': Agendamento.PAGAMENTO_CHOICES,
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
