from django.views.generic import ListView
from .models import Servico

class CatalogoView(ListView):
    model = Servico
    
    template_name = 'home.html' 
    
    context_object_name = 'terapias'

    def get_queryset(self):
        return Servico.objects.filter(ativo=True)