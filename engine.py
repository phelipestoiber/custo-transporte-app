# engine.py
import math
from typing import Dict, Any
from helpers import *

def calcular_opex_variavel(
    # Inputs de Cenário
    distancia_km: float,
    dias_operacao_periodo: float,
    
    # Inputs de Engenharia e Operação
    vel_embarcacao_nos: float,
    vel_correnteza_nos: float,
    calado_operacional: float,
    comp_balsa: float,
    boca_balsa: float,
    pontal_balsa: float,
    coef_bloco: float,
    num_balsas_long: int,
    num_balsas_par: int,
    eficiencia_propulsor: float,
    
    # Inputs de Tempos
    tempo_eclusa_por_viagem_min: float,
    tempo_manobra_por_balsa_min: float,
    prod_carregamento_th: float,
    prod_descarregamento_th: float,
    num_bercos: int,
    
    # Inputs de Custo e Combustível
    consumo_especifico_motor: float, # kg/HP/h
    preco_combustivel: float,
    densidade_combustivel: float
) -> Dict[str, Any]:
    """
    Calcula os Custos Operacionais Variáveis (Combustível) e métricas de performance.
    Também determina o BHP necessário, que será usado no CAPEX.

    Retorna um dicionário com:
    - 'custo_variavel_total': R$ total no período
    - 'bhp_requerido': Potência necessária (para CAPEX)
    - 'num_viagens': Quantidade de viagens realizadas
    - 'carga_total_periodo': Toneladas transportadas
    - 'consumo_total_kg': Para métricas ESG
    """
    
    # 1. Cálculos Físicos da Balsa e Comboio
    peso_leve = calcular_peso_leve_balsa(comp_balsa, boca_balsa, pontal_balsa)
    vol_deslocado_balsa = calcular_volume_operacional_balsa(
        comp_balsa, boca_balsa, calado_operacional, coef_bloco
    )
    cap_carga_balsa = calcular_capacidade_carga_balsa(vol_deslocado_balsa, peso_leve)
    
    num_total_balsas = num_balsas_long * num_balsas_par
    carga_por_viagem_comboio = cap_carga_balsa * num_total_balsas
    vol_deslocado_comboio = vol_deslocado_balsa * num_total_balsas

    # 2. Cálculo de Tempos de Ciclo
    v_ida, v_volta = calcular_velocidades_solo(vel_embarcacao_nos, vel_correnteza_nos)
    
    tempo_nav_h = calcular_tempo_viagem_puro(distancia_km, v_ida, v_volta)
    
    tempo_porto_h = calcular_tempo_porto_total(
        carga_por_viagem_comboio, prod_carregamento_th, prod_descarregamento_th, num_bercos
    )
    
    tempo_manobra_h = calcular_tempo_manobras_e_eclusas(
        tempo_eclusa_por_viagem_min, tempo_manobra_por_balsa_min, num_total_balsas
    )
    
    tempo_ciclo_total_h = tempo_nav_h + tempo_porto_h + tempo_manobra_h
    
    # 3. Produtividade (Viagens)
    num_viagens = calcular_numero_viagens_periodo(tempo_ciclo_total_h, dias_operacao_periodo)
    
    # 4. Potência e Consumo
    bhp_principal = calcular_bhp_propulsao(
        vol_deslocado_comboio, comp_balsa, boca_balsa, 
        num_balsas_long, num_balsas_par, vel_embarcacao_nos, eficiencia_propulsor
    )
    
    bhp_auxiliar = calcular_bhp_auxiliar(bhp_principal)
    
    # Consumo Principal: Apenas navegando
    consumo_principal_kg = calcular_consumo_motor_kg(
        bhp_principal, tempo_nav_h, consumo_especifico_motor
    )
    
    # Consumo Auxiliar: Todo o ciclo (navegação + porto + manobras)
    # Assumindo que geradores rodam 100% do tempo
    consumo_auxiliar_kg = calcular_consumo_motor_kg(
        bhp_auxiliar, tempo_ciclo_total_h, consumo_especifico_motor
    )
    
    consumo_total_ciclo_kg = consumo_principal_kg + consumo_auxiliar_kg
    consumo_total_periodo_kg = consumo_total_ciclo_kg * num_viagens
    
    # 5. Custo Monetário
    custo_combustivel_periodo = calcular_custo_monetario_combustivel(
        consumo_total_periodo_kg, preco_combustivel, densidade_combustivel
    )
    
    # Emissões (Bônus)
    emissoes_co2 = calcular_emissoes_co2(consumo_total_periodo_kg)

    return {
        "custo_variavel_total": custo_combustivel_periodo,
        "custo_combustivel": custo_combustivel_periodo, # Alias para clareza
        "bhp_requerido": bhp_principal,
        "num_viagens": num_viagens,
        "carga_total_transportada": carga_por_viagem_comboio * num_viagens,
        "carga_por_viagem": carga_por_viagem_comboio,
        "consumo_total_kg": consumo_total_periodo_kg,
        "emissoes_co2_ton": emissoes_co2 / 1000.0,
        "tempo_ciclo_h": tempo_ciclo_total_h,
        "tempo_navegacao_h": tempo_nav_h
    }

