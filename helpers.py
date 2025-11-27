import math
from typing import Tuple, Dict, Any

# ==============================================================================
# GRUPO 1: ENGENHARIA NAVAL E ARRANJO (HELPER FUNCTIONS)
# ==============================================================================

def calcular_peso_leve_balsa(
    comp: float, 
    boca: float, 
    pontal: float
) -> float:
    """
    Estima o peso leve (Lightweight) de uma balsa graneleira fluvial.

    Utiliza uma regressão linear baseada no "número cúbico" (L * B * H) da embarcação,
    derivada de dados históricos de projetos aprovados pelo FMM (Fundo da Marinha Mercante)
    para a região Amazônica.

    Parâmetros:
        comp (float): Comprimento total da balsa (m).
        boca (float): Boca moldada da balsa (m).
        pontal (float): Pontal moldado da balsa (m).

    Retorna:
        float: O peso leve estimado da balsa em toneladas.

    Nota de Uso:
        Utilizada em `engine.calcular_opex_variavel` para determinar o deslocamento vazio
        e em `engine.calcular_capex` como base para o custo de construção (o custo do aço
        é proporcional ao peso leve).
    """
    # O termo (comp * boca * pontal) / 1000 é o "Número Cúbico" (Cn) normalizado.
    # Os coeficientes (18.85... e 112.86...) foram obtidos via regressão linear 
    # de uma base de dados de balsas padrão Mississippi/Amazônia.
    # Peso Leve = Intercepto + Inclinação * Cn
    return 18.858037300571 + 112.865401771503 * (comp * boca * pontal / 1000.0)

def calcular_volume_operacional_balsa(
    comp: float, 
    boca: float, 
    calado: float, 
    coef_bloco: float
) -> float:
    """
    Calcula o volume deslocado de carena de uma balsa em condição operacional.

    Baseia-se na geometria básica do casco, ajustada pelo Coeficiente de Bloco (Cb),
    que representa a "finura" ou "cheio" do casco em relação a um paralelepípedo.

    Parâmetros:
        comp (float): Comprimento na linha d'água (m).
        boca (float): Boca na linha d'água (m).
        calado (float): Calado operacional atual (m).
        coef_bloco (float): Coeficiente de bloco (adimensional, tipicamente 0.85-0.95 para balsas).

    Retorna:
        float: Volume deslocado em metros cúbicos (m³).

    Nota de Uso:
        Fundamental em `engine.py` para converter o calado (limitado pelo rio) 
        em capacidade de carga física (Princípio de Arquimedes).
    """
    # Volume = L * B * T * Cb
    # Para balsas de fundo chato (tipo caixa), o Cb é alto (~0.90 ou mais).
    return comp * boca * calado * coef_bloco

def calcular_capacidade_carga_balsa(
    volume_deslocado: float, 
    peso_leve: float,
    densidade_agua: float = 1.0
) -> float:
    """
    Determina a capacidade de carga líquida (Deadweight Cargo) de uma balsa.

    Aplica o Princípio de Arquimedes: o deslocamento total (peso da água deslocada)
    deve ser igual ao peso total da embarcação (Peso Leve + Carga).

    Parâmetros:
        volume_deslocado (float): Volume submerso do casco (m³).
        peso_leve (float): Peso da estrutura vazia da balsa (t).
        densidade_agua (float, opcional): Densidade da água em t/m³. 
                                          Padrão 1.0 para água doce.

    Retorna:
        float: Capacidade de carga em toneladas (t). Retorna 0.0 se o peso leve exceder o deslocamento.

    Nota de Uso:
        Usada em `engine.calcular_opex_variavel` para definir a receita potencial (carga transportada)
        em função do calado disponível no mês.
    """
    deslocamento_total = volume_deslocado * densidade_agua
    capacidade = deslocamento_total - peso_leve
    
    # Proteção contra valores negativos caso o calado seja insuficiente para flutuar a balsa vazia
    return max(0.0, capacidade)

# def calcular_arranjo_comboio(
#     comp_balsa: float,
#     boca_balsa: float,
#     raio_curvatura_rio: float,
#     largura_canal_rio: float
# ) -> Tuple[int, int]:
#     """
#     Define a formação ótima do comboio (nº de balsas longitudinais x transversais)
#     respeitando as restrições geométricas da via navegável.

#     Parâmetros:
#         comp_balsa (float): Comprimento unitário da balsa (m).
#         boca_balsa (float): Boca unitária da balsa (m).
#         raio_curvatura_rio (float): Raio da curva mais restritiva do trecho (m).
#         largura_canal_rio (float): Largura útil do canal de navegação (m).

#     Retorna:
#         Tuple[int, int]: Um par (num_longitudinal, num_paralela) representando o arranjo.

#     Nota de Uso:
#         Chamada por `engine.calcular_custos_comboio` e `analysis.run_global_optimization`
#         para dimensionar a frota antes de calcular a hidrodinâmica.
#     """
#     # Restrição 1: Comprimento do Comboio (L_max)
#     # Regra prática: O comprimento total rígido não deve exceder R/5 para garantir a inscrição na curva.
#     # (Ref: PIANC / Normas da Marinha para navegação interior)
#     l_max_comboio = raio_curvatura_rio / 5.0
    
