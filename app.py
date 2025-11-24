# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import analysis
import data_utils

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="Simulador de Frota Naval")

# --- 2. PARÂMETROS GLOBAIS (RIO) ---
LISTA_PROF_MESES = [
    7.72, 9.87, 10.86, 10.98, 8.43, 6.35, 
    5.12, 3.89, 3.30, 3.00, 3.65, 5.23
]
MESES_ABREV = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']

# --- 3. SIDEBAR: INPUTS ---
st.sidebar.title("Parâmetros de Simulação")

st.sidebar.header("1. Parâmetros de Mercado")
preco_frete_input = st.sidebar.number_input(
    "Preço do Frete (R$/t)", 
    min_value=0.0, value=30.00, step=0.50,
    help="Preço de venda do serviço. Usado no Break-Even."
)
demanda_anual = st.sidebar.number_input(
    "Demanda Anual de Mercado (t)", 
    value=10_000_000, step=100_000,
    help="Volume total a ser transportado. Usado na Otimização de Frota."
)

with st.sidebar.expander("2. Engenharia e Rio"):
    folga_seguranca = st.number_input("Folga de Segurança (m)", value=0.50)
    calado_design_alvo = st.number_input("Calado de Design (m)", value=3.66)
    dias_base_anuais = st.number_input("Dias Disponíveis/Ano", value=330.0)
    dist_km_input = st.number_input("Distância de Viagem (km)", value=500.0)
    comp_balsa = st.number_input("Comprimento Balsa (m)", value=60.96)
    boca_balsa = st.number_input("Boca Balsa (m)", value=10.67)
    pontal_balsa = st.number_input("Pontal Balsa (m)", value=4.27)
    coef_bloco = st.number_input("Coef. Bloco (Cb)", value=0.90)
    raio_curvatura = st.number_input("Raio Curvatura Rio (m)", value=750.0)
    largura_canal = st.number_input("Largura Canal (m)", value=70.0)

with st.sidebar.expander("3. Operação (Base)"):
    vel_embarcacao_nos = st.slider("Velocidade Alvo (nós)", 4.0, 12.0, 8.0, 0.1)
    vel_correnteza_nos = st.number_input("Velocidade Correnteza (nós)", value=1.92)
    t_eclusagem_min = st.number_input("Tempo Eclusa (min)", value=92.0)
    t_manobra_balsa_min = st.number_input("Tempo Manobra/Balsa (min)", value=20.0)
    num_bercos = st.number_input("Nº Berços", value=2)
    prod_carregamento = st.number_input("Prod. Carga (t/h)", value=2500.0)
    prod_descarregamento = st.number_input("Prod. Descarga (t/h)", value=1250.0)
    num_tripulantes = st.number_input("Tripulação", value=8)
    eficiencia_propulsor = st.number_input("Eficiência Propulsiva", value=0.50)

with st.sidebar.expander("4. Financeiro"):
    try:
        taxa_juros_base, info_selic = data_utils.buscar_meta_selic_anual()
    except:
        taxa_juros_base, info_selic = 0.15, "Padrão (Falha API)"
        
    taxa_juros_input_pct = st.number_input(f"Taxa de Juros Anual (%) - {info_selic}", value=taxa_juros_base * 100)
    taxa_juros_input = taxa_juros_input_pct / 100.0
    vida_util_anos = st.number_input("Vida Útil (anos)", value=20)
    preco_combustivel = st.number_input("Preço Diesel (R$/L)", value=6.06)
    consumo_motor_fc = st.number_input("Consumo Específico (kg/HP/h)", value=0.16)
    densidade_combustivel = st.number_input("Densidade Diesel (kg/L)", value=0.85)
    salario_medio = st.number_input("Salário Médio (R$)", value=4500.0)
    vale_alimentacao = st.number_input("Vale Alimentação (R$)", value=720.0)
    encargos_sociais_pct = st.number_input("Encargos Sociais (%)", value=0.90)

run_button = st.sidebar.button("EXECUTAR SIMULAÇÃO", type="primary")

