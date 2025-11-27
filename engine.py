# engine.py
from typing import Dict, Any
import helpers

# ==============================================================================
# MÓDULO DE MOTOR DE CÁLCULO (CORE)
# ==============================================================================
# Este arquivo contém as funções puras de cálculo físico e financeiro.
# Ele orquestra as chamadas às fórmulas do 'helpers.py' para compor os custos.
# ==============================================================================

def calcular_opex_variavel(
    # Inputs de Cenário
    distancia_km: float,
    dias_operacao_periodo: float,

    # Inputs Ambientais
    largura_canal: float,
    profundidade_rio: float,
    
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
    
    Esta função realiza a simulação física da viagem, determinando a resistência
    ao avanço, a potência requerida, o tempo de ciclo e o consumo de combustível
    necessário para cumprir a missão de transporte no período especificado.

    Parâmetros:
        distancia_km (float): Distância de perna única (One-way) em km.
        dias_operacao_periodo (float): Janela de tempo disponível para operação (dias).
        [... demais parâmetros físicos e operacionais ...]

    Retorna:
        Dict[str, Any]: Dicionário contendo:
            - 'custo_variavel_total': Custo total com combustível (R$).
            - 'carga_total_transportada': Capacidade efetiva no período (t).
            - 'num_viagens': Número de ciclos realizados.
            - 'bhp_requerido': Potência demandada dos motores principais.
            - 'emissoes_co2_ton': Pegada de carbono total.

    Nota de Uso:
        Utilizada extensivamente nos loops de otimização do módulo `analysis.py` 
        (funções `_simular_ano_operacional` e `run_global_optimization`) para 
        avaliar o desempenho dinâmico em cada mês do ano.
    """
    
    # 1. Definição das Características Físicas da Balsa e do Comboio
    # Cálculo do peso leve para determinar a capacidade de carga líquida (Deadweight)
    peso_leve_balsa = helpers.calcular_peso_leve_balsa(comp_balsa, boca_balsa, pontal_balsa)
    
    # Determinação do volume submerso com base no calado operacional (restrição do rio)
    vol_desloc_balsa = helpers.calcular_volume_operacional_balsa(
        comp_balsa, boca_balsa, calado_operacional, coef_bloco
    )
    
    # Capacidade de carga unitária (Princípio de Arquimedes)
    cap_carga_balsa = helpers.calcular_capacidade_carga_balsa(vol_desloc_balsa, peso_leve_balsa)
    
    # Consolidação para o comboio inteiro
    num_total_balsas = num_balsas_long * num_balsas_par
    cap_carga_comboio = cap_carga_balsa * num_total_balsas
    vol_desloc_comboio = vol_desloc_balsa * num_total_balsas

    # 2. Cálculo de Tempos de Ciclo (Logística)
    # Determinação das velocidades em relação ao solo (SOG) considerando a correnteza
    v_ida_kmh, v_volta_kmh = helpers.calcular_velocidades_solo(
        vel_embarcacao_nos, vel_correnteza_nos
    )
    
    # Tempo de navegação pura (ida e volta)
    tempo_nav_h = helpers.calcular_tempo_viagem_puro(distancia_km, v_ida_kmh, v_volta_kmh)
    
    # Tempo de estadia no porto (carregamento/descarregamento)
    tempo_porto_h = helpers.calcular_tempo_porto_total(
        cap_carga_comboio, prod_carregamento_th, prod_descarregamento_th, num_bercos
    )
    
    # Tempos acessórios (eclusas e manobras de formação)
    tempo_manobras_h = helpers.calcular_tempo_manobras_e_eclusas(
        tempo_eclusa_por_viagem_min, tempo_manobra_por_balsa_min, num_total_balsas
    )
    
    tempo_ciclo_total_h = tempo_nav_h + tempo_porto_h + tempo_manobras_h
    
    # 3. Cálculo de Produtividade (Viagens e Carga)
    # Aplica a "Armadilha dos Inteiros": número de viagens deve ser inteiro
    num_viagens = helpers.calcular_numero_viagens_periodo(tempo_ciclo_total_h, dias_operacao_periodo)
    carga_total_periodo = cap_carga_comboio * num_viagens

    # 4. Cálculo de Potência e Consumo (Engenharia)
    # Potência necessária nos motores principais para vencer a resistência hidrodinâmica
    bhp_propulsao = helpers.calcular_bhp_propulsao(
        comp_balsa=comp_balsa,
        boca_balsa=boca_balsa,
        calado_m=calado_operacional,
        n_long=num_balsas_long,
        n_par=num_balsas_par,
        vel_nos=vel_embarcacao_nos,
        largura_canal_m=largura_canal,
        profundidade_canal_m=profundidade_rio,
        eficiencia_global=eficiencia_propulsor
    )
    
    # Potência auxiliar (geradores) estimada como fração da principal
    bhp_auxiliar = helpers.calcular_bhp_auxiliar(bhp_propulsao)
    
    # O consumo dos MCPs (Motores Principais) ocorre apenas durante a navegação e manobras
    tempo_consumo_principal = (tempo_nav_h + tempo_manobras_h) * num_viagens
    
    # O consumo dos MCAs (Auxiliares) ocorre durante todo o ciclo (inclusive no porto)
    tempo_consumo_auxiliar = tempo_ciclo_total_h * num_viagens
    
    # Massa de combustível consumida (kg)
    consumo_principal_kg = helpers.calcular_consumo_motor_kg(
        bhp_propulsao, tempo_consumo_principal, consumo_especifico_motor
    )
    consumo_auxiliar_kg = helpers.calcular_consumo_motor_kg(
        bhp_auxiliar, tempo_consumo_auxiliar, consumo_especifico_motor
    )
    consumo_total_kg = consumo_principal_kg + consumo_auxiliar_kg
    
    # 5. Conversão Financeira e Ambiental
    custo_combustivel = helpers.calcular_custo_monetario_combustivel(
        consumo_total_kg, preco_combustivel, densidade_combustivel
    )
    
    emissoes_co2 = helpers.calcular_emissoes_co2(consumo_total_kg)

    return {
        'custo_variavel_total': custo_combustivel,
        'carga_total_transportada': carga_total_periodo,
        'num_viagens': num_viagens,
        'bhp_requerido': bhp_propulsao,
        'tempo_ciclo_h': tempo_ciclo_total_h,
        'consumo_total_kg': consumo_total_kg,
        'carga_por_viagem': cap_carga_comboio,
        'emissoes_co2_ton': emissoes_co2
    }

def calcular_capex(
    # Inputs Dimensionais
    comp_balsa: float,
    boca_balsa: float,
    pontal_balsa: float,
    num_balsas_long: int,
    num_balsas_par: int,
    
    # Input de Engenharia (Dimensionamento)
    bhp_instalado: float,
    
    # Inputs Financeiros
    taxa_juros_anual: float,
    vida_util_anos: int
) -> Dict[str, Any]:
    """
    Calcula os Custos de Capital (CAPEX) e o investimento inicial necessário.
    
    Utiliza modelos paramétricos de regressão (definidos em `helpers.py`) para 
    estimar o valor de construção dos ativos (balsas e empurrador) com base em
    suas características físicas e aplica matemática financeira para anualizar 
    este investimento (Custo de Oportunidade + Depreciação).

    Parâmetros:
        comp_balsa, boca_balsa, pontal_balsa: Dimensões unitárias.
        num_balsas_long, num_balsas_par: Arranjo do comboio.
        bhp_instalado: Potência total instalada (deve ser o pico de demanda).
        taxa_juros_anual: Custo de capital (WACC/SELIC).
        vida_util_anos: Período de amortização.

    Retorna:
        Dict[str, Any]: Dicionário contendo:
            - 'custo_capex_anual': Valor da anuidade equivalente (R$/ano).
            - 'investimento_total': Valor total de aquisição da frota (R$).
            - 'investimento_empurrador': Custo estimado do empurrador.
            - 'investimento_balsas': Custo estimado do conjunto de balsas.
            
    Nota de Uso:
        Chamada pelo módulo `analysis.py` (especialmente na função `run_global_optimization`)
        para determinar os custos fixos de capital associados a uma decisão de design (tamanho do motor).
    """
    
    # 1. Estimativa do Investimento em Balsas
    # Estima o peso leve de uma unidade para obter o custo de construção
    peso_leve_unitario = helpers.calcular_peso_leve_balsa(comp_balsa, boca_balsa, pontal_balsa)
    custo_unitario_balsa = helpers.estimar_custo_construcao_balsa(peso_leve_unitario)
    
    num_total_balsas = num_balsas_long * num_balsas_par
    investimento_balsas = custo_unitario_balsa * num_total_balsas
    
    # 2. Estimativa do Investimento no Empurrador
    # O custo é função direta da potência instalada (BHP)
    investimento_empurrador = helpers.estimar_custo_construcao_empurrador(bhp_instalado)
    
    investimento_total = investimento_balsas + investimento_empurrador
    
    # 3. Anualização do Investimento (Custo Econômico)
    # Aplica o Fator de Recuperação de Capital (FRC) para distribuir o custo ao longo da vida útil
    frc = helpers.calcular_fator_recuperacao_capital(taxa_juros_anual, vida_util_anos)
    custo_anual_equivalente = investimento_total * frc
    
    return {
        'custo_capex_anual': custo_anual_equivalente,
        'investimento_total': investimento_total,
        'investimento_balsas': investimento_balsas,
        'investimento_empurrador': investimento_empurrador,
        'frc': frc,
        "vida_util_anos": vida_util_anos,
        "taxa_juros": taxa_juros_anual
    }

def calcular_opex_fixo(
    investimento_total_frota: float,
    num_tripulantes: int,
    salario_medio: float,
    vale_alimentacao: float,
    encargos_sociais_pct: float
) -> Dict[str, Any]:
    """
    Calcula os Custos Operacionais Fixos anuais (Tripulação, Manutenção, Seguros).
    
    Estes custos ocorrem independentemente da operação da embarcação (navegando ou parada)
    e são dimensionados com base no valor do ativo (taxas de seguro/manutenção) e no 
    tamanho da guarnição (regras de negócio de RH).

    Parâmetros:
        investimento_total_frota (float): Valor de reposição dos ativos (Base para seguros/manut).
        [... parâmetros de RH ...]

    Retorna:
        Dict[str, Any]: Breakdown detalhado dos custos fixos anuais.
        
    Nota de Uso:
        Integrada à composição de custos totais no módulo `analysis.py`.
    """
    
    # 1. Custos de Recursos Humanos
    custo_anual_tripulacao = helpers.calcular_custo_anual_tripulacao(
        num_tripulantes, salario_medio, encargos_sociais_pct
    )
    custo_anual_alimentacao = helpers.calcular_custo_anual_alimentacao(
        num_tripulantes, vale_alimentacao
    )
    
    # 2. Custos de Manutenção e Seguros (Baseados no Valor do Ativo)
    custo_anual_manutencao = helpers.estimar_custo_manutencao_anual(investimento_total_frota)
    custo_anual_seguros = helpers.estimar_custo_seguro_anual(investimento_total_frota)
    
    custos_fixos_operacionais = (
        custo_anual_tripulacao + 
        custo_anual_alimentacao + 
        custo_anual_manutencao + 
        custo_anual_seguros
    )
    
    # 3. Custos Administrativos Fixos (Overhead)
    # Assume-se 10% sobre os custos fixos operacionais
    custo_admin_fixo = helpers.calcular_custo_administrativo(custos_fixos_operacionais, 0.10)
    
    custos_fixos_totais = custos_fixos_operacionais + custo_admin_fixo
    
    return {
        'custos_fixos_anuais_total': custos_fixos_totais,
        'custo_tripulacao': custo_anual_tripulacao,
        'custo_alimentacao': custo_anual_alimentacao,
        'custo_manutencao': custo_anual_manutencao,
        'custo_seguros': custo_anual_seguros,
        'custo_admin_fixo': custo_admin_fixo
    }

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
    num_bercos: int,
    prod_carregamento: float,
    prod_descarregamento: float,
    num_tripulantes: int,
    eficiencia_propulsor: float,
    
    # Parâmetros Financeiros e de Custo
    demanda_anual: float, # Apenas pass-through
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
    Função Orquestradora (Wrapper) para cálculo completo de um cenário ESTÁTICO.
    
    Coordena a chamada sequencial das funções de cálculo modular (Engenharia -> 
    Física -> CAPEX -> OPEX) para consolidar todos os custos e métricas de um 
    comboio específico em um cenário fixo (calado constante, velocidade constante).

    Esta função garante compatibilidade com versões anteriores e simplifica chamadas
    que não requerem otimização dinâmica.

    Retorna:
        Dict[str, Any]: Relatório completo de custos (TCO) e performance operacional,
                        estruturado para consumo direto pelo dashboard ou análises simples.
        
    Nota de Uso:
        Ponto de entrada principal para a "Aba 0" (Cenário Atual) e validações rápidas.
    """
    
    # 1. Definição do Arranjo do Comboio (Engenharia)
    n_long, n_par = helpers.calcular_arranjo_comboio(
        comp_balsa, boca_balsa, raio_curvatura, largura_canal
    )
    
    # 2. Cálculo Operacional e Variável (Motor Físico)
    # Executado primeiro para determinar a potência (BHP) requerida pela velocidade alvo
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
    # Usa o BHP calculado na etapa anterior para dimensionar e orçar o empurrador
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
    # Baseado no valor do investimento (para seguros/manutenção) e tripulação
    res_fixo = calcular_opex_fixo(
        investimento_total_frota=res_capex['investimento_total'],
        num_tripulantes=num_tripulantes,
        salario_medio=salario_medio,
        vale_alimentacao=vale_alimentacao,
        encargos_sociais_pct=encargos_sociais_pct
    )
    
    # 5. Consolidação e Overhead Variável
    # Aplica taxa administrativa sobre os custos variáveis (ex: gestão de combustível)
    custo_admin_variavel = helpers.calcular_custo_administrativo(res_var['custo_variavel_total'], 0.10)
    
    # Soma final do Custo Total de Propriedade (TCO) anualizado
    custo_total_anual = (
        res_capex['custo_capex_anual'] +           # Capital
        res_fixo['custos_fixos_anuais_total'] +    # Fixo
        res_var['custo_variavel_total'] +          # Variável
        custo_admin_variavel                       # Admin Variável
    )
    
    carga_total = res_var['carga_total_transportada']
    custo_por_tonelada = custo_total_anual / carga_total if carga_total > 0 else 0.0
    
    # Estrutura de retorno compatível com a expectativa do `analysis.py` e `app.py`
    resultados = {
        # Métricas Principais
        'custo_total_anual': custo_total_anual,
        'custo_por_tonelada': custo_por_tonelada,
        'carga_total_ano': carga_total,
        'num_viagens_ano': res_var['num_viagens'],
        'cap_carga_comboio': res_var['carga_por_viagem'],
        
        # Breakdowns para Análise
        'custos_fixos_anuais_total': res_fixo['custos_fixos_anuais_total'] + res_capex['custo_capex_anual'],
        'custos_variaveis_total': res_var['custo_variavel_total'] + custo_admin_variavel,
        
        'custo_capex_anual_puro': res_capex['custo_capex_anual'],
        'custo_capex_anual_total': res_capex['custo_capex_anual'], 
        
        'custo_variavel_combustivel_puro': res_var['custo_variavel_total'],
        'custo_admin_variavel': custo_admin_variavel,
        'custo_admin_fixo': res_fixo['custo_admin_fixo'],
        
        # Detalhes para gráficos
        'custo_anual_tripulacao': res_fixo['custo_tripulacao'],
        'custo_anual_alimentacao': res_fixo['custo_alimentacao'],
        'custo_anual_manutencao': res_fixo['custo_manutencao'],
        'custo_anual_seguradora': res_fixo['custo_seguros'],
        
        # Dados de Engenharia e Sustentabilidade
        'num_balsas_longitudinal': n_long,
        'num_balsas_paralela': n_par,
        'bhp_requerido': res_var['bhp_requerido'],
        'emissoes_co2_ton': res_var['emissoes_co2_ton']
    }
    
    return resultados

if __name__ == "__main__":
    import pprint
    
    pp = pprint.PrettyPrinter(indent=4, width=80, compact=False)

    print("\n" + "="*80)
    print("⚓  RELATÓRIO DE VALIDAÇÃO DETALHADA: ENGINE.PY  ⚓")
    print("="*80)

    # --- CENÁRIO DE TESTE (MOCK DATA) ---
    # Definição de um cenário padrão para garantir que o motor está calibrado
    profundidades_rio = [7.0, 8.0, 9.0, 9.0, 8.5, 7.5, 6.0, 5.0, 4.0, 3.8, 4.5, 6.0]
    FOLGA_SEGURANCA = 0.5      
    CALADO_MAX_PROJETO = 3.66  
    
    # Dimensões da Balsa (Padrão Mississippi/Amazonas)
    L_BALSA = 60.96; B_BALSA = 10.67; H_BALSA = 4.27; CB_BALSA = 0.90  
    
    # Parâmetros Operacionais
    RAIO_CURVA = 800.0; LARGURA_CANAL = 100.0 
    VEL_ALVO = 5.8; VEL_CORRENTEZA = 2.0
    DISTANCIA = 1000.0; DIAS_OP_MES = 27.5

    # Portos e RH
    PROD_CARGA = 1200; PROD_DESCARGA = 1000; NUM_BERCOS = 2
    NUM_TRIPULANTES = 8; SALARIO_MEDIO = 5000.0; VALE_ALIMENTACAO = 800.0; ENCARGOS_SOCIAIS = 0.90
    
    # Custos
    PRECO_DIESEL = 4.50; DENSIDADE_DIESEL = 0.85; FC_MOTOR = 0.16           
    TAXA_JUROS = 0.15; VIDA_UTIL = 20            

    # 1. Arranjo
    n_long, n_par = helpers.calcular_arranjo_comboio(L_BALSA, B_BALSA, RAIO_CURVA, LARGURA_CANAL)
    
    print(f"\n--- [0] PARÂMETROS FÍSICOS E ARRANJO ---")
    print(f"Arranjo Calculado: {n_long}x{n_par} = {n_long*n_par} Balsas")

    # 2. Simulação Mensal
    print("\n" + "-"*80)
    print(">>> 1. ANÁLISE DE PERFORMANCE OPERACIONAL (MÊS A MÊS)")
    print(f"    Rota: {DISTANCIA} km | Velocidade Alvo: {VEL_ALVO} nós | Correnteza: {VEL_CORRENTEZA} nós")
    
    total_custo_var = 0.0
    total_carga = 0.0
    max_bhp_necessario = 0.0 

    print(f"{'Mês':<3} {'Rio (m)':<8} {'Calado (m)':<10} {'Carga (t)':<12} {'Viagens':<8} {'BHP Req.':<10} {'Consumo (L)':<12} {'Custo Comb. (R$)':<15}")
    
    for i, prof_rio in enumerate(profundidades_rio):
        calado_mes = helpers.calcular_calado_maximo_operacional(prof_rio, FOLGA_SEGURANCA, CALADO_MAX_PROJETO)
        
        res_opex = calcular_opex_variavel(
            distancia_km=DISTANCIA, dias_operacao_periodo=DIAS_OP_MES,
            vel_embarcacao_nos=VEL_ALVO, vel_correnteza_nos=VEL_CORRENTEZA,
            calado_operacional=calado_mes, comp_balsa=L_BALSA, boca_balsa=B_BALSA,
            pontal_balsa=H_BALSA, coef_bloco=CB_BALSA, num_balsas_long=n_long, num_balsas_par=n_par,
            eficiencia_propulsor=0.50, tempo_eclusa_por_viagem_min=0, tempo_manobra_por_balsa_min=15,
            prod_carregamento_th=PROD_CARGA, prod_descarregamento_th=PROD_DESCARGA, num_bercos=NUM_BERCOS,
            consumo_especifico_motor=FC_MOTOR, preco_combustivel=PRECO_DIESEL, densidade_combustivel=DENSIDADE_DIESEL
        )
        
        total_custo_var += res_opex['custo_variavel_total']
        total_carga += res_opex['carga_total_transportada']
        if res_opex['bhp_requerido'] > max_bhp_necessario: max_bhp_necessario = res_opex['bhp_requerido']
        
        litros = res_opex['consumo_total_kg'] / DENSIDADE_DIESEL
        
        print(f"{i+1:<3} {prof_rio:<8.2f} {calado_mes:<10.2f} {res_opex['carga_total_transportada']:<12,.2f} {res_opex['num_viagens']:<8.0f} {res_opex['bhp_requerido']:<10.2f} {litros:<12,.2f} {res_opex['custo_variavel_total']:<15,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))

    print(f"TOTAL {sum(profundidades_rio)/12:<8.2f} {sum([helpers.calcular_calado_maximo_operacional(p, FOLGA_SEGURANCA, CALADO_MAX_PROJETO) for p in profundidades_rio])/12:<10.2f} {total_carga:<12,.2f} {36:<8} {max_bhp_necessario:<10.2f} {total_custo_var/PRECO_DIESEL:<12,.2f} {total_custo_var:<15,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    print("-" * 100)

    # 3. CAPEX e 4. OPEX Fixo
    print("\n>>> 2. ESTRUTURA DE CAPITAL (CAPEX)")
    print(f"    Dimensionamento Motor: {max_bhp_necessario:.0f} BHP (Baseado no pico operacional)")
    
    res_capex = calcular_capex(
        comp_balsa=L_BALSA, boca_balsa=B_BALSA, pontal_balsa=H_BALSA,
        num_balsas_long=n_long, num_balsas_par=n_par, bhp_instalado=max_bhp_necessario,
        taxa_juros_anual=TAXA_JUROS, vida_util_anos=VIDA_UTIL
    )
    for k, v in res_capex.items(): print(f"{k:>25} {v:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    
    print("\n>>> 3. CUSTOS FIXOS ANUAIS (OPEX FIXO)")
    res_opex_fixo = calcular_opex_fixo(
        investimento_total_frota=res_capex['investimento_total'],
        num_tripulantes=NUM_TRIPULANTES, salario_medio=SALARIO_MEDIO,
        vale_alimentacao=VALE_ALIMENTACAO, encargos_sociais_pct=ENCARGOS_SOCIAIS
    )
    for k, v in res_opex_fixo.items(): print(f"{k:>25} {v:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))

    # 5. Consolidação
    print("\n>>> 4. CONSOLIDAÇÃO FINAL (TCO)")
    admin_var = 0.10 * total_custo_var
    tco = res_capex['custo_capex_anual'] + res_opex_fixo['custos_fixos_anuais_total'] + total_custo_var + admin_var
    
    print(f"{'1. CAPEX Anualizado':>25} {res_capex['custo_capex_anual']:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    print(f"{'2. OPEX Fixo Anual':>25} {res_opex_fixo['custos_fixos_anuais_total']:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    print(f"{'3. OPEX Variável Anual':>25} {total_custo_var:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    print(f"{'4. Admin Variável (Est.)':>25} {admin_var:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    print(f"=== CUSTO TOTAL ANUAL === {tco:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    print(f"  === CARGA TOTAL (t) === {total_carga:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    print(f"    === R$ / TONELADA === {tco/total_carga:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    print("="*100)