#     # Restrição 2: Largura do Comboio (B_max)
#     # A largura total deve ser menor que a largura do canal (excluindo margens de segurança implícitas aqui).
#     b_max_comboio = largura_canal_rio
    
#     # Cálculo do número máximo teórico de balsas em cada dimensão
#     # Usa-se divisão inteira (floor) pois não existe meia balsa.
#     n_long_max = math.floor(l_max_comboio / comp_balsa)
#     n_par_max = math.floor(b_max_comboio / boca_balsa)
    
#     # Regra de Estabilidade e Navegabilidade:
#     # Evitar comboios muito "largos e curtos" que são instáveis direcionalmente.
#     # A regra abaixo prioriza a formação longitudinal até que a relação L/B fique equilibrada,
#     # mas permite expansão lateral se o rio for largo.
#     # Lógica simplificada: Tenta manter n_long >= n_par se possível, ou preenche o retângulo permitido.
    
#     # Aqui adotamos a estratégia de maximizar a capacidade dentro do retângulo permitido (L_max * B_max).
#     # Em uma implementação mais complexa, verificaríamos a resistência ao avanço para cada arranjo.
    
#     # Garante pelo menos 1 balsa se as dimensões permitirem
#     n_long = max(1, n_long_max)
#     n_par = max(1, n_par_max)
    
#     return int(n_long), int(n_par)

def calcular_arranjo_comboio(
    comp_balsa: float,
    boca_balsa: float,
    raio_curvatura_rio: float,
    largura_canal_rio: float
) -> Tuple[int, int]:
    """
    Determina a formação ótima (N_longitudinal x N_paralela) baseada nas
    restrições físicas da hidrovia (Raio e Largura).
    
    Retorna:
        (num_balsas_longitudinal, num_balsas_paralela)
    """
    # Restrições geométricas empíricas
    l_max_permitido = raio_curvatura_rio / 5.0
    b_max_permitido = largura_canal_rio
    
    n_long_teorico = l_max_permitido / comp_balsa if l_max_permitido / comp_balsa <= 7 else 7
    n_par_teorico = b_max_permitido / boca_balsa if b_max_permitido / boca_balsa <= 5 else 5
    
    num_long = math.floor(n_long_teorico)
    if num_long < 1: num_long = 1
    
    # Regra heurística: Evitar comboios "mais largos que compridos" se possível,
    # mas respeitando a largura do canal.
    razao_aspecto = num_long / n_par_teorico
    
    if razao_aspecto < 1.0:
        # Se for ficar muito "quadrado" ou largo, limita pelo comprimento
        num_par = num_long + 1
    else:
        num_par = math.floor(n_par_teorico)
        
    if num_par < 1: num_par = 1
    
    return int(num_long), int(num_par)


# ==============================================================================
# GRUPO 2: ENGENHARIA DE CUSTOS E MATEMÁTICA FINANCEIRA
# ==============================================================================

def estimar_custo_construcao_balsa(peso_leve_ton: float) -> float:
    """
    Estima o custo de construção de uma balsa graneleira (unidade).

    O modelo utiliza uma regressão linear onde o peso leve (aço) é a variável
    explicativa preponderante para o custo de estaleiro. Os coeficientes foram
    calibrados com dados de mercado da região Norte e projetos do FMM.

    Parâmetros:
        peso_leve_ton (float): Peso leve da embarcação em toneladas.

    Retorna:
        float: Custo estimado de construção em Reais (R$).

    Nota de Uso:
        Chamada por `engine.calcular_capex` para compor o investimento inicial 
        das balsas.
    """
    # Coeficientes de regressão linear (Custo = Alpha * Peso + Beta)
    # Alpha (R$/ton): Custo marginal do aço processado e mão de obra associada.
    # Beta (R$): Custos fixos de projeto, lançamento e acabamento básico.
    return 7182.1661 * peso_leve_ton + 144536.9815

def estimar_custo_construcao_empurrador(bhp_instalado: float) -> float:
    """
    Estima o custo de construção de um empurrador fluvial.

    Aplica um modelo paramétrico baseado na potência instalada (BHP), que é
    o principal direcionador de custo para este tipo de embarcação (motores,
    eixos, redutores, hélices e sistemas auxiliares representam a maior fatia).

    Parâmetros:
        bhp_instalado (float): Potência total dos motores principais (Brake Horsepower).

    Retorna:
        float: Custo estimado de construção em Reais (R$).

    Nota de Uso:
        Chamada por `engine.calcular_capex`. Esta função é fundamental para a 
        análise de trade-off (Otimização Global), pois traduz a "necessidade de 
        velocidade" (BHP) em "custo de investimento".
    """
    # Coeficientes de regressão linear (Custo = Alpha * BHP + Beta)
    # Baseado em análise estatística de empurradores fluviais construídos no Brasil.
    return 612.5116 * bhp_instalado + 70039.8262

