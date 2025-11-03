# analysis.py
import math
import numpy as np
from typing import Dict, Any
import engine

# --- FUNÇÃO WRAPPER ---
def run_simulacao_dinamica(params: Dict[str, Any], 
                              lista_prof_meses: list, 
                              calado_design_alvo: float, 
                              folga_seguranca: float,
                              dias_base_anuais: float,
                              print_detalhes: bool = False) -> Dict[str, Any]:
    """
    Executa a Simulação 2 completa (dinâmica mês a mês)
    e retorna os resultados anuais totais.
    """
    
    prof_min_estiagem = min(lista_prof_meses)
    calado_op_estiagem = min(calado_design_alvo, prof_min_estiagem - folga_seguranca)

    # Roda uma simulação "fictícia" SÓ para pegar os custos fixos anuais
    params_fixos = params.copy()
    res_fixos = engine.calcular_custos_comboio(
        **params_fixos,
        calado_op_input=calado_op_estiagem,
        dias_operacao_input=1 
    )
    
    CAPEX_ANUAL_POR_COMBOIO = res_fixos['custo_capex_anual_puro']
    CUSTO_FIXO_TOTAL_ANUAL = res_fixos['custos_fixos_anuais_total']
    OPEX_FIXO_ANUAL_POR_COMBOIO = CUSTO_FIXO_TOTAL_ANUAL - CAPEX_ANUAL_POR_COMBOIO
    formacao_nbl = res_fixos.get('num_balsas_longitudinal', 0)
    formacao_nbp = res_fixos.get('num_balsas_paralela', 0)

    # Inicializa totais para somar os 12 meses
    custos_variaveis_total_anual = 0.0
    combustivel_total_anual = 0.0
    admin_var_total_anual = 0.0
    carga_total_sim2 = 0.0
    viagens_total_sim2 = 0.0
    detalhes_sim2 = []
    
    dias_op_por_mes = dias_base_anuais / 12.0

    for mes_idx, prof_mes in enumerate(lista_prof_meses):
        calado_op_mes = min(calado_design_alvo, prof_mes - folga_seguranca)
        
        params_mes = params.copy()
        res_mes = engine.calcular_custos_comboio(
            **params_mes,
            calado_op_input=calado_op_mes,
            dias_operacao_input=dias_op_por_mes
        )
        
        custos_variaveis_total_anual += res_mes['custos_variaveis_total']
        combustivel_total_anual += res_mes['custo_variavel_combustivel_puro']
        admin_var_total_anual += res_mes['custo_admin_variavel']
        carga_total_sim2 += res_mes['carga_total_ano']
        viagens_total_sim2 += res_mes['num_viagens_ano']

        detalhes_sim2.append({
            'mes': mes_idx + 1,
            'calado': calado_op_mes,
            'viagens': res_mes['num_viagens_ano'],
            'carga_mes': res_mes['carga_total_ano'],
            'cap_carga': res_mes['cap_carga_comboio']
        })

    OPEX_ANUAL_TOTAL_POR_COMBOIO = OPEX_FIXO_ANUAL_POR_COMBOIO + custos_variaveis_total_anual
    custo_total_sim2 = CAPEX_ANUAL_POR_COMBOIO + OPEX_ANUAL_TOTAL_POR_COMBOIO
    custo_ton_sim2 = custo_total_sim2 / carga_total_sim2 if carga_total_sim2 > 0 else 0
    custo_ton_km_sim2 = custo_ton_sim2 / params['dist_km_input'] if params['dist_km_input'] > 0 else 0
    frota_necessaria_demanda = math.ceil(params['demanda_anual'] / carga_total_sim2) if carga_total_sim2 > 0 else 0

    resultados_finais = {
        'inputs': {'calado_op': "Dinâmico Mês a Mês", 'dias_op': dias_base_anuais},
        'cap_carga_comboio': "Misto", 
        'num_viagens_ano': viagens_total_sim2,
        'carga_total_ano': carga_total_sim2,
        'custo_total_anual': custo_total_sim2,
        'custo_por_tonelada': custo_ton_sim2,
        'custo_por_tonelada_km': custo_ton_km_sim2,
        'detalhes': detalhes_sim2,
        'formacao_nbl': formacao_nbl,
        'formacao_nbp': formacao_nbp,
        'custo_capex_anual_total': CAPEX_ANUAL_POR_COMBOIO,
        'custo_opex_anual_total': OPEX_ANUAL_TOTAL_POR_COMBOIO,
        'custos_fixos_anuais_total': CUSTO_FIXO_TOTAL_ANUAL,
        'custos_variaveis_total': custos_variaveis_total_anual,
        'frota_necessaria_demanda': frota_necessaria_demanda,
        'breakdown_capital': CAPEX_ANUAL_POR_COMBOIO,
        'breakdown_combustivel': combustivel_total_anual,
        'breakdown_admin': res_fixos['custo_admin_fixo'] + admin_var_total_anual,
        'breakdown_tripulacao_alim': res_fixos['custo_anual_tripulacao'] + res_fixos['custo_anual_alimentacao'],
        'breakdown_manutencao_seguro': res_fixos['custo_anual_manutencao'] + res_fixos['custo_anual_seguradora']
    }
    
    return resultados_finais

