from django.db import models
from django.utils import timezone


class Player(models.Model):
    name = models.CharField(max_length=100)
    papel = models.CharField(max_length=100)  # ex: 'Presidente'
    pontuacao_individual = models.IntegerField(default=0)
    pontuacao_coletiva = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.papel}"


class GameSession(models.Model):
    """
    Salva os dados de um jogo completo após o término
    """
    COMUNICACAO_CHOICES = [
        ('SIM', 'Com Comunicação'),
        ('NAO', 'Sem Comunicação'),
    ]

    STATUS_CHOICES = [
        ('COMPLETO', 'Completado (6 rounds)'),
        ('INTERROMPIDO', 'Interrompido (colapso)'),
    ]

    # Identificação
    nome_sessao = models.CharField(max_length=200, verbose_name="Nome da Sessão")
    tipo_comunicacao = models.CharField(
        max_length=3,
        choices=COMUNICACAO_CHOICES,
        verbose_name="Tipo de Comunicação"
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        verbose_name="Status"
    )

    # Resultados finais
    rounds_completados = models.IntegerField(verbose_name="Rounds Completados")
    estabilidade_final = models.IntegerField(verbose_name="Estabilidade Final")
    seguranca_final = models.IntegerField(verbose_name="Segurança Final")
    economia_final = models.IntegerField(verbose_name="Economia Final")
    liberdade_final = models.IntegerField(verbose_name="Liberdade Final")

    # Estatísticas dos jogadores (JSON para simplicidade)
    pontuacoes_individuais = models.JSONField(verbose_name="Pontuações Individuais")
    pontuacoes_coletivas = models.JSONField(verbose_name="Pontuações Coletivas")

    # Estatísticas do jogo
    total_consensos = models.IntegerField(default=0, verbose_name="Total de Consensos")
    total_empates = models.IntegerField(default=0, verbose_name="Total de Empates")

    # Metadata
    criado_em = models.DateTimeField(default=timezone.now, verbose_name="Criado em")
    observacoes = models.TextField(blank=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Sessão de Jogo"
        verbose_name_plural = "Sessões de Jogo"
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.nome_sessao} ({self.get_tipo_comunicacao_display()})"


class Scenario(models.Model):
    par = models.CharField(max_length=50, blank=True, null=True)
    codigo = models.CharField(max_length=20, unique=True)
    numero = models.IntegerField()  # ordem do cenário
    titulo = models.CharField(max_length=200)
    contexto = models.TextField()
    dilema = models.TextField()

    # impactos da opção SIM (A)
    impacto_sim_estabilidade = models.IntegerField()
    impacto_sim_seguranca = models.IntegerField()
    impacto_sim_economia = models.IntegerField()
    impacto_sim_liberdade = models.IntegerField()

    # impactos da opção NÃO (B)
    impacto_nao_estabilidade = models.IntegerField()
    impacto_nao_seguranca = models.IntegerField()
    impacto_nao_economia = models.IntegerField()
    impacto_nao_liberdade = models.IntegerField()

    # impactos do EMPATE
    impacto_empate_estabilidade = models.IntegerField()
    impacto_empate_seguranca = models.IntegerField()
    impacto_empate_economia = models.IntegerField()
    impacto_empate_liberdade = models.IntegerField()

    tema = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        ordering = ["numero"]

    def __str__(self):
        return f"{self.codigo} - {self.titulo}"


class GameState(models.Model):
    rodada_atual = models.IntegerField(default=1)
    estabilidade = models.IntegerField(default=3)
    seguranca = models.IntegerField(default=3)
    economia = models.IntegerField(default=3)
    liberdade = models.IntegerField(default=3)
    active = models.BooleanField(default=True)  # se False => terminou

    updated_at = models.DateTimeField(auto_now=True)


class Round(models.Model):
    numero = models.IntegerField()
    scenario = models.ForeignKey(Scenario, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class Choice(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    escolha = models.CharField(max_length=1, choices=(("A", "A"), ("B", "B")))
    alinhado = models.BooleanField(default=False)
    impacto = models.JSONField(null=True, blank=True)
    pontos_ganhos = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)