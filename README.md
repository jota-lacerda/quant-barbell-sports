# Quant Sports Pipeline 📊

An automated, end-to-end Python pipeline for probabilistic sports modeling and quantitative capital allocation. This project implements a strict expected value (+EV) architecture, utilizing a Dixon-Coles adjusted Poisson model and Nassim Taleb's Barbell strategy for risk management. 

Designed as a foundational transition into analytics engineering, this pipeline prioritizes vectorized operations, strict backtesting protocols, and modular data transformations.

**Core Objectives**
* Replace manual calculations with a fully vectorized Python environment using `pandas` and `numpy`.
* Eliminate look-ahead bias and hallucination through strict walk-forward validation and robust API ingestion.
* Manage variance using asymmetric capital allocation (85% low-variance Anchor, 15% high-yield Convex tail).

**Pipeline Architecture**
* **Phase 1: Ingestion (Bronze):** Automated extraction of expected goals (xG) and market closing odds via REST APIs.
* **Phase 2: Feature Engineering (Silver):** Exponential Weighted Moving Averages (EWMA) to calculate team momentum and decay variables.
* **Phase 3: Modeling (Gold):** Bivariate Poisson distribution parameterized via Maximum Likelihood Estimation (MLE) using `scipy.optimize`.
* **Phase 4: Sizing:** Fractional Kelly Criterion to scale edges dynamically without risking systemic ruin.
* **Phase 5: Deploy:** Automated integration with Google Sheets via `gspread` for Closing Line Value (CLV) auditing and dashboarding.

**Local Setup**
Built and tested with Python 3.12+. 

```bash
git clone [https://github.com/jota-lacerda/quant-sports-pipeline.git](https://github.com/jota-lacerda/quant-sports-pipeline.git)
cd quant-sports-pipeline
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux/Mac (Bash)
source .venv/bin/activate

# Install dependencies
pip install pandas numpy scipy scikit-learn requests gspread oauth2client
