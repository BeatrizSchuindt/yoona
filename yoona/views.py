from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test

# --- LÓGICA DE REDIRECIONAMENTO INTELIGENTE ---
@login_required
def direcionar_usuario(request):
    """Verifica o tipo de usuário e envia para o painel correto."""
    if request.user.is_staff or request.user.is_superuser:
        return redirect('servicos:painel_admin')
    else:
        # Se não é staff, assumimos que é um Terapeuta
        return redirect('painel_terapeuta')

# --- TESTES DE PERMISSÃO ---
def is_admin(user):
    return user.is_staff or user.is_superuser

# --- VIEWS DOS PAINÉIS (PROTEGIDAS) ---
@login_required
@user_passes_test(is_admin, login_url='/login/') # Só Admin acessa
def painel_admin(request):
    # Aqui depois buscaremos as Terapias para a listagem
    return redirect('servicos:painel_admin')

@login_required # Terapeutas acessam
def painel_terapeuta(request):
    """Agenda diária do terapeuta logado (US07) — somente seus atendimentos."""
    from datetime import date
    from agendamentos.models import Agendamento

    terapeuta = getattr(request.user, 'terapeuta', None)

    data_str = request.GET.get('data', date.today().isoformat())
    try:
        data_filtro = date.fromisoformat(data_str)
    except ValueError:
        data_filtro = date.today()

    agendamentos = []
    if terapeuta:
        agendamentos = (
            Agendamento.objects
            .filter(terapeuta=terapeuta, data_agendamento=data_filtro)
            .select_related('cliente', 'servico')
            .order_by('horario_agendamento')
        )

    return render(request, 'painel_terapeuta.html', {
        'terapeuta': terapeuta,
        'agendamentos': agendamentos,
        'data_filtro': data_filtro.isoformat(),
    })