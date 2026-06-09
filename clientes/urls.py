from django.urls import path
from .views import IdentificacaoView

app_name = 'clientes'

urlpatterns = [
    path('agendar/', IdentificacaoView.as_view(), name='identificacao'),
]
