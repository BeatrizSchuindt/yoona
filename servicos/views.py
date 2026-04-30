from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Servico
from .forms import ServicoForm

# --- VIEW PÚBLICA (CLIENTE) ---

class CatalogoView(ListView):
    """
    Exibição do catálogo de terapias para o cliente final.
    Lista apenas serviços com status 'Ativo'.
    """
    model = Servico
    template_name = 'home.html' 
    context_object_name = 'terapias'

    def get_queryset(self):
        # Filtra apenas os serviços ativos para o cliente
        return Servico.objects.filter(ativo=True)


# --- VIEWS ADMINISTRATIVAS (EQUIPE) ---

class AdminStaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin utilitário para restringir acesso apenas a administradores (is_staff).
    """
    def test_func(self):
        return self.request.user.is_staff


class ServicoAdminListView(AdminStaffRequiredMixin, ListView):
    """
    Painel de Gestão: Lista todas as terapias (ativas e inativas).
    Requisito: Paginação de 10 registros por página.
    """
    model = Servico
    template_name = 'painel_admin.html'
    context_object_name = 'terapias_admin'
    paginate_by = 10 

    def get_queryset(self):
        return Servico.objects.all().order_by('nome')


class ServicoCreateView(AdminStaffRequiredMixin, CreateView):
    """
    Cadastro de Nova Terapia.
    Utiliza o ServicoForm para validação automática dos campos.
    """
    model = Servico
    form_class = ServicoForm
    template_name = 'nova_terapia.html'
    
    success_url = reverse_lazy('servicos:painel_admin')

    def form_valid(self, form):
        return super().form_valid(form)