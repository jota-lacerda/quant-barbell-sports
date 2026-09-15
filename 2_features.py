import pandas as pd
import os

def calculate_live_ewma(df, span=5):
    """
    Camada Silver (LIVE): Calcula o EWMA no histórico (FT) 
    e projeta o último poder de fogo para os jogos futuros (NS).
    """
    # 1. Separa o Passado (FT) do Futuro (NS = Not Started, TBD = To Be Decided)
    df_past = df[df['status'] == 'FT'].copy().sort_values('date')
    df_future = df[df['status'].isin(['NS', 'TBD', 'PST'])].copy()
    
    if df_past.empty:
        print("Erro: Nenhum jogo finalizado encontrado para base de cálculo.")
        return df

    # 2. Calcula o EWMA apenas no Passado (Exatamente como fazíamos)
    home_stats = df_past[['date', 'home_team', 'home_goals', 'away_goals']].copy()
    home_stats.rename(columns={'home_team': 'team', 'home_goals': 'scored', 'away_goals': 'conceded'}, inplace=True)
    
    away_stats = df_past[['date', 'away_team', 'away_goals', 'home_goals']].copy()
    away_stats.rename(columns={'away_team': 'team', 'away_goals': 'scored', 'home_goals': 'conceded'}, inplace=True)
    
    team_history = pd.concat([home_stats, away_stats]).sort_values(['team', 'date'])
    
    team_history['ewma_attack'] = team_history.groupby('team')['scored'].transform(lambda x: x.shift(1).ewm(span=span).mean())
    team_history['ewma_defense'] = team_history.groupby('team')['conceded'].transform(lambda x: x.shift(1).ewm(span=span).mean())
    
    global_avg = team_history['scored'].mean()
    team_history.fillna({'ewma_attack': global_avg, 'ewma_defense': global_avg}, inplace=True)
    
    # 3. Mapeia o Passado de volta para o df_past
    df_past = df_past.merge(team_history[['date', 'team', 'ewma_attack', 'ewma_defense']], 
                  left_on=['date', 'home_team'], right_on=['date', 'team'], how='left').drop('team', axis=1)
    df_past.rename(columns={'ewma_attack': 'home_attack_form', 'ewma_defense': 'home_defense_form'}, inplace=True)
    
    df_past = df_past.merge(team_history[['date', 'team', 'ewma_attack', 'ewma_defense']], 
                  left_on=['date', 'away_team'], right_on=['date', 'team'], how='left').drop('team', axis=1)
    df_past.rename(columns={'ewma_attack': 'away_attack_form', 'ewma_defense': 'away_defense_form'}, inplace=True)

    # =========================================================
    # A MÁGICA LIVE: PROJETANDO PARA O FUTURO
    # =========================================================
    if not df_future.empty:
        # Pega a última linha de performance conhecida de CADA time
        last_known_form = team_history.dropna().groupby('team').last()[['ewma_attack', 'ewma_defense']]
        
        # Injeta no time da casa (jogos futuros)
        df_future = df_future.merge(last_known_form, left_on='home_team', right_index=True, how='left')
        df_future.rename(columns={'ewma_attack': 'home_attack_form', 'ewma_defense': 'home_defense_form'}, inplace=True)
        
        # Injeta no time visitante (jogos futuros)
        df_future = df_future.merge(last_known_form, left_on='away_team', right_index=True, how='left')
        df_future.rename(columns={'ewma_attack': 'away_attack_form', 'ewma_defense': 'away_defense_form'}, inplace=True)
        
        # Preenche times novos (ex: que subiram de divisão e não têm histórico) com a média global
        df_future.fillna(global_avg, inplace=True)

    # Une passado e futuro novamente em uma tabela só
    df_final = pd.concat([df_past, df_future]).sort_values('date').reset_index(drop=True)
    
    return df_final

if __name__ == "__main__":
    leagues = [
        'Serie_A_Brazil', 'Serie_B_Brazil', 'Premier_League', 
        'La_Liga', 'Serie_A_Italy', 'Ligue_1', 
        'Libertadores', 'Champions_League'
    ]
    
    print("=== INICIANDO ENGENHARIA DE FEATURES (LIVE) ===")
    for league in leagues:
        bronze_path = f"G:/Meu Drive/Quant/bronze/{league}_2026.csv"
        
        if not os.path.exists(bronze_path):
            continue
            
        df_bronze = pd.read_csv(bronze_path)
        
        # Só processa se tiver jogos suficientes (evita erro em ligas vazias)
        if len(df_bronze) > 0:
            df_silver = calculate_live_ewma(df_bronze)
            
            os.makedirs("G:/Meu Drive/Quant/silver", exist_ok=True)
            silver_path = f"G:/Meu Drive/Quant/silver/{league}_2026_Features.csv"
            df_silver.to_csv(silver_path, index=False)
            
            df_futuro = df_silver[df_silver['status'].isin(['NS', 'TBD', 'PST'])]
            print(f"[{league}] -> {len(df_futuro)} jogos futuros projetados com EWMA!")