# --- FUNÇÕES DE ANÁLISE (A, B, C, D) ---

def run_analysis_sensitivity(base_params: dict, 
                             lista_prof_meses: list, 
                             calado_design_alvo: float, 
                             folga_seguranca: float,
                             dias_base_anuais: float,
                             base_cost: float) -> list:
    """
    Executa a Análise de Sensibilidade (A).
    Retorna uma lista de dicionários com os resultados.
    """
    print("--- EXECUTANDO: Análise de Sensibilidade (Base: Simulação 2) ---")
    print(f"Custo Base (Simulação 2): R$ {base_cost:,.3f} / tonelada")
    
    SENSIBILIDADE_PCT = 0.10
    vars_to_test = [
        ('Preço Combustível', 'preco_combustivel'),
        ('Consumo Motor (kg/HP/h)', 'consumo_motor_fc'),
        ('Taxa de Juros (Selic)', 'taxa_juros_input'),
        ('Velocidade Embarcação', 'vel_embarcacao_nos'),
        ('Salário Tripulação', 'salario_medio')
    ]
    sensitivity_results = []

    for nome_var, chave_var in vars_to_test:
        print(f"    Testando variável: {nome_var}...")
        
        params_plus = base_params.copy()
        params_plus[chave_var] = base_params[chave_var] * (1 + SENSIBILIDADE_PCT)
        res_plus = run_simulacao_dinamica(params_plus, lista_prof_meses, calado_design_alvo, folga_seguranca, dias_base_anuais)
        cost_plus = res_plus['custo_por_tonelada']
        
        params_minus = base_params.copy()
        params_minus[chave_var] = base_params[chave_var] * (1 - SENSIBILIDADE_PCT)
        res_minus = run_simulacao_dinamica(params_minus, lista_prof_meses, calado_design_alvo, folga_seguranca, dias_base_anuais)
        cost_minus = res_minus['custo_por_tonelada']
        
        impact_plus_pct = (cost_plus / base_cost - 1) * 100
        impact_minus_pct = (cost_minus / base_cost - 1) * 100
        
        sensitivity_results.append({
            'variavel': nome_var,
            'custo_base': base_cost,
            'custo_menos_10': cost_minus,
            'impacto_menos_10': impact_minus_pct,
            'custo_mais_10': cost_plus,
            'impacto_mais_10': impact_plus_pct,
            'faixa_impacto': impact_plus_pct - impact_minus_pct
        })

    sensitivity_results.sort(key=lambda x: x['faixa_impacto'], reverse=True)
    return sensitivity_results

def run_analysis_break_even(sim2_results: dict, frete_input: float) -> dict:
    """
    Executa a Análise de Ponto de Equilíbrio (B).
    Retorna um dicionário com os resultados.
    """
    print("\n" + "=" * 62)
    print("--- EXECUTANDO: Análise de Ponto de Equilíbrio (Base: Simulação 2) ---")
    
    custos_fixos_totais = sim2_results['custos_fixos_anuais_total']
    custos_variaveis_totais = sim2_results['custos_variaveis_total']
    carga_total_anual_sim2 = sim2_results['carga_total_ano']
    
    custo_variavel_por_ton = custos_variaveis_totais / carga_total_anual_sim2 if carga_total_anual_sim2 > 0 else 0
    margem_contribuicao_por_ton = frete_input - custo_variavel_por_ton
    
    results = {
        'preco_frete': frete_input,
        'custos_fixos_anuais_totais': custos_fixos_totais,
        'custo_variavel_por_ton': custo_variavel_por_ton,
        'margem_contribuicao_por_ton': margem_contribuicao_por_ton,
        'is_viable': margem_contribuicao_por_ton > 0
    }

    if results['is_viable']:
        volume_break_even_ton = custos_fixos_totais / margem_contribuicao_por_ton
        viagens_totais_sim2 = sim2_results['num_viagens_ano']
        capacidade_media_por_viagem = carga_total_anual_sim2 / viagens_totais_sim2 if viagens_totais_sim2 > 0 else 0
        
        results['volume_break_even_ton'] = volume_break_even_ton
        results['faturamento_break_even'] = volume_break_even_ton * frete_input
        results['viagens_break_even'] = volume_break_even_ton / capacidade_media_por_viagem if capacidade_media_por_viagem > 0 else 0
        results['carga_total_anual_sim2'] = carga_total_anual_sim2
        results['margem_seguranca_ton'] = carga_total_anual_sim2 - volume_break_even_ton
        results['margem_seguranca_pct'] = (results['margem_seguranca_ton'] / carga_total_anual_sim2) * 100 if carga_total_anual_sim2 > 0 else 0
    
    return results

