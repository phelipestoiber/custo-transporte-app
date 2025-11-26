# analysis.py
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import engine
import helpers

# ==============================================================================
# MÓDULO DE ANÁLISE E OTIMIZAÇÃO (CONTROLLER)
# ==============================================================================
# Este arquivo contém a lógica de negócios e os algoritmos de otimização.
# Ele orquestra múltiplas chamadas ao 'engine.py' para simular cenários
# completos (ano fiscal), sensibilidade e dimensionamento de frota.
# ==============================================================================

# =============================================================================
# FUNÇÕES AUXILIARES (HELPERS INTERNOS)
# =============================================================================

def _simular_ano_operacional(
    params: Dict[str, Any],
    lista_prof_meses: List[float],
    calado_design_alvo: float,
    folga_seguranca: float,
    dias_base_anuais: float,
    velocidades_mensais: Optional[List[float]] = None,
    override_bhp: Optional[float] = None
) -> Dict[str, Any]:
    """
    Simula um ano fiscal completo de operação do comboio.

    Esta é a função 'core' de agregação temporal. Ela integra o desempenho
    físico mensal (variável conforme o calado do rio) com a estrutura de
    custos anual (fixos e variáveis) para determinar o custo unitário médio.

    Parâmetros:
        params (Dict): Dicionário contendo todos os parâmetros base (física, custos).
        lista_prof_meses (List[float]): Lista de 12 profundidades médias (jan-dez).
        calado_design_alvo (float): Calado máximo estrutural da balsa.
        folga_seguranca (float): 'Keel clearance' (pé de piloto).
        dias_base_anuais (float): Dias disponíveis para operação no ano (ex: 330).
        velocidades_mensais (List[float], opcional): Lista de velocidades para cada mês.
            Se None, usa a velocidade fixa definida em `params`.
        override_bhp (float, opcional): Força um tamanho de motor específico (HP).
            Usado na Otimização Global para fixar o CAPEX enquanto varia o OPEX.

    Retorna:
        Dict[str, Any]: Métricas anuais consolidadas (Custo Unitário, Carga Total, etc.).

    Nota de Uso:
        Utilizada por todas as funções de análise deste módulo (`run_sensitivity`,
        `run_fleet_optimization`, etc.) como a unidade básica de simulação.
    """
    
    # 1. Dimensionamento e Custos Fixos (CAPEX + OPEX Fixo)
    # Determina o calado máximo possível no ano para dimensionar o comboio no "pior caso" (cheia/carga máxima)
    calado_maximo_ano = min(calado_design_alvo, max(lista_prof_meses) - folga_seguranca)
    
    # Define a velocidade de referência para o projeto do motor (Design Speed)
    if velocidades_mensais:
        v_design = max(velocidades_mensais)
    else:
        v_design = params['vel_embarcacao_nos']
        
    # Calcula a geometria do comboio (Arranjo)
    n_long, n_par = engine.helpers.calcular_arranjo_comboio(
        params['comp_balsa'], params['boca_balsa'], 
        params['raio_curvatura'], params['largura_canal']
    )
    
    # Calcula o deslocamento máximo para dimensionar a propulsão
    vol_desloc_max = engine.helpers.calcular_volume_operacional_balsa(
        params['comp_balsa'], params['boca_balsa'], calado_maximo_ano, params['coef_bloco']
    ) * (n_long * n_par)
    
    # Determina a potência instalada (BHP). 
    # Se `override_bhp` for fornecido (loop de design), usa-o. Caso contrário, calcula o necessário.
    if override_bhp:
        bhp_instalado = override_bhp
    else:
        bhp_instalado = engine.helpers.calcular_bhp_propulsao(
            vol_desloc_max, params['comp_balsa'], params['boca_balsa'],
            n_long, n_par, v_design, params['eficiencia_propulsor']
        )

    # Calcula o CAPEX Anualizado (Investimento)
    res_capex = engine.calcular_capex(
        params['comp_balsa'], params['boca_balsa'], params['pontal_balsa'],
        n_long, n_par, bhp_instalado, params['taxa_juros_input'], params['vida_util_anos']
    )
    
    # Calcula o OPEX Fixo (Tripulação, Seguros, Manutenção)
    res_opex_fixo = engine.calcular_opex_fixo(
        res_capex['investimento_total'], params['num_tripulantes'],
        params['salario_medio'], params['vale_alimentacao'], params['encargos_sociais_pct']
    )
    
    custo_fixo_anual_total = res_capex['custo_capex_anual'] + res_opex_fixo['custos_fixos_anuais_total']

    # 2. Loop Operacional Mensal (OPEX Variável)
    # Itera sobre os 12 meses para capturar a sazonalidade do rio (Calado -> Carga)
    custo_variavel_anual_total = 0.0
    carga_anual_total = 0.0
    viagens_anuais_total = 0.0
    emissoes_anual_total = 0.0
    
    dias_op_mes = dias_base_anuais / 12.0
    
    for i, prof_mes in enumerate(lista_prof_meses):
        # Calado disponível neste mês específico
        calado_mes = min(calado_design_alvo, prof_mes - folga_seguranca)
        
        # Velocidade operacional neste mês
        v_mes = velocidades_mensais[i] if velocidades_mensais else params['vel_embarcacao_nos']
        
        # Chama o motor físico para calcular o desempenho do mês
        res_var = engine.calcular_opex_variavel(
            distancia_km=params['dist_km_input'],
            dias_operacao_periodo=dias_op_mes,
            vel_embarcacao_nos=v_mes,
            vel_correnteza_nos=params['vel_correnteza_nos'],
            calado_operacional=calado_mes,
            comp_balsa=params['comp_balsa'],
            boca_balsa=params['boca_balsa'],
            pontal_balsa=params['pontal_balsa'],
            coef_bloco=params['coef_bloco'],
            num_balsas_long=n_long,
            num_balsas_par=n_par,
            eficiencia_propulsor=params['eficiencia_propulsor'],
            tempo_eclusa_por_viagem_min=params['t_eclusagem_min'],
            tempo_manobra_por_balsa_min=params['t_manobra_balsa_min'],
            prod_carregamento_th=params['prod_carregamento'],
            prod_descarregamento_th=params['prod_descarregamento'],
            num_bercos=params['num_bercos'],
            consumo_especifico_motor=params['consumo_motor_fc'],
            preco_combustivel=params['preco_combustivel'],
            densidade_combustivel=params['densidade_combustivel']
        )
        
        # Aplica taxa administrativa variável (Overhead) sobre o custo de combustível do mês
        # Premissa: 10% de overhead sobre custos diretos variáveis
        custo_var_mes = res_var['custo_variavel_total'] * 1.10
        
        # Acumula totais anuais
        custo_variavel_anual_total += custo_var_mes
        carga_anual_total += res_var['carga_total_transportada']
        viagens_anuais_total += res_var['num_viagens']
        emissoes_anual_total += res_var['emissoes_co2_ton']

    # 3. Consolidação dos Resultados
    custo_total_anual = custo_fixo_anual_total + custo_variavel_anual_total
    custo_unitario = custo_total_anual / carga_anual_total if carga_anual_total > 0 else float('inf')
    
    # Cálculo da Intensidade de Carbono (kgCO2 / t)
    intensidade_carbono = (emissoes_anual_total * 1000.0) / carga_anual_total if carga_anual_total > 0 else 0.0
    
    # Breakdown de custos para gráficos (Pizza)
    # Remove o overhead do combustível para mostrar puro no gráfico
    combustivel_puro = custo_variavel_anual_total / 1.10
    admin_variavel = custo_variavel_anual_total - combustivel_puro
    
    breakdown = {
         'Combustível': combustivel_puro,
         'Custo de Capital (CAPEX)': res_capex['custo_capex_anual'],
         'Administrativo': res_opex_fixo['custo_admin_fixo'] + admin_variavel,
         'Tripulação + Alimentação': res_opex_fixo['custo_tripulacao'] + res_opex_fixo['custo_alimentacao'],
         'Outros (Manut. + Seguros)': res_opex_fixo['custo_manutencao'] + res_opex_fixo['custo_seguros']
    }

    return {
        'custo_unitario_R$_t': custo_unitario,
        'custo_total_anual': custo_total_anual,
        'carga_anual': carga_anual_total,
        'viagens_anuais': viagens_anuais_total,
        'bhp_instalado': bhp_instalado,
        'investimento_inicial': res_capex['investimento_total'],
        'custo_fixo_anual': custo_fixo_anual_total,
        'custo_variavel_anual': custo_variavel_anual_total,
        'emissoes_total_ton': emissoes_anual_total,
        'intensidade_carbono_kg_t': intensidade_carbono,
        'breakdown_custos': breakdown,
        'df_mensal': pd.DataFrame([]), # Placeholder para compatibilidade, preenchido apenas na simulação detalhada
        # Dados de engenharia úteis para debug
        'n_long': n_long,
        'n_par': n_par
    }

