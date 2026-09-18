import pandas as pd
import gspread
import os
import glob
import json
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

def ask_llm_for_barbell_strategy(df_signals, bankroll=50.0):
    """
    Camada 5 (Agente LLM): Injeta os dados matemáticos no Gemini e extrai 
    os bilhetes estruturados com base no prompt Quantitativo (Nova SDK - v3.6).
    """
    logging.info("Conectando ao cérebro LLM (Google GenAI - v3.6)...")
    
    # Pega apenas os top 15 maiores Edges para economizar tokens
    df_top = df_signals.sort_values(by='edge', ascending=False).head(15)
    
    # INCLUSÃO DA DATA e correção do formato ISO
    dados_json = df_top[['date', 'league', 'home_team', 'away_team', 'market_type', 'market_odd', 'edge', 'prob']].to_json(orient='records', date_format='iso')    
    
    # Inicializa o cliente da nova SDK
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = f"""
    Você é um Engenheiro Quantitativo de Mercados Esportivos, operando um fundo baseado na Estratégia Barbell (Antifragilidade).
    Seu objetivo é analisar o JSON de oportunidades calculadas pelo motor Python e alocar o orçamento diário garantindo a sobrevivência matemática e a captura de convexidade.

    ORÇAMENTO DA SESSÃO: R$ {bankroll} (Exposição total = 100%)

    DADOS QUANTITATIVOS DA RODADA (JSON):
    Os dados abaixo já possuem as datas (date), probabilidades matemáticas (prob), odds da SuperBet (market_odd) e o Valor Esperado validado (edge).
    {dados_json}

    REGRAS DE ALOCAÇÃO BARBELL:
    1. PONTA ÂNCORA (70% a 85% do capital): 1 a 2 apostas em mercados de baixa variância (1X2 favorito, DNB, Dupla Chance). Perfil de odds: 1.45 a 2.10.
    2. PONTA CONVEXA (15% a 30% do capital): 1 a 2 bilhetes compostos (Bet Builders) ou zebras isoladas. Perfil de odds: 4.50+. A tese deve justificar o risco assimétrico.

ESTRUTURA DE SAÍDA OBRIGATÓRIA (JSON ESTRITO):
Você é um Analista Quantitativo Sênior. Sua missão é ler as probabilidades matemáticas puras (xG, Poisson) e encontrar assimetrias contra as cotações das casas de apostas. 
Você DEVE analisar a correlação matemática (ex: se o modelo prevê um jogo truncado e Under 2.5, evite Handicaps negativos altos; se prevê domínio absoluto, sugira Asian Handicap no lugar da Vitória Seca).

Sua resposta deve ser EXCLUSIVAMENTE um array JSON com as recomendações de apostas, respeitando a estrutura Barbell:
[
  {{
    "ponta": "Âncora ou Convexa",
    "torneio": "Nome da Liga",
    "bilhete": "Confronto",
    "selecao_principal": "O mercado com maior Edge (ex: Handicap Asiático +1.0, Under 2.5, BTTS Sim, Dupla Chance)",
    "odd_projetada_minima": "Odd mínima aceitável para manter o EV+",
    "alocacao_pct": "80% da Unidade Diária (se Âncora) ou 20% da Unidade Diária (se Convexa)",
    "analise_correlacao": "Explique a correlação matemática. Ex: 'O modelo indica 60% de chance de vitória, mas forte tendência de Under 2.5. Para a perna Âncora, o Handicap -0.25 ou o DNB absorvem o risco do jogo terminar 0x0 ou 1x1.'",
    "edge_calculado": "O valor esperado percentual (+EV)"
  }}
]
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
        )
        
        recomendacoes = json.loads(response.text)
        return pd.DataFrame(recomendacoes)
    except Exception as e:
        logging.error(f"Erro na requisição ao LLM: {e}")
        return pd.DataFrame()

def export_to_sheets(df, sheet_url):
    """
    Injeta o relatório estruturado do LLM no Google Sheets.
    """
    if df.empty:
        logging.warning("Nenhum dado para exportar ao Sheets.")
        return
        
    logging.info(f"Conectando ao Google Cloud via URL da Planilha...")
    
    if not os.path.exists('credentials.json'):
        logging.error("Erro FATAL: Arquivo credentials.json não encontrado.")
        return
        
    gc = gspread.service_account(filename='credentials.json')
    
    try:
        # BYPASS ANTI-BOT: Abrimos pela URL direta em vez de pesquisar pelo nome
        sh = gc.open_by_url(sheet_url) 
        worksheet = sh.sheet1
    except Exception as e:
        logging.error(f"Erro ao abrir a planilha: {e}")
        return
    
    # Formatação das colunas para envio
    df_export = df.copy()
    
    # Capitaliza o cabeçalho para ficar elegante na planilha
    df_export.columns = [col.replace('_', ' ').title() for col in df_export.columns]
    df_export = df_export.fillna('').astype(str)
    
    dados = [df_export.columns.values.tolist()] + df_export.values.tolist()
    
    worksheet.clear()
    worksheet.update(values=dados, range_name='A1')
    
    logging.info(f"[SUCESSO] Relatório de IA Quantitativa exportado para o dashboard online!")

if __name__ == "__main__":
    import pytz
    load_dotenv()
    
    print("\n--- INICIANDO CAMADA 5: AGENTE DE IA QUANTITATIVO ---")
    
    arquivos_platinum = glob.glob("G:/Meu Drive/Quant/platinum/*_Sizing_Live.csv")
    
    if not arquivos_platinum:
        print("Erro FATAL: Nenhum arquivo Platinum encontrado.")
        exit()
        
    paineis = []
    for arq in arquivos_platinum:
        paineis.append(pd.read_csv(arq))
        
    df_mestre = pd.concat(paineis, ignore_index=True)
    
    # Converte para formato de data
    df_mestre['date'] = pd.to_datetime(df_mestre['date'], errors='coerce')
    
    # Captura a data exata de HOJE forçando o fuso horário do Brasil
    fuso_br = pytz.timezone('America/Sao_Paulo')
    data_alvo = datetime.now(fuso_br).strftime('%Y-%m-%d')
    
    # Filtra: apenas jogos do dia, que não estão ignorados e que possuem Edge positivo
    filtro_data = df_mestre['date'].dt.strftime('%Y-%m-%d') == data_alvo
    filtro_estrategia = df_mestre['strategy'] != 'Ignore'
    filtro_edge = df_mestre['edge'] > 0
    
    df_signals = df_mestre[filtro_data & filtro_estrategia & filtro_edge].copy()
    
    if df_signals.empty:
        print(f"Nenhuma assimetria encontrada para a data {data_alvo}.")
    else:
        print(f"[{len(df_signals)}] oportunidades encontradas para {data_alvo}. Passando para o LLM...")
        
        # 1. Pede para a IA ler, raciocinar e montar as Múltiplas/Bilhetes Barbell
        df_recomendacoes_ia = ask_llm_for_barbell_strategy(df_signals, bankroll=50.0)
        
        # 2. Faz o deploy apenas do relatório final da IA no Google Sheets
        export_to_sheets(df_recomendacoes_ia, sheet_url="https://docs.google.com/spreadsheets/d/1kpnZ5rrQSIwv1GBozO0uQ9OR6_huJTJEhzaSmXvwO2w/edit?gid=0#gid=0")