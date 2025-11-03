# Custo-Transporte-App

Aplicativo de simulação e análise de viabilidade econômica para comboios fluviais, focado no cálculo de custo (R$/tonelada) e na otimização de frotas.

Este aplicativo, construído em Streamlit, permite que engenheiros navais, planejadores logísticos e analistas financeiros modelem o Custo Total de Propriedade (TCO) para operações de comboios fluviais (empurradores e balsas).

A ferramenta utiliza parâmetros de engenharia, operação e financeiros para executar simulações e fornecer análises de viabilidade.

## Acesso Rápido (Online)

O aplicativo está hospedado no Streamlit Community Cloud e pode ser acessado publicamente através do seguinte link:

**[https://custo-transporte.streamlit.app/](https://custo-transporte.streamlit.app/)**

## Funcionalidades Principais

O dashboard principal permite ao usuário ajustar dezenas de parâmetros e executa um conjunto de análises automaticamente:

  * **Simulação Dinâmica (Base):**
    Calcula o desempenho e o custo do comboio (R$/t) considerando a variação da profundidade do rio mês a mês. O calado operacional é ajustado dinamicamente, afetando a capacidade de carga em cada viagem.

  * **Análise A: Sensibilidade (Gráfico de Tornado):**
    Testa o impacto no custo final (R$/t) ao variar os principais parâmetros de entrada (como preço do combustível, taxa de juros, velocidade, etc.) em +/- 10%.

  * **Análise B: Ponto de Equilíbrio (Break-Even):**
    Com base em um preço de frete (R$/t) inserido pelo usuário, calcula o volume mínimo de carga (em toneladas) que o comboio precisa transportar anualmente para cobrir todos os custos fixos e variáveis.

  * **Análise C: Otimização de Velocidade (Comboio Único):**
    Executa a simulação dinâmica completa para uma faixa de velocidades (ex: 4 a 9 nós) e identifica qual velocidade resulta no menor custo por tonelada (R$/t) para um *único comboio*.

  * **Análise D: Otimização de Frota (Negócio Total):**
    Utiliza os resultados da Análise C para calcular o custo ótimo para atender a uma *demanda de mercado total*. Esta análise encontra a velocidade que minimiza o custo final para o negócio como um todo, calculando a frota necessária (número de comboios) para cada ponto de velocidade.

  * **Análise F: Matriz de Lucratividade:**
    Gera duas matrizes (Lucro Anual Total em R$ Milhões e Margem de Lucro %) que cruzam diferentes velocidades de operação com diferentes preços de frete, permitindo uma visualização clara dos cenários de maior rentabilidade.

## Arquitetura do Projeto

O código é modularizado para separar a interface, a lógica de análise e o motor de cálculo:

  * **`app.py`**

      * O frontend da aplicação, construído com **Streamlit**.
      * Responsável por renderizar a interface do usuário (sidebar de parâmetros e painel de resultados).
      * Coleta todas as entradas do usuário e orquestra a execução das simulações ao chamar as funções do `analysis.py`.
      * Exibe os resultados em forma de métricas, tabelas (Pandas) e gráficos (Plotly).

  * **`analysis.py`**

      * Contém a lógica de negócios e as funções para cada análise (A, B, C, D).
      * Orquestra as simulações. Por exemplo, a `run_simulacao_dinamica` chama o `engine.py` 12 vezes (uma para cada mês) para simular o ano dinâmico. A `run_analysis_velocity_optimization` chama a `run_simulacao_dinamica` múltiplas vezes (uma para cada velocidade testada).

  * **`engine.py`**

      * O "motor" de cálculo principal do projeto.
      * Contém a função `calcular_custos_comboio`, que recebe todos os parâmetros de engenharia, operação e finanças.
      * Executa uma única simulação estática (para um calado e dias de operação definidos) e retorna um dicionário com todos os custos (CAPEX, OPEX) e métricas de desempenho (viagens, carga total, etc.).

  * **`data_utils.py`**

      * Módulo utilitário para buscar dados externos.
      * Inclui uma função para buscar a meta da taxa SELIC (taxa de juros) mais recente da API do Banco Central do Brasil (BCB), usada como valor padrão no formulário.

## Lógica de Cálculo Principal (Engine)

A função `calcular_custos_comboio` é a base de todas as análises e segue esta lógica:

1.  **Formação do Comboio:** Determina automaticamente a formação ideal do comboio (número de balsas na longitudinal vs. paralela) com base nas restrições de engenharia inseridas (raio de curvatura do rio e largura do canal).
2.  **Capacidade de Carga:** Calcula a capacidade de carga por balsa e por comboio com base no calado operacional (`calado_op_input`) fornecido para a simulação.
3.  **Cálculo de Tempos:** Calcula o tempo de ida (a favor da correnteza) e volta (contra a correnteza), além dos tempos de eclusagem, manobra e operação portuária (carga/descarga), resultando no tempo total de viagem.
4.  **Desempenho Anual:** Com base no tempo de viagem e nos dias de operação, calcula o número total de viagens por ano e a carga total transportada.
5.  **Custos (CAPEX e OPEX):**
      * Calcula o **CAPEX** (Custo de Capital) usando fórmulas empíricas para o custo de construção do empurrador (baseado no BHP necessário) e das balsas (baseado no peso leve).
      * Anualiza o CAPEX usando o Fator de Recuperação de Capital (FRC) com base na taxa de juros e vida útil.
      * Calcula o **OPEX Fixo** (tripulação, alimentação, seguros, manutenção) e o **OPEX Variável** (principalmente combustível, com base no consumo do motor, BHP e tempo de viagem).
6.  **Resultado Final:** Retorna o custo total anual, custo por tonelada (R$/t) e custo por tonelada-quilômetro (R$/t-km).

## Avisos Importantes e Limitações

**Atenção:** Este simulador é uma ferramenta de modelagem e deve ser usado com as seguintes ressalvas:

1.  **Dados de Profundidade (Calado):** Os níveis médios mensais do rio (a variável `LISTA_PROF_MESES`) estão fixados diretamente no código-fonte do arquivo `app.py`. Para uma simulação correta, o usuário **deve** alterar esta lista para que reflita os dados históricos ou projetados do trecho de rio específico a ser analisado.

2.  **Fórmulas Empíricas:** Os cálculos de engenharia, como o `bhp_necessario`, `custo_construcao_comboio` e `custo_construcao_empurrador` (localizados em `engine.py`), são baseados em fórmulas empíricas e regressões. Estas fórmulas podem necessitar de calibração ou substituição dependendo da frota, estaleiro e bacia hidrográfica em questão.

## Como Executar

1.  Clone este repositório:
    ```bash
    git clone https://github.com/phelipestoiber/custo-transporte-app
    ```
2.  Instale as dependências. É recomendado criar um ambiente virtual:
    ```bash
    pip install -r requirements.txt
    ```
3.  Execute a aplicação Streamlit:
    ```bash
    streamlit run app.py
    ```
    ou em caso de erro
    ```bash
    python -m streamlit run app.py
    ```
5.  A aplicação será aberta automaticamente no seu navegador.

## Dependências

O projeto requer as seguintes bibliotecas Python:

```
# requirements.txt
streamlit
pandas
numpy
plotly
requests
holidays
```
