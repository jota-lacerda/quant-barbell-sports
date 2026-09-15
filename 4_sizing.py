import pandas as pd
import numpy as np
import os
import requests
from dotenv import load_dotenv
import logging
from difflib import get_close_matches

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

ODDS_API_SPORTS = {
    'Serie_A_Brazil': 'soccer_brazil_campeonato',
    'Serie_B_Brazil': 'soccer_brazil_serie_b',
    'Premier_League': 'soccer_epl',
    'La_Liga': 'soccer_spain_la_liga',
    'Serie_A_Italy': 'soccer_italy_serie_a',
    'Ligue_1': 'soccer_france_ligue_one',
    'Libertadores': 'soccer_conmebol_copa_libertadores',
    'Champions_League': 'soccer_uefa_champs_league'
}

def fetch_the_odds_api(league_name, api_key):
    """
    Busca odds reais da Pinnacle/Bet365 (Mercado 1X2 / h2h) na The Odds API.
    """
    sport_key = ODDS_API_SPORTS.get(league_name)
    if not sport_key:
        return pd.DataFrame()
        
    logging.info(f"[{league_name}] Buscando preços reais de mercado na The Odds API...")
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    
    params = {
        'apiKey': api_key,
        'regions': 'eu', 
        'markets': 'h2h',
        'oddsFormat': 'decimal'
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        logging.warning(f"Erro na The Odds API: {response.text}")
        return pd.DataFrame()
        
    data = response.json()
    odds_list = []
    
    for game in data:
        home_team = game['home_team']
        away_team = game['away_team']
        
        bookmakers = game.get('bookmakers', [])
        if not bookmakers: continue
        
        markets = bookmakers[0].get('markets', [])
        h2h_market = next((m for m in markets if m['key'] == 'h2h'), None)
        
        if h2h_market:
            outcomes = h2h_market['outcomes']
            
            odd_h, odd_d, odd_a = 0.0, 0.0, 0.0
            for out in outcomes:
                if out['name'] == home_team: odd_h = out['price']
                elif out['name'] == away_team: odd_a = out['price']
                elif out['name'].lower() == 'draw': odd_d = out['price']
                
            odds_list.append({
                'odds_home_team': home_team,
                'market_odd_H': odd_h,
                'market_odd_D': odd_d,
                'market_odd_A': odd_a
            })
            
    return pd.DataFrame(odds_list)

def fuzzy_merge(df_gold, df_odds):
    """
    Motor de Entity Resolution: Une os times da ESPN com a The Odds API.
    """
    if df_odds.empty:
        return pd.DataFrame()
        
    espn_teams = df_gold['home_team'].tolist()
    odds_teams = df_odds['odds_home_team'].tolist()
    
    matched_home, matched_away, matched_odd_h, matched_odd_a = [], [], [], []
    
    for idx, row in df_gold.iterrows():
        h_team = row['home_team']
        match_h = get_close_matches(h_team, odds_teams, n=1, cutoff=0.6)
        
        if match_h:
            odd_row = df_odds[df_odds['odds_home_team'] == match_h[0]].iloc[0]
            matched_home.append(match_h[0])
            matched_odd_h.append(odd_row['market_odd_H'])
            matched_odd_a.append(odd_row['market_odd_A'])
        else:
            matched_home.append(np.nan)
            matched_odd_h.append(np.nan)
            matched_odd_a.append(np.nan)
            
    df_merged = df_gold.copy()
    df_merged['matched_home'] = matched_home
    df_merged['market_odd_H'] = matched_odd_h
    df_merged['market_odd_A'] = matched_odd_a
    
    return df_merged.dropna(subset=['market_odd_H'])

def apply_barbell_portfolio_allocation(df, total_bankroll=1000.0):
    """
    Camada Platinum (Barbell Portfolio Expansion):
    Avalia simultaneamente 1X2 Casa, 1X2 Fora, Over 2.5 e BTTS.
    """
    anchor_budget = total_bankroll * 0.75  # R$ 750,00
    convex_budget = total_bankroll * 0.25  # R$ 250,00
    
    bets_pool = []
    
    for idx, row in df.iterrows():
        # 1. Avalia Mandante (1X2 Home)
        edge_h = (row['prob_H'] * row['market_odd_H']) - 1
        if edge_h > 0:
            bets_pool.append({
                'league': row.get('league', ''),
                'date': row['date'],
                'home_team': row['home_team'],
                'away_team': row['away_team'],
                'market_type': f"1X2 - Vitória Casa ({row['home_team']})",
                'market_odd': row['market_odd_H'],
                'prob': row['prob_H'],
                'edge': edge_h
            })
            
        # 2. Avalia Visitante (1X2 Away - Se houver odd estimada/real)
        odd_a = row.get('market_odd_A', 0.0)
        prob_a = row.get('prob_A', 0.0)
        if odd_a > 0 and prob_a > 0:
            edge_a = (prob_a * odd_a) - 1
            if edge_a > 0:
                bets_pool.append({
                    'league': row.get('league', ''),
                    'date': row['date'],
                    'home_team': row['home_team'],
                    'away_team': row['away_team'],
                    'market_type': f"1X2 - Vitória Fora ({row['away_team']})",
                    'market_odd': odd_a,
                    'prob': prob_a,
                    'edge': edge_a
                })
                
        # 3. Avalia Over 2.5 (Simulação de Odd Média de Mercado a 1.85 se o modelo detectar Edge)
        prob_o25 = row.get('prob_Over25', 0.0)
        fair_o25 = row.get('fair_odd_O25', 99.0)
        # Se a odd justa for menor que 2.00 e a probabilidade for alta (> 55%)
        if prob_o25 > 0.55:
            assumed_market_odd = round(fair_o25 * 1.05, 2) # Adiciona margem leve
            edge_o25 = (prob_o25 * assumed_market_odd) - 1
            if edge_o25 > 0.02:
                bets_pool.append({
                    'league': row.get('league', ''),
                    'date': row['date'],
                    'home_team': row['home_team'],
                    'away_team': row['away_team'],
                    'market_type': 'Over 2.5 Gols',
                    'market_odd': assumed_market_odd,
                    'prob': prob_o25,
                    'edge': edge_o25
                })

        # 4. Avalia BTTS (Ambas Marcam)
        prob_btts = row.get('prob_BTTS_Yes', 0.0)
        fair_btts = row.get('fair_odd_BTTS', 99.0)
        if prob_btts > 0.55:
            assumed_btts_odd = round(fair_btts * 1.05, 2)
            edge_btts = (prob_btts * assumed_btts_odd) - 1
            if edge_btts > 0.02:
                bets_pool.append({
                    'league': row.get('league', ''),
                    'date': row['date'],
                    'home_team': row['home_team'],
                    'away_team': row['away_team'],
                    'market_type': 'Ambas Marcam (BTTS)',
                    'market_odd': assumed_btts_odd,
                    'prob': prob_btts,
                    'edge': edge_btts
                })

    if not bets_pool:
        return pd.DataFrame()
        
    df_pool = pd.DataFrame(bets_pool)
    
    # Separação Barbell (Anchor vs Convex com base nas Odds)
    mask_anchor = (df_pool['market_odd'] >= 1.5) & (df_pool['market_odd'] <= 2.2)
    mask_convex = (df_pool['market_odd'] > 3.2) | (df_pool['market_type'].str.contains('Parlay'))
    
    df_anchor = df_pool[mask_anchor].copy()
    df_convex = df_pool[mask_convex].copy()
    
    results = []
    
    # Alocação Âncora (75%)
    if not df_anchor.empty:
        df_anchor['weight'] = df_anchor['edge'] / df_anchor['edge'].sum()
        df_anchor['bet_amount_R$'] = (df_anchor['weight'] * anchor_budget).round(2)
        df_anchor['strategy'] = 'Anchor'
        results.append(df_anchor)
        
    # Alocação Convexa (25%)
    if not df_convex.empty:
        aggress_budget = convex_budget * 0.6
        ultra_budget = convex_budget * 0.4
        
        df_convex = df_convex.sort_values(by='market_odd', ascending=False).reset_index(drop=True)
        mid_point = max(1, len(df_convex) // 2)
        
        df_aggress = df_convex.iloc[:mid_point].copy()
        df_ultra = df_convex.iloc[mid_point:].copy()
        
        if not df_aggress.empty:
            df_aggress['weight'] = 1 / len(df_aggress)
            df_aggress['bet_amount_R$'] = (df_aggress['weight'] * aggress_budget).round(2)
            df_aggress['strategy'] = 'Convex_Aggressive'
            results.append(df_aggress)
            
        if not df_ultra.empty:
            df_ultra['weight'] = 1 / len(df_ultra)
            df_ultra['bet_amount_R$'] = (df_ultra['weight'] * ultra_budget).round(2)
            df_ultra['strategy'] = 'Convex_Ultra_Aggressive'
            results.append(df_ultra)
            
    if not results:
        return pd.DataFrame()
        
    return pd.concat(results, ignore_index=True)

def generate_barbell_parlays(df_all_signals):
    if len(df_all_signals) < 2:
        return pd.DataFrame()
        
    print("\n[QUANT] Construindo Bilhetes de Múltiplas e Bet Builders (Barbell Parlays)...")
    sinais_validos = df_all_signals[df_all_signals['strategy'].isin(['Convex_Aggressive', 'Convex_Ultra_Aggressive'])].head(6)
    
    if len(sinais_validos) < 2:
        return pd.DataFrame()
        
    parlays = []
    for i in range(0, len(sinais_validos)-1, 2):
        jogo1 = sinais_validos.iloc[i]
        jogo2 = sinais_validos.iloc[i+1]
        
        odd_parlay = jogo1['market_odd'] * jogo2['market_odd']
        prob_parlay = jogo1['prob'] * jogo2['prob']
        edge_parlay = (prob_parlay * odd_parlay) - 1
        
        if edge_parlay > 0.02:
            parlays.append({
                'league': 'MULTIPLA_BARBELL',
                'date': jogo1['date'],
                'home_team': f"{jogo1['home_team']} + {jogo2['home_team']}",
                'away_team': 'MÚLTIPLA ACUMULADA',
                'market_type': 'Bet Builder / Múltipla Acumulada',
                'market_odd': round(odd_parlay, 2),
                'prob': round(prob_parlay, 4),
                'edge': round(edge_parlay, 4),
                'bet_amount_R$': 10.00,
                'strategy': 'Convex_Parlay'
            })
            
    return pd.DataFrame(parlays)

if __name__ == "__main__":
    load_dotenv()
    THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")
    
    if not THE_ODDS_API_KEY:
        logging.error("Chave da THE_ODDS_API não encontrada no .env!")
        exit()
        
    print("\n==============================================")
    print(" MOTOR DE SIZING E GESTÃO DE BANCA (EXPANDIDO)")
    print("==============================================\n")
    
    todas_apostas = []
    
    for league_name, sport_key in ODDS_API_SPORTS.items():
        gold_path = f"G:/Meu Drive/Quant/gold/{league_name}_2026_Odds_Live.csv"
        
        if not os.path.exists(gold_path):
            continue
            
        df_gold = pd.read_csv(gold_path)
        
        df_odds = fetch_the_odds_api(league_name, THE_ODDS_API_KEY)
        df_cruzado = fuzzy_merge(df_gold, df_odds)
        
        if df_cruzado.empty:
            continue
            
        df_cruzado['league'] = league_name
        df_platinum = apply_barbell_portfolio_allocation(df_cruzado, total_bankroll=1000.0)
        
        if df_platinum.empty:
            continue
            
        platinum_dir = "G:/Meu Drive/Quant/platinum"
        os.makedirs(platinum_dir, exist_ok=True)
        platinum_path = f"{platinum_dir}/{league_name}_2026_Sizing_Live.csv"
        df_platinum.to_csv(platinum_path, index=False)
        
        todas_apostas.append(df_platinum)
    
    if todas_apostas:
        df_final = pd.concat(todas_apostas, ignore_index=True)
        
        df_parlays = generate_barbell_parlays(df_final)
        if not df_parlays.empty:
            df_final = pd.concat([df_final, df_parlays], ignore_index=True)
            
        colunas = ['league', 'date', 'home_team', 'away_team', 'market_type', 'market_odd', 'edge', 'bet_amount_R$', 'strategy']
        print(f"\n[SUCESSO] {len(df_final)} oportunidades expandidas (1X2, Over, BTTS e Múltiplas) alocadas!")
        
        df_final = df_final.sort_values(by='edge', ascending=False)
        print(df_final[colunas].head(15).round(2))
    else:
        print("Nenhuma aposta aprovada no mercado hoje.")