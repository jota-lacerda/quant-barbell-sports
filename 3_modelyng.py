import pandas as pd
import numpy as np
from scipy.stats import poisson
import os

def calculate_poisson_and_markets(df, home_advantage=1.15):
    print("Modelando matrizes de Poisson, mercados simples e Bet Builders...")
    
    df_future = df[df['status'].isin(['NS', 'TBD', 'PST'])].copy()
    if df_future.empty:
        return df_future
        
    df_future['exp_goals_H'] = df_future['home_attack_form'] * df_future['away_defense_form'] * home_advantage
    df_future['exp_goals_A'] = df_future['away_attack_form'] * df_future['home_defense_form']
    
    prob_H, prob_D, prob_A = [], [], []
    prob_Over25, prob_BTTS = [], []
    fair_home_over, fair_btts_over = [], []
    
    max_goals = 7
    i_grid, j_grid = np.ogrid[0:max_goals+1, 0:max_goals+1]
    total_goals_matrix = i_grid + j_grid
    
    for idx, row in df_future.iterrows():
        lambda_h = row['exp_goals_H']
        lambda_a = row['exp_goals_A']
        
        pois_h = poisson.pmf(np.arange(max_goals+1), lambda_h)
        pois_a = poisson.pmf(np.arange(max_goals+1), lambda_a)
        
        score_matrix = np.outer(pois_h, pois_a)
        
        # 1. Mercados Simples
        p_H = np.sum(np.tril(score_matrix, -1))
        p_D = np.sum(np.diag(score_matrix))
        p_A = np.sum(np.triu(score_matrix, 1))
        p_O25 = np.sum(score_matrix[total_goals_matrix > 2])
        p_BTTS = np.sum(score_matrix[1:, 1:])
        
        # 2. Bet Builders Correlacionados (Same Game Parlay)
        # Combo A: Mandante Vence + Over 2.5 Gols
        cond_win_over = (i_grid > j_grid) & (total_goals_matrix > 2)
        p_win_over = np.sum(score_matrix[cond_win_over])
        
        # Combo B: Ambas Marcam (BTTS) + Over 2.5 Gols
        cond_btts_over = (i_grid > 0) & (j_grid > 0) & (total_goals_matrix > 2)
        p_btts_over = np.sum(score_matrix[cond_btts_over])
        
        prob_H.append(p_H)
        prob_D.append(p_D)
        prob_A.append(p_A)
        prob_Over25.append(p_O25)
        prob_BTTS.append(p_BTTS)
        
        fair_home_over.append(1 / p_win_over if p_win_over > 0 else 99.0)
        fair_btts_over.append(1 / p_btts_over if p_btts_over > 0 else 99.0)
        
    df_future['prob_H'] = prob_H
    df_future['prob_D'] = prob_D
    df_future['prob_A'] = prob_A
    df_future['prob_Over25'] = prob_Over25
    df_future['prob_BTTS_Yes'] = prob_BTTS
    
    df_future['fair_odd_H'] = 1 / df_future['prob_H']
    df_future['fair_odd_O25'] = 1 / df_future['prob_Over25']
    df_future['fair_odd_BTTS'] = 1 / df_future['prob_BTTS_Yes']
    df_future['fair_odd_Home_Over25'] = fair_home_over
    df_future['fair_odd_BTTS_Over25'] = fair_btts_over
    
    return df_future

if __name__ == "__main__":
    leagues = [
        'Serie_A_Brazil', 'Serie_B_Brazil', 'Premier_League', 
        'La_Liga', 'Serie_A_Italy', 'Ligue_1', 
        'Libertadores', 'Champions_League'
    ]
    
    print("=== INICIANDO PRECIFICAÇÃO DE POISSON (LIVE) ===")
    
    for league in leagues:
        silver_path = f"G:/Meu Drive/Quant/silver/{league}_2026_Features.csv"
        
        if not os.path.exists(silver_path):
            continue
            
        df_silver = pd.read_csv(silver_path)
        
        # Só modela se houver jogos futuros com features calculadas
        df_futuros = df_silver[df_silver['status'].isin(['NS', 'TBD', 'PST'])]
        if len(df_futuros) > 0:
            df_gold = calculate_poisson_and_markets(df_silver)
            
            gold_dir = "G:/Meu Drive/Quant/gold"
            os.makedirs(gold_dir, exist_ok=True)
            gold_path = f"{gold_dir}/{league}_2026_Odds_Live.csv"
            
            df_gold.to_csv(gold_path, index=False)
            print(f"[{league}] Fair Odds calculadas para {len(df_gold)} jogos futuros.")
            
            # Imprime uma amostra rápida da Premier League ou Brasileirão para auditoria
            if league in ['Serie_A_Brazil', 'Premier_League']:
                print(f"\n--- AMOSTRA DE MERCADOS: {league} ---")
                colunas_exibir = ['date', 'home_team', 'away_team', 'fair_odd_H', 'fair_odd_O25', 'fair_odd_BTTS']
                print(df_gold[colunas_exibir].head(4).round(2))
                print("-" * 50)