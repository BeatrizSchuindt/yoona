from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import Terapeuta


# ---------------------------------------------------------------------------
# Cadastro: cria User (login) + Terapeuta em uma operação atômica
# ---------------------------------------------------------------------------

class TerapeutaCreateForm(forms.ModelForm):
    """
    Formulário de cadastro de terapeuta que também cria o usuário de acesso.
    O User é criado em TerapeutaCreateView dentro de transaction.atomic().
    """

    username = forms.CharField(
        max_length=150,
        label='Nome de usuário (login)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        error_messages={'required': 'Informe um nome de usuário para o login.'},
    )
    email = forms.EmailField(
        required=False,
        label='E-mail (opcional)',
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        error_messages={'invalid': 'Informe um e-mail válido.'},
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        error_messages={'required': 'Defina uma senha para o login.'},
    )

    class Meta:
        model = Terapeuta
        fields = ['nome_terapeuta', 'percentual_comissao', 'ativo']
        widgets = {
            'nome_terapeuta': forms.TextInput(attrs={'class': 'form-control'}),
            'percentual_comissao': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100',
            }),
        }
        error_messages = {
            'nome_terapeuta': {'required': 'Informe o nome profissional do terapeuta.'},
        }

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Este nome de usuário já está em uso.')
        return username

    def clean_percentual_comissao(self):
        pct = self.cleaned_data.get('percentual_comissao')
        if pct is not None and (pct < 0 or pct > 100):
            raise forms.ValidationError('O percentual deve estar entre 0 e 100.')
        return pct

    def clean_password(self):
        senha = self.cleaned_data.get('password')
        if senha:
            try:
                validate_password(senha)
            except DjangoValidationError as e:
                raise forms.ValidationError(list(e.messages))
        return senha

    def save(self, commit=True):
        terapeuta = super().save(commit=False)
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data.get('email', ''),
            password=self.cleaned_data['password'],
        )
        terapeuta.usuario = user
        if commit:
            terapeuta.save()
        return terapeuta


# ---------------------------------------------------------------------------
# Edição: login imutável; senha opcional (em branco = mantém a atual)
# ---------------------------------------------------------------------------

class TerapeutaUpdateForm(forms.ModelForm):
    """
    Edição de terapeuta. O nome de usuário não é editável.
    'nova_senha' em branco mantém a senha atual.
    """

    email = forms.EmailField(
        required=False,
        label='E-mail (opcional)',
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        error_messages={'invalid': 'Informe um e-mail válido.'},
    )
    nova_senha = forms.CharField(
        required=False,
        label='Nova senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        help_text='Deixe em branco para manter a senha atual.',
    )

    class Meta:
        model = Terapeuta
        fields = ['nome_terapeuta', 'percentual_comissao', 'ativo']
        widgets = {
            'nome_terapeuta': forms.TextInput(attrs={'class': 'form-control'}),
            'percentual_comissao': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100',
            }),
        }
        error_messages = {
            'nome_terapeuta': {'required': 'Informe o nome profissional do terapeuta.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.usuario_id:
            self.fields['email'].initial = self.instance.usuario.email

    def clean_percentual_comissao(self):
        pct = self.cleaned_data.get('percentual_comissao')
        if pct is not None and (pct < 0 or pct > 100):
            raise forms.ValidationError('O percentual deve estar entre 0 e 100.')
        return pct

    def clean_nova_senha(self):
        senha = self.cleaned_data.get('nova_senha')
        if senha:
            try:
                validate_password(senha, self.instance.usuario)
            except DjangoValidationError as e:
                raise forms.ValidationError(list(e.messages))
        return senha

    def save(self, commit=True):
        terapeuta = super().save(commit=commit)
        user = terapeuta.usuario
        user.email = self.cleaned_data.get('email', '')
        nova = self.cleaned_data.get('nova_senha')
        if nova:
            user.set_password(nova)
        if commit:
            user.save()
        return terapeuta
