from django import forms
from datetime import date, datetime
from django.db.models import Q
from servicos.models import Servico
from .models import Agendamento, BloqueioAgenda, Voucher


class SolicitacaoAgendamentoForm(forms.Form):
    """
    Formulário de solicitação de agendamento — preenchido pelo cliente.
    Não inclui terapeuta nem voucher (atribuídos pelo admin depois).
    """

    servico = forms.ModelChoiceField(
        queryset=Servico.objects.filter(ativo=True).order_by('nome'),
        label='Terapia',
        empty_label='Selecione a terapia…',
        error_messages={'required': 'Por favor, selecione uma terapia.'},
    )

    data_agendamento = forms.DateField(
        label='Data',
        widget=forms.DateInput(attrs={
            'type': 'date',
        }),
        error_messages={'required': 'Por favor, selecione uma data.'},
    )

    horario_agendamento = forms.TimeField(
        label='Horário',
        widget=forms.HiddenInput(),
        error_messages={'required': 'Por favor, selecione um horário.'},
    )

    metodo_pagamento = forms.ChoiceField(
        choices=Agendamento.PAGAMENTO_CHOICES,
        label='Método de pagamento',
        error_messages={
            'required': 'Por favor, selecione como deseja realizar o pagamento no dia do atendimento.'
        },
        widget=forms.HiddenInput(),   # Seleção via cards JS; valor enviado como hidden
    )

    def clean_data_agendamento(self):
        data = self.cleaned_data.get('data_agendamento')
        if data and data < date.today():
            raise forms.ValidationError('Não é possível agendar para uma data passada.')
        if data:
            bloqueado = BloqueioAgenda.objects.filter(
                Q(tipo='dia_semana', dia_semana=data.weekday()) |
                Q(tipo='data', data=data)
            ).exists()
            if bloqueado:
                raise forms.ValidationError(
                    'Esta data não está disponível para agendamentos. '
                    'Por favor, escolha outro dia.'
                )
        return data

    def clean(self):
        cleaned = super().clean()
        data    = cleaned.get('data_agendamento')
        horario = cleaned.get('horario_agendamento')
        metodo  = cleaned.get('metodo_pagamento')

        if not metodo:
            self.add_error(
                'metodo_pagamento',
                'Por favor, selecione como deseja realizar o pagamento no dia do atendimento.'
            )

        if data and horario:
            # Rejeita horários que já passaram quando a data é hoje
            if data == date.today() and horario <= datetime.now().time():
                self.add_error(
                    'horario_agendamento',
                    'Este horário já passou. Por favor, escolha um horário futuro.'
                )

            # Verifica conflito de horário (sem lock — feito de novo na view com select_for_update)
            conflito = Agendamento.objects.filter(
                data_agendamento=data,
                horario_agendamento=horario,
                status__in=Agendamento.STATUS_ATIVOS,
            ).exists()
            if conflito:
                raise forms.ValidationError(
                    'Desculpe, este horário acabou de ser preenchido. '
                    'Por favor, escolha outra opção.'
                )

        return cleaned


class BloqueioAgendaForm(forms.ModelForm):
    """Formulário do painel admin para criar bloqueios de agenda."""

    class Meta:
        model = BloqueioAgenda
        fields = ['tipo', 'dia_semana', 'data', 'motivo']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()
        tipo       = cleaned.get('tipo')
        dia_semana = cleaned.get('dia_semana')
        data       = cleaned.get('data')

        if tipo == 'dia_semana':
            if dia_semana is None:
                self.add_error('dia_semana', 'Selecione o dia da semana.')
            cleaned['data'] = None
        elif tipo == 'data':
            if not data:
                self.add_error('data', 'Informe a data específica.')
            cleaned['dia_semana'] = None

        return cleaned


# ---------------------------------------------------------------------------
# Formulário de Voucher (US08)
# ---------------------------------------------------------------------------

class VoucherForm(forms.ModelForm):
    """
    Cadastro e edição de vouchers.
    - Código convertido para maiúsculas e validado como único.
    - Desconto percentual limitado a 1–100.
    - Limite em branco/0 = uso ilimitado.
    - Edição restrita: se já houve uso, Tipo e Valor ficam bloqueados.
    """

    class Meta:
        model = Voucher
        fields = [
            'codigo_promocional', 'tipo_desconto', 'valor_desconto',
            'limite_uso', 'data_validade', 'status_voucher',
        ]
        widgets = {
            'codigo_promocional': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: BEMVINDO',
                'style': 'text-transform:uppercase;',
            }),
            'tipo_desconto': forms.Select(attrs={'class': 'form-control'}),
            'valor_desconto': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'placeholder': '0.00',
            }),
            'limite_uso': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'placeholder': 'Em branco = ilimitado',
            }),
            'data_validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status_voucher': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Proteção financeira: voucher já utilizado não altera tipo nem valor
        if self.instance and self.instance.pk and self.instance.usos_realizados > 0:
            self.fields['tipo_desconto'].disabled = True
            self.fields['valor_desconto'].disabled = True

    def clean_codigo_promocional(self):
        codigo = self.cleaned_data['codigo_promocional'].strip().upper()
        qs = Voucher.objects.filter(codigo_promocional__iexact=codigo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                'Este código promocional já existe. Por favor, escolha outro nome.'
            )
        return codigo

    def clean_limite_uso(self):
        limite = self.cleaned_data.get('limite_uso')
        # None ou 0 → ilimitado
        return limite or None

    def clean(self):
        cleaned = super().clean()
        tipo  = cleaned.get('tipo_desconto')
        valor = cleaned.get('valor_desconto')

        if tipo == 'percentual' and valor is not None:
            if valor < 1 or valor > 100:
                self.add_error(
                    'valor_desconto',
                    'Para desconto percentual, informe um valor entre 1 e 100.'
                )

        return cleaned
