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
    Suporta paginação configurável via ?por_pagina=10|20|50.
    """
    model = Servico
    template_name = 'painel_admin.html'
    context_object_name = 'terapias_admin'

    OPCOES_POR_PAGINA = [10, 20, 50]
    DEFAULT_POR_PAGINA = 10

    def get_paginate_by(self, queryset):
        try:
            por_pagina = int(self.request.GET.get('por_pagina', self.DEFAULT_POR_PAGINA))
            if por_pagina in self.OPCOES_POR_PAGINA:
                return por_pagina
        except (ValueError, TypeError):
            pass
        return self.DEFAULT_POR_PAGINA

    def get_queryset(self):
        return Servico.objects.all().order_by('nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        por_pagina = self.get_paginate_by(self.get_queryset())
        page_obj   = context['page_obj']
        # Índices para o contador "Mostrando de X até Y de Z"
        context['por_pagina']      = por_pagina
        context['opcoes_pagina']   = self.OPCOES_POR_PAGINA
        context['indice_inicio']   = page_obj.start_index()
        context['indice_fim']      = page_obj.end_index()
        context['total_registros'] = page_obj.paginator.count
        return context


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