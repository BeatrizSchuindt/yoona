from django.contrib import admin
from django.urls import path, include
from django.conf import settings # Importação necessária para ler as configurações
from django.conf.urls.static import static # Importação para servir arquivos estáticos/mídia
from django.contrib.auth import views as auth_views
from servicos.views import CatalogoView
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', CatalogoView.as_view(), name='home'),

    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Redirecionamento e Painéis
    path('direcionamento/', views.direcionar_usuario, name='direcionar_usuario'),
    path('painel/admin/', views.painel_admin, name='painel_admin'),
    path('painel/terapeuta/', views.painel_terapeuta, name='painel_terapeuta'),
    
    # Recuperação de Senha (Rotas Nativas) - Podemos mapear os templates depois
    path('recuperar-senha/', auth_views.PasswordResetView.as_view(), name="password_reset"),
    path('recuperar-senha/enviado/', auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path('recuperar-senha/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path('recuperar-senha/sucesso/', auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    
    # path('servicos/', include('servicos.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)