def calcular_fator_recuperacao_capital(
    taxa_juros_anual: float, 
    vida_util_anos: int
) -> float:
    """
    Calcula o Fator de Recuperação de Capital (FRC) ou Capital Recovery Factor (CRF).

    Este fator financeiro é utilizado para distribuir o valor presente de um investimento
    (CAPEX) em uma série uniforme de pagamentos anuais (anuidade), considerando
    o valor do dinheiro no tempo (juros).

    Fórmula:
        FRC = (i * (1 + i)^n) / ((1 + i)^n - 1)

    Parâmetros:
        taxa_juros_anual (float): Taxa de desconto ou custo de oportunidade (decimal, ex: 0.15).
        vida_util_anos (int): Período de amortização do ativo em anos.

    Retorna:
        float: O fator multiplicador (adimensional).

    Nota de Uso:
        Utilizada em `engine.calcular_capex` para anualizar o custo de aquisição
        da frota (Empurrador + Balsas).
    """
    if taxa_juros_anual <= 0:
        # Fallback para depreciação linear simples se juros for zero (caso teórico)
        return 1.0 / vida_util_anos if vida_util_anos > 0 else 0.0

    numerador = taxa_juros_anual * ((1 + taxa_juros_anual) ** vida_util_anos)
    denominador = ((1 + taxa_juros_anual) ** vida_util_anos) - 1
    
    return numerador / denominador

# ==============================================================================
# GRUPO 3: FÍSICA DA NAVEGAÇÃO E HIDRODINÂMICA
# ==============================================================================

def calcular_velocidades_solo(
    vel_embarcacao_nos: float,
    vel_correnteza_nos: float
) -> Tuple[float, float]:
    """
    Calcula as velocidades efetivas de avanço (Speed over Ground - SOG) para
    os trechos de ida e volta, considerando o vetor da correnteza.

    Na navegação fluvial, a velocidade em relação ao solo (que define o tempo
    de viagem) difere da velocidade na água (que define o consumo e esforço
    da máquina).

    Parâmetros:
        vel_embarcacao_nos (float): Velocidade alvo da embarcação na água (STW) em nós.
        vel_correnteza_nos (float): Velocidade média da correnteza do rio em nós.

    Retorna:
        Tuple[float, float]:
            - v_ida (km/h): Velocidade no sentido da corrente (A favor).
            - v_volta (km/h): Velocidade contra a corrente.

    Nota de Uso:
        Utilizada em `engine.calcular_opex_variavel` para determinar a duração
        do ciclo de viagem.
    """
    # Fator de conversão internacional: 1 nó = 1.852 km/h
    FATOR_NO_PARA_KMH = 1.852
    
    v_emb_kmh = vel_embarcacao_nos * FATOR_NO_PARA_KMH
    v_corr_kmh = vel_correnteza_nos * FATOR_NO_PARA_KMH
    
    # Ida (Descida): Soma-se a correnteza (V_total = V_barco + V_rio)
    v_ida = v_emb_kmh + v_corr_kmh
    
    # Volta (Subida): Subtrai-se a correnteza (V_total = V_barco - V_rio)
    # Garante que não seja negativa ou zero (evita divisão por zero no tempo)
    v_volta = max(0.1, v_emb_kmh - v_corr_kmh)
    
    return v_ida, v_volta

def calcular_tempo_viagem_puro(
    distancia_km: float,
    v_ida_kmh: float,
    v_volta_kmh: float
) -> float:
    """
    Calcula o tempo total de navegação (ida e volta) sem considerar paradas.

    Aplica a fórmula básica da cinemática (Tempo = Distância / Velocidade)
    para os dois pernas da viagem separadamente, capturando a assimetria
    do transporte fluvial causada pela correnteza.

    Parâmetros:
        distancia_km (float): Distância do trecho (sentido único).
        v_ida_kmh (float): Velocidade de descida (km/h).
        v_volta_kmh (float): Velocidade de subida (km/h).

    Retorna:
        float: Tempo total de navegação em horas.

    Nota de Uso:
        Essencial para o cálculo de consumo de combustível principal (motores
        de propulsão operam apenas durante este tempo).
    """
    t_ida = distancia_km / v_ida_kmh
    t_volta = distancia_km / v_volta_kmh
    
    return t_ida + t_volta

