from __future__ import annotations

import html
import re
from datetime import datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


st.set_page_config(
    page_title="MarketPulse | Financial News & Markets",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

WATCHLIST = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DAX (FRANKFURT)": "^GDAXI",
    "FTSE 100": "^FTSE",
    "SSE COMPOSITE": "000001.SS",
    "KOSPI": "^KS11",
    "NIKKEI 225": "^N225",
}

STOCKS = {
    "Reliance Industries": "RELIANCE.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Tata Consultancy Services": "TCS.NS",
    "Infosys": "INFY.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "State Bank of India": "SBIN.NS",
    "Bharti Airtel": "BHARTIARTL.NS",
    "Larsen & Toubro": "LT.NS",
}

ASSET_UNIVERSE = {
    "Reliance Industries": ("RELIANCE.NS", "Stock"),
    "HDFC Bank": ("HDFCBANK.NS", "Stock"),
    "Tata Consultancy Services": ("TCS.NS", "Stock"),
    "Infosys": ("INFY.NS", "Stock"),
    "ICICI Bank": ("ICICIBANK.NS", "Stock"),
    "State Bank of India": ("SBIN.NS", "Stock"),
    "Bharti Airtel": ("BHARTIARTL.NS", "Stock"),
    "Apple": ("AAPL", "Stock"),
    "Microsoft": ("MSFT", "Stock"),
    "NVIDIA": ("NVDA", "Stock"),
    "Nippon India Nifty 50 BeES": ("NIFTYBEES.NS", "Fund / ETF"),
    "SBI Nifty ETF": ("SETFNIF50.NS", "Fund / ETF"),
    "Nippon India Gold BeES": ("GOLDBEES.NS", "Fund / ETF"),
    "Vanguard Total Bond Market ETF": ("BND", "Bond ETF"),
    "iShares 20+ Year Treasury Bond ETF": ("TLT", "Bond ETF"),
    "US 10-Year Treasury Yield": ("^TNX", "Bond yield"),
    "Gold Futures": ("GC=F", "Commodity"),
    "Silver Futures": ("SI=F", "Commodity"),
    "Crude Oil Futures": ("CL=F", "Commodity"),
    "Natural Gas Futures": ("NG=F", "Commodity"),
    "Bitcoin": ("BTC-USD", "Crypto"),
}


