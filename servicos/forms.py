from django import forms
from .models import Servico

class ServicoForm(forms.ModelForm):
    """
    Formulário para criação e edição de terapias e serviços.
    Utiliza ModelForm para herdar validações e metadados do modelo Servico.
    """
    class Meta:
        model = Servico
        fields = ['nome', 'descricao', 'duracao', 'preco_base', 'imagem', 'ativo']
        
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Massagem Terapêutica'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descreva detalhadamente os benefícios e etapas do serviço...'
            }),
            'duracao': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tempo em minutos (ex: 60)'
            }),
            'preco_base': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'imagem': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'ativo': forms.Select(attrs={
                'class': 'form-control',
            }, choices=[(True, 'Ativo'), (False, 'Inativo')]),
        }

        error_messages = {
            'nome': {
                'required':   'O nome da terapia é obrigatório.',
                'max_length': 'O nome não pode ultrapassar 100 caracteres.',
            },
            'descricao': {
                'required': 'A descrição da terapia é obrigatória.',
            },
            'duracao': {
                'required': 'A duração é obrigatória.',
                'invalid':  'Informe um número inteiro de minutos (ex: 60).',
            },
            'preco_base': {
                'required': 'O preço base é obrigatório.',
                'invalid':  'Informe um valor monetário válido (ex: 120.00).',
            },
            'imagem': {
                'invalid_image': (
                    'Envie uma imagem válida. '
                    'O arquivo enviado não é uma imagem ou está corrompido.'
                ),
            },
        }

    def clean_duracao(self):
        duracao = self.cleaned_data.get('duracao')
        if duracao is not None and duracao <= 0:
            raise forms.ValidationError('A duração deve ser maior que zero.')
        return duracao

    def clean_preco_base(self):
        preco = self.cleaned_data.get('preco_base')
        if preco is not None and preco < 0:
            raise forms.ValidationError('O preço base não pode ser um valor negativo.')
        return preco