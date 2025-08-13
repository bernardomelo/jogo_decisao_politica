from django.contrib import admin
from .models import Player, GameState, Scenario, Round, Choice, GameSession


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = [
        'nome_sessao',
        'status',
        'rounds_completados',
        'total_consensos',
        'total_empates',
        'criado_em'
    ]
    list_filter = ['tipo_comunicacao', 'status', 'criado_em']
    search_fields = ['nome_sessao', 'observacoes']
    readonly_fields = ['criado_em']

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome_sessao', 'tipo_comunicacao', 'status', 'criado_em')
        }),
        ('Resultados do Jogo', {
            'fields': (
                'rounds_completados',
                ('estabilidade_final', 'seguranca_final'),
                ('economia_final', 'liberdade_final')
            )
        }),
        ('Pontuações dos Jogadores', {
            'fields': ('pontuacoes_individuais', 'pontuacoes_coletivas'),
            'classes': ('collapse',)
        }),
        ('Estatísticas', {
            'fields': ('total_consensos', 'total_empates')
        }),
        ('Observações', {
            'fields': ('observacoes',),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + [
                'tipo_comunicacao', 'status', 'rounds_completados',
                'estabilidade_final', 'seguranca_final', 'economia_final', 'liberdade_final',
                'pontuacoes_individuais', 'pontuacoes_coletivas',
                'total_consensos', 'total_empates'
            ]
        return self.readonly_fields


# Manter os admins existentes
@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['name', 'papel', 'pontuacao_individual', 'pontuacao_coletiva']


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'titulo', 'numero', 'tema']
    list_filter = ['tema']
    ordering = ['numero']


@admin.register(GameState)
class GameStateAdmin(admin.ModelAdmin):
    list_display = ['rodada_atual', 'estabilidade', 'seguranca', 'economia', 'liberdade', 'active']


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ['numero', 'scenario', 'created_at']
    list_filter = ['created_at']


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['player', 'round', 'escolha', 'alinhado', 'pontos_ganhos']
    list_filter = ['escolha', 'alinhado', 'round__numero']