def _calcular_frota_demanda(res_unitario: Dict, demanda_total: float) -> Dict:
    """
    Extrapola os resultados de um único comboio para uma frota capaz de atender
    uma demanda de mercado alvo.

    Parâmetros:
        res_unitario (Dict): Resultado da simulação anual de 1 comboio.
        demanda_total (float): Demanda anual total do contrato/mercado (t).

    Retorna:
        Dict: Métricas consolidadas da frota (Nº Comboios, Investimento Total, etc.).

    Nota de Uso:
        Utilizada na função `run_fleet_optimization`.
    """
    capacidade_unitaria = res_unitario['carga_anual']
    
    if capacidade_unitaria <= 0:
        return {'frota_necessaria': 0, 'custo_final_por_tonelada_demandada': float('inf'), 
                'investimento_total_frota': 0, 'custo_anual_operacao_frota': 0}
        
    # Calcula número de comboios (sempre arredonda para cima)
    frota_necessaria = engine.helpers.calcular_frota_necessaria(demanda_total, capacidade_unitaria)
    
    # Multiplica os custos unitários pelo tamanho da frota
    custo_total_frota = res_unitario['custo_total_anual'] * frota_necessaria
    investimento_frota = res_unitario['investimento_inicial'] * frota_necessaria
    
    # Custo Real Unitário: Custo Total da Frota / Demanda Total (não Capacidade Total)
    # Isso captura a ineficiência de ter "sobra" de capacidade no último comboio.
    custo_medio_real = custo_total_frota / demanda_total
    
    return {
        'frota_necessaria': frota_necessaria,
        'capacidade_frota': capacidade_unitaria * frota_necessaria,
        'investimento_total_frota': investimento_frota,
        'custo_anual_operacao_frota': custo_total_frota,
        'custo_final_por_tonelada_demandada': custo_medio_real
    }


# ------------------------------------------------------------------------------
# FUNÇÕES DE ANÁLISE (PÚBLICAS - CHAMADAS PELO APP.PY)
# ------------------------------------------------------------------------------