def calcular_bhp_propulsao(
    comp_balsa: float,
    boca_balsa: float,
    calado_m: float,
    n_long: int,
    n_par: int,
    vel_nos: float,
    largura_canal_m: float,
    profundidade_canal_m: float,
    eficiencia_global: float = 0.50
) -> float:
    """
    Estima a Potência (BHP) usando a formulação de Howe (1967) adaptada por Padovezi (1997) e (2003).

    Esta formulação é específica para comboios fluviais e considera os efeitos
    de águas rasas e canais restritos, comuns na região Amazónica.

    Fórmula Base (Padovezi, 1997, p. 33):
        Pe (kW) = 0.14426 * F * Termo_Calado * Termo_Canal * L^0.38 * B^1.19 * V^3 + Delta_PE

    Para Chatas Vazias (Tc < 0.80m) (Padovezi, 2003, p. 70):
        Pe_total = Pe_howe + 1.83 * V^3

    Parâmetros:
        comp_balsa, boca_balsa (float): Dimensões unitárias (m).
        calado_m (float): Calado operacional (m) (Hc).
        n_long (int): Número de chatas no comprimento (Colunas na terminologia Padovezi).
        n_par (int): Número de chatas na largura (Linhas na terminologia Padovezi).
        vel_nos (float): Velocidade na água em nós.
        largura_canal_m (float): Largura do canal navegável (m) (W).
        profundidade_canal_m (float): Profundidade do canal (m) (h).
        eficiencia_global (float): Eficiência propulsiva (eta).

    Retorna:
        float: Potência requerida (BHP) em Cavalos-Vapor (HP).
    """
    # 1. Conversão de Unidades
    # Howe utiliza m/s para velocidade e metros para dimensões.
    vel_ms = vel_nos * 0.514444
    
    # Dimensões Totais do Comboio (Lc e Bc)
    l_total = comp_balsa * n_long
    b_total = boca_balsa * n_par
    
    # 2. Definição do Fator de Forma (F) - Tabela 4.1 (Padovezi, 2003, p. 71)
    if n_par == 1 and n_long == 1:
        fator_f = 0.040  # Uma chata
    elif n_par == 1 and n_long == 2:
        fator_f = 0.050  # Duas chatas em linha (1 linha, 2 colunas)
    elif n_par == 2 and n_long == 1:
        fator_f = 0.043  # Duas chatas em paralelo (2 linhas, 1 coluna)
    elif n_par == 1 and n_long == 3:
        fator_f = 0.040  # Três chatas em linha
    elif n_par == 2 and n_long == 2:
        fator_f = 0.045  # Quatro chatas (2x2)
    elif n_par == 2 and n_long == 3:
        fator_f = 0.058  # Seis chatas (2 linhas, 3 colunas - Mais longo)
    elif n_par == 3 and n_long == 2:
        fator_f = 0.070  # Seis chatas (3 linhas, 2 colunas - Mais largo)
    else:
        fator_f = 0.070  # Outras formações (Default conservador)

    # 3. Cálculo dos Termos da Equação de Howe 
    # Termo Exponencial de Calado: e^(0.445 / (H - Tc))
    termo_calado_exp = math.exp(0.445 / (profundidade_canal_m - calado_m))
    
    # Termo de Restrição Lateral (Largura do Canal): (Hc / 0.3048)^(0.6 + 15.24/(W - Bc))
    # 0.3048 é a conversão de pés para metros, mantida da fórmula original.
    folga_lateral = largura_canal_m - b_total
    expoente_canal = 0.6 + (15.24 / folga_lateral)
    termo_restricao = (calado_m / 0.3048) ** expoente_canal
    
    # Potência Efetiva Base (kW) em Águas Profundas
    pe_base_kw = (
        0.14426 
        * fator_f 
        * termo_calado_exp 
        * termo_restricao 
        * (l_total ** 0.38) 
        * (b_total ** 1.19) 
        * (vel_ms ** 3)
    )

    # Para Chatas Vazias (Seção 4.1.1, p. 70)
    # A fórmula de Howe subestima a resistência de empurradores grandes com chatas vazias.
    if calado_m < 0.80:
        pe_base_kw = pe_base_kw + (1.83 * (vel_ms ** 3))
    
    # # 4. Correção de Águas Rasas (Delta PE)
    # # Baseado no Número de Froude de Profundidade (Fnh) [cite: 7693]
    # g = 9.81
    # froude_depth = vel_ms / math.sqrt(g * profundidade_canal_m)
    
    delta_pe_kw = 0.0
    # if froude_depth > 0.50:
    #     # Padovezi indica correção para Fnh > 0.50
    #     # Fórmula: 75 * (V - 3.3)^3. V deve ser m/s.
    #     # A correção só faz sentido físico se V > 3.3 m/s (~6.4 nós), 
    #     # caso contrário o termo cúbico seria negativo ou zero.
    #     if vel_ms > 3.3:
    #         delta_pe_kw = 75.0 * ((vel_ms - 3.3) ** 3)
            
    pe_total_kw = pe_base_kw + delta_pe_kw
    
    # 5. Conversão final para BHP (Horsepower)
    # 1 kW = 1.341 HP (mecânico/imperial)
    # BHP = EHP / Eficiência Global
    ehp_total = pe_total_kw * 1.34102
    bhp_requerido = ehp_total / eficiencia_global
    
    return bhp_requerido

def calcular_bhp_auxiliar(
    bhp_principal: float,
    fator_carga: float = 0.25
) -> float:
    """
    Estima a potência média consumida pelos Grupos Geradores (MCPs Auxiliares).
    
    Geralmente dimensionados como uma fração da potência instalada principal para 
    cobrir hotelaria, bombas e sistemas de navegação.

    Parâmetros:
        bhp_principal (float): Potência total dos motores de propulsão.
        fator_carga (float): Fator de demanda elétrica (padrão 0.25 ou 25%).

    Retorna:
        float: Potência média auxiliar em HP.
    """
    return bhp_principal * fator_carga

