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

    # TOdo: verificar validações depois
    def clean_preco_base(self):
        preco = self.cleaned_data.get('preco_base')
        if preco and preco < 0:
            raise forms.ValidationError("O preço base não pode ser um valor negativo.")
        return preco