# --- ANÁLISE 0: Detalhes iniciais
def run_detailed_base_simulation(
    params: Dict[str, Any], 
    lista_prof_meses: list, 
    calado_design_alvo: float, 
    folga_seguranca: float, 
    dias_base_anuais: float
) -> Dict[str, Any]:
    """
    Roda a simulação detalhada para o Cenário Base (Inputs do usuário).
    Retorna breakdown completo de custos e tabela mensal.
    """
    print("--- EXECUTANDO: Simulação Detalhada do Cenário Base ---")
    
    # 1. Engenharia e Custos Fixos
    calado_maximo_ano = min(calado_design_alvo, max(lista_prof_meses) - folga_seguranca)
    
    n_long, n_par = helpers.calcular_arranjo_comboio(
        params['comp_balsa'], params['boca_balsa'], 
        params['raio_curvatura'], params['largura_canal']
    )
    
    vol_desloc_max = helpers.calcular_volume_operacional_balsa(
        params['comp_balsa'], params['boca_balsa'], calado_maximo_ano, params['coef_bloco']
    ) * (n_long * n_par)
    
    bhp_instalado = helpers.calcular_bhp_propulsao(
        vol_desloc_max, params['comp_balsa'], params['boca_balsa'],
        n_long, n_par, params['vel_embarcacao_nos'], params['eficiencia_propulsor']
    )

    res_capex = engine.calcular_capex(
        params['comp_balsa'], params['boca_balsa'], params['pontal_balsa'],
        n_long, n_par, bhp_instalado, params['taxa_juros_input'], params['vida_util_anos']
    )
    
    res_opex_fixo = engine.calcular_opex_fixo(
        res_capex['investimento_total'], params['num_tripulantes'],
        params['salario_medio'], params['vale_alimentacao'], params['encargos_sociais_pct']
    )
    
    # 2. Loop Mensal (Variáveis)
    custo_combustivel_anual = 0.0
    carga_total = 0.0
    viagens_totais = 0.0
    emissoes_totais = 0.0
    tabela_mensal = []
    dias_op_mes = dias_base_anuais / 12.0
    
    for i, prof_mes in enumerate(lista_prof_meses):
        calado_mes = min(calado_design_alvo, prof_mes - folga_seguranca)
        
        res_var = engine.calcular_opex_variavel(
            distancia_km=params['dist_km_input'],
            dias_operacao_periodo=dias_op_mes,
            vel_embarcacao_nos=params['vel_embarcacao_nos'],
            vel_correnteza_nos=params['vel_correnteza_nos'],
            calado_operacional=calado_mes,
            comp_balsa=params['comp_balsa'],
            boca_balsa=params['boca_balsa'],
            pontal_balsa=params['pontal_balsa'],
            coef_bloco=params['coef_bloco'],
            num_balsas_long=n_long,
            num_balsas_par=n_par,
            eficiencia_propulsor=params['eficiencia_propulsor'],
            tempo_eclusa_por_viagem_min=params['t_eclusagem_min'],
            tempo_manobra_por_balsa_min=params['t_manobra_balsa_min'],
            prod_carregamento_th=params['prod_carregamento'],
            prod_descarregamento_th=params['prod_descarregamento'],
            num_bercos=params['num_bercos'],
            consumo_especifico_motor=params['consumo_motor_fc'],
            preco_combustivel=params['preco_combustivel'],
            densidade_combustivel=params['densidade_combustivel']
        )
        
        custo_combustivel_anual += res_var['custo_variavel_total']
        carga_total += res_var['carga_total_transportada']
        viagens_totais += res_var['num_viagens']
        emissoes_totais += res_var['emissoes_co2_ton']
        
        tabela_mensal.append({
            'Mês': i + 1,
            'Calado (m)': calado_mes,
            'Capacidade Viagem (t)': res_var['carga_por_viagem'],
            'Viagens': res_var['num_viagens'],
            'Carga no Mês (t)': res_var['carga_total_transportada'],
            'Emissões (tCO2)': res_var['emissoes_co2_ton']
        })
        
    # 3. Consolidação
    # Admin Variável (10% do Combustível)
    custo_admin_var = 0.10 * custo_combustivel_anual
    
    # Componentes para o Gráfico
    breakdown = {
        'Combustível': custo_combustivel_anual,
        'Custo de Capital (CAPEX)': res_capex['custo_capex_anual'],
        'Administrativo': res_opex_fixo['custo_admin_fixo'] + custo_admin_var,
        'Tripulação + Alimentação': res_opex_fixo['custo_tripulacao'] + res_opex_fixo['custo_alimentacao'],
        'Outros (Manut. + Seguros)': res_opex_fixo['custo_manutencao'] + res_opex_fixo['custo_seguros']
    }
    
    custo_total_anual = sum(breakdown.values())
    custo_unitario = custo_total_anual / carga_total if carga_total > 0 else 0.0
    carbon_intensity = (emissoes_totais * 1000) / carga_total if carga_total > 0 else 0.0
    
    return {
        'n_long': n_long,
        'n_par': n_par,
        'custo_unitario': custo_unitario,
        'carga_anual': carga_total,
        'viagens_anuais': viagens_totais,
        'custo_total_anual': custo_total_anual,
        'breakdown_custos': breakdown,
        'df_mensal': pd.DataFrame(tabela_mensal),
        'emissoes_total_ton': emissoes_totais,
        'intensidade_carbono_kg_t': carbon_intensity
    }

