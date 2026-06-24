from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction

from servicos.views import AdminStaffRequiredMixin
from .models import Terapeuta
from .forms import TerapeutaCreateForm, TerapeutaUpdateForm


class TerapeutaListView(AdminStaffRequiredMixin, ListView):
    """Listagem de todos os terapeutas (ativos e inativos)."""
    model = Terapeuta
    template_name = 'gestao_terapeutas.html'
    context_object_name = 'terapeutas'

    def get_queryset(self):
        return Terapeuta.objects.select_related('usuario').order_by('nome_terapeuta')


class TerapeutaCreateView(AdminStaffRequiredMixin, CreateView):
    """Cadastro de terapeuta com criação do login (User) de forma atômica."""
    model = Terapeuta
    form_class = TerapeutaCreateForm
    template_name = 'novo_terapeuta.html'
    success_url = reverse_lazy('terapeutas:lista')

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
        messages.success(self.request, 'Terapeuta cadastrado com sucesso!')
        return response


class TerapeutaUpdateView(AdminStaffRequiredMixin, UpdateView):
    """Edição de terapeuta (login imutável; senha opcional)."""
    model = Terapeuta
    form_class = TerapeutaUpdateForm
    template_name = 'editar_terapeuta.html'
    success_url = reverse_lazy('terapeutas:lista')

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
        messages.success(self.request, 'Terapeuta atualizado com sucesso!')
        return response


class TerapeutaToggleStatusView(AdminStaffRequiredMixin, View):
    """Alterna o status do terapeuta entre ativo e inativo."""

    def post(self, request, pk):
        terapeuta = get_object_or_404(Terapeuta, pk=pk)
        terapeuta.ativo = not terapeuta.ativo
        terapeuta.save(update_fields=['ativo'])
        estado = 'ativado' if terapeuta.ativo else 'inativado'
        messages.success(request, f'Terapeuta "{terapeuta.nome_terapeuta}" {estado}.')
        return redirect('terapeutas:lista')
