from django.db import models


class Cliente(models.Model):
    """
    Representa um cliente identificado pelo CPF
    Não possui login — a identificação é feita pelo CPF no momento do agendamento
    """
    cpf = models.CharField(
        max_length=14,
        unique=True,
        verbose_name='CPF',
        help_text='Formato: 000.000.000-00',
    )
    nome_completo = models.CharField(max_length=150, verbose_name='Nome completo')
    telefone = models.CharField(max_length=20, verbose_name='Telefone / WhatsApp')
    data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de cadastro')

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nome_completo']

    def __str__(self):
        return f'{self.nome_completo} ({self.cpf})'

    @property
    def cpf_numeros(self):
        """Retorna CPF somente com dígitos"""
        return ''.join(filter(str.isdigit, self.cpf))


class Anamnese(models.Model):
    """
    Ficha de saúde capilar/anamnese vinculada a um cliente
    Preenchida uma vez após o primeiro agendamento e pode ser atualizada.
    """
    SENSIBILIDADE_CHOICES = [
        ('normal',     'Normal (sem incômodos frequentes)'),
        ('sensivel',   'Sensível (fica irritado com facilidade)'),
        ('dermatite',  'Dermatite, descamação ou caspa ativa'),
        ('dor',        'Sinto dor ao toque ou ao prender o cabelo'),
    ]

    cliente = models.OneToOneField(
        Cliente,
        on_delete=models.CASCADE,
        related_name='anamnese',
        verbose_name='Cliente',
    )
    alergias = models.TextField(
        blank=True,
        verbose_name='Alergias conhecidas',
        help_text='Cosméticos, óleos essenciais, látex etc. Deixe em branco se não houver.',
    )
    sensibilidades = models.CharField(
        max_length=20,
        choices=SENSIBILIDADE_CHOICES,
        default='normal',
        verbose_name='Sensibilidade do couro cabeludo',
    )
    procedimentos_anteriores = models.TextField(
        blank=True,
        verbose_name='Procedimentos químicos anteriores',
        help_text='Alisamentos, descolorações, tinturas — e há quanto tempo.',
    )
    preferencias = models.TextField(
        blank=True,
        verbose_name='Preferências de atendimento',
        help_text='Pressão da massagem, aromas preferidos, silêncio etc.',
    )
    consentimento_lgpd = models.BooleanField(
        default=False,
        verbose_name='Consentimento LGPD',
        help_text='Cliente autorizou o armazenamento dos dados de saúde capilar.',
    )
    data_preenchimento = models.DateTimeField(auto_now_add=True, verbose_name='Preenchido em')
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Anamnese'
        verbose_name_plural = 'Anamneses'

    def __str__(self):
        return f'Anamnese de {self.cliente.nome_completo}'