def run_sensitivity_analysis(
    base_params: Dict, 
    lista_prof_meses: list, 
    calado_design: float, 
    folga: float, 
    dias_op: float
) -> pd.DataFrame:
    """
    Executa a Análise de Sensibilidade (Tornado).
    
    Varia parâmetros chave em +/- 10% e calcula o impacto percentual no Custo Unitário.
    Permite identificar quais variáveis são críticas para o projeto (Risco).

    Nota de Uso:
        Alimenta a "Aba 1: Sensibilidade" no `app.py`.
    """
    print("--- EXECUTANDO: Análise 1 - Sensibilidade ---")
    
    # Cenário Base
    base_res = _simular_ano_operacional(base_params, lista_prof_meses, calado_design, folga, dias_op)
    custo_base = base_res['custo_unitario_R$_t']
    
    # Lista de variáveis a testar
    variaveis = [
        ('Preço Combustível', 'preco_combustivel'),
        ('Velocidade (nós)', 'vel_embarcacao_nos'),
        ('Taxa de Juros', 'taxa_juros_input'),
        ('Salário Tripulação', 'salario_medio'), 
        ('Velocidade Correnteza', 'vel_correnteza_nos')
    ]
    
    resultados = []
    
    for nome, chave in variaveis:
        # +10%
        p_plus = base_params.copy()
        p_plus[chave] = base_params[chave] * 1.10
        res_plus = _simular_ano_operacional(p_plus, lista_prof_meses, calado_design, folga, dias_op)
        delta_plus = (res_plus['custo_unitario_R$_t'] / custo_base) - 1
        
        # -10%
        p_minus = base_params.copy()
        p_minus[chave] = base_params[chave] * 0.90
        res_minus = _simular_ano_operacional(p_minus, lista_prof_meses, calado_design, folga, dias_op)
        delta_minus = (res_minus['custo_unitario_R$_t'] / custo_base) - 1
        
        resultados.append({
            'Parâmetro': nome,
            'Impacto (+10%)': delta_plus * 100,
            'Impacto (-10%)': delta_minus * 100,
            'Sensibilidade Total': abs(delta_plus - delta_minus) * 100
        })
        
    # Adiciona Disponibilidade (Dias/Ano) separadamente
    p_dias_plus = base_params.copy()
    res_dias_plus = _simular_ano_operacional(p_dias_plus, lista_prof_meses, calado_design, folga, dias_op * 1.10)
    delta_dias_plus = (res_dias_plus['custo_unitario_R$_t'] / custo_base) - 1
    
    p_dias_minus = base_params.copy()
    res_dias_minus = _simular_ano_operacional(p_dias_minus, lista_prof_meses, calado_design, folga, dias_op * 0.90)
    delta_dias_minus = (res_dias_minus['custo_unitario_R$_t'] / custo_base) - 1
    
    resultados.append({
        'Parâmetro': 'Disponibilidade (Dias/Ano)',
        'Impacto (+10%)': delta_dias_plus * 100,
        'Impacto (-10%)': delta_dias_minus * 100,
        'Sensibilidade Total': abs(delta_dias_plus - delta_dias_minus) * 100
    })

    return pd.DataFrame(resultados).sort_values('Sensibilidade Total', ascending=False)

def run_breakeven_analysis(
    base_params: Dict, 
    lista_prof_meses: list, 
    calado_design: float, 
    folga: float, 
    dias_op: float,
    target_price_freight: float
) -> Dict:
    """
    Calcula o Ponto de Equilíbrio (Break-Even) Financeiro.

    Determina o volume de carga necessário para cobrir todos os custos (fixos e variáveis)
    dado um preço de frete alvo. Também retorna indicadores de saúde financeira.

    Nota de Uso:
        Alimenta a "Aba 2: Break-Even" no `app.py`.
    """
    print(f"--- EXECUTANDO: Análise 2 - Break-Even (Preço Alvo: R$ {target_price_freight:.2f}) ---")
    
    res = _simular_ano_operacional(base_params, lista_prof_meses, calado_design, folga, dias_op)
    
    # Extração de custos para cálculo
    custo_fixo_total = res['custo_fixo_anual']
    custo_var_unitario = res['custo_variavel_anual'] / res['carga_anual'] if res['carga_anual'] > 0 else 0
    
    margem_contribuicao = target_price_freight - custo_var_unitario
    
    if margem_contribuicao <= 0:
        return {
            'viavel': False, 
            'motivo': 'Margem de Contribuição Negativa',
            'custo_variavel_por_ton': custo_var_unitario,
            'preco_frete': target_price_freight
        }
        
    # Cálculo do Ponto de Equilíbrio (Q = CF / Margem)
    break_even_ton = engine.helpers.calcular_break_even_point(custo_fixo_total, margem_contribuicao)
    
    # Viagens equivalentes
    carga_por_viagem_media = res['carga_anual'] / res['viagens_anuais'] if res['viagens_anuais'] > 0 else 0
    break_even_viagens = break_even_ton / carga_por_viagem_media if carga_por_viagem_media > 0 else 0
    
    return {
        'viavel': True,
        'break_even_ton': break_even_ton,
        'break_even_viagens': break_even_viagens,
        'capacidade_atual': res['carga_anual'],
        'ocupacao_necessaria_pct': (break_even_ton / res['carga_anual']) * 100,
        'custos_fixos_anuais_totais': custo_fixo_total,
        'custo_variavel_por_ton': custo_var_unitario,
        'margem_contribuicao_por_ton': margem_contribuicao,
        'faturamento_break_even': break_even_ton * target_price_freight,
        'lucro_projetado_cenario_base': (res['carga_anual'] * target_price_freight) - res['custo_total_anual']
    }

def run_fixed_speed_optimization(
    base_params: Dict, 
    lista_prof_meses: list, 
    calado_design: float, 
    folga: float, 
    dias_op: float,
) -> pd.DataFrame:
    """
    Otimização de Velocidade Fixa (OPEX).

    Simula o ano inteiro para diversas velocidades fixas (ex: 4 a 12 nós)
    para encontrar o ponto de mínimo custo operacional. Assume motor dimensionado
    para a velocidade testada.

    Nota de Uso:
        Alimenta a "Aba 3: Velocidade Fixa" no `app.py`.
    """
    print("--- EXECUTANDO: Análise 3 - Melhor Velocidade Fixa ---")
    
    velocidades = np.arange(4.0, 10.1, 0.1)
    resultados = []
    
    for v in velocidades:
        p_sim = base_params.copy()
        p_sim['vel_embarcacao_nos'] = v
        
        res = _simular_ano_operacional(p_sim, lista_prof_meses, calado_design, folga, dias_op)
        
        resultados.append({
            'Velocidade (nós)': v,
            'Custo (R$/t)': res['custo_unitario_R$_t'],
            'Carga Anual (t)': res['carga_anual'],
            'Viagens/Ano': res['viagens_anuais'],
            'BHP Necessário': res['bhp_instalado']
        })
        
    return pd.DataFrame(resultados)

