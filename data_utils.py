# data_utils.py
import requests
import datetime
import holidays 
import pandas as pd
from io import StringIO
from typing import Tuple

def buscar_meta_selic_anual(valor_padrao: float = 0.15) -> Tuple[float, str]:
    """
    Busca a meta da taxa SELIC anual mais recente da API do Banco Central.
    """
    url_api = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
    
    try:
        response = requests.get(url_api, timeout=5)
        response.raise_for_status()
        dados = response.json()
        if dados and isinstance(dados, list) and 'valor' in dados[0]:
            taxa_percentual = float(dados[0]['valor'])
            taxa_decimal = taxa_percentual / 100.0
            print(f"--- INFO: Meta SELIC obtida via API: {taxa_percentual:.2f}% a.a. ---")
            return taxa_decimal, f"API BCB (SELIC: {taxa_percentual:.2f}%)"
    except requests.exceptions.RequestException as e:
        print(f"--- ALERTA: Falha ao buscar API do BCB ({e}). Usando taxa padrão. ---")
    except (ValueError, KeyError, IndexError):
        print("--- ALERTA: Resposta da API do BCB em formato inesperado. Usando taxa padrão. ---")
        
    taxa_padrao_pct = valor_padrao * 100
    print(f"--- INFO: Usando taxa de juros padrão: {taxa_padrao_pct:.2f}% a.a. ---")
    return valor_padrao, f"Padrão ({taxa_padrao_pct:.2f}%)"

def get_info_dias_operacao(dias_base_input: float) -> str:
    """
    Informa sobre feriados, mas confirma que os dias de operação são um input de disponibilidade.
    """
    try:
        ano_corrente = datetime.date.today().year
        feriados_br = holidays.Brazil(year=ano_corrente)
        num_feriados = len(feriados_br)
        return f"INFO: Dias de operação baseados em input de disponibilidade ({dias_base_input:.0f} dias). Ref: {num_feriados} feriados nacionais em {ano_corrente} (lib 'holidays')."
    except Exception:
        return f"INFO: Dias de operação baseados em input de disponibilidade ({dias_base_input:.0f} dias)."

def buscar_niveis_mensais_ana(codigo_estacao: str, ano: int) -> list:
    """
    Busca as cotas médias mensais de uma estação da ANA para um ano específico.
    (Função mantida para uso futuro)
    """
    print(f"--- INFO: Buscando dados de nível (Cota) da ANA para estação {codigo_estacao}...")
    url = "https://www.ana.gov.br/telemetria/dadosfull"
    params = {
        'codEstacao': codigo_estacao, 'tipoDados': '3', 'dataInicio': f'01/01/{ano}',
        'dataFim': f'31/12/{ano}', 'slcTipoEstacao': 'F', 'txTitulo': 'Dados da Estação',
        'comp': 'false', 'resp': 'tab', 'tipoArq': '2'
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data_io = StringIO(response.text)
        df = pd.read_csv(data_io, sep=';', skiprows=11, decimal=',', 
                         usecols=['Data', 'Nivel'], parse_dates=['Data'], dayfirst=True)
        df['Nivel'] = pd.to_numeric(df['Nivel'], errors='coerce')
        df = df.dropna(subset=['Nivel'])
        df = df.set_index('Data')
        df_mensal = df['Nivel'].resample('M').mean()
        lista_niveis_m = (df_mensal / 100.0).tolist()
        if len(lista_niveis_m) != 12:
            raise ValueError(f"Dados incompletos da ANA, {len(lista_niveis_m)} meses encontrados.")
        print("--- INFO: Dados da ANA obtidos e processados com sucesso. ---")
        return lista_niveis_m
    except requests.exceptions.RequestException as e:
        print(f"--- ALERTA: Falha ao buscar API da ANA ({e}). Usando dados estáticos. ---")
        return None
    except Exception as e:
        print(f"--- ALERTA: Falha ao processar dados da ANA ({e}). Usando dados estáticos. ---")
        return None