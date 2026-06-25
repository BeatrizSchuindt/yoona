from django.urls import path
from .views import (
    IdentificacaoView, AnamneseView, AnamneseDetailView,
    ClienteListView, ClienteDetailView, ClienteUpdateView,
)

app_name = 'clientes'

urlpatterns = [
    path('agendar/', IdentificacaoView.as_view(), name='identificacao'),
    path('agendar/anamnese/', AnamneseView.as_view(), name='anamnese'),

    # Painel admin — Gestão de clientes (US13)
    path('painel/admin/clientes/', ClienteListView.as_view(), name='gestao_clientes'),
    path('painel/admin/clientes/<int:pk>/', ClienteDetailView.as_view(), name='cliente_detalhe'),
    path('painel/admin/clientes/<int:pk>/editar/', ClienteUpdateView.as_view(), name='editar_cliente'),

    # Painel interno — visualização da ficha (admin/terapeuta)
    path('painel/admin/clientes/<int:pk>/anamnese/', AnamneseDetailView.as_view(), name='anamnese_detalhe'),
]
