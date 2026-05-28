from django.urls import path
from .views import SolicitacaoView, HorariosDisponiveisView

app_name = 'agendamentos'

urlpatterns = [
    path('agendar/servico/', SolicitacaoView.as_view(), name='solicitacao'),
    path('agendar/horarios/', HorariosDisponiveisView.as_view(), name='horarios_disponiveis'),
]