def calcular_calado_maximo_operacional(
    profundidade_rio_m: float,
    folga_seguranca_m: float,
    calado_design_m: float
) -> float:
    """
    Determina o calado efetivo permitido para um determinado mês/trecho.

    Respeita a restrição física do rio (Profundidade - Keel Clearance) e a 
    restrição estrutural da balsa (Calado de Projeto).

    Parâmetros:
        profundidade_rio_m (float): Profundidade do canal navegável no período.
        folga_seguranca_m (float): Margem de segurança sob a quilha (UKC).
        calado_design_m (float): Calado máximo estrutural da embarcação (borda livre).

    Retorna:
        float: O calado operacional em metros.
    """
    calado_disponivel_rio = profundidade_rio_m - folga_seguranca_m
    # O calado nunca pode ser negativo, nem maior que o projeto da balsa
    return max(0.0, min(calado_disponivel_rio, calado_design_m))

# ==============================================================================
# GRUPO 4: CICLO OPERACIONAL E PRODUTIVIDADE
# ==============================================================================

def calcular_tempo_porto_total(
    carga_total_ton: float,
    prod_carregamento_th: float,
    prod_descarregamento_th: float,
    num_bercos: int
) -> float:
    """
    Calcula o tempo total de estadia no porto (loading/unloading) por viagem.

    Considera a produtividade dos equipamentos de terra (shiploaders/grabbers)
    e o número de berços disponíveis para operação simultânea.

    Parâmetros:
        carga_total_ton (float): Carga total transportada no comboio (t).
        prod_carregamento_th (float): Taxa de carregamento (t/h).
        prod_descarregamento_th (float): Taxa de descarregamento (t/h).
        num_bercos (int): Número de berços operando simultaneamente.

    Retorna:
        float: Tempo total de operação portuária em horas.

    Nota de Uso:
        Utilizada em `engine.calcular_opex_variavel` para compor o Tempo de Ciclo Total.
    """
    if num_bercos <= 0: return float('inf')
    
    # O tempo é limitado pelo gargalo (capacidade do terminal dividida pelos berços)
    t_carga = carga_total_ton / (prod_carregamento_th * num_bercos)
    t_descarga = carga_total_ton / (prod_descarregamento_th * num_bercos)
    
    return t_carga + t_descarga

def calcular_tempo_manobras_e_eclusas(
    tempo_eclusa_min: float,
    tempo_manobra_unitario_min: float,
    num_balsas: int
) -> float:
    """
    Estima tempos "mortos" operacionais não produtivos.

    Inclui transposição de desníveis (eclusas) e manobras de formação/desmembramento
    do comboio, que são proporcionais ao número de balsas (em terminais sem
    estrutura para comboios inteiros).

    Parâmetros:
        tempo_eclusa_min (float): Tempo total em eclusas por ciclo (min).
        tempo_manobra_unitario_min (float): Tempo de manobra por balsa individual (min).
        num_balsas (int): Quantidade total de balsas no comboio.

    Retorna:
        float: Tempo total acessório em horas.
    """
    t_manobra_total = tempo_manobra_unitario_min * num_balsas
    t_total_min = tempo_eclusa_min + t_manobra_total
    return t_total_min / 60.0

def calcular_numero_viagens_periodo(
    tempo_ciclo_h: float,
    dias_disponiveis: float
) -> float:
    """
    Determina o número de viagens possíveis (Round Trips) no período.

    IMPORTANTE: Aplica a função piso (floor) para refletir a "Armadilha dos Inteiros".
    Na logística fluvial, uma viagem só gera receita se for concluída. Frações de
    viagem não contam como produtividade realizada no período contábil.

    Parâmetros:
        tempo_ciclo_h (float): Duração total de uma viagem redonda (horas).
        dias_disponiveis (float): Janela de tempo disponível (dias).

    Retorna:
        float: Número inteiro de viagens completas.

    Nota de Uso:
        Fundamental em `engine.calcular_opex_variavel`. É esta função que gera
        os "degraus" na curva de custo x velocidade.
    """
    if tempo_ciclo_h <= 0: return 0.0
    
    horas_disponiveis = dias_disponiveis * 24.0
    return math.floor(horas_disponiveis / tempo_ciclo_h)

# ==============================================================================
# GRUPO 5: CONSUMO E SUSTENTABILIDADE (COMBUSTÍVEL & CO2)
# ==============================================================================

def calcular_consumo_motor_kg(
    bhp_operante: float,
    tempo_horas: float,
    consumo_especifico: float
) -> float:
    """
    Calcula a massa de combustível consumida com base na engenharia térmica.

    Fórmula: Consumo (kg) = Potência (HP) * Tempo (h) * SFC (kg/HP/h)
    SFC = Specific Fuel Consumption (Consumo Específico).

    Parâmetros:
        bhp_operante (float): Potência efetivamente utilizada (não a instalada).
        tempo_horas (float): Duração da operação nesta potência.
        consumo_especifico (float): Eficiência térmica do motor (ex: 0.160 kg/HP/h).

    Retorna:
        float: Massa total de combustível em kg.
    """
    return bhp_operante * tempo_horas * consumo_especifico

