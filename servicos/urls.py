from django.urls import path
from .views import CatalogoView, ServicoAdminListView, ServicoCreateView

app_name = 'servicos'

urlpatterns = [
    # Rota Pública (Cliente) 
    path('', CatalogoView.as_view(), name='home'),
    
    # Rotas Privadas (Admin) - Gestão do Catálogo
    path('painel/admin/', ServicoAdminListView.as_view(), name='painel_admin'),
    path('painel/admin/terapias/nova/', ServicoCreateView.as_view(), name='nova_terapia'),
]