from django import forms
from .models import Cliente

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
