from django.contrib import admin
from .models import Cliente, Anamnese


class AnamneseInline(admin.StackedInline):
    model = Anamnese
    extra = 0
    can_delete = False
    verbose_name_plural = 'Ficha de Anamnese'
    readonly_fields = ('data_preenchimento', 'data_atualizacao')


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'cpf', 'telefone', 'tem_anamnese', 'data_cadastro')
    search_fields = ('nome_completo', 'cpf', 'telefone')
    readonly_fields = ('data_cadastro',)
    inlines = [AnamneseInline]

    @admin.display(boolean=True, description='Anamnese?')
    def tem_anamnese(self, obj):
        return hasattr(obj, 'anamnese')


@admin.register(Anamnese)
class AnamneseAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'sensibilidades', 'consentimento_lgpd', 'data_preenchimento')
    list_filter = ('sensibilidades', 'consentimento_lgpd')
    search_fields = ('cliente__nome_completo', 'cliente__cpf')
    readonly_fields = ('data_preenchimento', 'data_atualizacao')
