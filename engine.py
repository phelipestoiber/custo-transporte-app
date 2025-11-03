# engine.py
import math
from typing import Dict, Any

def calcular_custos_comboio(
    # Parâmetros de Simulação
    calado_op_input: float, 
    dias_operacao_input: float, 
    
    # Parâmetros de Engenharia e Trajeto
    comp_balsa: float,
    boca_balsa: float,
    pontal_balsa: float,
    coef_bloco: float,
    raio_curvatura: float,
    largura_canal: float,
    dist_km_input: float,
    t_eclusagem_min: float,
    t_manobra_balsa_min: float,
    
    # Parâmetros de Operação
    vel_embarcacao_nos: float,
    vel_correnteza_nos: float,
    num_bercos: float,
    prod_carregamento: float,
    prod_descarregamento: float,
    num_tripulantes: float,
    eficiencia_propulsor: float,
    
    # Parâmetros Financeiros e de Custo
    demanda_anual: int,
    taxa_juros_input: float,
    vida_util_anos: int,
    preco_combustivel: float,
    consumo_motor_fc: float,
    densidade_combustivel: float,
    salario_medio: float,
    vale_alimentacao: float,
    encargos_sociais_pct: float
    ) -> Dict[str, Any]:
    """
    Calcula os custos operacionais de um comboio de balsas.
    Esta é uma função "pura", todos os inputs são parâmetros.
    """

    # Fator de conversão
    FATOR_NO_PARA_KMH = 1.852

    # --- Inputs Variáveis (Parâmetros da Simulação) ---
    calado_op = calado_op_input
    dias_operacao = dias_operacao_input
    taxa_juros_anual = taxa_juros_input
    dist_km = dist_km_input

    # Dicionário para armazenar todos os resultados
    resultados = {}
    resultados['inputs'] = {'calado_op': calado_op, 'dias_op': dias_operacao}

    # --- 2. CÁLCULOS SEQUENCIAIS ---

    # CARACTERISTICAS DAS BALSAS (Cálculos)
    # A Formula de peso leve foi feita apartide de regreção linear 
    # utilizando o proxy (L * B * H) / 1000 como parâmetro
    peso_leve = 18.858037300571 + 112.865401771503 * (comp_balsa * boca_balsa * pontal_balsa / 1000)
    volume_op_balsa = comp_balsa * boca_balsa * calado_op * coef_bloco
    # Na formula da capacidade da balsa utilizou-se o volume pois a 
    # densidade em água doce é igual a 1 t/m³
    cap_carga_balsa = volume_op_balsa - peso_leve
    
    resultados['peso_leve'] = peso_leve
    resultados['cap_carga_balsa'] = cap_carga_balsa

    # CARACTERISTICAS DO COMBOIO (Cálculos)
    l_max_comboio = raio_curvatura / 5
    b_max_comboio = largura_canal
    
    nblp_max_teorico = l_max_comboio / comp_balsa
    nbpp_max_teorico = b_max_comboio / boca_balsa
    
    # Fez-se a restrição de que um comboio nao deve ter mais balsas 
    # paralelas do que balças na longitudinal
    num_balsas_longitudinal = math.floor(nblp_max_teorico)
    condicao = num_balsas_longitudinal / nbpp_max_teorico < 1
    
    if condicao:
        num_balsas_paralela = num_balsas_longitudinal
    else:
        num_balsas_paralela = math.floor(nbpp_max_teorico)
    
    if num_balsas_longitudinal == 0: num_balsas_longitudinal = 1
    if num_balsas_paralela == 0: num_balsas_paralela = 1
        
    num_total_balsas = num_balsas_longitudinal * num_balsas_paralela
    cap_carga_comboio = num_total_balsas * cap_carga_balsa
    volume_op_comboio = volume_op_balsa * num_total_balsas
    
    resultados['cap_carga_comboio'] = cap_carga_comboio
    resultados['num_balsas_longitudinal'] = num_balsas_longitudinal
    resultados['num_balsas_paralela'] = num_balsas_paralela

    # CÁLCULO DE TEMPOS (Operação)
    t_eclusagem_h = t_eclusagem_min / 60.0
    t_manobra_balsa_h = t_manobra_balsa_min / 60.0

    v_embarcacao_kmh = vel_embarcacao_nos * FATOR_NO_PARA_KMH
    v_correnteza_kmh = vel_correnteza_nos * FATOR_NO_PARA_KMH
    
    # Considerou-se o cebario onde a balsa faz o caminho de ida a favor da 
    # correnteza e o de volta contra correnteza
    tempo_ida_h = dist_km / (v_embarcacao_kmh + v_correnteza_kmh)
    tempo_volta_h = dist_km / (v_embarcacao_kmh - v_correnteza_kmh)
    
    tempo_manobra_total_h = t_manobra_balsa_h * num_total_balsas
    tempo_carregamento_h = cap_carga_comboio / (prod_carregamento * num_bercos)
    tempo_descarregamento_h = cap_carga_comboio / (prod_descarregamento * num_bercos)
    tempo_operacao_porto_h = tempo_carregamento_h + tempo_descarregamento_h
    tempo_viagem_h = tempo_ida_h + tempo_volta_h
    
    tempo_viagem_total_h = tempo_viagem_h + t_eclusagem_h + tempo_manobra_total_h + tempo_operacao_porto_h
    
    num_viagens_periodo = math.floor((dias_operacao * 24) / tempo_viagem_total_h) if tempo_viagem_total_h > 0 else 0
    
    resultados['tempo_viagem_total_h'] = tempo_viagem_total_h
    resultados['num_viagens_ano'] = num_viagens_periodo

    # CARACTERISTICAS DE DEMANDA (Cálculo)
    carga_total_periodo = cap_carga_comboio * num_viagens_periodo
    frota_necessaria = demanda_anual / carga_total_periodo if carga_total_periodo > 0 else 0
    resultados['frota_necessaria'] = frota_necessaria

    # CUSTO E CONSUMO (Cálculos)
    termo_geo = (comp_balsa * num_balsas_longitudinal) / (boca_balsa * num_balsas_paralela)
    # Foi-se utilizada a formulas empiricas para calcuslo de BHP necessario 
    # e custos de contrução de comboio e empurrador
    bhp_necessario = 10.84 * (10**-5) * volume_op_comboio * (termo_geo**-0.473) * (vel_embarcacao_nos**3.46) / eficiencia_propulsor
    custo_construcao_comboio = (7182.1661 * peso_leve + 144536.9815) * num_total_balsas
    custo_construcao_empurrador = 612.5116 * bhp_necessario + 70039.8262
    bhp_auxiliar = 0.25 * bhp_necessario
    
    custo_comb_viagem = (consumo_motor_fc / densidade_combustivel) * \
                        (bhp_necessario * tempo_viagem_h * preco_combustivel + \
                         bhp_auxiliar * tempo_viagem_total_h * preco_combustivel)
                         
    custo_variavel_combustivel = custo_comb_viagem * num_viagens_periodo
    
    custo_capital_total = custo_construcao_comboio + custo_construcao_empurrador
    custo_anual_manutencao = 0.04 * custo_capital_total
    
    resultados['custo_capital_total'] = custo_capital_total
    resultados['custo_comb_viagem'] = custo_comb_viagem
    resultados['custo_anual_combustivel'] = custo_variavel_combustivel
    resultados['custo_anual_manutencao'] = custo_anual_manutencao

    # FRC E CAC (Custos FIXOS anuais)
    i = taxa_juros_anual
    n = vida_util_anos
    frc_num = i * ((1 + i)**n)
    frc_den = ((1 + i)**n) - 1
    fator_recup_capital = frc_num / frc_den
    custo_anual_capital = fator_recup_capital * custo_capital_total
    
    resultados['custo_anual_capital'] = custo_anual_capital

    # OUTROS CUSTOS (Custos FIXOS anuais)
    custo_anual_tripulacao = 12 * salario_medio * num_tripulantes * (1 + encargos_sociais_pct)
    custo_anual_seguradora = 0.016 * custo_capital_total
    custo_anual_alimentacao = num_tripulantes * vale_alimentacao * 12
    
    custos_fixos_anuais = (custo_anual_manutencao + 
                             custo_anual_capital + 
                             custo_anual_tripulacao + 
                             custo_anual_seguradora + 
                             custo_anual_alimentacao)

    # Custos Administrativos
    custo_admin_fixo = 0.10 * custos_fixos_anuais
    custo_admin_variavel = 0.10 * custo_variavel_combustivel
    custos_administrativos_total = custo_admin_fixo + custo_admin_variavel
    
    resultados['custos_fixos_anuais_base'] = custos_fixos_anuais
    resultados['custo_admin_fixo'] = custo_admin_fixo
    resultados['custo_admin_variavel'] = custo_admin_variavel
    resultados['custos_administrativos_total'] = custos_administrativos_total

    # CUSTO TOTAL
    custo_total_fixo_anual = custos_fixos_anuais + custo_admin_fixo
    custo_total_variavel_periodo = custo_variavel_combustivel + custo_admin_variavel
    custo_total_periodo = custo_total_fixo_anual + custo_total_variavel_periodo

    resultados['custo_total_anual'] = custo_total_periodo
    resultados['custos_fixos_anuais_total'] = custo_total_fixo_anual
    resultados['custos_variaveis_total'] = custo_total_variavel_periodo

    # CUSTOS POR TONELADA
    carga_total_periodo = cap_carga_comboio * num_viagens_periodo
    custo_por_tonelada = custo_total_periodo / carga_total_periodo if carga_total_periodo > 0 else 0
    custo_por_tonelada_km = custo_por_tonelada / dist_km if dist_km > 0 else 0

    # Separação de OPEX e CAPEX
    resultados['custo_capex_anual_puro'] = custo_anual_capital
    resultados['custo_opex_total_anual'] = custo_total_periodo - custo_anual_capital
    
    resultados['carga_total_ano'] = carga_total_periodo
    resultados['custo_por_tonelada'] = custo_por_tonelada
    resultados['custo_por_tonelada_km'] = custo_por_tonelada_km

    # Componentes de Custo para Gráfico
    resultados['custo_anual_tripulacao'] = custo_anual_tripulacao
    resultados['custo_anual_alimentacao'] = custo_anual_alimentacao
    resultados['custo_anual_manutencao'] = custo_anual_manutencao
    resultados['custo_anual_seguradora'] = custo_anual_seguradora
    resultados['custo_variavel_combustivel_puro'] = custo_variavel_combustivel

    return resultados