from django.shortcuts import render, redirect
from django.db import transaction
from django.db.models import Count
from .models import Player, GameState, Scenario, Round, Choice, GameSession

ROLE_INTEREST = {
    'Presidente': 'estabilidade',
    'Lider Militar': 'seguranca',
    'Lider Politico': 'economia',
    'Lider da População': 'liberdade',
}

DEFAULT_PLAYERS = [
    ('Presidente', 'Presidente'),
    ('Lider Militar', 'Lider Militar'),
    ('Lider Politico', 'Lider Politico'),
    ('Lider da População', 'Lider da População'),
]

MAX_ROUNDS = 8


def _init_if_needed():
    """Inicializa jogadores e estado do jogo se necessário"""
    # Criar jogadores se não existirem
    if not Player.objects.exists():
        for name, papel in DEFAULT_PLAYERS:
            Player.objects.create(name=name, papel=papel)
        print("DEBUG: Jogadores criados")

    # Criar estado do jogo se não existir
    if not GameState.objects.exists():
        GameState.objects.create(
            rodada_atual=1,
            estabilidade=5,
            seguranca=5,
            economia=5,
            liberdade=5,
            active=True
        )
        print("DEBUG: GameState criado")
    else:
        gs = GameState.objects.first()
        print(f"DEBUG: GameState existente - ativo: {gs.active}, rodada: {gs.rodada_atual}")
        # NÃO reativar automaticamente - deixar o usuário decidir


def _get_random_scenario_for_round(round_number):
    """Pega um cenário aleatório que ainda não foi usado neste jogo"""
    # Pegar cenários já usados neste jogo
    used_scenarios = Round.objects.values_list('scenario_id', flat=True)

    # Pegar um cenário disponível
    available_scenarios = Scenario.objects.exclude(id__in=used_scenarios)

    if available_scenarios.exists():
        return available_scenarios.order_by('?').first()  # Ordem aleatória
    else:
        # Se todos foram usados, pegar qualquer um (fallback)
        return Scenario.objects.order_by('?').first()


def _save_game_session(gs, players, tipo_comunicacao='SIM'):
    """Salva os dados da sessão quando o jogo termina"""
    # Contar estatísticas
    rounds = Round.objects.all()
    total_consensos = 0
    total_empates = 0

    for round_obj in rounds:
        choices_in_round = Choice.objects.filter(round=round_obj)
        choice_counts = choices_in_round.values('escolha').annotate(count=Count('escolha'))

        if len(choice_counts) == 1:  # Unanimous
            total_consensos += 1
        else:
            # Check if it's a tie
            counts = [item['count'] for item in choice_counts]
            if len(set(counts)) == 1:  # All counts are equal (tie)
                total_empates += 1

    # Determinar status
    if (gs.estabilidade == 1 or gs.seguranca == 1 or
            gs.economia == 1 or gs.liberdade == 1):
        status = 'INTERROMPIDO'
    else:
        status = 'COMPLETO'

    # Preparar dados dos jogadores
    pontuacoes_individuais = {}
    pontuacoes_coletivas = {}
    for player in players:
        pontuacoes_individuais[player.papel] = player.pontuacao_individual
        pontuacoes_coletivas[player.papel] = player.pontuacao_coletiva

    # Criar nome da sessão
    count = GameSession.objects.count() + 1
    tipo_display = 'Com Comunicação' if tipo_comunicacao == 'SIM' else 'Sem Comunicação'
    nome_sessao = f"Sessão {count} - {tipo_display}"

    # Calcular rounds completados corretamente
    rounds_completados = rounds.count()

    # Salvar sessão
    GameSession.objects.create(
        nome_sessao=nome_sessao,
        tipo_comunicacao=tipo_comunicacao,
        status=status,
        rounds_completados=rounds_completados,
        estabilidade_final=gs.estabilidade,
        seguranca_final=gs.seguranca,
        economia_final=gs.economia,
        liberdade_final=gs.liberdade,
        pontuacoes_individuais=pontuacoes_individuais,
        pontuacoes_coletivas=pontuacoes_coletivas,
        total_consensos=total_consensos,
        total_empates=total_empates,
    )

    print(f"DEBUG: Sessão salva - {rounds_completados} rounds completados, status: {status}")