def calcular_capex(
    # Inputs de Engenharia
    comp_balsa: float,
    boca_balsa: float,
    pontal_balsa: float,
    num_balsas_long: int,
    num_balsas_par: int,
    bhp_instalado: float,
    
    # Inputs Financeiros
    taxa_juros_anual: float,
    vida_util_anos: int
) -> Dict[str, Any]:
    """
    Calcula os Custos de Capital (Investimento e Amortização).
    
    Lógica:
    1. Estima custo de construção das balsas (função do peso de aço).
    2. Estima custo de construção do empurrador (função da potência instalada).
    3. Anualiza o investimento total usando o FRC (Fator de Recuperação de Capital).
    
    Args:
        bhp_instalado: Potência total dos motores principais (HP).
        [Outros]: Dimensões e parâmetros financeiros.
        
    Returns:
        Dict com breakdown dos custos de capital (Total e Anual).
    """
    
    # 1. Custo das Balsas
    peso_leve_unitario = calcular_peso_leve_balsa(comp_balsa, boca_balsa, pontal_balsa)
    custo_unitario_balsa = estimar_custo_construcao_balsa(peso_leve_unitario)
    
    num_total_balsas = num_balsas_long * num_balsas_par
    custo_total_balsas = custo_unitario_balsa * num_total_balsas
    
    # 2. Custo do Empurrador
    custo_total_empurrador = estimar_custo_construcao_empurrador(bhp_instalado)
    
    # 3. Investimento Total (Principal)
    investimento_inicial_total = custo_total_balsas + custo_total_empurrador
    
    # 4. Anualização (Engenharia Econômica)
    frc = calcular_fator_recuperacao_capital(taxa_juros_anual, vida_util_anos)
    capex_anual = investimento_inicial_total * frc
    
    return {
        "custo_capex_anual": capex_anual,
        "investimento_total": investimento_inicial_total,
        "investimento_balsas": custo_total_balsas,
        "investimento_empurrador": custo_total_empurrador,
        "custo_unitario_balsa": custo_unitario_balsa,
        "frc": frc,
        "vida_util_anos": vida_util_anos,
        "taxa_juros": taxa_juros_anual
    }

