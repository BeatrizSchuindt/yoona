from django.urls import path
from .views import CatalogoView

app_name = 'servicos'

urlpatterns = [
    path('', CatalogoView.as_view(), name='catalogo'),
]