def run_fleet_optimization(
    base_params: Dict, 
    lista_prof_meses: list, 
    calado_design: float, 
    folga: float, 
    dias_op: float,
    demanda_total: float
) -> pd.DataFrame:
    """
    Otimização de Frota (CAPEX + Escala).

    Determina o número ideal de comboios para atender uma demanda fixa de mercado.
    Considera a eficiência de escala e a "Armadilha dos Inteiros" (comboios discretos).

    Nota de Uso:
        Alimenta a "Aba 4: Otimização de Frota" no `app.py`.
    """
    print(f"--- EXECUTANDO: Análise 4 - Otimização de Frota (Demanda: {demanda_total:,.0f} t) ---")
    
    velocidades = np.arange(4.0, 10.1, 0.1)
    resultados = []
    
    for v in velocidades:
        p_sim = base_params.copy()
        p_sim['vel_embarcacao_nos'] = v
        
        # Simula 1 comboio
        res_unitario = _simular_ano_operacional(p_sim, lista_prof_meses, calado_design, folga, dias_op)
        
        # Extrapola para a frota necessária
        res_frota = _calcular_frota_demanda(res_unitario, demanda_total)
        
        resultados.append({
            'Velocidade (nós)': v,
            'Frota Necessária': res_frota['frota_necessaria'],
            'Custo Final da Demanda (R$/t)': res_frota['custo_final_por_tonelada_demandada'],
            'Investimento Total (R$)': res_frota['investimento_total_frota'],
            'Custo Op. Anual Frota (R$)': res_frota['custo_anual_operacao_frota']
        })
        
    return pd.DataFrame(resultados)