def calcular_custo_monetario_combustivel(
    consumo_kg: float,
    preco_por_litro: float,
    densidade_t_m3: float
) -> float:
    """
    Converte o consumo físico (kg) em custo financeiro (R$), considerando a
    densidade para conversão de massa para volume.

    Parâmetros:
        consumo_kg (float): Massa de combustível (kg).
        preco_por_litro (float): Preço de mercado (R$/L).
        densidade_t_m3 (float): Densidade do diesel (t/m³ ou kg/L). Ex: 0.85.

    Retorna:
        float: Custo total em Reais.

    Nota de Uso:
        O mercado negocia diesel em Litros, mas a engenharia calcula em Kg.
        Esta função faz a ponte entre `engine` e `financeiro`.
    """
    if densidade_t_m3 <= 0: return 0.0
    
    # Densidade t/m³ é numericamente igual a kg/L
    litros_consumidos = consumo_kg / densidade_t_m3
    return litros_consumidos * preco_por_litro

def calcular_emissoes_co2(
    consumo_diesel_kg: float,
    fator_emissao: float = 3.206
) -> float:
    """
    Estima a pegada de carbono da operação (Tank-to-Wake).

    Utiliza fator de emissão padrão da IMO (International Maritime Organization)
    para Diesel Marítimo (MGO/MDO).

    Parâmetros:
        consumo_diesel_kg (float): Massa de combustível queimado.
        fator_emissao (float): kg de CO2 emitido por kg de combustível. 
                               Padrão 3.206 para Marine Diesel Oil.

    Retorna:
        float: Emissões totais de CO2 em toneladas (tCO2).
    """
    kg_co2 = consumo_diesel_kg * fator_emissao
    return kg_co2 / 1000.0  # Converte para toneladas

# ==============================================================================
# GRUPO 6: CUSTOS FIXOS E RECURSOS HUMANOS
# ==============================================================================

def calcular_custo_anual_tripulacao(
    num_tripulantes: float,
    salario_base_medio: float,
    encargos_sociais_pct: float
) -> float:
    """
    Calcula o custo anual total com folha de pagamento (Mão de Obra).

    Parâmetros:
        num_tripulantes (float): Tamanho da guarnição.
        salario_base_medio (float): Salário médio mensal (R$).
        encargos_sociais_pct (float): Multiplicador de encargos (ex: 0.90 para 90%).
                                      Inclui INSS, FGTS, Férias, 13º, Adicionais.

    Retorna:
        float: Custo anual total da tripulação (13 salários considerados indiretamente via encargos).
               Assumindo base de cálculo padrão: Salário * 12 meses * (1 + Encargos).
    """
    # Considera 12 meses. O 13º e férias devem estar diluídos no percentual de encargos
    # ou pode-se usar 13.33 meses se encargos forem apenas impostos diretos.
    # Adota-se aqui a convenção: Custo Mensal * 12.
    custo_mensal_por_cabeca = salario_base_medio * (1.0 + encargos_sociais_pct)
    return custo_mensal_por_cabeca * num_tripulantes * 12.0

def calcular_custo_anual_alimentacao(
    num_tripulantes: float,
    vale_alimentacao_mensal: float
) -> float:
    """
    Calcula custos de rancho/alimentação (Provisões de Bordo).

    Parâmetros:
        num_tripulantes (float): Tamanho da guarnição.
        vale_alimentacao_mensal (float): Custo mensal por tripulante (R$).

    Retorna:
        float: Custo anual total de alimentação.
    """
    return num_tripulantes * vale_alimentacao_mensal * 12.0

def estimar_custo_manutencao_anual(
    valor_ativo_total: float,
    taxa_anual: float = 0.04
) -> float:
    """
    Estima a provisão anual para Manutenção e Reparos (M&R).

    Aplica uma heurística de mercado baseada em percentual do valor de
    reposição do ativo (CAPEX).
    Ref: UFPR/ITTI (2017) sugere 4% para empurradores e 2% para balsas.
    Aqui usamos uma média ponderada ou valor único simplificado.

    Parâmetros:
        valor_ativo_total (float): Investimento inicial (R$).
        taxa_anual (float): Percentual de manutenção (padrão 4%).

    Retorna:
        float: Custo anual estimado de manutenção.
    """
    return valor_ativo_total * taxa_anual

def estimar_custo_seguro_anual(
    valor_ativo_total: float,
    taxa_anual: float = 0.015
) -> float:
    """
    Estima o custo anual de Seguros (Casco e Máquinas + P&I).

    Baseado em percentual do valor do ativo (Hull Value).
    Ref: Rodrigues & Lemgruber (2008) sugerem 1.5%.

    Parâmetros:
        valor_ativo_total (float): Valor segurado (R$).
        taxa_anual (float): Taxa de prêmio anual (padrão 1.5%).

    Retorna:
        float: Custo anual de seguro.
    """
    return valor_ativo_total * taxa_anual

