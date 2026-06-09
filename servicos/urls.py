from django.urls import path
from .views import CatalogoView, ServicoAdminListView, ServicoCreateView, ServicoUpdateView, ServicoDeleteView

app_name = 'servicos'

urlpatterns = [
    # Rota Pública (Cliente)
    path('', CatalogoView.as_view(), name='home'),

    # Rotas Privadas (Admin) - Gestão do Catálogo
    path('painel/admin/', ServicoAdminListView.as_view(), name='painel_admin'),
    path('painel/admin/terapias/nova/', ServicoCreateView.as_view(), name='nova_terapia'),
    path('painel/admin/terapias/<int:pk>/editar/', ServicoUpdateView.as_view(), name='editar_terapia'),
    path('painel/admin/terapias/<int:pk>/remover/', ServicoDeleteView.as_view(), name='remover_terapia'),
]