# --- ANÁLISE 5: OTIMIZAÇÃO GLOBAL (JÁ EXISTENTE REVISADA) ---
def run_global_optimization(
    params: Dict[str, Any], 
    lista_prof_meses: List[float], 
    calado_design_alvo: float, 
    folga_seguranca: float, 
    dias_base_anuais: float
) -> Dict[str, Any]:
    """
    Executa a Otimização Global de Frota utilizando algoritmo de Descida Coordenada.

    Diferente da otimização simples (que fixa a velocidade ou o motor), esta função
    encontra simultaneamente o melhor par (Motor, Perfil Operacional). Ela resolve o
    problema de otimização não-linear mista inteira (MINLP) onde:
    1. A escolha do motor (v_design) define o Custo Fixo (CAPEX) e o limite de potência.
    2. A escolha da velocidade mensal (v_op) define o Custo Variável (Combustível) e a
       Produtividade (Carga Transportada).

    O algoritmo evita o "Paradoxo de Simpson" (otimizar cada mês individualmente piora
    o resultado anual) ao otimizar diretamente a função objetivo global:
       Minimizar (Custo Total Anual / Carga Total Anual)

    Parâmetros:
        params (Dict): Parâmetros base de engenharia e custos.
        lista_prof_meses (List[float]): Perfil de profundidade do rio (12 meses).
        calado_design_alvo (float): Restrição de calado estrutural da balsa.
        folga_seguranca (float): Margem de segurança sob a quilha (UKC).
        dias_base_anuais (float): Disponibilidade anual da frota.

    Retorna:
        Dict contendo o 'melhor_cenario' (resumo), 'tabela_operacao_otima' (detalhe mensal)
        e 'historico' (curva de trade-off design vs custo).

    Nota de Uso:
        Chamada pela "Aba 5: Otimização Global" no `app.py`. É a análise mais avançada
        e computacionalmente intensiva do sistema.
    """
    print("--- EXECUTANDO: Otimização Global (Coordinate Descent) ---")
    
    # 1. Definição do Espaço de Busca de Design (Motores)
    # Iteramos sobre "Velocidades de Projeto". Cada velocidade define implicitamente
    # um tamanho de motor (BHP) necessário para atingir essa velocidade na pior condição
    # (cheia/carga máxima). Isso discretiza o problema de investimento (CAPEX).
    velocidades_projeto = np.arange(4.0, 10.1, 0.1) 
    dias_op_por_mes = dias_base_anuais / 12.0
    
    melhor_cenario_global = None
    melhor_tabela_mensal_global = []
    menor_custo_global = float('inf')
    historico_simulacoes = []
    
    # --- LOOP EXTERNO: Decisão de Investimento (CAPEX) ---
    # Para cada motor possível que podemos comprar...
    for v_design in velocidades_projeto:
        
        # A. Dimensionamento do Motor (Fixo para este loop)
        # Calculamos qual o BHP necessário para garantir a 'v_design' mesmo no cenário
        # de maior resistência hidrodinâmica (calado máximo). Isso define o "Teto de Potência".
        calado_maximo = min(calado_design_alvo, max(lista_prof_meses) - folga_seguranca)
        
        n_long, n_par = engine.helpers.calcular_arranjo_comboio(
            params['comp_balsa'], params['boca_balsa'], 
            params['raio_curvatura'], params['largura_canal']
        )
        
        # Deslocamento máximo (Fully Loaded) para dimensionamento conservador
        vol_desloc_max = engine.helpers.calcular_volume_operacional_balsa(
            params['comp_balsa'], params['boca_balsa'], calado_maximo, params['coef_bloco']
        ) * (n_long * n_par)
        
        # Potência Instalada (BHP): O limite físico do motor comprado
        bhp_instalado = engine.helpers.calcular_bhp_propulsao(
            vol_desloc_max, params['comp_balsa'], params['boca_balsa'],
            n_long, n_par, v_design, params['eficiencia_propulsor']
        )
        
        # Cálculo do Custo Fixo Anual (Constante para este design)
        # Inclui o custo de capital (amortização do motor+balsas) e custos fixos de operação.
        res_capex = engine.calcular_capex(
            params['comp_balsa'], params['boca_balsa'], params['pontal_balsa'],
            n_long, n_par, bhp_instalado, params['taxa_juros_input'], params['vida_util_anos']
        )
        res_opex_fixo = engine.calcular_opex_fixo(
            res_capex['investimento_total'], params['num_tripulantes'],
            params['salario_medio'], params['vale_alimentacao'], params['encargos_sociais_pct']
        )
        CUSTO_FIXO_ANUAL = res_capex['custo_capex_anual'] + res_opex_fixo['custos_fixos_anuais_total']

        # --- B. Pré-Cálculo das Opções Operacionais (Lookup Table) ---
        # Em vez de simular tudo dentro do loop de otimização, pré-calculamos todas as
        # possibilidades físicas viáveis para cada mês. Isso acelera o algoritmo drasticamente.
        opcoes_meses = [] # Lista de listas de dicionários
        
        # Testamos operar de 3.0 nós até um pouco acima do design (para casos de calado leve onde sobra motor)
        velocidades_op_teste = np.arange(3.0, v_design + 2.0, 0.1)
        design_valido = True

        for prof_mes in lista_prof_meses:
            calado_mes = min(calado_design_alvo, prof_mes - folga_seguranca)
            opcoes_deste_mes = []
            
            for v_op in velocidades_op_teste:
                # Check Físico de Potência: O motor aguenta essa velocidade neste calado?
                # Recalculamos a demanda de potência para a condição específica do mês (calado atual).
                vol_desloc_atual = engine.helpers.calcular_volume_operacional_balsa(
                    params['comp_balsa'], params['boca_balsa'], calado_mes, params['coef_bloco']
                ) * (n_long * n_par)
                
                bhp_necessario = engine.helpers.calcular_bhp_propulsao(
                    vol_desloc_atual, params['comp_balsa'], params['boca_balsa'],
                    n_long, n_par, v_op, params['eficiencia_propulsor']
                )
                
                # Restrição Física: Se a potência exigida > instalada, essa velocidade é impossível.
                # Tolerância de 0.1% para erros de ponto flutuante.
                if bhp_necessario > (bhp_instalado * 1.001): 
                    continue

                # Se passou no check físico, calculamos os custos variáveis (Combustível)
                res_var = engine.calcular_opex_variavel(
                    distancia_km=params['dist_km_input'],
                    dias_operacao_periodo=dias_op_por_mes,
                    vel_embarcacao_nos=v_op,
                    vel_correnteza_nos=params['vel_correnteza_nos'],
                    calado_operacional=calado_mes,
                    comp_balsa=params['comp_balsa'],
                    boca_balsa=params['boca_balsa'],
                    pontal_balsa=params['pontal_balsa'],
                    coef_bloco=params['coef_bloco'],
                    num_balsas_long=n_long,
                    num_balsas_par=n_par,
                    eficiencia_propulsor=params['eficiencia_propulsor'],
                    tempo_eclusa_por_viagem_min=params['t_eclusagem_min'],
                    tempo_manobra_por_balsa_min=params['t_manobra_balsa_min'],
                    prod_carregamento_th=params['prod_carregamento'],
                    prod_descarregamento_th=params['prod_descarregamento'],
                    num_bercos=params['num_bercos'],
                    consumo_especifico_motor=params['consumo_motor_fc'],
                    preco_combustivel=params['preco_combustivel'],
                    densidade_combustivel=params['densidade_combustivel']
                )
                
                # Armazenamos apenas as opções que geram transporte efetivo (viagens > 0)
                if res_var['carga_total_transportada'] > 0:
                    opcoes_deste_mes.append({
                        'v_op': v_op,
                        'carga': res_var['carga_total_transportada'],
                        'custo_var': res_var['custo_variavel_total'] * 1.10, # Adiciona overhead variável (Admin)
                        'calado': calado_mes,
                        'emissoes': res_var['emissoes_co2_ton']
                    })
            
            # Se em algum mês não houver NENHUMA velocidade viável (ex: motor muito fraco para a correnteza),
            # o design inteiro é inválido.
            if not opcoes_deste_mes:
                design_valido = False
                break
            opcoes_meses.append(opcoes_deste_mes)
        
        if not design_valido: continue

        # --- C. Otimização Global (Algoritmo de Descida Coordenada) ---
        # Aqui resolvemos o problema combinatório: Qual conjunto de 12 velocidades (uma por mês)
        # minimiza a média anual global?
        
        # Estado inicial: Começamos escolhendo a velocidade mediana disponível para cada mês
        indices_escolhidos = [len(opts)//2 for opts in opcoes_meses]
        
        melhorou = True
        # Loop de convergência: Continua refinando até não conseguir mais baixar o custo global
        while melhorou:
            melhorou = False
            
            # Calcula o Custo Global com a configuração atual
            total_carga = sum(opcoes_meses[m][i]['carga'] for m, i in enumerate(indices_escolhidos))
            total_custo_var = sum(opcoes_meses[m][i]['custo_var'] for m, i in enumerate(indices_escolhidos))
            
            # Função Objetivo Global: (Fixo + Variável Total) / Carga Total
            custo_global_atual = (CUSTO_FIXO_ANUAL + total_custo_var) / total_carga
            
            # Tenta otimizar um mês de cada vez (Coordinate Descent)
            for m in range(12):
                idx_atual = indices_escolhidos[m]
                
                # Remove a contribuição deste mês do total para simular a troca
                base_carga = total_carga - opcoes_meses[m][idx_atual]['carga']
                base_custo_var = total_custo_var - opcoes_meses[m][idx_atual]['custo_var']
                
                # Testa TODAS as opções de velocidade disponíveis para este mês
                # verificando qual delas, quando combinada com os outros 11 meses fixos,
                # resulta na menor média global.
                melhor_idx_mes = idx_atual
                min_custo_global_teste = custo_global_atual
                
                for i, opcao in enumerate(opcoes_meses[m]):
                    novo_global = (CUSTO_FIXO_ANUAL + base_custo_var + opcao['custo_var']) / (base_carga + opcao['carga'])
                    
                    if novo_global < min_custo_global_teste:
                        min_custo_global_teste = novo_global
                        melhor_idx_mes = i
                
                # Se encontrou uma velocidade melhor para este mês, atualiza o estado global
                if melhor_idx_mes != idx_atual:
                    indices_escolhidos[m] = melhor_idx_mes
                    # Atualiza os totais para a próxima iteração do loop de meses
                    total_carga = base_carga + opcoes_meses[m][melhor_idx_mes]['carga']
                    total_custo_var = base_custo_var + opcoes_meses[m][melhor_idx_mes]['custo_var']
                    custo_global_atual = min_custo_global_teste
                    melhorou = True # Sinaliza que houve mudança, então deve rodar o loop while novamente

        # --- D. Registro e Comparação do Design Otimizado ---
        if custo_global_atual < menor_custo_global:
            menor_custo_global = custo_global_atual

            # Calcular totais finais do cenário vencedor
            total_emissoes_global = sum(opcoes_meses[m][i]['emissoes'] for m, i in enumerate(indices_escolhidos))
            
            # Reconstrói a tabela detalhada do melhor cenário para exibição
            tabela_detalhada = []
            for m, idx in enumerate(indices_escolhidos):
                opt = opcoes_meses[m][idx]
                # Custo unitário mensal (apenas indicativo, pois a otimização foi global)
                custo_mes_visual = ( (CUSTO_FIXO_ANUAL/12) + opt['custo_var'] ) / opt['carga']
                
                tabela_detalhada.append({
                    'Mes': m + 1,
                    'Calado (m)': opt['calado'],
                    'Velocidade Op (nós)': opt['v_op'],
                    'Custo Mês (R$/t)': custo_mes_visual, 
                    'Carga (t)': opt['carga'],
                    'Emissões (tCO2)': opt['emissoes']
                })
            
            melhor_cenario_global = {
                'v_design_otima': v_design,
                'bhp_ideal': bhp_instalado,
                'custo_minimo_global': menor_custo_global,
                'investimento_inicial': res_capex['investimento_total'],
                'carga_anual': total_carga,
                'emissoes_total': total_emissoes_global,
                'intensidade_co2': (total_emissoes_global * 1000) / total_carga if total_carga > 0 else 0
            }

            melhor_tabela_mensal_global = tabela_detalhada
            
        historico_simulacoes.append({
            'v_design': v_design,
            'custo_ton': custo_global_atual
        })

    return {
        'melhor_cenario': melhor_cenario_global,
        'tabela_operacao_otima': pd.DataFrame(melhor_tabela_mensal_global),
        'historico': pd.DataFrame(historico_simulacoes)
    }

def run_profitability_matrix_analysis(
    df_frota: pd.DataFrame, 
    demanda_total: float, 
    preco_frete_base: float
) -> Dict[str, pd.DataFrame]:
    """
    Gera matrizes de sensibilidade (Preço x Velocidade) para Lucro e Margem.

    Nota de Uso:
        Alimenta a "Aba 6: Matriz de Lucro" no `app.py`.
    """
    print(f"--- EXECUTANDO: Análise 6 - Matrizes de Lucratividade (Base Frete: R$ {preco_frete_base:.2f}) ---")
    
    faixa_variacao = 5.0
    passo = 0.50
    precos_teste = np.arange(preco_frete_base - faixa_variacao, preco_frete_base + faixa_variacao + 0.01, passo)
    
    if 'Velocidade (nós)' in df_frota.columns:
        df_base = df_frota.set_index('Velocidade (nós)')[['Custo Final da Demanda (R$/t)']].copy()
    else:
        df_base = df_frota[['Custo Final da Demanda (R$/t)']].copy()
        
    df_base.rename(columns={'Custo Final da Demanda (R$/t)': 'Custo (R$/t)'}, inplace=True)
    
    df_lucro = df_base.copy()
    df_margem = df_base.copy()
    
    for preco in precos_teste:
        col_label = f"R$ {preco:.2f}"
        
        # Lucro Anual (Milhões)
        lucro_col = (preco - df_base['Custo (R$/t)']) * demanda_total / 1_000_000.0
        df_lucro[col_label] = lucro_col
        
        # Margem (%)
        margem_col = ((preco - df_base['Custo (R$/t)']) / preco) * 100.0
        df_margem[col_label] = margem_col
        
    return {
        'lucro_milhoes': df_lucro,
        'margem_pct': df_margem
    }

def run_environmental_analysis(
    base_params: Dict, 
    lista_prof_meses: list, 
    calado_design: float, 
    folga: float, 
    dias_op: float
) -> pd.DataFrame:
    """
    Análise Ambiental: Emissões de CO2 vs Velocidade.

    Calcula a pegada de carbono para diversas velocidades fixas, permitindo
    visualizar o trade-off entre custo financeiro e custo ambiental.

    Nota de Uso:
        Alimenta a "Aba 7: Sustentabilidade" no `app.py`.
    """
    print("--- EXECUTANDO: Análise 7 - Sustentabilidade (CO2) ---")
    
    velocidades = np.arange(4.0, 10.1, 0.1)
    resultados = []
    
    for v in velocidades:
        p_sim = base_params.copy()
        p_sim['vel_embarcacao_nos'] = v
        
        res = _simular_ano_operacional(p_sim, lista_prof_meses, calado_design, folga, dias_op)
        
        resultados.append({
            'Velocidade (nós)': v,
            'Emissões Totais (tCO2)': res['emissoes_total_ton'],
            'Intensidade (kgCO2/t)': res['intensidade_carbono_kg_t'],
            'Carga Total (t)': res['carga_anual'],
            'Custo (R$/t)': res['custo_unitario_R$_t']
        })
        
    return pd.DataFrame(resultados)

if __name__ == "__main__":
    import pandas as pd
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)

    # MOCK DATA
    LISTA_PROF = [
        7.72, 9.87, 10.86, 10.98, 8.43, 6.35, 
        5.12, 3.89, 3.30, 3.00, 3.65, 5.23
    ]
    MOCK_PARAMS = {
        # Trajeto
        "comp_balsa": 60.96, "boca_balsa": 10.67, "pontal_balsa": 4.27,
        "coef_bloco": 0.90, "raio_curvatura": 800.0, "largura_canal": 100.0,
        "dist_km_input": 1000.0, "t_eclusagem_min": 0.0, "t_manobra_balsa_min": 20.0,
        
        # Operação (Velocidade será sobrescrita pelo otimizador)
        "vel_embarcacao_nos": 6.0, # Valor dummy, o otimizador vai variar isso
        "vel_correnteza_nos": 2.0, "num_bercos": 2,
        "prod_carregamento": 2000, "prod_descarregamento": 1000,
        "num_tripulantes": 8, "eficiencia_propulsor": 0.50,
        
        # Finanças
        "demanda_anual": 10_000_000, "taxa_juros_input": 0.15, "vida_util_anos": 20,
        "preco_combustivel": 4.50, "consumo_motor_fc": 0.16, "densidade_combustivel": 0.85,
        "salario_medio": 5000.0, "vale_alimentacao": 800.0, "encargos_sociais_pct": 0.90
    }
    CALADO = 3.66
    FOLGA = 0.5
    DIAS = 330.0

    print("\n=== TESTE DE ANÁLISES ===")
    
    # 1. Sensibilidade
    df_sens = run_sensitivity_analysis(MOCK_PARAMS, LISTA_PROF, CALADO, FOLGA, DIAS)
    print("\n[1] Sensibilidade (Top 3 Impactos):")
    print(df_sens.head(8).to_string(index=False))
    
    # 2. Break-Even
    res_be = run_breakeven_analysis(MOCK_PARAMS, LISTA_PROF, CALADO, FOLGA, DIAS, target_price_freight=40.00)
    print(f"\n[2] Break-Even: {res_be['break_even_ton']:,.0f} t ({res_be['ocupacao_necessaria_pct']:.1f}% ocupação)")
    
    # 3. Velocidade Fixa
    df_fixa = run_fixed_speed_optimization(MOCK_PARAMS, LISTA_PROF, CALADO, FOLGA, DIAS)
    best_fixa = df_fixa.loc[df_fixa['Custo (R$/t)'].idxmin()]
    print(f"\n[3] Melhor Vel. Fixa: {best_fixa['Velocidade (nós)']} nós -> R$ {best_fixa['Custo (R$/t)']:.2f}/t")
    
    # 4. Frota
    df_frota = run_fleet_optimization(MOCK_PARAMS, LISTA_PROF, CALADO, FOLGA, DIAS, demanda_total=2_000_000)
    best_frota = df_frota.loc[df_frota['Custo Final da Demanda (R$/t)'].idxmin()]
    print(f"\n[4] Melhor Frota: {best_frota['Frota Necessária']:.0f} comboios @ {best_frota['Velocidade (nós)']} nós -> R$ {best_frota['Custo Final da Demanda (R$/t)']:.2f}/t")

    # 5. Otimização Global
    print("\n--- [5] RODANDO OTIMIZAÇÃO GLOBAL (COORDINATE DESCENT) ---")
    res_global = run_global_optimization(
        params=MOCK_PARAMS,
        lista_prof_meses=LISTA_PROF,
        calado_design_alvo=CALADO,
        folga_seguranca=FOLGA,
        dias_base_anuais=DIAS
    )
    
    if res_global and res_global.get('melhor_cenario'):
        best = res_global['melhor_cenario']
        df_operacao = res_global['tabela_operacao_otima']
        
        print("\n>>> VENCEDOR GLOBAL <<<")
        print(f"Velocidade de Projeto (Motor): {best['v_design_otima']:.1f} nós")
        print(f"Potência Instalada (BHP):      {best['bhp_ideal']:.0f} HP")
        print(f"Investimento (CAPEX):          R$ {best['investimento_inicial']:,.2f}")
        print(f"CUSTO MÍNIMO GLOBAL:           R$ {best['custo_minimo_global']:.2f} / t")
        
        if not df_operacao.empty:
            print("\n>>> PLANO DE OPERAÇÃO MENSAL OTIMIZADO <<<")
            print(df_operacao[['Mes', 'Calado (m)', 'Velocidade Op (nós)', 'Custo Mês (R$/t)', 'Carga (t)', 'Emissões (tCO2)']].to_string(index=False, float_format=lambda x: "{:.2f}".format(x)))
    else:
        print("\n>>> OTIMIZAÇÃO GLOBAL NÃO ENCONTROU SOLUÇÃO VIÁVEL <<<")