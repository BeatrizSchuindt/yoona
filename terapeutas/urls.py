from django.urls import path
from .views import (
    TerapeutaListView, TerapeutaCreateView,
    TerapeutaUpdateView, TerapeutaToggleStatusView,
)

app_name = 'terapeutas'

urlpatterns = [
    path('painel/admin/terapeutas/', TerapeutaListView.as_view(), name='lista'),
    path('painel/admin/terapeutas/novo/', TerapeutaCreateView.as_view(), name='novo'),
    path('painel/admin/terapeutas/<int:pk>/editar/', TerapeutaUpdateView.as_view(), name='editar'),
    path('painel/admin/terapeutas/<int:pk>/status/', TerapeutaToggleStatusView.as_view(), name='toggle'),
]