def run_analysis_velocity_optimization(base_params: dict, 
                                       lista_prof_meses: list, 
                                       calado_design_alvo: float, 
                                       folga_seguranca: float,
                                       dias_base_anuais: float) -> list:
    """
    Executa a Análise de Otimização de Velocidade (C).
    Retorna uma lista de dicionários com os resultados.
    """
    print("\n" + "=" * 62)
    print("--- EXECUTANDO: Análise C - Otimização da Velocidade (Base: Simulação 2) ---")
    
    #Range de velocidade para análise
    # escolheu-se um range entre 4 e 9 nós com passo de 0,25
    velocidades_teste = np.arange(4.0, 9.0 + 0.25, 0.25)
    otimizacao_results = []
    
    print("    Testando velocidades (nós): ", end="")
    for vel in velocidades_teste:
        print(f"{vel:.2f}... ", end="")
        
        params_vel = base_params.copy()
        params_vel['vel_embarcacao_nos'] = vel
        
        res_vel = run_simulacao_dinamica(
            params_vel, 
            lista_prof_meses, 
            calado_design_alvo, 
            folga_seguranca, 
            dias_base_anuais
        )
        
        res_vel['velocidade'] = vel
        otimizacao_results.append(res_vel)
    print("\n")
    return otimizacao_results

def run_analysis_fleet_optimization(optimization_results: list, demanda_total_mercado: int) -> list:
    """
    Executa a Análise de Otimização de Frota (D).
    Retorna uma lista de dicionários com os resultados.
    """
    print("\n" + "=" * 62)
    print(f"--- EXECUTANDO: Análise D - Otimização de Frota (vs. Demanda de {demanda_total_mercado/1_000_000:.0f}M t) ---")
    
    fleet_analysis_results = []
    
    for res_vel in optimization_results:
        velocidade = res_vel['velocidade']
        carga_por_comboio_ano = res_vel['carga_total_ano']
        frota_necessaria = res_vel['frota_necessaria_demanda']
        
        capex_anual_por_comboio = res_vel['custo_capex_anual_total']
        opex_fixo_por_comboio = res_vel['custos_fixos_anuais_total'] - res_vel['custo_capex_anual_total']
        opex_var_por_comboio = res_vel['custos_variaveis_total']
        
        opex_var_por_ton = opex_var_por_comboio / carga_por_comboio_ano if carga_por_comboio_ano > 0 else 0
        
        custo_capex_frota_total = capex_anual_por_comboio * frota_necessaria
        custo_opex_fixo_frota_total = opex_fixo_por_comboio * frota_necessaria
        custo_opex_var_frota_total = opex_var_por_ton * demanda_total_mercado
        custo_total_da_frota = custo_capex_frota_total + custo_opex_fixo_frota_total + custo_opex_var_frota_total
        custo_final_por_tonelada = custo_total_da_frota / demanda_total_mercado
        
        fleet_analysis_results.append({
            'velocidade': velocidade,
            'frota_necessaria': frota_necessaria,
            'custo_final_por_tonelada': custo_final_por_tonelada,
            'custo_capex_frota_total': custo_capex_frota_total,
            'custo_opex_frota_total': custo_opex_fixo_frota_total + custo_opex_var_frota_total,
            'custo_tco_total': custo_capex_frota_total + custo_opex_fixo_frota_total + custo_opex_var_frota_total
        })
    
    return fleet_analysis_results