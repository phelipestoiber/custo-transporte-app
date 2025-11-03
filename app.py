# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import analysis
import data_utils

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador de Frota Naval")

# --- 2. DEFINIÇÃO DE PARÂMETROS GLOBAIS ---
# As profundidades foram retiradas de graficos de profundidade mínima e curvas de permanecnia
LISTA_PROF_MESES = [
    7.72, 9.87, 10.86, 10.98, 8.43, 6.35, 
    5.12, 3.89, 3.30, 3.00, 3.65, 5.23
]
MESES_ABREV = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
MESES_DO_ANO = 12

# --- 3. BARRA LATERAL (SIDEBAR) PARA INPUTS ---
st.sidebar.title("Parâmetros de Simulação")

st.sidebar.header("Parâmetros de Análise")
preco_frete_input = st.sidebar.number_input(
    "Preço do Frete (R$/t)", 
    min_value=0.0, 
    value=23.50, 
    step=0.50,
    help="Preço de venda (receita) que sua empresa cobra por tonelada. Usado na Análise B (Break-Even) e F (Matriz de Lucro)."
)

with st.sidebar.expander("Parâmetros Globais do Cenário"):
    folga_seguranca = st.number_input(
        "Folga de Segurança (m)", 
        value=0.50, 
        help="Keel Margin ou 'pé de piloto'. Margem de segurança entre a quilha do barco e o fundo do rio."
    )
    calado_design_alvo = st.number_input(
        "Calado de Design Alvo (m)", 
        value=3.66,
        help="Calado operacional máximo desejado para o projeto. O calado real será o *menor* valor entre este e o (Nível do Rio - Folga)."
    )
    dias_base_anuais = st.number_input(
        "Dias de Operação Anuais", 
        value=330.0,
        help="Número total de dias que o comboio está disponível para operar por ano (ex: 365 - dias de manutenção)."
    )

st.sidebar.header("Parâmetros Base do Comboio")

with st.sidebar.expander("Parâmetros de Trajeto"):
    comp_balsa = st.number_input(
        "Comprimento Balsa (m)", 
        value=60.980,
        help="Comprimento total (Length Overall - LOA) de uma única balsa."
    )
    boca_balsa = st.number_input(
        "Boca Balsa (m)", 
        value=10.670,
        help="Largura máxima (Boca) de uma única balsa."
    )
    pontal_balsa = st.number_input(
        "Pontal Balsa (m)", 
        value=4.27,
        help="Distância vertical da quilha ao convés principal (H). Usado para calcular o peso leve e o custo de construção."
    )
    coef_bloco = st.number_input(
        "Coef. de Bloco (Cb)", 
        value=0.900,
        help="Coeficiente de Bloco (Cb) da balsa. Indica o quão 'cheio' é o casco. (ex: 0.90 é típico de balsa)."
    )
    raio_curvatura = st.number_input(
        "Raio de Curvatura (m)", 
        value=750.000,
        help="Raio de curvatura do trecho mais restritivo do rio. Limita o comprimento máximo do comboio (L_max = R/5)."
    )
    largura_canal = st.number_input(
        "Largura do Canal (m)", 
        value=70.000,
        help="Largura do canal de navegação. Limita a boca máxima (largura) do comboio."
    )
    dist_km_input = st.number_input(
        "Distância (km)", 
        value=500.000,
        help="Distância (em km) de ida do trajeto (do porto de carga ao de descarga)."
    )
    t_eclusagem_min = st.number_input(
        "Tempo de Eclusagem (min)", 
        value=92.0,
        help="Tempo médio gasto em minutos para transpor a(s) eclusa(s) em cada sentido da viagem."
    )
    t_manobra_balsa_min = st.number_input(
        "Tempo de Manobra p/ Balsa (min)", 
        value=20.0,
        help="Tempo de manobra (atracação/desatracação) no porto, em minutos, *por cada balsa* do comboio."
    )