def calcular_custo_administrativo(
    base_custo: float,
    taxa_admin: float = 0.10
) -> float:
    """
    Calcula o Overhead Administrativo (Despesas Gerais e Administrativas - DG&A).
    
    Pode ser aplicado tanto sobre custos fixos (estrutura de escritório) quanto 
    variáveis (gestão da operação), dependendo da política da empresa.

    Parâmetros:
        base_custo (float): O valor sobre o qual a taxa incide (ex: Soma dos Custos Fixos).
        taxa_admin (float): Percentual de overhead (padrão 10%).

    Retorna:
        float: Valor monetário do custo administrativo.
    """
    return base_custo * taxa_admin

# ==============================================================================
# GRUPO 7: INDICADORES DE VIABILIDADE E ESTRATÉGIA (HELPER FUNCTIONS)
# ==============================================================================

def calcular_frota_necessaria(
    demanda_total_anual: float,
    capacidade_anual_unitaria: float
) -> int:
    """
    Calcula o número de comboios necessários para atender uma demanda de mercado.
    
    Aplica arredondamento para cima (teto), pois não é possível ter fração de navio.

    Parâmetros:
        demanda_total_anual (float): Carga total a transportar (t/ano).
        capacidade_anual_unitaria (float): Capacidade produtiva de 1 comboio (t/ano).

    Retorna:
        int: Número inteiro de comboios.
    """
    if capacidade_anual_unitaria <= 0:
        return 0
    return math.ceil(demanda_total_anual / capacidade_anual_unitaria)

def calcular_break_even_point(
    custo_fixo_total: float,
    margem_contribuicao_unitaria: float
) -> float:
    """
    Calcula o Ponto de Equilíbrio (em toneladas ou unidades).

    Fórmula: PE = Custo Fixo / (Preço - Custo Variável Unitário)
    O denominador (Preço - CV) é a Margem de Contribuição.

    Parâmetros:
        custo_fixo_total (float): Soma de todos os custos fixos anuais.
        margem_contribuicao_unitaria (float): Resultado de (Frete - Custo Var/t).

    Retorna:
        float: Volume necessário para zerar o lucro (Break-Even).
    """
    if margem_contribuicao_unitaria <= 0:
        return float('inf') # Nunca atinge o break-even se margem for negativa/zero
        
    return custo_fixo_total / margem_contribuicao_unitaria

def calcular_margem_lucro(
    receita_total: float,
    custo_total: float
) -> float:
    """
    Calcula a margem de lucro líquida percentual.

    Parâmetros:
        receita_total (float): Faturamento bruto.
        custo_total (float): Custo total (Fixo + Variável + Financeiro).

    Retorna:
        float: Margem em porcentagem (ex: 15.5 para 15.5%).
    """
    if receita_total <= 0:
        return -100.0 # Prejuízo total ou sem receita
        
    lucro = receita_total - custo_total
    return (lucro / receita_total) * 100.0

