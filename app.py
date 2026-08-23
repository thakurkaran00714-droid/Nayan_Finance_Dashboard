from __future__ import annotations

import html
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


st.markdown(
    """
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
def fetch_news(query: str, limit: int = 18) -> list[dict]:
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
    st.markdown("### MarketPulse")
    page = st.radio("Navigate", ["Markets & News", "Stocks", "Forecast Lab"], label_visibility="collapsed")
    st.divider()
    focus = st.selectbox("Market focus", list(WATCHLIST), index=0)
    period = st.select_slider("Chart range", options=["1mo", "3mo", "6mo", "1y", "2y"], value="6mo")
    topics = st.multiselect("News desk", ["India markets", "Economy", "Companies", "IPO", "Global markets"],
                            default=["India markets", "Economy"])
    st.caption("Data refreshes every 15–30 minutes while the app is in use.")

st.markdown(f"""<div class="brand"><div><h1>Market<b>Pulse</b></h1>
<span>NEWS · MARKETS · INSIGHTS</span></div><div class="status">INDIA EDITION<br>{datetime.now().strftime('%d %b %Y · %I:%M %p')}</div></div>""",
            unsafe_allow_html=True)

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

if page == "Markets & News":
    left, right = st.columns([1.65, 1], gap="large")
    with left:
        st.markdown('<div class="section-title">Top Stories</div>', unsafe_allow_html=True)
        if news:
            lead = news[0]
            st.markdown(f'<div class="hero"><div class="meta">TOP STORY · {html.escape(lead["source"])}</div>'
                        f'<h2>{html.escape(lead["title"])}</h2><a href="{html.escape(lead["link"], quote=True)}" '
                        f'target="_blank">Read full coverage →</a></div>', unsafe_allow_html=True)
        render_news(news, 1, 8)
    with right:
        st.markdown('<div class="section-title">Global News</div>', unsafe_allow_html=True)
        global_news = fetch_news("global stock markets Wall Street Europe China Asia economy when:1d")
        render_news(global_news, count=6)
        st.markdown('<div class="section-title">Institutional & Bulk Deals</div>', unsafe_allow_html=True)
        deal_news = fetch_news("India NSE BSE bulk deal block deal institutional buying FII DII when:2d")
        render_news(deal_news, count=6)

elif page == "Stocks":
    st.markdown('<div class="section-title">Indian Equity Dashboard</div>', unsafe_allow_html=True)
    table = company_table()
    if not table.empty:
        cols = st.columns(min(4, len(table)))
        for col, (_, row) in zip(cols, table.head(4).iterrows()):
            col.metric(row["Symbol"], f'₹{row["Price (₹)"]:,.2f}', f'{row["Change %"]:+.2f}%')
        st.dataframe(table.style.format({"Price (₹)": "{:,.2f}", "Change %": "{:+.2f}%"}),
                     hide_index=True, use_container_width=True)
    st.markdown('<div class="section-title">Company News</div>', unsafe_allow_html=True)
    render_news(fetch_news("NSE OR BSE Indian companies earnings when:2d"), count=12)

else:
    st.markdown('<div class="section-title">Forecast Lab</div>', unsafe_allow_html=True)
    st.info("Scenario projections are illustrative analytics, not investment advice.")
    symbol_name = st.selectbox("Asset", list(WATCHLIST), index=list(WATCHLIST).index(focus))
    horizon = st.slider("Projection horizon (trading days)", 5, 90, 30)
    hist = price_history(WATCHLIST[symbol_name], "1y")
    if not hist.empty:
        returns = hist["Close"].pct_change().dropna()
        last = float(hist["Close"].iloc[-1])
        daily_mean, daily_vol = float(returns.mean()), float(returns.std())
        future_dates = pd.bdate_range(hist.index[-1].date(), periods=horizon + 1)[1:]
        steps = pd.Series(range(1, horizon + 1), index=future_dates)
        base = last * (1 + daily_mean) ** steps
        upper = base * (1 + daily_vol * steps.pow(.5))
        lower = base * (1 - daily_vol * steps.pow(.5))
        fig = go.Figure([
            go.Scatter(x=hist.index[-120:], y=hist["Close"].iloc[-120:], name="Historical", line=dict(color="#0b65c2")),
            go.Scatter(x=future_dates, y=upper, name="Upper scenario", line=dict(width=0), showlegend=False),
            go.Scatter(x=future_dates, y=lower, name="Lower scenario", fill="tonexty",
                       fillcolor="rgba(11,101,194,.12)", line=dict(width=0), showlegend=False),
            go.Scatter(x=future_dates, y=base, name="Baseline", line=dict(color="#f28c28", dash="dash")),
        ])
        fig.update_layout(height=480, paper_bgcolor="white", plot_bgcolor="white", hovermode="x unified",
                          margin=dict(l=10, r=10, t=35, b=10), yaxis=dict(gridcolor="#edf1f5"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        a, b, c = st.columns(3)
        a.metric("Latest close", f"{last:,.2f}")
        b.metric("Baseline estimate", f"{base.iloc[-1]:,.2f}", f"{(base.iloc[-1]/last-1)*100:+.2f}%")
        c.metric("Annualized volatility", f"{daily_vol * (252 ** .5) * 100:.1f}%")

st.markdown("""<div class="footer">Market data provided through Yahoo Finance; headlines aggregated from Google News RSS.
Quotes may be delayed. Forecast scenarios are statistical illustrations only and are not financial advice.</div>""",
            unsafe_allow_html=True)

