# 📊 Agentic Quant: Sports Betting Barbell Pipeline

Este repositório contém um pipeline quantitativo de ponta a ponta projetado para o mercado de derivativos esportivos (Futebol). O sistema utiliza modelagem estatística (Distribuição de Poisson, EWMA, Expected Goals), integração de APIs de mercado em tempo real e um fluxo de trabalho autônomo (Agentic AI Workflow) alimentado por LLMs para alocação de portfólio baseada na **Estratégia Barbell de Nassim Taleb**.

## 🧠 Filosofia de Alocação (Antifragilidade)
O motor financeiro não busca "adivinhar" resultados, mas sim precificar ineficiências (Expected Value / +EV) e gerenciar a ruína. O capital diário é dividido em dois extremos:
*   **Ponta Âncora (75%-85%):** Proteção de caixa, eventos de baixa variância, absorção de ruído.
*   **Ponta Convexa (15%-25%):** Captura de "Cisnes Negros", múltiplas correlacionadas via Cópulas Bivariadas (ex: Game State + Cartões), assimetria brutal de lucros.

## 🏗️ Arquitetura do Sistema (As 5 Camadas)

O pipeline foi desenhado inspirado na arquitetura de medalhões (Bronze, Silver, Gold, Platinum):

1.  **Camada 1 (Ingestion):** Extração de dados de *fixtures* da ESPN.
2.  **Camada 2 (Silver - ETL):** Limpeza e padronização de nomenclaturas.
3.  **Camada 3 (Gold - Modeling):** Cálculo dos parâmetros $\lambda_{home}$ e $\lambda_{away}$ ajustados por xG. Aplicação de *Shrinkage* (James-Stein) para mitigar viés de recência e multiplicadores friccionais (clima, altitude).
4.  **Camada 4 (Platinum - Sizing):** Script `4_sizing.py`. 
    * Consome **The Odds API** para odds reais de fechamento.
    * Executa *Entity Resolution* (Fuzzy Matching) entre equipes.
    * Calcula o *Edge* matemático (EV > 0).
    * Fatiamento inicial do portfólio (Âncora vs. Convexa).
5.  **Camada 5 (Deploy - Agentic AI):** Script `5_deploy.py`. 
    * Um Agente LLM (Google Gemini 3.6 Flash) atua como Engenheiro Quantitativo.
    * Recebe os dados purificados em JSON.
    * Constrói os bilhetes e escreve o racional de gestão de risco.
    * Injeta as recomendações de forma atômica no **Google Sheets** via API (`gspread`).

## 🚀 Tecnologias e Dependências

*   **Python 3.10+**
*   `pandas`, `numpy` (Manipulação e Vetorização de Dados)
*   `requests` (The Odds API)
*   `google-genai` (SDK Oficial do Gemini para Agentic AI)
*   `gspread` (Integração Google Cloud / Google Sheets)
*   `python-dotenv` (Gestão de Variáveis de Ambiente)
*   `difflib` (Fuzzy String Matching)

## ⚙️ Instalação e Setup

1. Clone o repositório:
   ```bash
   git clone [https://github.com/SEU_USUARIO/quant-barbell-sports.git](https://github.com/SEU_USUARIO/quant-barbell-sports.git)
   cd quant-barbell-sports