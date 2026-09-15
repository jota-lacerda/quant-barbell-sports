import os
import pandas as pd
import requests
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

SEASON = 2026

# Mapeamento Global: {Nome da Liga: (ID_API_Football, Codigo_ESPN)}
LEAGUES = {
    'Serie_A_Brazil': (71, 'bra.1'),
    'Serie_B_Brazil': (72, 'bra.2'),
    'Premier_League': (39, 'eng.1'),
    'La_Liga': (140, 'esp.1'),
    'Serie_A_Italy': (135, 'ita.1'),
    'Ligue_1': (61, 'fra.1'),
    'Libertadores': (13, 'conmebol.libertadores'),
    'Champions_League': (2, 'uefa.champions')
}

def extract_api_football(league_id, season, api_key):
    logging.info("Tentando extrator primário (API-Football)...")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": api_key}
    
    response = requests.get(url, headers=headers, params={"league": str(league_id), "season": str(season)})
    if response.status_code != 200: raise Exception(f"HTTP {response.status_code}")
        
    data = response.json()
    if data.get('errors'): raise Exception(f"Bloqueio da API: {data['errors']}")
    if len(data.get('response', [])) == 0: raise Exception("API retornou 0 registros válidos.")
    
    return pd.DataFrame()

def extract_espn_api(espn_code):
    """
    Fallback Dinâmico da ESPN. Recebe o código exato da liga que está sendo processada.
    """
    logging.info(f"Acionando Fallback ESPN ({espn_code})...")
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{espn_code}/scoreboard"
    
    params = {
        "dates": f"{SEASON}0101-{SEASON}1231", 
        "limit": "800" # Aumentado para cobrir todas as fases de ligas longas
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f"Erro HTTP {response.status_code} na ESPN.")
            
        json_data = response.json()
        events = json_data.get('events', [])
        
        matches_list = []
        for event in events:
            fix_id = event.get('id')
            date_str = event.get('date')
            
            state = event['status']['type']['state']
            if state == 'post':
                status = 'FT'
            elif state == 'pre':
                status = 'NS'
            else:
                status = 'LIVE'
                
            competitors = event['competitions'][0]['competitors']
            home_team, away_team = "", ""
            home_goals, away_goals = 0.0, 0.0
            
            for comp in competitors:
                team_name = comp['team']['name']
                score = float(comp.get('score', 0)) if state == 'post' else 0.0
                
                if comp['homeAway'] == 'home':
                    home_team, home_goals = team_name, score
                else:
                    away_team, away_goals = team_name, score
                    
            matches_list.append({
                "fixture_id": f"espn_{fix_id}", 
                "date": date_str,
                "status": status,
                "home_team": home_team,
                "away_team": away_team,
                "home_goals": home_goals,
                "away_goals": away_goals
            })
            
        df = pd.DataFrame(matches_list)
        return df
        
    except Exception as e:
        raise Exception(f"Falha na API da ESPN: {e}")

def run_ingestion_pipeline(league_name, api_id, espn_code, api_key):
    file_path = f"G:/Meu Drive/Quant/bronze/{league_name}_{SEASON}.csv"
    
    if os.path.exists(file_path):
        logging.info(f"[CACHE] Dados de {league_name} já existem no disco.")
        return pd.read_csv(file_path)
        
    logging.info(f"== Processando {league_name} ==")
    
    try:
        df = extract_api_football(api_id, SEASON, api_key)
    except Exception as e_api:
        logging.warning(f"Extrator primário bloqueado: {e_api}")
        try:
            df = extract_espn_api(espn_code)
        except Exception as e_espn:
            logging.error(f"Extrator secundário falhou: {e_espn}")
            return pd.DataFrame()

    if not df.empty:
        os.makedirs("G:/Meu Drive/Quant/bronze", exist_ok=True)
        df.to_csv(file_path, index=False)
        logging.info(f"SUCESSO! {len(df)} partidas de {league_name} salvas em {file_path}\n")
        
    return df

if __name__ == "__main__":
    load_dotenv()
    API_KEY = os.getenv("API_FOOTBALL_KEY")
    
    print("\n=======================================================")
    print(" MOTOR DE INGESTÃO LIVE (MULTI-LIGAS COM FALLBACKS)")
    print("=======================================================\n")
    
    all_dataframes = {}
    
    for league_name, codes in LEAGUES.items():
        api_id = codes[0]
        espn_code = codes[1]
        
        df_league = run_ingestion_pipeline(league_name, api_id, espn_code, API_KEY)
        if not df_league.empty:
            all_dataframes[league_name] = df_league
            
    print("\n=== RESUMO DO DATA LAKE BRONZE (2026) ===")
    for nome, dataframe in all_dataframes.items():
        # Filtramos para mostrar rapidamente quantos jogos já ocorreram (FT) e quantos estão no futuro (NS)
        ft_count = len(dataframe[dataframe['status'] == 'FT'])
        ns_count = len(dataframe[dataframe['status'] == 'NS'])
        print(f"{nome}: {len(dataframe)} partidas totais (Passado: {ft_count} | Futuro: {ns_count})")