from django.urls import path
from .views import IdentificacaoView, AnamneseView

app_name = 'clientes'

urlpatterns = [
    path('agendar/', IdentificacaoView.as_view(), name='identificacao'),
    path('agendar/anamnese/', AnamneseView.as_view(), name='anamnese'),
]
