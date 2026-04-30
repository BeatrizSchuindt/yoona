from django.contrib import admin
from django.urls import path, include
from django.conf import settings # Importação necessária para ler as configurações
from django.conf.urls.static import static # Importação para servir arquivos estáticos/mídia
from servicos.views import CatalogoView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', CatalogoView.as_view(), name='home'),
    
    # path('servicos/', include('servicos.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)