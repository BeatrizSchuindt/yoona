from django.db import models

class Servico(models.Model):
    nome = models.CharField(
        max_length=100, 
        verbose_name="Nome do Tratamento"
    )
    descricao = models.TextField(
        verbose_name="Descrição Detalhada"
    )
    duracao = models.IntegerField(
        help_text="Duração em minutos", 
        verbose_name="Duração Estimada"
    )
    preco_base = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Preço Base"
    )
    imagem = models.ImageField(
        upload_to='servicos/imagens/', 
        help_text="Apenas imagens com resolução 16:9", 
        verbose_name="Imagem do Serviço",
        null=True, 
        blank=True
    )
    ativo = models.BooleanField(
        default=True, 
        verbose_name="Status de Disponibilidade"
    )

    class Meta:
        verbose_name = "Terapia/Serviço"
        verbose_name_plural = "Terapias e Serviços"
        ordering = ['nome'] 

    def __str__(self):
        return f"{self.nome} - R$ {self.preco_base}"