def calcular_opex_fixo(
    # Input Financeiro (Vindo do CAPEX)
    investimento_total_frota: float,
    
    # Inputs de Operação e RH
    num_tripulantes: float,
    salario_medio: float,
    vale_alimentacao: float,
    encargos_sociais_pct: float
) -> Dict[str, Any]:
    """
    Calcula os Custos Operacionais Fixos Anuais (Tripulação, Manutenção, Seguros, Admin).
    
    Lógica:
    1. Calcula custos de RH (Salários + Encargos + Alimentação).
    2. Estima Manutenção e Seguros como % do valor do ativo (Investimento).
    3. Calcula Overhead Administrativo Fixo (10% da base fixa).
    
    Args:
        investimento_total_frota: Valor total de aquisição (Empurrador + Balsas).
        
    Returns:
        Dict com o breakdown dos custos fixos anuais.
    """
    
    # 1. Recursos Humanos (Tripulação)
    custo_tripulacao = calcular_custo_anual_tripulacao(
        num_tripulantes, salario_medio, encargos_sociais_pct
    )
    
    custo_alimentacao = calcular_custo_anual_alimentacao(
        num_tripulantes, vale_alimentacao
    )
    
    # 2. Custos Baseados no Ativo (Manutenção e Seguros)
    custo_manutencao = estimar_custo_manutencao_anual(investimento_total_frota)
    custo_seguros = estimar_custo_seguro_anual(investimento_total_frota)
    
    # Soma da Base de Custos Fixos
    custos_fixos_base = (
        custo_tripulacao + 
        custo_alimentacao + 
        custo_manutencao + 
        custo_seguros
    )
    
    # 3. Administrativo Fixo (Overhead)
    # Regra de Negócio: 10% sobre a base de custos fixos
    # (Nota: O Admin Variável sobre combustível será somado depois no Custo Total)
    custo_admin_fixo = 0.10 * custos_fixos_base
    
    custos_fixos_totais = custos_fixos_base + custo_admin_fixo
    
    return {
        "custos_fixos_anuais_total": custos_fixos_totais,
        "custo_tripulacao": custo_tripulacao,
        "custo_alimentacao": custo_alimentacao,
        "custo_manutencao": custo_manutencao,
        "custo_seguros": custo_seguros,
        "custo_admin_fixo": custo_admin_fixo,
        "custos_fixos_base": custos_fixos_base # Sem admin
    }

# engine.py (Adicione isso após as funções calcular_capex, calcular_opex_fixo, etc.)

