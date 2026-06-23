from django.urls import path
from .views import (
    SolicitacaoView, HorariosDisponiveisView, ValidarVoucherView,
    GerenciarBloqueiosView, RemoverBloqueioView,
    GestaoAgendaView, AtualizarAgendamentoView,
    VoucherListView, VoucherCreateView, VoucherUpdateView, VoucherToggleStatusView,
)

app_name = 'agendamentos'

urlpatterns = [
    # Fluxo do cliente
    path('agendar/servico/', SolicitacaoView.as_view(), name='solicitacao'),
    path('agendar/horarios/', HorariosDisponiveisView.as_view(), name='horarios_disponiveis'),
    path('agendar/voucher/validar/', ValidarVoucherView.as_view(), name='validar_voucher'),

    # Painel admin — Gestão diária de agendamentos
    path('painel/admin/agenda/', GestaoAgendaView.as_view(), name='gestao_agenda'),
    path('painel/admin/agenda/<int:pk>/atualizar/', AtualizarAgendamentoView.as_view(), name='atualizar_agendamento'),

    # Painel admin — Bloqueios de agenda
    path('painel/admin/agenda/bloqueios/', GerenciarBloqueiosView.as_view(), name='gerenciar_bloqueios'),
    path('painel/admin/agenda/bloqueios/<int:pk>/remover/', RemoverBloqueioView.as_view(), name='remover_bloqueio'),

    # Painel admin — Gestão de vouchers
    path('painel/admin/vouchers/', VoucherListView.as_view(), name='gestao_vouchers'),
    path('painel/admin/vouchers/novo/', VoucherCreateView.as_view(), name='novo_voucher'),
    path('painel/admin/vouchers/<int:pk>/editar/', VoucherUpdateView.as_view(), name='editar_voucher'),
    path('painel/admin/vouchers/<int:pk>/status/', VoucherToggleStatusView.as_view(), name='toggle_voucher'),
]
