from django import forms
from .models import Cliente, Anamnese

def _cpf_digitos(cpf: str) -> str:
    return ''.join(filter(str.isdigit, cpf))


def _cpf_matematicamente_valido(cpf: str) -> bool:
    nums = _cpf_digitos(cpf)

    if len(nums) != 11:
        return False

    if nums == nums[0] * 11:
        return False

    soma = sum(int(nums[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    d1 = 0 if resto >= 10 else resto
    if d1 != int(nums[9]):
        return False

    soma = sum(int(nums[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    d2 = 0 if resto >= 10 else resto
    return d2 == int(nums[10])


def _cpf_formatado(cpf: str) -> str:
    n = _cpf_digitos(cpf)
    return f'{n[:3]}.{n[3:6]}.{n[6:9]}-{n[9:11]}'

class CPFForm(forms.Form):
    cpf = forms.CharField(
        max_length=14,
        label='CPF',
        widget=forms.TextInput(attrs={
            'placeholder': '000.000.000-00',
            'inputmode': 'numeric',
            'autocomplete': 'off',
        }),
    )

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '')
        if not _cpf_matematicamente_valido(cpf):
            raise forms.ValidationError(
                'CPF inválido. Por favor, verifique os números informados.'
            )
        return _cpf_formatado(cpf)


class NovoCadastroForm(forms.Form):
    """
    Etapa 1b — campos extras exibidos quando o CPF não está cadastrado.
    Combina CPF (já validado) + nome + telefone.
    """
    cpf = forms.CharField(widget=forms.HiddenInput())

    nome_completo = forms.CharField(
        max_length=150,
        label='Nome completo',
        widget=forms.TextInput(attrs={
            'placeholder': 'Seu nome completo',
            'autocomplete': 'name',
        }),
        error_messages={'required': 'Este campo é obrigatório.'},
    )

    telefone = forms.CharField(
        max_length=20,
        label='Telefone / WhatsApp',
        widget=forms.TextInput(attrs={
            'placeholder': '(00) 00000-0000',
            'inputmode': 'numeric',
            'autocomplete': 'tel',
        }),
        error_messages={'required': 'Este campo é obrigatório.'},
    )

    def clean_telefone(self):
        tel = self.cleaned_data.get('telefone', '')
        digitos = ''.join(filter(str.isdigit, tel))
        if len(digitos) < 10:
            raise forms.ValidationError('Informe um telefone válido com DDD.')
        return tel


# ---------------------------------------------------------------------------
# Formulário de Anamnese (US06)
# ---------------------------------------------------------------------------

SIM_NAO = [('True', 'Sim'), ('False', 'Não')]


class AnamneseForm(forms.ModelForm):
    """
    Ficha de saúde capilar preenchida pelo cliente após o agendamento.
    Campos booleanos são apresentados como radio Sim/Não com áreas condicionais.
    """

    tem_alergias = forms.ChoiceField(
        choices=SIM_NAO,
        widget=forms.RadioSelect,
        label='Você possui alguma alergia conhecida?',
        error_messages={'required': 'Por favor, responda se possui alergias.'},
    )
    tem_sensibilidade = forms.ChoiceField(
        choices=SIM_NAO,
        widget=forms.RadioSelect,
        label='Possui sensibilidade no couro cabeludo?',
        error_messages={'required': 'Por favor, responda sobre sensibilidade.'},
    )
    usa_medicamentos = forms.ChoiceField(
        choices=SIM_NAO,
        widget=forms.RadioSelect,
        label='Faz uso de medicamentos de uso contínuo?',
        error_messages={'required': 'Por favor, responda sobre medicamentos.'},
    )

    class Meta:
        model = Anamnese
        fields = [
            'tem_alergias', 'alergias_detalhes',
            'tem_sensibilidade', 'sensibilidade_detalhes',
            'procedimentos_anteriores',
            'usa_medicamentos', 'medicamentos_detalhes',
            'preferencias',
            'consentimento_lgpd',
        ]
        widgets = {
            'alergias_detalhes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Ex: alergia a látex, óleo de coco, corantes…',
            }),
            'sensibilidade_detalhes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Ex: couro cabeludo fica irritado com facilidade, dermatite…',
            }),
            'procedimentos_anteriores': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Ex: progressiva há 2 meses, descoloração há 6 meses…',
            }),
            'medicamentos_detalhes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Ex: isotretinoína, anticoagulantes, corticoides…',
            }),
            'preferencias': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Ex: prefiro pressão leve, sem aromaterapia, ambiente silencioso…',
            }),
        }
        error_messages = {
            'consentimento_lgpd': {
                'required': 'Você precisa consentir com o armazenamento dos dados para continuarmos.',
            },
        }

    # ── Conversão de string para bool ─────────────────────────────────────

    def clean_tem_alergias(self):
        return self.cleaned_data['tem_alergias'] == 'True'

    def clean_tem_sensibilidade(self):
        return self.cleaned_data['tem_sensibilidade'] == 'True'

    def clean_usa_medicamentos(self):
        return self.cleaned_data['usa_medicamentos'] == 'True'

    # ── Validações condicionais ───────────────────────────────────────────

    def clean(self):
        cleaned = super().clean()

        if cleaned.get('tem_alergias') and not cleaned.get('alergias_detalhes', '').strip():
            self.add_error('alergias_detalhes', 'Por favor, especifique suas alergias.')

        if cleaned.get('tem_sensibilidade') and not cleaned.get('sensibilidade_detalhes', '').strip():
            self.add_error('sensibilidade_detalhes', 'Por favor, descreva a sensibilidade.')

        if cleaned.get('usa_medicamentos') and not cleaned.get('medicamentos_detalhes', '').strip():
            self.add_error('medicamentos_detalhes', 'Por favor, liste os medicamentos em uso.')

        if not cleaned.get('consentimento_lgpd'):
            self.add_error(
                'consentimento_lgpd',
                'Você precisa consentir com o armazenamento dos dados para continuarmos.',
            )

        return cleaned

    def initial_radio(self, field_name):
        """Retorna 'True'/'False' (string) para pré-preencher os radios no template."""
        val = self.initial.get(field_name)
        if val is None and self.instance and self.instance.pk:
            val = getattr(self.instance, field_name, False)
        return 'True' if val else 'False'
