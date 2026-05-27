from django.contrib import admin
from .models import Voucher, Agendamento, Comissao


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = (
        'codigo_promocional', 'tipo_desconto', 'valor_desconto',
        'status_voucher', 'usos_realizados', 'limite_uso', 'usos_restantes',
    )
    list_filter = ('status_voucher', 'tipo_desconto')
    search_fields = ('codigo_promocional',)
    readonly_fields = ('usos_realizados', 'data_criacao')

    @admin.display(description='Restantes')
    def usos_restantes(self, obj):
        return obj.usos_restantes


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = (
        'cliente', 'servico', 'terapeuta',
        'data_agendamento', 'horario_agendamento',
        'status', 'valor_final',
    )
    list_filter = ('status', 'data_agendamento', 'terapeuta')
    search_fields = ('cliente__nome_completo', 'cliente__cpf', 'servico__nome')
    readonly_fields = ('data_criacao', 'data_atualizacao')
    autocomplete_fields = ['cliente', 'servico', 'terapeuta']
    date_hierarchy = 'data_agendamento'

    fieldsets = (
        ('Dados do Atendimento', {
            'fields': ('cliente', 'servico', 'data_agendamento', 'horario_agendamento'),
        }),
        ('Gestão', {
            'fields': ('terapeuta', 'status', 'voucher', 'valor_final'),
        }),
        ('Registro', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Comissao)
class ComissaoAdmin(admin.ModelAdmin):
    list_display = ('terapeuta', 'agendamento', 'valor_calculado', 'data_registro')
    list_filter = ('terapeuta', 'data_registro')
    search_fields = ('terapeuta__nome_terapeuta', 'agendamento__cliente__nome_completo')
    readonly_fields = ('agendamento', 'terapeuta', 'valor_calculado', 'data_registro')
    date_hierarchy = 'data_registro'

    def has_add_permission(self, request):
        """Comissões só são criadas automaticamente pelo sistema, nunca pelo admin"""
        return False

    def has_change_permission(self, request, obj=None):
        """Comissões são imutáveis — nenhuma edição permitida"""
        return False
