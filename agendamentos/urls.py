from django.urls import path
from .views import (
    SolicitacaoView, HorariosDisponiveisView,
    GerenciarBloqueiosView, RemoverBloqueioView,
    GestaoAgendaView, AtualizarAgendamentoView,
)

app_name = 'agendamentos'

urlpatterns = [
    # Fluxo do cliente
    path('agendar/servico/', SolicitacaoView.as_view(), name='solicitacao'),
    path('agendar/horarios/', HorariosDisponiveisView.as_view(), name='horarios_disponiveis'),

    # Painel admin — Gestão diária de agendamentos
    path('painel/admin/agenda/', GestaoAgendaView.as_view(), name='gestao_agenda'),
    path('painel/admin/agenda/<int:pk>/atualizar/', AtualizarAgendamentoView.as_view(), name='atualizar_agendamento'),

    # Painel admin — Bloqueios de agenda
    path('painel/admin/agenda/bloqueios/', GerenciarBloqueiosView.as_view(), name='gerenciar_bloqueios'),
    path('painel/admin/agenda/bloqueios/<int:pk>/remover/', RemoverBloqueioView.as_view(), name='remover_bloqueio'),
]
