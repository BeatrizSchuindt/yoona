from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test

# --- LÓGICA DE REDIRECIONAMENTO INTELIGENTE ---
@login_required
def direcionar_usuario(request):
    """Verifica o tipo de usuário e envia para o painel correto."""
    if request.user.is_staff or request.user.is_superuser:
        return redirect('painel_admin')
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
    return render(request, 'painel_admin.html')

@login_required # Terapeutas acessam
def painel_terapeuta(request):
    return render(request, 'painel_terapeuta.html')