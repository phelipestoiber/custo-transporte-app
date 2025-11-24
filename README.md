# Custo-Transporte-App: Simulador de Viabilidade Econômica Fluvial

Este repositório contém uma ferramenta avançada de modelagem financeira e engenharia naval para simulação de custos de transporte em comboios fluviais. Desenvolvido em **Python** com interface **Streamlit**, o sistema oferece uma suíte completa de análises para tomada de decisão estratégica em logística hidroviária.

## 🎯 Objetivo

Calcular o **Custo Total de Propriedade (TCO)** e o custo unitário (**R$/tonelada**) de operações fluviais, considerando:
* **Física da Navegação:** Resistência ao avanço, potência (BHP), consumo de combustível e restrições de calado.
* **Engenharia Econômica:** CAPEX (Amortização SAC/Price via FRC), OPEX Fixo (Tripulação, Seguros) e Variável (Diesel).
* **Sazonalidade:** Impacto da variação do nível do rio (calado dinâmico) mês a mês na capacidade de carga.

## 🚀 Funcionalidades (Módulos de Análise)

O dashboard está dividido em 8 abas de análise estratégica:

1.  **Cenário Atual (Base):** Simulação detalhada dos parâmetros inseridos, com breakdown de custos (Pizza) e tabela de operação mensal.
2.  **Sensibilidade:** Gráfico de Tornado analisando o impacto (+/- 10%) de variáveis críticas (Combustível, Velocidade, Juros, etc.) no custo final.
3.  **Break-Even (Ponto de Equilíbrio):** Cálculo do volume mínimo para viabilidade financeira, com alertas visuais de capacidade excedida.
4.  **Velocidade Fixa (Otimização OPEX):** Encontra a velocidade operacional ideal considerando um motor pré-definido.
5.  **Otimização de Frota:** Dimensionamento do número de comboios para atender uma demanda anual de mercado (ex: 2M tons).
6.  **Otimização Global (Design vs. Operação):**
    * Algoritmo iterativo que simula a compra de diferentes motores (**Decisão de Investimento/CAPEX**).
    * Otimiza a operação mês a mês respeitando a potência do motor escolhido (**Decisão Operacional/OPEX**).
7.  **Matriz de Lucratividade:** Mapa de calor (Heatmap) cruzando **Velocidade** vs **Preço de Frete** para visualizar margens de lucro e riscos.
8.  **Sustentabilidade ($CO_2$):** Cálculo de emissões totais e intensidade de carbono ($kgCO_2/t$), analisando o trade-off entre custo financeiro e impacto ambiental.

## 🏗️ Arquitetura do Projeto

O código foi refatorado para seguir uma arquitetura modular e desacoplada:

* **`app.py` (Interface):** Camada de apresentação (View). Gerencia os inputs do usuário na Sidebar, chama os controladores e renderiza gráficos (Plotly) e tabelas.
* **`analysis.py` (Controller / Business Logic):** Cérebro da aplicação. Contém os loops de otimização, algoritmos de busca e orquestração de cenários.
* **`engine.py` (Core):** Motor de cálculo determinístico. Contém as funções puras para cálculo de CAPEX, OPEX e Física Naval. Não contém lógica de iteração.
* **`helpers.py` (Utils):** Fórmulas de engenharia naval (estimativa de peso leve, resistência ao avanço, arranjo de comboios).
* **`data_utils.py` (Data):** Conectores externos (ex: API do Banco Central para taxa SELIC).

## ⚠️ Avisos Importantes e Limitações

**Atenção:** Este simulador é uma ferramenta de modelagem e deve ser usado com as seguintes ressalvas:

1.  **Dados de Profundidade (Calado):** Os níveis médios mensais do rio (a variável `LISTA_PROF_MESES`) estão fixados diretamente no código-fonte do arquivo `app.py`. Para uma simulação correta, o usuário **deve** alterar esta lista para que reflita os dados históricos ou projetados do trecho de rio específico a ser analisado.

2.  **Fórmulas Empíricas:** Os cálculos de engenharia, como o `bhp_necessario`, `custo_construcao_comboio` e `custo_construcao_empurrador` (localizados em `helpers.py`), são baseados em fórmulas empíricas e regressões. Estas fórmulas podem necessitar de calibração ou substituição dependendo da frota, estaleiro e bacia hidrográfica em questão.

## 🔧 Como Executar

### Pré-requisitos
* Python 3.8+
* Virtualenv (recomendado)

### Instalação e Execução

1.  Clone o repositório:
    ```bash
    git clone [https://github.com/seu-usuario/custo-transporte-app.git](https://github.com/seu-usuario/custo-transporte-app.git)
    cd custo-transporte-app
    ```

2.  Crie e ative um ambiente virtual (opcional, mas recomendado):
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # Linux/Mac:
    source .venv/bin/activate
    ```

3.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

4.  Execute a aplicação Streamlit:
    ```bash
    streamlit run app.py
    ```
    Ou, em caso de erro no comando acima:
    ```bash
    python -m streamlit run app.py
    ```

5.  A aplicação será aberta automaticamente no seu navegador.

## 📊 Metodologia de Cálculo

* **Dimensionamento de Motor:** Baseado na fórmula de resistência ao avanço (Fórmula de Howe/Empírica) ajustada para águas rasas.
* **Custo de Capital:** Utiliza o **Fator de Recuperação de Capital (FRC)** para anualizar o investimento considerando a taxa de atratividade (WACC/SELIC).
* **Restrições Físicas:** O algoritmo de otimização global verifica mês a mês se a potência exigida pela velocidade desejada ($BHP_{req}$) não excede a potência instalada do motor ($BHP_{inst}$).

## 🛠️ Tecnologias Utilizadas

* **Streamlit:** Frontend interativo.
* **Pandas & NumPy:** Manipulação de dados e vetores.
* **Plotly:** Visualização de dados (Gráficos interativos).
* **Requests:** Integração com APIs externas.

---
*Desenvolvido para análise estratégica de logística fluvial na região Amazônica.*