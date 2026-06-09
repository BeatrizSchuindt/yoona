from django import forms
from datetime import date, datetime
from servicos.models import Servico
from .models import Agendamento


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
                status__in=['aguardando', 'confirmado'],
            ).exists()
            if conflito:
                raise forms.ValidationError(
                    'Desculpe, este horário acabou de ser preenchido. '
                    'Por favor, escolha outra opção.'
                )

        return cleaned