with st.sidebar.expander("Parâmetros de Operação"):
    vel_embarcacao_nos = st.slider(
        "Velocidade da Embarcação (nós)", 
        min_value=2.0, 
        max_value=12.0, 
        value=8.00, 
        step=0.25,
        help="Velocidade de serviço do comboio. Principal variável para Análise C e D."
    )
    vel_correnteza_nos = st.number_input(
        "Velocidade Correnteza (nós)", 
        value=1.944,
        help="Velocidade média da correnteza do rio (em nós)."
    )
    num_bercos = st.number_input(
        "Número de Berços", 
        value=2.000,
        help="Número de berços de carregamento/descarregamento disponíveis para o comboio no porto."
    )
    prod_carregamento = st.number_input(
        "Prod. Carregamento (t/h)", 
        value=2500.000,
        help="Taxa de carregamento total do porto (em toneladas por hora)."
    )
    prod_descarregamento = st.number_input(
        "Prod. Descarregamento (t/h)", 
        value=1250.000,
        help="Taxa de descarregamento total do porto (em toneladas por hora)."
    )
    num_tripulantes = st.number_input(
        "Número de Tripulantes", 
        value=8.000,
        help="Número de tripulantes na folha de pagamento do comboio."
    )
    eficiencia_propulsor = st.number_input(
        "Eficiência Propulsor (%)", 
        value=0.50,
        help="Eficiência propulsiva total (n_p), de 0 a 1. Converte potência do motor (BHP) em empuxo. (ex: 0.50 = 50%)"
    )

with st.sidebar.expander("Parâmetros Financeiros e de Custo"):
    demanda_anual = st.number_input(
        "Demanda Anual do Mercado (t)", 
        value=10_000_000,
        help="Demanda total do mercado (em toneladas/ano). Usado para calcular o tamanho da frota necessária (Análise D)."
    )
    
    try:
        # Chama a função do novo arquivo data_utils
        taxa_juros_base, info_selic = data_utils.buscar_meta_selic_anual()
    except Exception as e:
        st.error(f"Erro ao buscar SELIC: {e}")
        taxa_juros_base, info_selic = 0.15, "Padrão (Falha na API)"
        
    taxa_juros_input_pct = st.number_input(
        "Taxa de Juros Anual (%)", 
        value=taxa_juros_base * 100,
        help=f"Valor padrão buscado da API do BCB: {info_selic}"
    )
    taxa_juros_input = taxa_juros_input_pct / 100.0
    
    vida_util_anos = st.number_input(
        "Vida Útil (anos)", 
        value=20,
        help="Vida útil do ativo (comboio) para cálculo do Custo Anual de Capital (financiamento)."
    )
    preco_combustivel = st.number_input(
        "Preço do Combustível (R$/L)", 
        value=6.06,
        help="Custo do diesel marítimo (MGO) em R$ por Litro."
    )
    consumo_motor_fc = st.number_input(
        "Consumo Motor (kg/HP/h)", 
        value=0.16,
        help="Consumo Específico de Combustível (FC) do motor principal, em kg / HP / hora."
    )
    densidade_combustivel = st.number_input(
        "Densidade Combustível (t/m³)", 
        value=0.85,
        help="Densidade do combustível (ex: 0.85 para MGO)."
    )
    salario_medio = st.number_input(
        "Salário Médio Tripulação (R$)", 
        value=4500.0,
        help="Salário médio mensal (base) de um tripulante."
    )
    vale_alimentacao = st.number_input(
        "Vale Alimentação (R$)", 
        value=720.0,
        help="Custo médio mensal de alimentação (ou vale) por tripulante."
    )
    encargos_sociais_pct = st.number_input(
        "Encargos Sociais (%)", 
        value=0.90,
        help="Percentual de encargos sociais, férias, 13º, etc. sobre o salário base. (ex: 0.90 = 90%)"
    )

run_button = st.sidebar.button("Executar Simulações")

# --- 4. PÁGINA PRINCIPAL (CORPO DO DASHBOARD) ---
st.title("Dashboard de Análise de Viabilidade de Frota")

