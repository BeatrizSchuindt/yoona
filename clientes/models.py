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

    @property
    def cpf_mascarado(self):
        """CPF mascarado para exibição (LGPD). Ex: ***.434.671-**"""
        d = self.cpf_numeros
        if len(d) != 11:
            return self.cpf
        return f'***.{d[3:6]}.{d[6:9]}-**'

    @property
    def telefone_whatsapp(self):
        """Telefone só com dígitos e código do Brasil para link wa.me. None se inválido."""
        d = ''.join(filter(str.isdigit, self.telefone))
        return f'55{d}' if len(d) >= 10 else None


class Anamnese(models.Model):
    """
    Ficha de saúde capilar vinculada 1:1 ao cliente.
    Preenchida após o primeiro agendamento; pode ser atualizada em visitas posteriores.
    """

    cliente = models.OneToOneField(
        Cliente,
        on_delete=models.CASCADE,
        related_name='anamnese',
        verbose_name='Cliente',
    )

    # ── Alergias ──────────────────────────────────────────────────────────
    tem_alergias = models.BooleanField(
        default=False,
        verbose_name='Possui alergias?',
    )
    alergias_detalhes = models.TextField(
        blank=True,
        verbose_name='Quais alergias?',
        help_text='Cosméticos, óleos essenciais, látex etc.',
    )

    # ── Sensibilidade no couro cabeludo ───────────────────────────────────
    tem_sensibilidade = models.BooleanField(
        default=False,
        verbose_name='Possui sensibilidade no couro cabeludo?',
    )
    sensibilidade_detalhes = models.TextField(
        blank=True,
        verbose_name='Detalhes da sensibilidade',
        help_text='Descreva quando/como ocorre.',
    )

    # ── Procedimentos químicos recentes ───────────────────────────────────
    procedimentos_anteriores = models.TextField(
        blank=True,
        verbose_name='Procedimentos químicos recentes',
        help_text='Alisamentos, descolorações, tinturas — e há quanto tempo.',
    )

    # ── Medicamentos contínuos ────────────────────────────────────────────
    usa_medicamentos = models.BooleanField(
        default=False,
        verbose_name='Usa medicamentos de uso contínuo?',
    )
    medicamentos_detalhes = models.TextField(
        blank=True,
        verbose_name='Quais medicamentos?',
    )

    # ── Preferências ──────────────────────────────────────────────────────
    preferencias = models.TextField(
        blank=True,
        verbose_name='Preferências e observações adicionais',
        help_text='Pressão da massagem, aromas preferidos, silêncio etc.',
    )

    # ── LGPD ──────────────────────────────────────────────────────────────
    consentimento_lgpd = models.BooleanField(
        default=False,
        verbose_name='Consentimento LGPD',
    )

    data_preenchimento = models.DateTimeField(auto_now_add=True, verbose_name='Preenchido em')
    data_atualizacao   = models.DateTimeField(auto_now=True,     verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Anamnese'
        verbose_name_plural = 'Anamneses'

    def __str__(self):
        return f'Anamnese de {self.cliente.nome_completo}'