if __name__ == "__main__":
    # ==============================================================================
    # BLOCO DE TESTE PARA: calcular_bhp_propulsao
    # ==============================================================================

    # Parâmetros de entrada para o teste
    comp_balsa = 60.96
    boca_balsa = 10.67
    calado_m_inicial = 3.66
    raio_curvatura_rio = 750
    vel_nos = 5
    largura_canal_m = 200
    eficiencia_global = 0.5 # Eficiência 100% para ver a potência efetiva (EHP) em HP
    LISTA_PROF_MESES = [ 7.72, 9.87, 10.86, 10.98, 8.43, 6.35, 5.12, 3.89, 3.30, 3.00, 3.65, 5.23 ]

    print("\n--- PARÂMETROS GLOBAIS DO TESTE ---")
    print(f"  > Comp. Balsa (unit): {comp_balsa} m")
    print(f"  > Boca Balsa (unit): {boca_balsa} m")
    print(f"  > Calado de Projeto: {calado_m_inicial} m")
    print(f"  > Raio de Curvatura: {raio_curvatura_rio} m")
    print(f"  > Largura do Canal: {largura_canal_m} m")
    print(f"  > Velocidade Alvo: {vel_nos} nós")
    print(f"  > Eficiência Global: {eficiencia_global}")

    vel_ms = vel_nos * 0.514444

    print(f"Velocidade em nós: {vel_nos} nós, velocidade em m/s: {vel_ms:.2f} m/s\n")
        
    n_long, n_par = calcular_arranjo_comboio(
        comp_balsa=comp_balsa,
        boca_balsa=boca_balsa,
        raio_curvatura_rio=raio_curvatura_rio,
        largura_canal_rio=largura_canal_m
    )

    n_long, n_par = 4, 5
    print(f"Arranjo do comboio calculado: {n_long} balsas de comprimento x {n_par} balsas de largura.\n")

    l_total = comp_balsa * n_long
    b_total = boca_balsa * n_par
    print(f"  > Comprimento Total do Comboio (L_total): {l_total:.2f} m")
    print(f"  > Boca Total do Comboio (B_total): {b_total:.2f} m")


    # 2. Definição do Fator de Forma (F) - Tabela 4.1 (Padovezi, 2003, p. 71)
    if n_par == 1 and n_long == 1:
        fator_f = 0.040  # Uma chata
    elif n_par == 1 and n_long == 2:
        fator_f = 0.050  # Duas chatas em linha (1 linha, 2 colunas)
    elif n_par == 2 and n_long == 1:
        fator_f = 0.043  # Duas chatas em paralelo (2 linhas, 1 coluna)
    elif n_par == 1 and n_long == 3:
        fator_f = 0.040  # Três chatas em linha
    elif n_par == 2 and n_long == 2:
        fator_f = 0.045  # Quatro chatas (2x2)
    elif n_par == 2 and n_long == 3:
        fator_f = 0.058  # Seis chatas (2 linhas, 3 colunas - Mais longo)
    elif n_par == 3 and n_long == 2:
        fator_f = 0.070  # Seis chatas (3 linhas, 2 colunas - Mais largo)
    else:
        fator_f = 0.070  # Outras formações (Default conservador)
    
    print(f"  > Fator de Forma (fator_f): {fator_f}")

    print("\n--- CÁLCULO ITERATIVO POR PROFUNDIDADE (MÊS) ---")
    for i, profundidade_canal_m in enumerate(LISTA_PROF_MESES):
        print(f"\n----------------- MÊS {i+1:02d} -----------------")
        print(f"  [ENTRADA] Profundidade do Canal (h): {profundidade_canal_m:.2f} m")

        # Usa o calado inicial para cada iteração
        calado_m = calado_m_inicial

        # Proteção para evitar que a profundidade seja menor ou igual ao calado
        if profundidade_canal_m <= calado_m + 0.5:
            print(f"  [AVISO] Profundidade ({profundidade_canal_m:.2f}m) é menor ou igual ao calado + pé de piloto ({calado_m:.2f}m + 0,5m).")
            # Ajusta o calado para ter uma folga mínima (ex: 0.5m)
            calado_m = profundidade_canal_m - 0.5
            if calado_m <= 0:
                print("  [ERRO] Calado resultante é negativo ou zero. Impossível navegar. Pulando mês.")
                continue
            print(f"  [AJUSTE] Novo calado operacional (Tc): {calado_m:.2f} m")
        else:
            print(f"  > Calado Operacional (Tc): {calado_m:.2f} m (sem ajuste)")

        # Cálculo dos Termos da Equação de Howe
        # Termo Exponencial de Calado: e^(0.445 / (h - Tc))
        termo_calado_exp = math.exp(0.445 / (profundidade_canal_m - calado_m))
        print(f"  > Termo Calado Exp (termo_calado_exp): {termo_calado_exp:.4f}")
            
        # Termo de Restrição Lateral (Largura do Canal): (Tc / 0.3048)^(0.6 + 15.24/(W - Bc))
        folga_lateral = largura_canal_m - b_total
        print(f"  > Folga Lateral (largura_canal - b_total): {folga_lateral:.2f} m")
        expoente_canal = 0.6 + (15.24 / folga_lateral)
        print(f"  > Expoente do Canal (expoente_canal): {expoente_canal:.4f}")
        termo_restricao = (calado_m / 0.3048) ** expoente_canal
        print(f"  > Termo de Restrição (termo_restricao): {termo_restricao:.4f}")

        # Potência Efetiva Base (kW) em Águas Profundas
        pe_base_kw = (
            0.14426 
            * fator_f 
            * termo_calado_exp 
            * termo_restricao 
            * (l_total ** 0.38) 
            * (b_total ** 1.19) 
            * (vel_ms ** 3)
        )
        print(f"  > Potência Base (pe_base_kw) [antes da correção]: {pe_base_kw:.4f} kW")

        # Correção para Chatas Vazias (calado < 0.80m)
        if calado_m < 0.80:
            correcao_vazia = 1.83 * (vel_ms ** 3)
            pe_base_kw = pe_base_kw + correcao_vazia
            print(f"  [CORREÇÃO] Calado < 0.80m. Adicionando {correcao_vazia:.4f} kW.")
            print(f"  > Potência Base (pe_base_kw) [após correção]: {pe_base_kw:.4f} kW")
        
        # Potência total em kW
        pe_total_kw = pe_base_kw
        print(f"  > Potência Efetiva Total (pe_total_kw): {pe_total_kw:.4f} kW")

        # Conversão final para BHP (Horsepower)
        # 1 kW = 1.34102 HP
        ehp_total = pe_total_kw * 1.34102
        print(f"  > Potência Efetiva Total (EHP): {ehp_total:.4f} HP")
        
        bhp_requerido = ehp_total / eficiencia_global
        print(f"  \n  [RESULTADO FINAL MÊS {i+1:02d}] BHP Requerido: {bhp_requerido:,.2f} HP")

    print("\n" + "="*60)
    print("TESTE DETALHADO CONCLUÍDO")
    print("="*60)