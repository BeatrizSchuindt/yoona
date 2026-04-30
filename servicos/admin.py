from django.contrib import admin
from .models import Servico

@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'duracao', 'preco_base', 'ativo')
    list_filter = ('ativo',)
    list_per_page = 10
    search_fields = ('nome',)