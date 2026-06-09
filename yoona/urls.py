from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('admin_django/', admin.site.urls),
    
    # --- AUTENTICAÇÃO GLOBAL ---
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('direcionamento/', views.direcionar_usuario, name='direcionar_usuario'),
    
    # --- ALTERAÇÃO DE SENHA (usuário logado) ---
    path('alterar-senha/', auth_views.PasswordChangeView.as_view(template_name='password_change.html'), name='password_change'),
    path('alterar-senha/sucesso/', auth_views.PasswordChangeDoneView.as_view(template_name='password_change_done.html'), name='password_change_done'),

    # --- RECUPERAÇÃO DE SENHA ---
    path('recuperar-senha/', auth_views.PasswordResetView.as_view(), name="password_reset"),
    path('recuperar-senha/enviado/', auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path('recuperar-senha/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path('recuperar-senha/sucesso/', auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),

    # --- INCLUSÃO DAS ROTAS DO APP SERVICOS ---
    path('', include('servicos.urls')),

    # --- INCLUSÃO DAS ROTAS DO APP CLIENTES ---
    path('', include('clientes.urls')),

    # --- INCLUSÃO DAS ROTAS DO APP AGENDAMENTOS ---
    path('', include('agendamentos.urls')),
    
    # Rota mantida no roteador central por enquanto (até você criar o app de atendimentos)
    path('painel/terapeuta/', views.painel_terapeuta, name='painel_terapeuta'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)