def clamp(v, lo=1, hi=8):
    """Limita valores entre 1 e 8"""
    return max(lo, min(hi, v))


def game_view(request):
    _init_if_needed()
    gs = GameState.objects.first()
    players = list(Player.objects.all())

    # Debug info
    print(f"DEBUG: GameState - active: {gs.active}, rodada: {gs.rodada_atual}")

    # Verificar se o jogo deve continuar
    scenario = None
    if gs.active and gs.rodada_atual <= MAX_ROUNDS:
        scenario = _get_random_scenario_for_round(gs.rodada_atual)
        print(f"DEBUG: Scenario encontrado para rodada {gs.rodada_atual}: {scenario is not None}")

    if request.method == "POST":
        # Verificar se é um reset do jogo
        if request.POST.get('reset_game'):
            # Reset completo do jogo
            with transaction.atomic():
                # Limpar dados do jogo anterior
                Round.objects.all().delete()  # Isso também deleta as Choices devido ao CASCADE

                # Reset dos jogadores
                for p in players:
                    p.pontuacao_individual = 0
                    p.pontuacao_coletiva = 0
                    p.save()

                # Reset do estado do jogo
                gs.active = True
                gs.rodada_atual = 1
                gs.estabilidade = 5
                gs.seguranca = 5
                gs.economia = 5
                gs.liberdade = 5
                gs.save()

                print("DEBUG: Jogo resetado com sucesso")
            return redirect("game:game")

        # Lógica normal do jogo - processar round
        if gs.active and scenario is not None:
            print(f"DEBUG: Processando rodada {gs.rodada_atual}")
            choices = {}
            votes_a = 0
            votes_b = 0

            for p in players:
                key = f"choice_{p.papel}"
                escolha = request.POST.get(key)
                if escolha == "A":
                    votes_a += 1
                elif escolha == "B":
                    votes_b += 1
                choices[p.papel] = escolha

            print(f"DEBUG: Votos A: {votes_a}, Votos B: {votes_b}")

            # Verificar se todas as escolhas foram feitas
            if not all(choices.values()):
                print("DEBUG: Nem todos votaram, retornando erro")
                return render(request, "game/game.html", {
                    "players": players, "gs": gs, "scenario": scenario,
                    "error": "Selecione uma opção (A/B) para todos os jogadores."
                })

            with transaction.atomic():
                # Determinar impacto final baseado na votação
                if votes_a > votes_b:
                    impacto_final = {
                        'estabilidade': scenario.impacto_sim_estabilidade,
                        'seguranca': scenario.impacto_sim_seguranca,
                        'economia': scenario.impacto_sim_economia,
                        'liberdade': scenario.impacto_sim_liberdade,
                    }
                    opcao_vencedora = "A"
                elif votes_b > votes_a:
                    impacto_final = {
                        'estabilidade': scenario.impacto_nao_estabilidade,
                        'seguranca': scenario.impacto_nao_seguranca,
                        'economia': scenario.impacto_nao_economia,
                        'liberdade': scenario.impacto_nao_liberdade,
                    }
                    opcao_vencedora = "B"
                else:  # empate
                    impacto_final = {
                        'estabilidade': scenario.impacto_empate_estabilidade,
                        'seguranca': scenario.impacto_empate_seguranca,
                        'economia': scenario.impacto_empate_economia,
                        'liberdade': scenario.impacto_empate_liberdade,
                    }
                    opcao_vencedora = "E"  # Empate

                # Criar round
                rnd = Round.objects.create(numero=gs.rodada_atual, scenario=scenario)

                # Salvar escolhas e calcular pontuação individual
                for p in players:
                    escolha = choices[p.papel]
                    interest = ROLE_INTEREST[p.papel]
                    aligned = False

                    # Verificar se a escolha está alinhada com o interesse do papel
                    if escolha == "A" and opcao_vencedora == "A":
                        aligned = scenario.__dict__[f"impacto_sim_{interest}"] > 0
                    elif escolha == "B" and opcao_vencedora == "B":
                        aligned = scenario.__dict__[f"impacto_nao_{interest}"] > 0
                    elif escolha in ["A", "B"] and opcao_vencedora == "E":
                        # Em caso de empate, verificar se a escolha individual beneficiaria o interesse
                        if escolha == "A":
                            aligned = scenario.__dict__[f"impacto_sim_{interest}"] > 0
                        else:  # escolha == "B"
                            aligned = scenario.__dict__[f"impacto_nao_{interest}"] > 0

                    pontos = 1 if aligned else 0

                    Choice.objects.create(
                        player=p,
                        round=rnd,
                        escolha=escolha,
                        alinhado=aligned,
                        impacto=impacto_final,
                        pontos_ganhos=pontos
                    )

                    # Atualizar pontuação individual
                    if aligned:
                        p.pontuacao_individual += 1
                        p.save()

                # Aplicar impacto no estado do país
                gs.estabilidade = clamp(gs.estabilidade + impacto_final['estabilidade'])
                gs.seguranca = clamp(gs.seguranca + impacto_final['seguranca'])
                gs.economia = clamp(gs.economia + impacto_final['economia'])
                gs.liberdade = clamp(gs.liberdade + impacto_final['liberdade'])

                print(
                    f"DEBUG: Indicadores após impacto - E:{gs.estabilidade} S:{gs.seguranca} Ec:{gs.economia} L:{gs.liberdade}")

                # Verificar condição para ponto coletivo (todos os indicadores entre 3 e 5)
                if (3 <= gs.estabilidade <= 5 and 3 <= gs.seguranca <= 5 and
                        3 <= gs.economia <= 5 and 3 <= gs.liberdade <= 5):
                    for p in players:
                        p.pontuacao_coletiva += 1
                        p.save()

                # VERIFICAR IMEDIATAMENTE se algum indicador chegou a 1
                if (gs.estabilidade == 1 or gs.seguranca == 1 or
                        gs.economia == 1 or gs.liberdade == 1):
                    gs.active = False
                    gs.save()
                    print("DEBUG: Jogo encerrado IMEDIATAMENTE - indicador chegou a 1")
                    # Salvar sessão e terminar
                    tipo_comunicacao = request.POST.get('tipo_comunicacao_final', 'SIM')
                    _save_game_session(gs, players, tipo_comunicacao)
                    return redirect("game:game")

                # Se chegou até aqui, o jogo continua - avançar rodada
                gs.rodada_atual += 1
                print(f"DEBUG: Rodada processada: {gs.rodada_atual - 1}, avançando para: {gs.rodada_atual}")

                # Verificar se completou 6 rounds
                if gs.rodada_atual > MAX_ROUNDS:
                    gs.active = False
                    print("DEBUG: Jogo encerrado - 6 rounds completados")
                    # Salvar sessão
                    tipo_comunicacao = request.POST.get('tipo_comunicacao_final', 'SIM')
                    _save_game_session(gs, players, tipo_comunicacao)

                gs.save()

            return redirect("game:game")

    # GET -> renderizar a tela do jogo
    context = {
        "players": players,
        "gs": gs,
        "scenario": scenario,
        "max_rounds": MAX_ROUNDS,
    }

    # Determinar motivo do fim se o jogo terminou
    if not gs.active:
        if (gs.estabilidade == 1 or gs.seguranca == 1 or
                gs.economia == 1 or gs.liberdade == 1):
            context["end_reason"] = "collapse"
        else:
            context["end_reason"] = "completed"

    return render(request, "game/game.html", context)