if run_button:
    
    # --- A. Monta o Dicionário de Parâmetros ---
    DEFAULT_PARAMS = {
        # Trajeto
        "comp_balsa": comp_balsa, "boca_balsa": boca_balsa, "pontal_balsa": pontal_balsa,
        "coef_bloco": coef_bloco, "raio_curvatura": raio_curvatura, "largura_canal": largura_canal,
        "dist_km_input": dist_km_input, "t_eclusagem_min": t_eclusagem_min, "t_manobra_balsa_min": t_manobra_balsa_min,
        # Operação
        "vel_embarcacao_nos": vel_embarcacao_nos, "vel_correnteza_nos": vel_correnteza_nos, "num_bercos": num_bercos,
        "prod_carregamento": prod_carregamento, "prod_descarregamento": prod_descarregamento,
        "num_tripulantes": num_tripulantes, "eficiencia_propulsor": eficiencia_propulsor,
        # Finanças e Custos
        "demanda_anual": demanda_anual, "taxa_juros_input": taxa_juros_input, "vida_util_anos": vida_util_anos,
        "preco_combustivel": preco_combustivel, "consumo_motor_fc": consumo_motor_fc, "densidade_combustivel": densidade_combustivel,
        "salario_medio": salario_medio, "vale_alimentacao": vale_alimentacao, "encargos_sociais_pct": encargos_sociais_pct
    }
    
    # Chama a função de info do data_utils
    info_dias = data_utils.get_info_dias_operacao(dias_base_anuais)
    st.info(info_dias)

    # --- B. Executa a Simulação com Calado Dinâmico ---
    st.header(f"Simulação do Cenário (@ {vel_embarcacao_nos:.2f} nós)")
    
    with st.spinner("Executando Simulação Base (Sim 2)..."):
        # Chama a função do novo arquivo analysis.py
        resultados_sim2 = analysis.run_simulacao_dinamica(
            params=DEFAULT_PARAMS,
            lista_prof_meses=LISTA_PROF_MESES,
            calado_design_alvo=calado_design_alvo,
            folga_seguranca=folga_seguranca,
            dias_base_anuais=dias_base_anuais,
            print_detalhes=False
        )

    formacao_nbl = resultados_sim2.get('formacao_nbl', 0)
    formacao_nbp = resultados_sim2.get('formacao_nbp', 0)
    st.subheader(f"Formação do Comboio: {formacao_nbl:.0f} (Longitudinal) x {formacao_nbp:.0f} (Paralela)")

    # Formatação PT-BR para st.metric
    col1, col2, col3, col4 = st.columns(4)
    fmt_custo_ton = f"R$ {resultados_sim2['custo_por_tonelada']:.2f}".replace('.', ',')
    fmt_carga_anual = f"{resultados_sim2['carga_total_ano']:,.0f} t".replace(',', 'X').replace('.', ',').replace('X', '.')
    fmt_viagens_ano = f"{resultados_sim2['num_viagens_ano']:.0f}"
    fmt_custo_total_m = f"R$ {resultados_sim2['custo_total_anual']/1_000_000:.2f} M".replace('.', ',')
    col1.metric("Custo (R$/t)", fmt_custo_ton)
    col2.metric("Carga Anual (t/comboio)", fmt_carga_anual)
    col3.metric("Viagens (n°/ano)", fmt_viagens_ano)
    col4.metric("Custo Total Anual (comboio)", fmt_custo_total_m)

    # Gráfico de Pizza (Composição de Custo)
    st.subheader("Composição do Custo Anual do Comboio (Simulação 2)")
    custos_breakdown = {
        'Capital (CAPEX)': resultados_sim2.get('breakdown_capital', 0),
        'Combustível (OPEX Var)': resultados_sim2.get('breakdown_combustivel', 0),
        'Tripulação + Alimentação (OPEX Fixo)': resultados_sim2.get('breakdown_tripulacao_alim', 0),
        'Administrativo (OPEX Fixo+Var)': resultados_sim2.get('breakdown_admin', 0),
        'Manutenção + Seguros (OPEX Fixo)': resultados_sim2.get('breakdown_manutencao_seguro', 0)
    }
    df_custos = pd.DataFrame(list(custos_breakdown.items()), columns=['Componente', 'Custo Anual (R$)'])
    fig = px.pie(
        df_custos, 
        names='Componente', 
        values='Custo Anual (R$)',
        title='Contribuição Percentual dos Custos Anuais'
    )
    fig.update_traces(
        textposition='inside', 
        textinfo='percent+label+value',
        hovertemplate='<b>%{label}</b><br>Custo: R$ %{value:,.2f}<br>Percentual: %{percent:,.2%}'
    )
    st.plotly_chart(fig, width="stretch")

    # Tabela de Detalhes Mensais (Sim 2)
    st.subheader("Detalhes Mensais da Simulação")
    df_detalhes = pd.DataFrame(resultados_sim2['detalhes'])
    df_detalhes['Mês'] = df_detalhes['mes'].apply(lambda x: MESES_ABREV[x-1])
    df_detalhes = df_detalhes.set_index('Mês')
    formatter_b_details = {
        'Calado (m)': '{:.2f}',
        'Cap. Viagem (t)': '{:.0f}',
        'Viagens/Mês': '{:.1f}',
        'Carga/Mês (t)': '{:.0f}'
    }
    df_detalhes_display = df_detalhes.rename(columns={
        'calado': 'Calado (m)', 'cap_carga': 'Cap. Viagem (t)',
        'viagens': 'Viagens/Mês', 'carga_mes': 'Carga/Mês (t)'
    })
    st.dataframe(df_detalhes_display[['Calado (m)', 'Cap. Viagem (t)', 'Viagens/Mês', 'Carga/Mês (t)']]
                 .style
                 .format(formatter_b_details, decimal=',', thousands='.'))

    # --- C. Executa e Exibe as Análises A, B, C, D, F ---
    
    # Análise de Sensibilidade (A)
    with st.spinner("Executando Análise A (Sensibilidade)..."):
        st.header("Análise A: Sensibilidade (Gráfico de Tornado)")
        resultados_sensibilidade = analysis.run_analysis_sensitivity(
            base_params=DEFAULT_PARAMS, lista_prof_meses=LISTA_PROF_MESES,
            calado_design_alvo=calado_design_alvo, folga_seguranca=folga_seguranca,
            dias_base_anuais=dias_base_anuais, base_cost=resultados_sim2['custo_por_tonelada']
        )
        df_sensibilidade = pd.DataFrame(resultados_sensibilidade).set_index('variavel')
        formatter_a = {
            'Impacto -10%': '{:+.2f}%',
            'Impacto +10%': '{:+.2f}%',
            'Faixa Total (pp)': '{:.2f} pp' 
        }
        df_sens_display = df_sensibilidade.rename(columns={
            'impacto_menos_10': 'Impacto -10%', 'impacto_mais_10': 'Impacto +10%',
            'faixa_impacto': 'Faixa Total (pp)'
        })
        st.dataframe(df_sens_display[['Impacto -10%', 'Impacto +10%', 'Faixa Total (pp)']]
                     .style
                     .format(formatter_a, decimal=',', thousands='.'))
    
    # Análise de Ponto de Equilíbrio (B)
    with st.spinner("Executando Análise B (Break-Even)..."):
        st.header(f"Análise B: Ponto de Equilíbrio (Frete: R$ {preco_frete_input:.2f}/t)")
        resultados_break_even = analysis.run_analysis_break_even(
            sim2_results=resultados_sim2,
            frete_input=preco_frete_input
        )
        if resultados_break_even['is_viable']:
            col1, col2, col3 = st.columns(3)
            fmt_vol_op = f"{resultados_break_even['carga_total_anual_sim2']:,.0f} t".replace(',', 'X').replace('.', ',').replace('X', '.')
            fmt_vol_be = f"{resultados_break_even['volume_break_even_ton']:,.0f} t".replace(',', 'X').replace('.', ',').replace('X', '.')
            fmt_margem_pct = f"{resultados_break_even['margem_seguranca_pct']:.2f} %".replace('.', ',')
            fmt_margem_ton = f"{resultados_break_even['margem_seguranca_ton']:,.0f} t".replace(',', 'X').replace('.', ',').replace('X', '.')
            col1.metric("Volume Operacional (Sim 2)", fmt_vol_op)
            col2.metric("Volume de Break-Even", fmt_vol_be)
            col3.metric("Margem de Segurança (%)", 
                        fmt_margem_pct,
                        delta=fmt_margem_ton,
                        delta_color="normal")
            with st.expander("Ver parâmetros do cálculo de Break-Even"):
                pcol1, pcol2, pcol3, pcol4, pcol5 = st.columns(5)
                fmt_custo_fixo_m = f"R$ {resultados_break_even['custos_fixos_anuais_totais']/1_000_000:,.2f} M".replace('.', ',')
                fmt_custo_var = f"R$ {resultados_break_even['custo_variavel_por_ton']:,.2f}".replace('.', ',')
                fmt_margem_cont = f"R$ {resultados_break_even['margem_contribuicao_por_ton']:,.2f}".replace('.', ',')
                fmt_fat_be_m = f"R$ {resultados_break_even['faturamento_break_even']/1_000_000:,.2f} M".replace('.', ',')
                fmt_viagens_be = f"{resultados_break_even['viagens_break_even']:.1f}".replace('.', ',')
                pcol1.metric("Custos Fixos Anuais Totais", fmt_custo_fixo_m)
                pcol2.metric("Custo Variável (R$/t)", fmt_custo_var)
                pcol3.metric("Margem de Contribuição (R$/t)", fmt_margem_cont)
                pcol4.metric("Faturamento no Break-Even", fmt_fat_be_m)
                pcol5.metric("Viagens para Break-Even", fmt_viagens_be)
        else:
            st.error(f"Não viável: Preço (R${preco_frete_input:.2f}) é menor que Custo Variável (R${resultados_break_even['custo_variavel_por_ton']:.2f})")

    # Análise de Otimização de Velocidade (C)
    with st.spinner("Executando Análise C (Otimização de Velocidade)..."):
        st.header("Análise C: Otimização de Velocidade (Custo/t por Comboio)")
        resultados_otimizacao_vel = analysis.run_analysis_velocity_optimization(
            base_params=DEFAULT_PARAMS, lista_prof_meses=LISTA_PROF_MESES,
            calado_design_alvo=calado_design_alvo, folga_seguranca=folga_seguranca,
            dias_base_anuais=dias_base_anuais
        )
        df_velocidade = pd.DataFrame(resultados_otimizacao_vel).set_index('velocidade')
        formatter_c = {
            'Custo (R$/t)': '{:.3f}',
            'Carga Total (t/ano)': '{:.0f}',
            'Viagens (n°/ano)': '{:.2f}'
        }
        df_vel_display = df_velocidade.rename(columns={
            'custo_por_tonelada': 'Custo (R$/t)',
            'carga_total_ano': 'Carga Total (t/ano)',
            'num_viagens_ano': 'Viagens (n°/ano)'
        })
        st.dataframe(df_vel_display[['Custo (R$/t)', 'Carga Total (t/ano)', 'Viagens (n°/ano)']]
                     .style
                     .highlight_min(axis=0, subset=['Custo (R$/t)'], color='lightgreen')
                     .format(formatter_c, decimal=',', thousands='.'))
        
        st.subheader("Gráfico: Custo por Tonelada vs. Velocidade")
        st.line_chart(df_velocidade['custo_por_tonelada']) 

        min_cost_vel_row = df_vel_display.loc[df_vel_display['Custo (R$/t)'].idxmin()]
        st.subheader(f"Conclusão C: Ponto Ótimo de Custo (1 Comboio)")
        
        fmt_vel_c = f"{min_cost_vel_row.name:.2f}".replace('.', ',')
        fmt_custo_c = f"{min_cost_vel_row['Custo (R$/t)']:.3f}".replace('.', ',')
        fmt_carga_c = f"{min_cost_vel_row['Carga Total (t/ano)']:.0f}"
        
        st.info(f"""
        **Velocidade:** {fmt_vel_c} nós  
        **Custo Mínimo:** R$ {fmt_custo_c} / tonelada  
        **Carga Transportada (nesta vel.):** {fmt_carga_c} t/ano
        """)

    # Análise de Otimização de Frota (D)
    with st.spinner("Executando Análise D (Otimização de Frota)..."):
        st.header("Análise D: Otimização de Frota (Custo Total do Negócio)")
        resultados_otimizacao_frota = analysis.run_analysis_fleet_optimization(
            optimization_results=resultados_otimizacao_vel,
            demanda_total_mercado=DEFAULT_PARAMS['demanda_anual']
        )
        df_frota = pd.DataFrame(resultados_otimizacao_frota).set_index('velocidade')
        
        formatter_d = {
            'Frota Necessária': '{:.0f}',
            'Custo Final (R$/t)': '{:.3f}',
            'CAPEX Frota (Anual)': '{:.0f}',
            'OPEX Frota (Anual)': '{:.0f}',
            'TCO Frota (Anual)': '{:.0f}'
        }
        df_frota_display = df_frota.rename(columns={
            'frota_necessaria': 'Frota Necessária',
            'custo_final_por_tonelada': 'Custo Final (R$/t)',
            'custo_capex_frota_total': 'CAPEX Frota (Anual)',
            'custo_opex_frota_total': 'OPEX Frota (Anual)',
            'custo_tco_total': 'TCO Frota (Anual)'
        })
        st.dataframe(df_frota_display[['Frota Necessária', 'Custo Final (R$/t)', 'CAPEX Frota (Anual)', 'OPEX Frota (Anual)', 'TCO Frota (Anual)']]
                     .style
                     .highlight_min(axis=0, subset=['Custo Final (R$/t)'], color='lightgreen')
                     .format(formatter_d, decimal=',', thousands='.'))
        
        st.subheader("Gráfico: Custo Final de Frota (R$/t) vs. Velocidade")
        st.line_chart(df_frota['custo_final_por_tonelada'])

        min_cost_frota_row = df_frota_display.loc[df_frota_display['Custo Final (R$/t)'].idxmin()]
        st.subheader(f"Conclusão D: Ponto Ótimo de Frota (Negócio Total)")
        
        fmt_vel_d = f"{min_cost_frota_row.name:.2f}".replace('.', ',')
        fmt_custo_d = f"{min_cost_frota_row['Custo Final (R$/t)']:.3f}".replace('.', ',')
        fmt_frota_d = f"{min_cost_frota_row['Frota Necessária']}"

        st.success(f"""
        **Velocidade:** {fmt_vel_d} nós  
        **Custo Final (R$/t):** {fmt_custo_d} / tonelada  
        **Tamanho da Frota:** {fmt_frota_d} comboios
        """)

    # Análise F (Matriz de Lucratividade)
    with st.spinner("Executando Análise F (Matriz de Lucratividade)..."):
        st.header("Análise F.1: Matriz de Lucratividade (Lucro Anual Total em R$ Milhões)")
        try:
            preco_central = preco_frete_input
            limite_inferior = preco_central - 5.0
            limite_superior = preco_central + 5.0 + 0.1 
            passo = 0.50
            precos_frete_teste = np.arange(limite_inferior, limite_superior, passo)
            
            base_matrix_df = df_frota[['custo_final_por_tonelada']].copy()
            base_matrix_df = base_matrix_df.rename(columns={'custo_final_por_tonelada': 'Custo (R$/t)'})
            demanda_anual_total = DEFAULT_PARAMS['demanda_anual']
            profit_matrix_df = base_matrix_df.copy()
            margin_matrix_df = base_matrix_df.copy()
            profit_cols = []
            margin_cols = []
            formatter_f1 = {'Custo (R$/t)': '{:.3f}'}
            formatter_f2 = {'Custo (R$/t)': '{:.3f}'}

            for preco in precos_frete_teste:
                preco_calc = 1e-9 if preco == 0 else preco 
                col_name_profit = f"Lucro @ R$ {preco:.2f}"
                col_name_margin = f"Margem @ R$ {preco:.2f}"
                lucro_total = (preco - base_matrix_df['Custo (R$/t)']) * demanda_anual_total / 1_000_000
                profit_matrix_df[col_name_profit] = lucro_total
                profit_cols.append(col_name_profit)
                formatter_f1[col_name_profit] = '{:.2f} M'
                margem_pct = ((preco_calc - base_matrix_df['Custo (R$/t)']) / preco_calc) * 100
                margin_matrix_df[col_name_margin] = margem_pct
                margin_cols.append(col_name_margin)
                formatter_f2[col_name_margin] = '{:.2f}%'

            # Tabela 1: Lucro Anual Total (R$ Milhões)
            st.dataframe(profit_matrix_df[['Custo (R$/t)'] + profit_cols]
                        .style
                        .background_gradient(cmap='RdYlGn', subset=profit_cols, axis=None)
                        .format(formatter_f1, decimal=',', thousands='.')
                        )
            st.caption(f"Valores da Matriz (excluindo Custo) estão em R\$ Milhões por ano, baseados no Preço Central de R$ {preco_central:.2f}/t.")
            
            # Tabela 2: Margem de Lucro (%)
            st.header("Análise F.2: Matriz de Margem de Lucro (%)")
            st.dataframe(margin_matrix_df[['Custo (R$/t)'] + margin_cols]
                        .style
                        .background_gradient(cmap='RdYlGn', subset=margin_cols, axis=None)
                        .format(formatter_f2, decimal=',', thousands='.')
                        )
            st.caption("Valores da Matriz (excluindo Custo) mostram a Margem de Lucro ( (Venda-Custo)/Venda )")

        except Exception as e:
            st.error(f"Erro ao gerar Matriz de Lucratividade: {e}")
else:
    st.info("Ajuste os parâmetros na barra lateral e clique em 'Executar Simulações' para ver os resultados.")