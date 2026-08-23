# MarketPulse Financial Dashboard

A public-ready Streamlit dashboard for Indian and global market quotes, financial news, company watchlists, and scenario-based forecasts.

## Data sources

- Market prices: Yahoo Finance via `yfinance`
- News: Google News RSS via `feedparser`

Both sources are keyless. Quotes may be delayed and feeds can be temporarily rate-limited. The app caches market data for 15 minutes and news for 30 minutes.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

1. Push this repository to GitHub.
2. Sign in at [share.streamlit.io](https://share.streamlit.io) with GitHub.
3. Select **Create app**, choose this repository and branch, and set the main file to `app.py`.
4. Choose an available `streamlit.app` subdomain and deploy.
5. In **App settings → Sharing**, set the app to public.

No environment variables are required. If a future data provider needs a secret, add it in **App settings → Secrets** using TOML syntax and read it from `st.secrets`; never commit secrets.

Streamlit Cloud automatically rebuilds the app after each push to the selected GitHub branch. Live market/news data refresh on app use and expire from cache every 15–30 minutes, satisfying daily refresh without a separate scheduler.