# --- 4. CORPO PRINCIPAL ---
st.title("⚓ Dashboard de Estratégia Fluvial")
st.markdown("Ferramenta de suporte à decisão para dimensionamento de frota e análise de viabilidade econômica.")

if run_button:
    # Dicionário de Parâmetros (Unificado)
    PARAMS = {
        "comp_balsa": comp_balsa, "boca_balsa": boca_balsa, "pontal_balsa": pontal_balsa,
        "coef_bloco": coef_bloco, "raio_curvatura": raio_curvatura, "largura_canal": largura_canal,
        "dist_km_input": dist_km_input, "t_eclusagem_min": t_eclusagem_min, "t_manobra_balsa_min": t_manobra_balsa_min,
        "vel_embarcacao_nos": vel_embarcacao_nos, "vel_correnteza_nos": vel_correnteza_nos, "num_bercos": num_bercos,
        "prod_carregamento": prod_carregamento, "prod_descarregamento": prod_descarregamento,
        "num_tripulantes": num_tripulantes, "eficiencia_propulsor": eficiencia_propulsor,
        "demanda_anual": demanda_anual, "taxa_juros_input": taxa_juros_input, "vida_util_anos": vida_util_anos,
        "preco_combustivel": preco_combustivel, "consumo_motor_fc": consumo_motor_fc, "densidade_combustivel": densidade_combustivel,
        "salario_medio": salario_medio, "vale_alimentacao": vale_alimentacao, "encargos_sociais_pct": encargos_sociais_pct
    }
    
    # --- CÁLCULO DO CENÁRIO BASE (Detalhado) ---
    with st.spinner("Calculando cenário base detalhado..."):
        res_base_detalhada = analysis.run_detailed_base_simulation(
            PARAMS, LISTA_PROF_MESES, calado_design_alvo, folga_seguranca, dias_base_anuais
        )

    # --- PREPARAÇÃO DE DADOS COMPARTILHADOS (CACHE) ---
    # Rodamos a otimização de velocidade aqui para usar nas Abas 3, 4 e 6
    with st.spinner("Processando cenário base..."):
        df_velocidade_fixa = analysis.run_fixed_speed_optimization(
            PARAMS, LISTA_PROF_MESES, calado_design_alvo, folga_seguranca, dias_base_anuais
        )
        # Otimização de Frota baseada na velocidade fixa (Análise 4)
        df_frota_otimizada = analysis.run_fleet_optimization(
            # optimization_results=None, # Passando None para forçar recálculo interno se necessário, mas...
            # ...o ideal é adaptar analysis.run_fleet_optimization para aceitar o df já calculado ou
            # chamar a função que já criamos. Vamos usar a versão atual do seu analysis.py:
            # Se run_fleet_optimization no seu analysis.py RECALCULA tudo, passamos os params.
            # Se ela pede o resultado anterior, passamos df_velocidade_fixa.
            # Assumindo a assinatura: run_fleet_optimization(base_params, ..., demanda_total)
            base_params=PARAMS,
            lista_prof_meses=LISTA_PROF_MESES,
            calado_design=calado_design_alvo,
            folga=folga_seguranca,
            dias_op=dias_base_anuais,
            demanda_total=demanda_anual
        )

    # --- ABAS DE ANÁLISE ---
    tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "0. Cenário Atual (Base)",
        "1. Sensibilidade", 
        "2. Break-Even", 
        "3. Velocidade Fixa (OPEX)", 
        "4. Otimização de Frota",
        "5. Otimização Global (Design)",
        "6. Matriz de Lucro",
        "7. Sustentabilidade (CO2)"
    ])

    # --- ABA 0: CENÁRIO ATUAL (BASE) ---
    with tab0:
        st.header("Resultados do Cenário Inserido")
        st.markdown(f"Condição atual: **{vel_embarcacao_nos} nós** | Calado Alvo: **{calado_design_alvo}m**")
        
        # 1. Métricas Principais
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Formação", f"{res_base_detalhada['n_long']}x{res_base_detalhada['n_par']}")
        col2.metric("Custo Unitário", f"R$ {res_base_detalhada['custo_unitario']:.2f} /t".replace('.',','))
        col3.metric("Carga Anual", f"{res_base_detalhada['carga_anual']:,.0f} t".replace(',','.'))
        col4.metric("Viagens Totais", f"{res_base_detalhada['viagens_anuais']:.0f}")
        col5.metric("Custo Total Anual (Comboio)", f"R$ {res_base_detalhada['custo_total_anual']/1e6:,.2f}M".replace('.',','))
        
        st.divider()

        st.subheader("Indicadores Ambientais")
        kpi1, kpi2 = st.columns(2)
        kpi1.metric("Emissões Totais (Ano)", f"{res_base_detalhada['emissoes_total_ton']:,.1f} tCO2")
        kpi2.metric("Intensidade de Carbono", f"{res_base_detalhada['intensidade_carbono_kg_t']:.2f} kgCO2/t")
        
        st.divider()
        
        # 2. Gráfico de Contribuição de Custos
        c_chart, c_table = st.columns([1, 1])
        
        with c_chart:
            st.subheader("Composição de Custos")
            df_breakdown = pd.DataFrame(list(res_base_detalhada['breakdown_custos'].items()), columns=['Componente', 'Valor (R$)'])
            fig_pie = px.pie(df_breakdown, values='Valor (R$)', names='Componente', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c_table:
            st.subheader("Detalhes Mensais")
            df_mensal = res_base_detalhada['df_mensal']
            
            # Funções auxiliares para formatação Brasileira (Ponto p/ milhar, Vírgula p/ decimal)
            fmt_br_dec = lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            fmt_br_int = lambda x: f"{x:,.0f}".replace(",", ".")
            fmt_br_1dec = lambda x: f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            # Formatação para exibição
            st.dataframe(
                df_mensal.style.format({
                    'Calado (m)': fmt_br_dec,
                    'Capacidade Viagem (t)': fmt_br_int,
                    'Viagens': fmt_br_1dec,
                    'Carga no Mês (t)': fmt_br_int
                }),
                use_container_width=True,
                height=400,
                hide_index=True
            )

    # --- ABA 1: SENSIBILIDADE ---
    with tab1:
        st.header("Análise de Sensibilidade (+/- 10%)")
        st.markdown("Impacto percentual no **Custo Unitário (R$/t)** ao variar cada parâmetro.")

        fmt_br = lambda x: f"{x:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
        
        with st.spinner("Calculando sensibilidades..."):
            df_sens = analysis.run_sensitivity_analysis(PARAMS, LISTA_PROF_MESES, calado_design_alvo, folga_seguranca, dias_base_anuais)
            
            # Gráfico Tornado
            df_sens_long = df_sens.melt(id_vars=['Parâmetro', 'Sensibilidade Total'], 
                                        value_vars=['Impacto (+10%)', 'Impacto (-10%)'],
                                        var_name='Variação', value_name='Impacto (%)')
            
            fig_sens = px.bar(df_sens_long, y='Parâmetro', x='Impacto (%)', color='Variação', 
                              orientation='h', title="Gráfico de Tornado (Sensibilidade)",
                              color_discrete_map={'Impacto (+10%)': '#ff4b4b', 'Impacto (-10%)': '#00cc96'})
            
            st.plotly_chart(fig_sens, use_container_width=True)
            st.dataframe(
                df_sens.style
                .format(fmt_br, subset=['Impacto (+10%)', 'Impacto (-10%)', 'Sensibilidade Total']),
                hide_index=True
            )

    # --- ABA 2: BREAK-EVEN ---
    with tab2:
        st.header("Análise de Ponto de Equilíbrio")
        res_be = analysis.run_breakeven_analysis(PARAMS, LISTA_PROF_MESES, calado_design_alvo, folga_seguranca, dias_base_anuais, preco_frete_input)
        
        if res_be['viavel']:
            c1, c2, c3 = st.columns(3)
            c1.metric("Preço do Frete", f"R$ {preco_frete_input:.2f}")
            c2.metric("Volume de Equilíbrio", f"{res_be['break_even_ton']:,.0f} t".replace(',','.'))
            
            # Formatação condicional da métrica de ocupação
            ocupacao_pct = res_be['ocupacao_necessaria_pct']
            delta_color = "normal" if ocupacao_pct <= 100 else "inverse" # Fica vermelho se estourar 100%
            c3.metric("Taxa de Ocupação Necessária", f"{ocupacao_pct:.1f}%", delta=f"{100-ocupacao_pct:.1f}% (Folga)", delta_color=delta_color)
            
            with st.expander("📊 Detalhes Financeiros do Equilíbrio", expanded=True):
                col_a, col_b, col_c, col_d, col_e = st.columns(5)
                
                # 1. Custos Fixos (O valor que precisamos cobrir)
                col_a.metric(
                    "Custos Fixos Anuais", 
                    f"R$ {res_be['custos_fixos_anuais_totais']/1e6:.2f} M",
                    help="Soma de CAPEX, Tripulação, Seguros, Manutenção e Admin Fixo."
                )
                
                # 2. Custo Variável (O custo para rodar)
                col_b.metric(
                    "Custo Variável", 
                    f"R$ {res_be['custo_variavel_por_ton']:,.2f} /t",
                    help="Custo marginal (Combustível + Admin Var) para transportar 1 tonelada."
                )
                
                # 3. Margem de Contribuição (O lucro bruto por tonelada)
                col_c.metric(
                    "Margem de Contribuição", 
                    f"R$ {res_be['margem_contribuicao_por_ton']:,.2f} /t",
                    help="Quanto sobra do Frete após pagar o Combustível. É isso que paga o Custo Fixo."
                )
                
                # 4. Faturamento no Break-Even
                col_d.metric(
                    "Faturamento Mínimo", 
                    f"R$ {res_be['faturamento_break_even']/1e6:.2f} M",
                    help="Receita Bruta necessária para zerar o prejuízo (Lucro = 0)."
                )

                 # 5. Viagens Necessárias
                col_e.metric(
                    "Viagens Necessárias", 
                    f"{res_be['break_even_viagens']:.1f}",
                    help="Número de ciclos completos (Ida+Volta) para atingir o volume de equilíbrio."
                )

            st.divider()
            
            # Lógica Visual (Pizza vs Barra de Déficit) - Mantida do passo anterior
            vol_be = res_be['break_even_ton']
            cap_max = res_be['capacidade_atual']

            if vol_be > cap_max:
                st.error(f"⚠️ **Capacidade Insuficiente!** Faltam {vol_be - cap_max:,.0f} toneladas.")
                df_chart = pd.DataFrame({
                    "Métrica": ["Capacidade Máxima", "Necessário"],
                    "Toneladas": [cap_max, vol_be],
                    "Situação": ["Limite", "Déficit"]
                })
                fig_be = px.bar(df_chart, x="Toneladas", y="Métrica", color="Situação", orientation='h', 
                                color_discrete_map={"Limite": "#bdc3c7", "Déficit": "#e74c3c"}, title="Déficit de Capacidade")
                st.plotly_chart(fig_be, use_container_width=True)
            else:
                st.success(f"Operação Saudável. Margem de segurança de {(cap_max - vol_be):,.0f} toneladas.")
                fig_be = px.pie(names=['Ponto de Equilíbrio (Custo)', 'Margem de Lucro (Potencial)'], 
                                values=[vol_be, cap_max - vol_be], hole=0.4, 
                                title="Uso da Capacidade",
                                color_discrete_sequence=["#503BEF", '#00CC96'])
                st.plotly_chart(fig_be, use_container_width=True)
        else:
            st.error(
                f"🚨 **Operação Inviável:** O Preço do Frete (R$ {res_be['preco_frete']:.2f}) é menor que o "
                f"Custo Variável (R$ {res_be['custo_variavel_por_ton']:.2f}).\n\n"
                "Cada tonelada transportada aumenta o prejuízo, não importa o volume."
            )

    # --- ABA 3: VELOCIDADE FIXA ---
    with tab3:
        st.header("Melhor Velocidade Operacional (Cenário Fixo)")
        st.markdown("Considerando que o motor já está comprado e dimensionado, qual a velocidade fixa ideal?")
        
        with st.spinner("Simulando velocidades..."):
            df_fixa = analysis.run_fixed_speed_optimization(PARAMS, LISTA_PROF_MESES, calado_design_alvo, folga_seguranca, dias_base_anuais)
            
            best_v = df_fixa.loc[df_fixa['Custo (R$/t)'].idxmin()]
            
            col1, col2 = st.columns([3, 1])
            with col1:
                fig_v = px.line(df_fixa, x='Velocidade (nós)', y='Custo (R$/t)', markers=True, title="Curva de Custo x Velocidade")
                st.plotly_chart(fig_v, use_container_width=True)
            
            with col2:
                st.info(f"**Melhor Velocidade:**\n# {best_v['Velocidade (nós)']:.2f} nós")
                st.metric("Custo Mínimo", f"R$ {best_v['Custo (R$/t)']:.2f}")
                st.metric("BHP Requerido", f"{best_v['BHP Necessário']:.0f} HP")

    # --- ABA 4: FROTA ---
    with tab4:
        st.header(f"Dimensionamento de Frota (Demanda: {demanda_anual/1e6:.1f}M t)")
        
        with st.spinner("Calculando frota ótima..."):
            df_frota = analysis.run_fleet_optimization(PARAMS, LISTA_PROF_MESES, calado_design_alvo, folga_seguranca, dias_base_anuais, demanda_anual)
            
            best_f = df_frota.loc[df_frota['Custo Final da Demanda (R$/t)'].idxmin()]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Frota Ideal", f"{best_f['Frota Necessária']:.0f} Comboios")
            c2.metric("Velocidade da Frota", f"{best_f['Velocidade (nós)']:.2f} nós")
            c3.metric("Investimento Total", f"R$ {best_f['Investimento Total (R$)']/1e6:.1f} Mi")
            
            fig_f = px.bar(df_frota, x='Velocidade (nós)', y='Frota Necessária', title="Tamanho da Frota vs Velocidade")
            fig_f.add_scatter(x=df_frota['Velocidade (nós)'], y=df_frota['Custo Final da Demanda (R$/t)'], mode='lines+markers', name='Custo (R$/t)', yaxis='y2')
            fig_f.update_layout(yaxis2=dict(overlaying='y', side='right', title='Custo (R$/t)'))
            st.plotly_chart(fig_f, use_container_width=True)

    # --- ABA 5: OTIMIZAÇÃO GLOBAL ---
    with tab5:
        st.header("Otimização Global de Design (CAPEX + OPEX)")
        st.markdown("Iteração sobre diferentes tamanhos de motor para encontrar o menor **Custo Total de Propriedade (TCO)**.")
        
        with st.spinner("Executando otimização iterativa..."):
            res_global = analysis.run_global_optimization_refined(PARAMS, LISTA_PROF_MESES, calado_design_alvo, folga_seguranca, dias_base_anuais)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.success("### Vencedor Global")
                st.metric("Velocidade de Projeto (Motor)", f"{res_global['v_design']:.2f} nós")
                st.metric("Potência Instalada (BHP)", f"{res_global['bhp']:.0f} HP")
            
            with col2:
                st.warning("### Impacto Financeiro")
                st.metric("Investimento Inicial (Unid.)", f"R$ {res_global['investimento']:,.2f}")
                st.metric("Custo Mínimo Global", f"R$ {res_global['custo']:.2f} /t")

            with col3:
                st.warning("### Ambiental")
                st.metric("Emissões Totais", f"{res_global['emissoes_total']:,.0f} tCO2/ano")
                st.metric("Intensidade", f"{res_global['intensidade_co2']:.2f} kgCO2/t")

    # --- ABA 6: MATRIZ DE LUCRATIVIDADE ---
    with tab6:
        st.header("Matriz de Lucratividade e Risco")
        st.markdown("Análise de sensibilidade cruzada: **Velocidade** (Linhas) x **Preço do Frete** (Colunas).")
        
        # Usamos o DataFrame da Frota (df_frota_otimizada) como base, pois ele contém o Custo Real para atender a demanda
        res_matrizes = analysis.run_profitability_matrix_analysis(
            df_frota=df_frota_otimizada,
            demanda_total=demanda_anual,
            preco_frete_base=preco_frete_input
        )
        
        # 1. Matriz de Lucro
        st.subheader("1. Lucro Anual Total (R$ Milhões)")
        st.caption("Lucro Líquido Anual projetado para o negócio.")
        df_lucro = res_matrizes['lucro_milhoes']
        cols_preco = [c for c in df_lucro.columns if "R$" in c and "Custo" not in c]
        
        st.dataframe(
            df_lucro.style
            .format("{:.2f}", subset=cols_preco)
            .format("{:.2f}", subset=['Custo (R$/t)'])
            .background_gradient(cmap='RdYlGn', subset=cols_preco, axis=None)
        )

        # 2. Matriz de Margem
        st.subheader("2. Margem de Lucro Líquida (%)")
        st.caption("Margem (%) = (Preço - Custo) / Preço.")
        df_margem = res_matrizes['margem_pct']
        
        st.dataframe(
            df_margem.style
            .format("{:.1f}%", subset=cols_preco)
            .format("{:.2f}", subset=['Custo (R$/t)'])
            .background_gradient(cmap='RdYlGn', subset=cols_preco, vmin=0, vmax=40, axis=None)
        )

    # --- ABA 7: SUSTENTABILIDADE ---
    with tab7:
        st.header("Análise de Sustentabilidade e Emissões")
        st.markdown("Impacto da velocidade operacional na pegada de carbono da frota.")
        
        with st.spinner("Calculando perfil de emissões..."):
            df_eco = analysis.run_environmental_analysis(PARAMS, LISTA_PROF_MESES, calado_design_alvo, folga_seguranca, dias_base_anuais)
            
            # Encontrar ponto de menor emissão (geralmente velocidade mais baixa)
            best_eco = df_eco.loc[df_eco['Intensidade (kgCO2/t)'].idxmin()]
            current_eco = res_base_detalhada
            
            # Comparativo
            c1, c2, c3 = st.columns(3)
            c1.metric("Cenário Atual (CO2/t)", f"{current_eco['intensidade_carbono_kg_t']:.2f} kg/t")
            c2.metric("Melhor Cenário CO2", f"{best_eco['Intensidade (kgCO2/t)']:.2f} kg/t", help=f"Atingido na velocidade de {best_eco['Velocidade (nós)']} nós")
            
            diff_pct = ((current_eco['intensidade_carbono_kg_t'] - best_eco['Intensidade (kgCO2/t)']) / current_eco['intensidade_carbono_kg_t']) * 100
            c3.metric("Potencial de Redução", f"{diff_pct:.1f}%", delta=f"-{diff_pct:.1f}%", delta_color="normal")
            
            # Gráfico de Linha Dupla: Custo x Emissões
            st.subheader("Trade-off: Custo Financeiro vs. Custo Ambiental")
            
            fig_eco = px.line(df_eco, x='Velocidade (nós)', y='Intensidade (kgCO2/t)', title="Intensidade de Carbono por Velocidade")
            fig_eco.update_traces(line_color='#2ecc71', name="Emissões (kgCO2/t)", showlegend=True)
            
            # Adicionar eixo secundário para Custo R$/t para mostrar o trade-off
            fig_eco.add_scatter(x=df_eco['Velocidade (nós)'], y=df_eco['Custo (R$/t)'], mode='lines', name='Custo (R$/t)', yaxis='y2', line=dict(color='#e74c3c'))
            
            fig_eco.update_layout(
                yaxis=dict(
                    title=dict(text="Intensidade de Carbono (kgCO2/t)", font=dict(color="#2ecc71"))
                ),
                yaxis2=dict(
                    title=dict(text="Custo Financeiro (R$/t)", font=dict(color="#e74c3c")),
                    overlaying='y', 
                    side='right'
                ),
                legend=dict(x=0.1, y=1.1, orientation='h')
            )
            
            st.plotly_chart(fig_eco, use_container_width=True)
            
            st.dataframe(df_eco.style.format("{:.2f}").background_gradient(cmap='Greens', subset=['Intensidade (kgCO2/t)']))

else:
    st.info("Configure os parâmetros na barra lateral e clique em 'EXECUTAR SIMULAÇÃO'.")