st.markdown(    """
    <style>
    :root { --navy:#071b33; --blue:#0b65c2; --ink:#15243a; --muted:#66758a; --line:#dce4ec; }
    .stApp { background:#f4f7fa; color:var(--ink); }
    [data-testid="stHeader"] { background:rgba(244,247,250,.88); }
    [data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--line); }
    .block-container { max-width:1440px; padding-top:1rem; }
    .brand { background:linear-gradient(120deg,#071b33,#123b67); color:white; padding:18px 24px;
      border-radius:8px; display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
    .brand h1 { margin:0; font-size:27px; letter-spacing:-.7px; }
    .brand b { color:#55b7ff; }
    .brand span { color:#bed2e8; font-size:12px; }
    .ticker { background:#fff; border:1px solid var(--line); border-radius:6px; padding:9px 12px;
      white-space:nowrap; overflow:hidden; margin-bottom:12px; font-size:13px; }
    .ticker .up { color:#07883d; } .ticker .down { color:#c62828; }
    .section-title { border-left:4px solid var(--blue); padding-left:10px; margin:12px 0 8px;
      color:var(--navy); font-size:19px; font-weight:750; }
    .news-card { background:white; border-bottom:1px solid var(--line); padding:13px 15px; }
    .news-card:hover { background:#f8fbff; }
    .news-card a { color:#142a45; text-decoration:none; font-size:16px; font-weight:700; line-height:1.3; }
    .news-card .meta { color:var(--muted); font-size:11px; margin-top:6px; text-transform:uppercase; }
    .hero { background:white; border:1px solid var(--line); border-radius:7px; padding:16px; }
    .hero h2 { color:var(--navy); margin:0 0 8px; font-size:23px; line-height:1.2; }
    .metric-card { background:white; border:1px solid var(--line); border-radius:6px; padding:12px; }
    div[data-testid="stMetric"] { background:white; border:1px solid var(--line); padding:12px;
      border-radius:7px; box-shadow:0 1px 2px rgba(7,27,51,.04); }
    div[data-testid="stMetricLabel"] { color:#56677c; }
    .status { font-size:11px; color:#66758a; text-align:right; }
    .footer { color:#728096; font-size:11px; border-top:1px solid var(--line); margin-top:25px; padding:15px 0; }
    .side-brand { background:linear-gradient(145deg,#06182d,#0b65c2); color:white; border-radius:14px;
      padding:18px 16px; margin:4px 0 18px; box-shadow:0 8px 24px rgba(7,27,51,.22); }
    .side-brand .logo { font-size:23px; font-weight:850; letter-spacing:-.7px; }
    .side-brand .logo b { color:#6cc4ff; }
    .side-brand .live { display:inline-block; margin-top:8px; font-size:10px; color:#cce7ff; letter-spacing:1.2px; }
    div[role="radiogroup"] { background:white; border:1px solid var(--line); border-radius:9px; padding:5px 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=900, show_spinner=False)
def market_snapshot() -> pd.DataFrame:
    rows = []
    for label, symbol in WATCHLIST.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=True)
            closes = hist["Close"].dropna()
            if len(closes) >= 2:
                last, previous = float(closes.iloc[-1]), float(closes.iloc[-2])
                rows.append({"Market": label, "Symbol": symbol, "Price": last,
                             "Change": last - previous, "Change %": (last / previous - 1) * 100})
        except Exception:
            continue
    return pd.DataFrame(rows)


@st.cache_data(ttl=1800, show_spinner=False)
def price_history(symbol: str, period: str) -> pd.DataFrame:
    try:
        return yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=1800, show_spinner=False)
def company_table() -> pd.DataFrame:
    rows = []
    for name, symbol in STOCKS.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=True)
            closes = hist["Close"].dropna()
            if len(closes) >= 2:
                last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
                rows.append({"Company": name, "Symbol": symbol.replace(".NS", ""), "Price (₹)": last,
                             "Change %": (last / prev - 1) * 100})
        except Exception:
            continue
    return pd.DataFrame(rows)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news(query: str, limit: int = 40) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    items = []
    try:
        response = requests.get(url, timeout=12, headers={"User-Agent": "MarketPulse/1.0"})
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        for entry in root.findall("./channel/item")[:limit]:
            source_node = entry.find("source")
            items.append({
                "title": entry.findtext("title", "Market update"),
                "link": entry.findtext("link", "#"),
                "published": entry.findtext("pubDate", "Latest"),
                "source": source_node.text if source_node is not None and source_node.text else "Google News",
            })
    except (requests.RequestException, ElementTree.ParseError):
        return []
    return items
@st.cache_data(ttl=1800, show_spinner=False)
def search_market_instruments(query: str) -> list[dict]:
    if len(query.strip()) < 2:
        return []
    try:
        response = requests.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": query.strip(), "quotesCount": 20, "newsCount": 0},
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0 MarketPulse/1.0"},
        )
        response.raise_for_status()
        allowed_types = {"EQUITY", "ETF", "MUTUALFUND", "INDEX", "FUTURE", "CRYPTOCURRENCY", "CURRENCY"}
        results = []
        seen = set()
        for quote in response.json().get("quotes", []):
            symbol = quote.get("symbol", "")
            quote_type = quote.get("quoteType", "")
            if not symbol or symbol in seen or quote_type not in allowed_types:
                continue
            seen.add(symbol)
            results.append({
                "symbol": symbol,
                "name": quote.get("longname") or quote.get("shortname") or symbol,
                "type": quote_type.replace("MUTUALFUND", "Mutual Fund").title(),
                "exchange": quote.get("exchange") or quote.get("exchDisp") or "",
            })
        return results
    except (requests.RequestException, ValueError):
        return []
@st.cache_data(ttl=86400, show_spinner=False)
def mutual_fund_schemes() -> list[dict]:
    try:
        response = requests.get("https://api.mfapi.in/mf", timeout=25,
                                headers={"User-Agent": "MarketPulse/1.0"})
        response.raise_for_status()
        schemes = response.json()
        return sorted(schemes, key=lambda item: item.get("schemeName", ""))
    except (requests.RequestException, ValueError):
        return []


@st.cache_data(ttl=21600, show_spinner=False)
def mutual_fund_nav(scheme_code: str) -> tuple[float | None, float | None, str]:
    try:
        response = requests.get(f"https://api.mfapi.in/mf/{scheme_code}", timeout=20,
                                headers={"User-Agent": "MarketPulse/1.0"})
        response.raise_for_status()
        payload = response.json()
        observations = payload.get("data", [])
        latest = float(observations[0]["nav"]) if observations else None
        previous = float(observations[1]["nav"]) if len(observations) > 1 else None
        nav_date = observations[0].get("date", "") if observations else ""
        return latest, previous, nav_date
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None, None, ""

@st.cache_data(ttl=3600, show_spinner=False)
def stock_research(symbol: str) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ticker = yf.Ticker(symbol)
    try:
        info = ticker.get_info()
    except Exception:
        info = {}
    try:
        income = ticker.quarterly_income_stmt
    except Exception:
        income = pd.DataFrame()
    try:
        balance = ticker.quarterly_balance_sheet
    except Exception:
        balance = pd.DataFrame()
    try:
        cashflow = ticker.quarterly_cashflow
    except Exception:
        cashflow = pd.DataFrame()
    return info, income, balance, cashflow


def compact_number(value: object, currency: str = "") -> str:
    if not isinstance(value, (int, float)) or pd.isna(value):
        return "N/A"
    number = float(value)
    for divisor, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(number) >= divisor:
            return f"{currency}{number / divisor:,.2f}{suffix}"
    return f"{currency}{number:,.2f}"


def analyze_transcript(text: str) -> dict[str, list[str]]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if len(part.strip()) > 35]
    themes = {
        "Guidance & Outlook": ("guidance", "outlook", "expect", "target", "forecast", "next quarter", "fy"),
        "Growth Drivers": ("growth", "demand", "order book", "expansion", "launch", "market share", "capacity"),
        "Margins & Profitability": ("margin", "profit", "ebitda", "cost", "pricing", "operating leverage"),
        "Risks & Watch Items": ("risk", "challenge", "pressure", "decline", "uncertain", "headwind", "slowdown"),
        "Capital Allocation": ("capex", "dividend", "buyback", "debt", "acquisition", "investment"),
    }
    result = {}
    for label, keywords in themes.items():
        matches = [sentence for sentence in sentences if any(word in sentence.lower() for word in keywords)]
        result[label] = matches[:4]
    return result

def chart(history: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=history.index, y=history["Close"], mode="lines", name="Close",
                             line=dict(color="#0b65c2", width=2), fill="tozeroy",
                             fillcolor="rgba(11,101,194,.08)"))
    fig.update_layout(title=title, height=350, margin=dict(l=10, r=10, t=45, b=10),
                      paper_bgcolor="white", plot_bgcolor="white", hovermode="x unified",
                      xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#edf1f5"),
                      showlegend=False)
    return fig


def render_news(items: list[dict], start: int = 0, count: int = 8) -> None:
    if not items:
        st.info("News feed is temporarily unavailable. Market data will continue to refresh.")
        return
    for item in items[start:start + count]:
        title = html.escape(item["title"])
        link = html.escape(item["link"], quote=True)
        meta = html.escape(f'{item["source"]} · {item["published"]}')
        st.markdown(f'<div class="news-card"><a href="{link}" target="_blank">{title}</a>'
                    f'<div class="meta">{meta}</div></div>', unsafe_allow_html=True)


with st.sidebar:
    st.markdown('<div class="side-brand"><div class="logo">Market<b>Pulse</b></div>'
                '<div class="live">● LIVE FINANCIAL INTELLIGENCE</div></div>', unsafe_allow_html=True)
    st.markdown("#### Personalise your feed")
    topics = st.multiselect("News desk", ["India markets", "Economy", "Companies", "IPO", "Global markets"],
                            default=["India markets", "Economy"])
    st.caption("Live headlines and quotes refresh every 15–30 minutes.")
    st.divider()
    st.caption("MarketPulse · India edition")

st.markdown(f"""<div class="brand"><div><h1>Market<b>Pulse</b></h1>
<span>NEWS · MARKETS · RESEARCH</span></div><div class="status">INDIA EDITION<br>{datetime.now().strftime('%d %b %Y · %I:%M %p')}</div></div>""",
            unsafe_allow_html=True)
page = st.radio("Primary navigation", ["Market News", "Stock Research", "Watchlist"],
                horizontal=True, label_visibility="collapsed")

with st.spinner("Connecting to live markets…"):
    markets = market_snapshot()

if not markets.empty:
    ticker_parts = []
    for _, row in markets.iterrows():
        cls = "up" if row["Change %"] >= 0 else "down"
        ticker_parts.append(f'<b>{row["Market"]}</b> {row["Price"]:,.2f} '
                            f'<span class="{cls}">{row["Change %"]:+.2f}%</span>')
    st.markdown('<div class="ticker">' + '&nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp;'.join(ticker_parts) + '</div>',
                unsafe_allow_html=True)
else:
    st.warning("Live market quotes are temporarily unavailable. Try refreshing in a moment.")

query = " OR ".join(topics) if topics else "India stock market economy business"
news = fetch_news(f"{query} when:1d")

if page == "Market News":
    left, right = st.columns([1.65, 1], gap="large")
    with left:
        st.markdown('<div class="section-title">Top Stories</div>', unsafe_allow_html=True)
        if news:
            lead = news[0]
            st.markdown(f'<div class="hero"><div class="meta">TOP STORY · {html.escape(lead["source"])}</div>'
                        f'<h2>{html.escape(lead["title"])}</h2><a href="{html.escape(lead["link"], quote=True)}" '
                        f'target="_blank">Read full coverage →</a></div>', unsafe_allow_html=True)
        if "news_count" not in st.session_state:
            st.session_state.news_count = 9
        render_news(news, 1, st.session_state.news_count - 1)
        if st.session_state.news_count < len(news):
            if st.button("Load more stories", use_container_width=True):
                st.session_state.news_count = min(st.session_state.news_count + 8, len(news))
                st.rerun()
    with right:
        st.markdown('<div class="section-title">Global News</div>', unsafe_allow_html=True)
        global_news = fetch_news("global stock markets Wall Street Europe China Asia economy when:1d")
        render_news(global_news, count=6)
        st.markdown('<div class="section-title">Institutional & Bulk Deals</div>', unsafe_allow_html=True)
        deal_news = fetch_news("India NSE BSE bulk deal block deal institutional buying FII DII when:2d")
        render_news(deal_news, count=6)

elif page == "Stock Research":
    st.markdown('<div class="section-title">Stock Research Centre</div>', unsafe_allow_html=True)
    st.caption("Search any Yahoo Finance symbol. For NSE stocks use .NS, for example RELIANCE.NS or TCS.NS.")
    preset = st.selectbox("Popular companies", ["Reliance Industries", "HDFC Bank", "Tata Consultancy Services",
                                                "Infosys", "ICICI Bank", "State Bank of India", "Custom symbol"])
    default_symbol = STOCKS.get(preset, "RELIANCE.NS")
    symbol = st.text_input("Stock symbol", value=default_symbol).strip().upper()
    if symbol:
        with st.spinner(f"Loading research for {symbol}..."):
            info, income, balance, cashflow = stock_research(symbol)
            research_history = price_history(symbol, "1y")
        company_name = info.get("longName") or info.get("shortName") or symbol
        st.markdown(f"## {company_name}")
        overview_tab, financials_tab, concall_tab = st.tabs(["Overview & Fundamentals", "Financial Statements", "Con-call Analysis"])
        with overview_tab:
            if research_history.empty and not info:
                st.error("No data found. Check the symbol and try again.")
            else:
                currency = info.get("currency", "")
                metric_cols = st.columns(4)
                metric_cols[0].metric("Market cap", compact_number(info.get("marketCap"), f"{currency} "))
                metric_cols[1].metric("Trailing P/E", compact_number(info.get("trailingPE")))
                metric_cols[2].metric("Price / Book", compact_number(info.get("priceToBook")))
                metric_cols[3].metric("Dividend yield", f"{info.get('dividendYield', 0) * 100:.2f}%" if info.get("dividendYield") else "N/A")
                metric_cols_2 = st.columns(4)
                metric_cols_2[0].metric("52-week high", compact_number(info.get("fiftyTwoWeekHigh"), f"{currency} "))
                metric_cols_2[1].metric("52-week low", compact_number(info.get("fiftyTwoWeekLow"), f"{currency} "))
                metric_cols_2[2].metric("ROE", f"{info.get('returnOnEquity', 0) * 100:.2f}%" if info.get("returnOnEquity") else "N/A")
                metric_cols_2[3].metric("Debt / Equity", compact_number(info.get("debtToEquity")))
                if not research_history.empty:
                    st.plotly_chart(chart(research_history, f"{company_name} · 1 year"), use_container_width=True,
                                    config={"displayModeBar": False})
                summary = info.get("longBusinessSummary")
                if summary:
                    st.markdown("#### Business overview")
                    st.write(summary)
        with financials_tab:
            statement_name = st.radio("Statement", ["Quarterly income", "Quarterly balance sheet", "Quarterly cash flow"], horizontal=True)
            statement = {"Quarterly income": income, "Quarterly balance sheet": balance,
                         "Quarterly cash flow": cashflow}[statement_name]
            if statement.empty:
                st.info("This financial statement is unavailable from the free data source.")
            else:
                display_statement = statement.iloc[:18, :5].copy()
                display_statement.columns = [str(col.date()) if hasattr(col, "date") else str(col) for col in display_statement.columns]
                st.dataframe(display_statement.style.format(lambda value: compact_number(value)), use_container_width=True)
        with concall_tab:
            st.markdown("#### Latest con-call and earnings coverage")
            render_news(fetch_news(f'"{company_name}" earnings call conference call transcript results when:180d'), count=8)
            st.markdown("#### Analyse a transcript")
            st.caption("Paste management commentary or a con-call transcript. Analysis runs privately in this session and is not saved.")
            transcript = st.text_area("Transcript text", height=220, placeholder="Paste the con-call transcript here...")
            if st.button("Analyse con-call", type="primary", disabled=len(transcript.strip()) < 100):
                analysis = analyze_transcript(transcript)
                for heading, findings in analysis.items():
                    st.markdown(f"**{heading}**")
                    if findings:
                        for finding in findings:
                            st.markdown(f"- {finding}")
                    else:
                        st.caption("No clear statement detected in the supplied text.")
                st.warning("Automated text extraction can miss context. Verify conclusions against the complete call and company filings.")

elif page == "Watchlist":
    st.markdown('<div class="section-title">My Watchlist</div>', unsafe_allow_html=True)
    st.caption("Build a live list of stocks, funds, bond instruments, commodities, or crypto. Start typing to filter suggestions.")
    if "personal_watchlist" not in st.session_state:
        st.session_state.personal_watchlist = [
            {"name": "Reliance Industries", "symbol": "RELIANCE.NS", "type": "Stock"},
            {"name": "Gold Futures", "symbol": "GC=F", "type": "Commodity"},
        ]
    market_tab, mutual_fund_tab = st.tabs(["Stocks, bonds & commodities", "Indian mutual funds"])
    with market_tab:
        search_col, custom_col = st.columns([1.35, 1])
        with search_col:
            stock_query = st.text_input("Search by company or symbol",
                                        placeholder="Example: Tata Motors, Reliance, Apple...")
        with custom_col:
            custom_symbol = st.text_input("Or enter an exact Yahoo symbol", placeholder="Example: RELIANCE.NS")
        live_results = search_market_instruments(stock_query) if stock_query.strip() else []
        selected_asset = None
        if stock_query.strip() and len(stock_query.strip()) < 2:
            st.caption("Enter at least two characters to search.")
        elif stock_query.strip() and not live_results:
            st.info("No live matches found. Try the company name, NSE/BSE symbol, or exact-symbol field.")
        elif live_results:
            selected_asset = st.selectbox(
                "Matching instruments",
                live_results,
                index=None,
                format_func=lambda asset: f'{asset["name"]} — {asset["symbol"]} · {asset["exchange"]} · {asset["type"]}',
                placeholder="Select the correct exchange-listed instrument...",
            )
        with st.expander("Browse popular instruments"):
            popular_labels = [f"{name} — {symbol} · {asset_type}" for name, (symbol, asset_type) in ASSET_UNIVERSE.items()]
            popular_asset = st.selectbox("Popular instruments", popular_labels, index=None,
                                         placeholder="Choose from the curated list...")
        if st.button("＋ Add market instrument", type="primary"):
            if custom_symbol.strip():
                new_symbol = custom_symbol.strip().upper()
                new_item = {"name": new_symbol, "symbol": new_symbol, "type": "Custom"}
            elif selected_asset:
                new_item = {"name": selected_asset["name"], "symbol": selected_asset["symbol"],
                            "type": selected_asset["type"]}
            elif popular_asset:
                popular_index = popular_labels.index(popular_asset)
                popular_name = list(ASSET_UNIVERSE)[popular_index]
                popular_symbol, popular_type = ASSET_UNIVERSE[popular_name]
                new_item = {"name": popular_name, "symbol": popular_symbol, "type": popular_type}
            else:
                new_item = None
                st.warning("Search and select an instrument, choose a popular item, or enter an exact symbol.")
            if new_item and new_item["symbol"] not in {item["symbol"] for item in st.session_state.personal_watchlist}:
                st.session_state.personal_watchlist.append(new_item)
                st.rerun()
    with mutual_fund_tab:
        with st.spinner("Loading Indian mutual-fund schemes..."):
            fund_schemes = mutual_fund_schemes()
        if fund_schemes:
            selected_fund = st.selectbox("Search mutual funds", fund_schemes, index=None,
                                         format_func=lambda fund: f'{fund.get("schemeName", "Fund")} · {fund.get("schemeCode", "")}',
                                         placeholder="Start typing a mutual-fund scheme name...")
            if st.button("＋ Add mutual fund", type="primary"):
                if selected_fund:
                    scheme_code = str(selected_fund.get("schemeCode", ""))
                    fund_item = {"name": selected_fund.get("schemeName", scheme_code),
                                 "symbol": scheme_code, "type": "Mutual Fund"}
                    if scheme_code not in {item["symbol"] for item in st.session_state.personal_watchlist}:
                        st.session_state.personal_watchlist.append(fund_item)
                        st.rerun()
                else:
                    st.warning("Select a mutual-fund scheme first.")
        else:
            st.warning("The mutual-fund directory is temporarily unavailable. Please retry shortly.")
    st.divider()
    if not st.session_state.personal_watchlist:
        st.info("Your watchlist is empty. Search above to add the first instrument.")
    for item_index, item in enumerate(st.session_state.personal_watchlist.copy()):
        latest = previous = None
        nav_date = ""
        if item["type"] == "Mutual Fund":
            latest, previous, nav_date = mutual_fund_nav(item["symbol"])
        else:
            history = price_history(item["symbol"], "5d")
            if not history.empty:
                closes = history["Close"].dropna()
                if len(closes) >= 1:
                    latest = float(closes.iloc[-1])
                if len(closes) >= 2:
                    previous = float(closes.iloc[-2])
        delta_pct = ((latest / previous - 1) * 100) if latest is not None and previous else None
        card_col, move_col, remove_col = st.columns([2.2, 1, .55])
        card_col.markdown(f"### {item['name']}")
        card_col.caption(f"{item['symbol']} · {item['type']}")
        if latest is not None:
            value_label = f"₹{latest:,.4f}" if item["type"] == "Mutual Fund" else f"{latest:,.2f}"
            move_col.metric("Latest NAV" if item["type"] == "Mutual Fund" else "Latest", value_label,
                            f"{delta_pct:+.2f}%" if delta_pct is not None else None)
            if nav_date:
                move_col.caption(f"NAV date: {nav_date}")
        else:
            move_col.metric("Latest", "Unavailable")
        if remove_col.button("Remove", key=f"remove_{item_index}"):
            st.session_state.personal_watchlist.remove(item)
            st.rerun()
        with st.expander(f"News and updates · {item['symbol']}"):
            related_query = f'"{item["name"]}" mutual fund stock commodity news when:7d'
            render_news(fetch_news(related_query), count=6)
        st.divider()
st.markdown("""<div class="footer">Market data provided through Yahoo Finance; headlines aggregated from Google News RSS.
Quotes may be delayed. Research tools are informational and are not financial advice.</div>""",
            unsafe_allow_html=True)

