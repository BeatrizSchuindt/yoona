from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Terapeuta(models.Model):
    """
    Perfil profissional vinculado a um usuário do sistema
    O login é feito pelo User do Django (is_staff=False)
    Este model armazena os dados de negócio do profissional
    """
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='terapeuta',
        verbose_name='Usuário do sistema',
    )
    nome_terapeuta = models.CharField(
        max_length=150,
        verbose_name='Nome profissional',
        help_text='Nome exibido nos agendamentos e comissões.',
    )
    percentual_comissao = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Percentual de comissão (%)',
        help_text='Ex: 30.00 para 30%. Usado no cálculo automático ao concluir o atendimento.',
        validators=[
            MinValueValidator(0, message='O percentual não pode ser negativo.'),
            MaxValueValidator(100, message='O percentual não pode ultrapassar 100%.'),
        ],
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo',
        help_text='Terapeutas inativos não aparecem na lista de vínculo de agendamentos.',
    )
    data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Cadastrado em')

    class Meta:
        verbose_name = 'Terapeuta'
        verbose_name_plural = 'Terapeutas'
        ordering = ['nome_terapeuta']

    def __str__(self):
        return self.nome_terapeuta

    @property
    def percentual_decimal(self):
        """Retorna o percentual como fração decimal. Ex: 30.00 para 0.30"""
        return self.percentual_comissao / 100
