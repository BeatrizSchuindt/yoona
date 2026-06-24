from django.urls import path
from .views import IdentificacaoView, AnamneseView, AnamneseDetailView

app_name = 'clientes'

urlpatterns = [
    path('agendar/', IdentificacaoView.as_view(), name='identificacao'),
    path('agendar/anamnese/', AnamneseView.as_view(), name='anamnese'),

    # Painel interno — visualização da ficha (admin/terapeuta)
    path('painel/admin/clientes/<int:pk>/anamnese/', AnamneseDetailView.as_view(), name='anamnese_detalhe'),
]
