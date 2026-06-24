import json
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, time, datetime, timedelta

from django.views import View
from django.views.generic import ListView, CreateView, UpdateView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Sum
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

    def _contexto_base(self, request, cliente, form, data_escolhida=None, codigo_voucher=''):
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
            'codigo_voucher': codigo_voucher,
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

        # Código de voucher aplicado pela cliente (campo hidden do form)
        codigo_voucher = (request.POST.get('codigo_voucher') or '').strip().upper()

        # Recupera a data escolhida para re-exibir slots corretos em caso de erro
        data_str = request.POST.get('data_agendamento', date.today().isoformat())
        try:
            data_escolhida = date.fromisoformat(data_str)
        except ValueError:
            data_escolhida = date.today()

        if not form.is_valid():
            return render(request, self.template_name,
                          self._contexto_base(request, cliente, form,
                                              data_escolhida, codigo_voucher))

        dados = form.cleaned_data
        voucher_invalido = False

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
                                                  dados['data_agendamento'],
                                                  codigo_voucher))

            # ── Voucher: re-valida no servidor e aplica (incrementa o uso) ──
            preco = dados['servico'].preco_base
            voucher_obj = None
            if codigo_voucher:
                voucher_obj = (
                    Voucher.objects.select_for_update()
                    .filter(codigo_promocional__iexact=codigo_voucher)
                    .first()
                )
                if voucher_obj and voucher_obj.motivo_indisponivel() is None:
                    desconto = voucher_obj.calcular_desconto(preco)
                    preco = max(preco - desconto, Decimal('0.00'))
                    voucher_obj.usos_realizados += 1
                    voucher_obj.save(update_fields=['usos_realizados'])
                else:
                    # Cupom ficou indisponível entre "Aplicar" e "Confirmar"
                    voucher_obj = None
                    voucher_invalido = True

            agendamento = Agendamento.objects.create(
                cliente=cliente,
                servico=dados['servico'],
                data_agendamento=dados['data_agendamento'],
                horario_agendamento=dados['horario_agendamento'],
                metodo_pagamento=dados['metodo_pagamento'],
                status='aguardando',
                voucher=voucher_obj,
                valor_final=preco,
            )

        # Persiste agendamento_id para a etapa de anamnese (US06)
        request.session['agendamento_id'] = agendamento.pk

        if voucher_invalido:
            messages.warning(
                request,
                'O cupom informado não está mais disponível e não foi aplicado. '
                'O agendamento foi reservado pelo valor integral.'
            )

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
# US09 — Validação de voucher (preview, não consome o limite)
# ---------------------------------------------------------------------------

class ValidarVoucherView(View):
    """
    POST /agendar/voucher/validar/  (chamado via AJAX pelo botão "Aplicar")
    Body: codigo, servico_id
    Apenas valida e calcula o preview do desconto — NÃO incrementa o uso.
    Retorna JSON:
      sucesso → {valido, codigo, valor_original, valor_desconto, valor_total}
      falha   → {valido: False, mensagem}
    """

    def post(self, request):
        codigo = (request.POST.get('codigo') or '').strip().upper()
        servico_id = request.POST.get('servico_id')

        if not codigo:
            return JsonResponse({'valido': False, 'mensagem': 'Digite um código de cupom.'})

        # Preço de referência: o serviço escolhido
        try:
            servico = Servico.objects.get(pk=servico_id, ativo=True)
        except (Servico.DoesNotExist, ValueError, TypeError):
            return JsonResponse({
                'valido': False,
                'mensagem': 'Selecione uma terapia antes de aplicar o cupom.',
            })

        # Existência (case-insensitive)
        voucher = Voucher.objects.filter(codigo_promocional__iexact=codigo).first()
        if not voucher:
            return JsonResponse({
                'valido': False,
                'mensagem': 'Este código promocional é inválido ou já expirou.',
            })

        # Status / validade / limite
        erro = voucher.motivo_indisponivel()
        if erro:
            return JsonResponse({'valido': False, 'mensagem': erro})

        valor_original = servico.preco_base
        valor_desconto = voucher.calcular_desconto(valor_original)
        valor_total = max(valor_original - valor_desconto, Decimal('0.00'))

        return JsonResponse({
            'valido': True,
            'codigo': voucher.codigo_promocional,
            'valor_original': f'{valor_original:.2f}',
            'valor_desconto': f'{valor_desconto:.2f}',
            'valor_total': f'{valor_total:.2f}',
        })


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
            .select_related('cliente', 'servico', 'terapeuta', 'comissao')
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


# ---------------------------------------------------------------------------
# US10 — Relatório de Comissões (fechamento de caixa)
# ---------------------------------------------------------------------------

class RelatorioComissoesView(AdminStaffRequiredMixin, View):
    """
    Lista os registros imutáveis de comissão, base para o fechamento de caixa.
    Filtros (GET): terapeuta, data_inicio, data_fim (sobre a data de registro).
    Exibe o total do período e a quantidade de atendimentos.
    """
    template_name = 'relatorio_comissoes.html'

    def get(self, request):
        comissoes = (
            Comissao.objects
            .select_related('terapeuta', 'agendamento', 'agendamento__cliente', 'agendamento__servico')
            .order_by('-data_registro')
        )

        # Filtro por terapeuta
        terapeuta_id = request.GET.get('terapeuta') or ''
        if terapeuta_id:
            comissoes = comissoes.filter(terapeuta_id=terapeuta_id)

        # Filtro por período (data de registro)
        data_inicio = request.GET.get('data_inicio') or ''
        data_fim = request.GET.get('data_fim') or ''
        if data_inicio:
            try:
                comissoes = comissoes.filter(data_registro__date__gte=date.fromisoformat(data_inicio))
            except ValueError:
                data_inicio = ''
        if data_fim:
            try:
                comissoes = comissoes.filter(data_registro__date__lte=date.fromisoformat(data_fim))
            except ValueError:
                data_fim = ''

        total = comissoes.aggregate(soma=Sum('valor_calculado'))['soma'] or Decimal('0.00')
        # SQLite devolve a soma como float; normaliza para 2 casas decimais
        total = Decimal(str(total)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return render(request, self.template_name, {
            'comissoes': comissoes,
            'total': total,
            'quantidade': comissoes.count(),
            'terapeutas': Terapeuta.objects.order_by('nome_terapeuta'),
            'terapeuta_sel': terapeuta_id,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
        })
