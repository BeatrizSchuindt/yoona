from django.db import models
from django.core.validators import MinValueValidator
from clientes.models import Cliente
from servicos.models import Servico
from terapeutas.models import Terapeuta


class Voucher(models.Model):
    """
    Cupom de desconto aplicável ao agendamento
    O desconto pode ser percentual (10%) ou fixo (R$ 20,00)
    """
    TIPO_CHOICES = [
        ('percentual', 'Percentual (%)'),
        ('fixo',       'Valor fixo (R$)'),
    ]
    STATUS_CHOICES = [
        ('ativo',   'Ativo'),
        ('inativo', 'Inativo'),
    ]

    codigo_promocional = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='Código promocional',
        help_text='Código que o cliente digita. Ex: YOONA10',
    )
    tipo_desconto = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        verbose_name='Tipo de desconto',
    )
    valor_desconto = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Valor do desconto',
        help_text='Para percentual: ex. 10.00 = 10%. Para fixo: ex. 20.00 = R$ 20,00.',
        validators=[MinValueValidator(0)],
    )
    status_voucher = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ativo',
        verbose_name='Status',
    )
    limite_uso = models.PositiveIntegerField(
        verbose_name='Limite de usos',
        help_text='Quantas vezes este voucher pode ser utilizado no total.',
    )
    usos_realizados = models.PositiveIntegerField(
        default=0,
        verbose_name='Usos realizados',
        help_text='Contador atualizado automaticamente a cada uso.',
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Voucher'
        verbose_name_plural = 'Vouchers'
        ordering = ['-data_criacao']

    def __str__(self):
        return f'{self.codigo_promocional} ({self.get_tipo_desconto_display()})'

    @property
    def disponivel(self):
        """True se o voucher está ativo e ainda tem disponíveis"""
        return self.status_voucher == 'ativo' and self.usos_realizados < self.limite_uso

    @property
    def usos_restantes(self):
        return max(0, self.limite_uso - self.usos_realizados)

    def calcular_desconto(self, valor_original):
        """
        Calcula o valor do desconto sobre um valor original
        Retorna o valor a descontar (nunca maior que o valor original)
        """
        if self.tipo_desconto == 'percentual':
            desconto = valor_original * (self.valor_desconto / 100)
        else:
            desconto = self.valor_desconto
        return min(desconto, valor_original)


class Agendamento(models.Model):
    """
    Registro central de um atendimento — desde a solicitação até a conclusão
    """
    STATUS_CHOICES = [
        ('aguardando',  'Aguardando'),
        ('confirmado',  'Confirmado'),
        ('concluido',   'Concluído'),
        ('cancelado',   'Cancelado'),
    ]
    PAGAMENTO_CHOICES = [
        ('pix',      'PIX'),
        ('credito',  'Cartão de Crédito'),
        ('debito',   'Cartão de Débito'),
        ('dinheiro', 'Dinheiro'),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='agendamentos',
        verbose_name='Cliente',
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.PROTECT,
        related_name='agendamentos',
        verbose_name='Serviço',
    )
    terapeuta = models.ForeignKey(
        Terapeuta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agendamentos',
        verbose_name='Terapeuta',
        help_text='Vinculado pelo administrador após o agendamento.',
    )
    voucher = models.ForeignKey(
        Voucher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agendamentos',
        verbose_name='Voucher',
    )
    data_agendamento = models.DateField(verbose_name='Data')
    horario_agendamento = models.TimeField(verbose_name='Horário')
    metodo_pagamento = models.CharField(
        max_length=10,
        choices=PAGAMENTO_CHOICES,
        default='pix',
        verbose_name='Método de pagamento',
        help_text='Forma de pagamento escolhida pelo cliente no ato do agendamento.',
    )
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default='aguardando',
        verbose_name='Status',
    )
    valor_final = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor final (R$)',
        help_text='Preenchido automaticamente ao concluir o atendimento.',
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
        ordering = ['data_agendamento', 'horario_agendamento']

    def __str__(self):
        return (
            f'{self.cliente.nome_completo} — '
            f'{self.servico.nome} em '
            f'{self.data_agendamento:%d/%m/%Y} às {self.horario_agendamento:%H:%M}'
        )

    @property
    def valor_base(self):
        """Preço do serviço sem desconto"""
        return self.servico.preco_base

    def calcular_valor_final(self):
        """
        Calcula o valor final aplicando o voucher, se houver
        Retorna o valor a cobrar
        """
        valor = self.servico.preco_base
        if self.voucher and self.voucher.disponivel:
            valor -= self.voucher.calcular_desconto(valor)
        return max(valor, 0)


class BloqueioAgenda(models.Model):
    """
    Datas ou dias da semana em que o spa não atende.
    O admin configura via painel — o calendário de agendamento respeita esses bloqueios.
    """
    TIPO_CHOICES = [
        ('dia_semana', 'Dia da semana (recorrente)'),
        ('data',       'Data específica'),
    ]
    # Segue a convenção do Python: weekday() → 0=Segunda … 6=Domingo
    DIAS_SEMANA = [
        (0, 'Segunda-feira'), (1, 'Terça-feira'), (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),  (4, 'Sexta-feira'), (5, 'Sábado'), (6, 'Domingo'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, verbose_name='Tipo')
    dia_semana = models.SmallIntegerField(
        null=True, blank=True, choices=DIAS_SEMANA, verbose_name='Dia da semana',
    )
    data = models.DateField(null=True, blank=True, verbose_name='Data específica')
    motivo = models.CharField(max_length=120, blank=True, verbose_name='Motivo / Descrição')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bloqueio de Agenda'
        verbose_name_plural = 'Bloqueios de Agenda'
        ordering = ['tipo', 'dia_semana', 'data']

    def __str__(self):
        if self.tipo == 'dia_semana':
            nome_dia = dict(self.DIAS_SEMANA).get(self.dia_semana, '?')
            return f'Todo(a) {nome_dia} — {self.motivo or "sem motivo"}'
        return f'{self.data:%d/%m/%Y} — {self.motivo or "sem motivo"}'


class Comissao(models.Model):
    """
    Registro financeiro gerado ao concluir um atendimento
    Uma vez criada, não pode ser alterada
    """
    agendamento = models.OneToOneField(
        Agendamento,
        on_delete=models.PROTECT,
        related_name='comissao',
        verbose_name='Agendamento',
    )
    terapeuta = models.ForeignKey(
        Terapeuta,
        on_delete=models.PROTECT,
        related_name='comissoes',
        verbose_name='Terapeuta',
    )
    valor_calculado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor da comissão (R$)',
        help_text='Calculado como: valor_final × percentual_comissao.',
    )
    data_registro = models.DateTimeField(auto_now_add=True, verbose_name='Registrado em')

    class Meta:
        verbose_name = 'Comissão'
        verbose_name_plural = 'Comissões'
        ordering = ['-data_registro']

    def __str__(self):
        return (
            f'Comissão de {self.terapeuta} — '
            f'R$ {self.valor_calculado} '
            f'({self.data_registro:%d/%m/%Y})'
        )

    def save(self, *args, **kwargs):
        """Impede qualquer alteração após o primeiro save"""
        if self.pk:
            raise ValueError(
                'Comissões são imutáveis. '
                'Um registro de comissão não pode ser alterado após criado.'
            )
        super().save(*args, **kwargs)
