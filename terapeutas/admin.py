from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Terapeuta

class TerapeutaInline(admin.StackedInline):
    """
    Exibe o perfil de terapeuta diretamente na página do usuário.
    Assim o admin cadastra usuário e dados profissionais em um único lugar.
    """
    model = Terapeuta
    extra = 0
    can_delete = False
    verbose_name_plural = 'Perfil de Terapeuta'
    readonly_fields = ('data_cadastro',)

class UserAdmin(BaseUserAdmin):
    inlines = [TerapeutaInline]

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Terapeuta)
class TerapeutaAdmin(admin.ModelAdmin):
    list_display = ('nome_terapeuta', 'usuario', 'percentual_comissao', 'ativo', 'data_cadastro')
    list_filter = ('ativo',)
    search_fields = ('nome_terapeuta', 'usuario__username', 'usuario__email')
    readonly_fields = ('data_cadastro',)
    list_editable = ('ativo',)