def calcular_custos_comboio(
    # Parâmetros de Simulação (Variáveis)
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
    num_bercos: int,
    prod_carregamento: float,
    prod_descarregamento: float,
    num_tripulantes: int,
    eficiencia_propulsor: float,
    
    # Parâmetros Financeiros e de Custo
    demanda_anual: float, # Apenas para repassar ou cálculo de frota
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
    Função Wrapper (Orquestradora) para manter compatibilidade com analysis.py.
    
    Ela coordena a chamada das funções modulares:
    1. Define arranjo (Helpers)
    2. Calcula Operação e Combustível (OPEX Variável) -> define BHP necessário
    3. Calcula Investimento (CAPEX) -> baseada no BHP
    4. Calcula Custos Fixos (OPEX Fixo) -> baseada no Investimento
    5. Consolida resultados.
    """
    
    # 1. Definição do Arranjo do Comboio (Engenharia)
    n_long, n_par = calcular_arranjo_comboio(
        comp_balsa, boca_balsa, raio_curvatura, largura_canal
    )
    
    # 2. Cálculo Operacional e Variável (Motor Físico)
    # Precisamos rodar isso primeiro para descobrir o BHP necessário para o CAPEX
    res_var = calcular_opex_variavel(
        distancia_km=dist_km_input,
        dias_operacao_periodo=dias_operacao_input,
        vel_embarcacao_nos=vel_embarcacao_nos,
        vel_correnteza_nos=vel_correnteza_nos,
        calado_operacional=calado_op_input,
        comp_balsa=comp_balsa,
        boca_balsa=boca_balsa,
        pontal_balsa=pontal_balsa,
        coef_bloco=coef_bloco,
        num_balsas_long=n_long,
        num_balsas_par=n_par,
        eficiencia_propulsor=eficiencia_propulsor,
        tempo_eclusa_por_viagem_min=t_eclusagem_min,
        tempo_manobra_por_balsa_min=t_manobra_balsa_min,
        prod_carregamento_th=prod_carregamento,
        prod_descarregamento_th=prod_descarregamento,
        num_bercos=num_bercos,
        consumo_especifico_motor=consumo_motor_fc,
        preco_combustivel=preco_combustivel,
        densidade_combustivel=densidade_combustivel
    )
    
    # 3. Cálculo de Capital (Investimento)
    # Usa o BHP calculado na etapa anterior
    res_capex = calcular_capex(
        comp_balsa=comp_balsa,
        boca_balsa=boca_balsa,
        pontal_balsa=pontal_balsa,
        num_balsas_long=n_long,
        num_balsas_par=n_par,
        bhp_instalado=res_var['bhp_requerido'], 
        taxa_juros_anual=taxa_juros_input,
        vida_util_anos=vida_util_anos
    )
    
    # 4. Cálculo de Custos Fixos (OPEX Fixo)
    # Usa o valor do investimento calculado na etapa anterior
    res_fixo = calcular_opex_fixo(
        investimento_total_frota=res_capex['investimento_total'],
        num_tripulantes=num_tripulantes,
        salario_medio=salario_medio,
        vale_alimentacao=vale_alimentacao,
        encargos_sociais_pct=encargos_sociais_pct
    )
    
    # 5. Consolidação e Custos Administrativos Variáveis
    # Regra: 10% sobre o combustível (Variável)
    # O admin fixo já veio dentro de res_fixo['custo_admin_fixo']
    custo_admin_variavel = 0.10 * res_var['custo_variavel_total']
    
    # Totais
    custo_total_anual = (
        res_capex['custo_capex_anual'] +           # Capital
        res_fixo['custos_fixos_anuais_total'] +    # Fixo (Pessoal, Manut, Seguro, Admin Fixo)
        res_var['custo_variavel_total'] +          # Combustível
        custo_admin_variavel                       # Admin Variável
    )
    
    carga_total = res_var['carga_total_transportada']
    custo_por_tonelada = custo_total_anual / carga_total if carga_total > 0 else 0.0
    
    # Monta o dicionário final compatível com analysis.py
    resultados = {
        # Métricas Principais
        'custo_total_anual': custo_total_anual,
        'custo_por_tonelada': custo_por_tonelada,
        'carga_total_ano': carga_total,
        'num_viagens_ano': res_var['num_viagens'],
        'cap_carga_comboio': res_var['carga_por_viagem'],
        
        # Breakdowns para Análise
        'custos_fixos_anuais_total': res_fixo['custos_fixos_anuais_total'] + res_capex['custo_capex_anual'], # Fixo Operacional + Capital
        'custos_variaveis_total': res_var['custo_variavel_total'] + custo_admin_variavel,
        
        'custo_capex_anual_puro': res_capex['custo_capex_anual'],
        'custo_capex_anual_total': res_capex['custo_capex_anual'], # Alias para compatibilidade
        
        'custo_variavel_combustivel_puro': res_var['custo_variavel_total'],
        'custo_admin_variavel': custo_admin_variavel,
        'custo_admin_fixo': res_fixo['custo_admin_fixo'],
        
        # Detalhes para gráficos de pizza
        'custo_anual_tripulacao': res_fixo['custo_tripulacao'],
        'custo_anual_alimentacao': res_fixo['custo_alimentacao'],
        'custo_anual_manutencao': res_fixo['custo_manutencao'],
        'custo_anual_seguradora': res_fixo['custo_seguros'],
        
        # Dados de Engenharia
        'num_balsas_longitudinal': n_long,
        'num_balsas_paralela': n_par,
        'bhp_requerido': res_var['bhp_requerido']
    }
    
    return resultados

if __name__ == "__main__":
    import pandas as pd
    
    # --- CONFIGURAÇÃO VISUAL DO PANDAS (Para o Terminal) ---
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', lambda x: '{:,.2f}'.format(x).replace(',', 'X').replace('.', ',').replace('X', '.'))

    print("\n" + "█"*100)
    print("⚓  RELATÓRIO TÉCNICO DE VALIDAÇÃO: ENGINE DE CÁLCULO  ⚓".center(100))
    print("█"*100)

    # --- 1. INPUTS DE CENÁRIO (MOCK DATA) ---
    # Dados de Rio (Perfil Anual Típico Amazônico)
    profundidades_rio = [
    7.72, 9.87, 10.86, 10.98, 8.43, 6.35, 
    5.12, 3.89, 3.30, 3.00, 3.65, 5.23
    ]
    
    # Engenharia Naval
    L_BALSA, B_BALSA, H_BALSA, T_PROJETO = 60.96, 10.67, 4.27, 3.66
    FOLGA_SEGURANCA = 0.5
    CB_BALSA = 0.90
    
    # Operação
    RAIO_CURVA = 800.0
    LARGURA_CANAL = 100.0
    VEL_ALVO = 5.8
    VEL_CORRENTEZA = 2.0
    DISTANCIA = 1000.0
    DIAS_OP_MES = 27.5
    T_MANOBRA = 20.0
    T_ECLUSA = 0.0
    
    # Portos
    PROD_CARGA, PROD_DESCARGA, NUM_BERCOS = 2000, 1000, 2
    
    # Custos
    PRECO_DIESEL = 4.50
    DENSIDADE_DIESEL = 0.85
    FC_MOTOR = 0.16
    
    # Financeiro
    TAXA_JUROS = 0.15
    VIDA_UTIL = 20
    DEMANDA_ANUAL = 10_000_000
    
    # RH
    NUM_TRIPULANTES = 8
    SALARIO_MEDIO = 5000.0
    VALE_ALIMENTACAO = 800.0
    ENCARGOS_SOCIAIS = 0.90

    # --- 2. SIMULAÇÃO DE PERFORMANCE (LOOP MENSAL) ---
    print(f"\n>>> 1. ANÁLISE DE PERFORMANCE OPERACIONAL (MÊS A MÊS)")
    print(f"    Rota: {DISTANCIA} km | Velocidade Alvo: {VEL_ALVO} nós | Correnteza: {VEL_CORRENTEZA} nós")
    
    # Cálculo do Arranjo
    n_long, n_par = calcular_arranjo_comboio(L_BALSA, B_BALSA, RAIO_CURVA, LARGURA_CANAL)
    
    registros_mensais = []
    max_bhp_necessario = 0.0
    
    for i, prof_rio in enumerate(profundidades_rio):
        # a. Calado
        calado_mes = calcular_calado_maximo_operacional(prof_rio, FOLGA_SEGURANCA, T_PROJETO)
        
        # b. Engine
        res = calcular_opex_variavel(
            distancia_km=DISTANCIA, dias_operacao_periodo=DIAS_OP_MES,
            vel_embarcacao_nos=VEL_ALVO, vel_correnteza_nos=VEL_CORRENTEZA,
            calado_operacional=calado_mes,
            comp_balsa=L_BALSA, boca_balsa=B_BALSA, pontal_balsa=H_BALSA, coef_bloco=CB_BALSA,
            num_balsas_long=n_long, num_balsas_par=n_par, eficiencia_propulsor=0.50,
            tempo_eclusa_por_viagem_min=T_ECLUSA, tempo_manobra_por_balsa_min=T_MANOBRA,
            prod_carregamento_th=PROD_CARGA, prod_descarregamento_th=PROD_DESCARGA, num_bercos=NUM_BERCOS,
            consumo_especifico_motor=FC_MOTOR, preco_combustivel=PRECO_DIESEL, densidade_combustivel=DENSIDADE_DIESEL
        )
        
        # c. Rastrear Pico de Potência
        if res['bhp_requerido'] > max_bhp_necessario:
            max_bhp_necessario = res['bhp_requerido']
            
        # d. Salvar dados para tabela
        linha = {
            "Mês": i + 1,
            "Rio (m)": prof_rio,
            "Calado (m)": calado_mes,
            "Carga (t)": res['carga_total_transportada'],
            "Viagens": res['num_viagens'],
            "BHP Req.": res['bhp_requerido'],
            "Consumo (L)": res['consumo_total_kg'] / DENSIDADE_DIESEL, # Convertendo para Litros para visualização
            "Custo Comb. (R$)": res['custo_variavel_total']
        }
        registros_mensais.append(linha)

    # Criar DataFrame
    df_ops = pd.DataFrame(registros_mensais)
    
    # Adicionar linha de Total/Média
    totais = {
        "Mês": "TOTAL",
        "Rio (m)": df_ops["Rio (m)"].mean(),
        "Calado (m)": df_ops["Calado (m)"].mean(),
        "Carga (t)": df_ops["Carga (t)"].sum(),
        "Viagens": df_ops["Viagens"].sum(),
        "BHP Req.": df_ops["BHP Req."].max(), # Pico
        "Consumo (L)": df_ops["Consumo (L)"].sum(),
        "Custo Comb. (R$)": df_ops["Custo Comb. (R$)"].sum()
    }
    
    # Concatenar totais (método moderno do pandas)
    df_final = pd.concat([df_ops, pd.DataFrame([totais])], ignore_index=True)
    
    print(df_final.to_string(index=False))
    print("-" * 100)

    # --- 3. ANÁLISE DE CAPEX ---
    print(f"\n>>> 2. ESTRUTURA DE CAPITAL (CAPEX)")
    print(f"    Dimensionamento Motor: {max_bhp_necessario:.0f} BHP (Baseado no pico operacional)")
    
    res_capex = calcular_capex(
        comp_balsa=L_BALSA, boca_balsa=B_BALSA, pontal_balsa=H_BALSA,
        num_balsas_long=n_long, num_balsas_par=n_par,
        bhp_instalado=max_bhp_necessario,
        taxa_juros_anual=TAXA_JUROS, vida_util_anos=VIDA_UTIL
    )
    
    df_capex = pd.DataFrame(list(res_capex.items()), columns=["Item", "Valor"])
    print(df_capex.to_string(index=False))
    print("-" * 60)

    # --- 4. ANÁLISE DE OPEX FIXO ---
    print(f"\n>>> 3. CUSTOS FIXOS ANUAIS (OPEX FIXO)")
    
    res_opex_fixo = calcular_opex_fixo(
        investimento_total_frota=res_capex['investimento_total'],
        num_tripulantes=NUM_TRIPULANTES, salario_medio=SALARIO_MEDIO,
        vale_alimentacao=VALE_ALIMENTACAO, encargos_sociais_pct=ENCARGOS_SOCIAIS
    )
    
    df_fixo = pd.DataFrame(list(res_opex_fixo.items()), columns=["Componente", "Valor Anual (R$)"])
    print(df_fixo.to_string(index=False))
    print("-" * 60)

    # --- 5. RESUMO EXECUTIVO ---
    print(f"\n>>> 4. CONSOLIDAÇÃO FINAL (TCO)")
    
    custo_var_anual = df_ops["Custo Comb. (R$)"].sum()
    custo_fixo_anual = res_opex_fixo['custos_fixos_anuais_total']
    custo_capital_anual = res_capex['custo_capex_anual']
    carga_total_anual = df_ops["Carga (t)"].sum()
    
    # Admin Variável (Ex: 10% do combustível)
    admin_var = 0.10 * custo_var_anual
    
    custo_total = custo_capital_anual + custo_fixo_anual + custo_var_anual + admin_var
    custo_unitario = custo_total / carga_total_anual if carga_total_anual > 0 else 0
    
    resumo = {
        "1. CAPEX Anualizado": custo_capital_anual,
        "2. OPEX Fixo Anual": custo_fixo_anual,
        "3. OPEX Variável Anual": custo_var_anual,
        "4. Admin Variável (Est.)": admin_var,
        "=== CUSTO TOTAL ANUAL ===": custo_total,
        "=== CARGA TOTAL (t) ===": carga_total_anual,
        "=== R$ / TONELADA ===": custo_unitario
    }
    
    df_resumo = pd.DataFrame(list(resumo.items()), columns=["Indicador", "Resultado"])
    print(df_resumo.to_string(index=False))
    print("="*100)