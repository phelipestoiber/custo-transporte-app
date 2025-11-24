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
    Estima o peso leve (Lightweight) de uma balsa usando regressão linear.
    Baseado no proxy cúbico (L * B * H).
    """
    # Fórmula empírica derivada de regressão linear
    return 18.858037300571 + 112.865401771503 * (comp * boca * pontal / 1000.0)

def calcular_volume_operacional_balsa(
    comp: float, 
    boca: float, 
    calado: float, 
    coef_bloco: float
) -> float:
    """
    Calcula o volume deslocado (m³) de uma balsa em operação.
    """
    return comp * boca * calado * coef_bloco

def calcular_capacidade_carga_balsa(
    volume_deslocado: float, 
    peso_leve: float,
    densidade_agua: float = 1.0
) -> float:
    """
    Calcula a capacidade de carga (Deadweight Cargo) de uma balsa.
    Densidade da água padrão = 1.0 t/m³ (água doce).
    """
    deslocamento_total = volume_deslocado * densidade_agua
    return deslocamento_total - peso_leve

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
    
    n_long_teorico = l_max_permitido / comp_balsa
    n_par_teorico = b_max_permitido / boca_balsa
    
    num_long = math.floor(n_long_teorico)
    if num_long < 1: num_long = 1
    
    # Regra heurística: Evitar comboios "mais largos que compridos" se possível,
    # mas respeitando a largura do canal.
    razao_aspecto = num_long / n_par_teorico
    
    if razao_aspecto < 1:
        # Se for ficar muito "quadrado" ou largo, limita pelo comprimento
        num_par = num_long
    else:
        num_par = math.floor(n_par_teorico)
        
    if num_par < 1: num_par = 1
    
    return int(num_long), int(num_par)

def estimar_custo_construcao_balsa(peso_leve: float) -> float:
    """
    Estima o custo de construção de UMA balsa baseado no peso de aço.
    Fórmula empírica.
    """
    return 7182.1661 * peso_leve + 144536.9815

def estimar_custo_construcao_empurrador(bhp_total: float) -> float:
    """
    Estima o custo de construção do empurrador baseado na potência instalada.
    Fórmula empírica.
    """
    return 612.5116 * bhp_total + 70039.8262

# ==============================================================================
# GRUPO 2: PROPULSÃO E POTÊNCIA (HELPER FUNCTIONS)
# ==============================================================================

def calcular_bhp_propulsao(
    volume_deslocado_comboio: float,
    comp_balsa: float,
    boca_balsa: float,
    n_long: int,
    n_par: int,
    velocidade_nos: float,
    eficiencia_propulsor: float
) -> float:
    """
    Calcula o BHP necessário para mover o comboio a uma certa velocidade.
    Usa fórmula empírica de resistência ao avanço (fórmula de Howe ou similar).
    """
    # Termo geométrico do comboio (L/B)
    termo_geo = (comp_balsa * n_long) / (boca_balsa * n_par)
    
    # Fórmula de potência: k * Vol * (Geo_factor) * V^3.46 / eta
    bhp = (10.84e-5 * volume_deslocado_comboio * (termo_geo**-0.473) * (velocidade_nos**3.46)) / eficiencia_propulsor
    
    return bhp

def calcular_bhp_auxiliar(bhp_principal: float, fator: float = 0.25) -> float:
    """
    Estima a potência dos motores auxiliares (geradores, etc).
    Padrão: 25% da potência principal.
    """
    return bhp_principal * fator

def calcular_consumo_motor_kg(
    potencia_hp: float,
    tempo_h: float,
    consumo_especifico: float
) -> float:
    """
    Calcula a massa (kg) de combustível consumida por um motor específico
    em um intervalo de tempo.
    """
    return potencia_hp * tempo_h * consumo_especifico

# ==============================================================================
# GRUPO 3: OPERAÇÃO E TEMPOS (HELPER FUNCTIONS)
# ==============================================================================

def calcular_velocidades_solo(
    vel_embarcacao_nos: float, 
    vel_correnteza_nos: float
) -> Tuple[float, float]:
    """
    Calcula a velocidade em relação ao solo (km/h) para Ida e Volta.
    Assume Ida a favor da correnteza e Volta contra.
    Retorna: (v_ida_kmh, v_volta_kmh)
    """
    FATOR_NO_PARA_KMH = 1.852
    v_emb_kmh = vel_embarcacao_nos * FATOR_NO_PARA_KMH
    v_corr_kmh = vel_correnteza_nos * FATOR_NO_PARA_KMH
    
    v_ida = v_emb_kmh + v_corr_kmh
    v_volta = v_emb_kmh - v_corr_kmh
    
    # Evita velocidade negativa ou zero no contra-fluxo
    if v_volta <= 0:
        v_volta = 0.1 # Valor mínimo para não quebrar divisão por zero
        
    return v_ida, v_volta

def calcular_tempo_viagem_puro(
    distancia_km: float,
    v_ida_kmh: float,
    v_volta_kmh: float
) -> float:
    """
    Calcula o tempo total de navegação (ida + volta) em horas.
    """
    t_ida = distancia_km / v_ida_kmh
    t_volta = distancia_km / v_volta_kmh
    return t_ida + t_volta

def calcular_tempo_porto_total(
    carga_total_t: float,
    prod_carregamento_th: float,
    prod_descarregamento_th: float,
    num_bercos: int
) -> float:
    """
    Calcula o tempo total (h) gasto em operações de carga e descarga.
    """
    if num_bercos <= 0: return float('inf')
    
    t_carga = carga_total_t / (prod_carregamento_th * num_bercos)
    t_descarga = carga_total_t / (prod_descarregamento_th * num_bercos)
    
    return t_carga + t_descarga

def calcular_tempo_manobras_e_eclusas(
    tempo_eclusa_por_viagem_min: float,
    tempo_manobra_por_balsa_min: float,
    num_total_balsas: int
) -> float:
    """
    Calcula tempos acessórios (manobras de atracação + eclusagem) em horas.
    Considera eclusagem na ida e na volta (x2 se o input for por sentido, 
    mas a lógica atual assume input por viagem completa ou ajustamos aqui).
    *Nota: O código original somava tempo_eclusa direto. Vamos assumir que o input
    já considera o ciclo total.*
    """
    t_eclusa_h = tempo_eclusa_por_viagem_min / 60.0
    t_manobra_h = (tempo_manobra_por_balsa_min * num_total_balsas) / 60.0
    return t_eclusa_h + t_manobra_h

# ==============================================================================
# GRUPO 4: FINANCEIRO E CUSTOS FIXOS (HELPER FUNCTIONS)
# ==============================================================================

def calcular_fator_recuperacao_capital(
    taxa_juros: float, 
    vida_util_anos: int
) -> float:
    """
    Calcula o FRC (Capital Recovery Factor).
    Transforma um valor presente em uma série uniforme de pagamentos (anuidades).
    """
    if taxa_juros <= 0:
        return 1.0 / vida_util_anos
        
    numerador = taxa_juros * ((1 + taxa_juros)**vida_util_anos)
    denominador = ((1 + taxa_juros)**vida_util_anos) - 1
    return numerador / denominador

def calcular_custo_anual_tripulacao(
    num_tripulantes: float,
    salario_medio: float,
    encargos_sociais_pct: float
) -> float:
    """
    Custo anual com folha de pagamento (inclui 13º/Férias via encargos ou média mensal).
    Assume 12 pagamentos mensais "cheios" (o 13º deve estar no encargos_pct ou
    multiplicamos por 13.33. O código original usa 12 * salario * encargos).
    """
    # Mantendo consistência com o original:
    return 12 * salario_medio * num_tripulantes * (1 + encargos_sociais_pct)

def calcular_custo_anual_alimentacao(
    num_tripulantes: float,
    vale_mensal: float
) -> float:
    return num_tripulantes * vale_mensal * 12

def estimar_custo_manutencao_anual(custo_capital_total: float) -> float:
    """
    Estimativa padrão: 4% do valor do ativo por ano.
    """
    return 0.04 * custo_capital_total

def estimar_custo_seguro_anual(custo_capital_total: float) -> float:
    """
    Estimativa padrão: 1.6% do valor do ativo por ano.
    """
    return 0.016 * custo_capital_total

def calcular_custo_administrativo(
    custo_fixo_operacional: float,
    custo_combustivel: float
) -> float:
    """
    Calcula overhead administrativo.
    Regra: 10% do Fixo + 10% do Variável (Combustível).
    """
    return 0.10 * custo_fixo_operacional + 0.10 * custo_combustivel

# ==============================================================================
# GRUPO 5: RESTRIÇÕES E LOGÍSTICA (HELPER FUNCTIONS)
# ==============================================================================

def calcular_calado_maximo_operacional(
    profundidade_rio: float,
    folga_seguranca: float,
    calado_max_projeto: float
) -> float:
    """
    Define o calado operacional considerando as restrições do rio e do projeto.
    O calado nunca pode ser maior que o calado de projeto da balsa.
    """
    calado_possivel_rio = profundidade_rio - folga_seguranca
    
    # Retorna o menor valor, garantindo que não seja negativo
    return max(0.0, min(calado_possivel_rio, calado_max_projeto))

def calcular_numero_viagens_periodo(
    tempo_viagem_total_h: float,
    dias_operacao_periodo: float
) -> int:
    """
    Calcula quantas viagens completas cabem no período de operação.
    Usa 'floor' pois não existe meia viagem comercial.
    """
    if tempo_viagem_total_h <= 0:
        return 0
    
    horas_disponiveis = dias_operacao_periodo * 24.0
    return math.floor(horas_disponiveis / tempo_viagem_total_h)

def calcular_frota_necessaria(
    demanda_total: float,
    capacidade_anual_um_comboio: float
) -> int:
    """
    Calcula quantos comboios são necessários para atender uma demanda de mercado.
    Usa 'ceil' (teto) pois se precisar de 1.1 comboios, você precisa de 2 físicos.
    """
    if capacidade_anual_um_comboio <= 0:
        return 0 # Ou levantar erro, dependendo da tratativa
        
    return math.ceil(demanda_total / capacidade_anual_um_comboio)

# ==============================================================================
# GRUPO 6: CUSTOS VARIÁVEIS E SUSTENTABILIDADE (HELPER FUNCTIONS)
# ==============================================================================

def calcular_custo_monetario_combustivel(
    consumo_kg: float,
    preco_por_litro: float,
    densidade_t_m3: float
) -> float:
    """
    Converte o consumo físico (kg) para custo monetário (R$).
    
    Lógica:
    Densidade t/m³ é numericamente igual a kg/L.
    Litros = Massa (kg) / Densidade (kg/L)
    """
    if densidade_t_m3 <= 0: return 0.0
    
    litros_consumidos = consumo_kg / densidade_t_m3
    return litros_consumidos * preco_por_litro

def calcular_emissoes_co2(
    consumo_diesel_kg: float,
    fator_emissao: float = 3.2
) -> float:
    """
    Estima as emissões de CO2 baseadas no consumo de combustível.
    Fator médio para Diesel Marítimo: ~3.2 kg CO2 por kg de combustível queimado.
    """
    return consumo_diesel_kg * fator_emissao

# ==============================================================================
# GRUPO 7: INDICADORES DE VIABILIDADE (HELPER FUNCTIONS)
# ==============================================================================

def calcular_break_even_point(
    custo_fixo_total: float,
    margem_contribuicao_unitaria: float
) -> float:
    """
    Calcula o Ponto de Equilíbrio (em toneladas ou unidades).
    PE = Custo Fixo / (Preço - Custo Variável Unitário)
    """
    if margem_contribuicao_unitaria <= 0:
        return float('inf') # Nunca atinge o break-even se margem for negativa/zero
        
    return custo_fixo_total / margem_contribuicao_unitaria

def calcular_margem_lucro(
    receita_total: float,
    custo_total: float
) -> float:
    """
    Calcula a margem de lucro percentual.
    """
    if receita_total <= 0:
        return -100.0 # Prejuízo total ou sem receita
        
    lucro = receita_total - custo_total
    return (lucro / receita_total) * 100.0