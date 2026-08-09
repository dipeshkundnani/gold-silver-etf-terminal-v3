import os
import json
import re
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh


# ============================================================
# GOLD & SILVER ETF DECISION TERMINAL — V3
# ============================================================
# Indian Gold & Silver ETF focused
# News-driven decision terminal
# Current India date based news filtering
# Trusted public/major financial sources only
# Yahoo live market data
# FRED macro data
# BLS / Treasury adapters
# Local JSON daily history
# ============================================================


# ============================================================
# PATHS / ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

# Streamlit Cloud writable temporary storage
DATA_DIR = Path("/tmp/gold_silver_etf_data")
HISTORY_DIR = DATA_DIR / "history"
STATE_FILE = DATA_DIR / "state.json"

try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# Local development .env
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Indian Gold & Silver ETF Terminal V3",
    page_icon="🥇",
    layout="wide",
)

# ============================================================
# DARK TERMINAL THEME
# ============================================================

st.markdown(
    """
    <style>

    /* Main application background */
    .stApp {
        background-color: #0b0f14;
        color: #f1f5f9;
    }

    /* Main content */
    .main {
        background-color: #0b0f14;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #080c11;
        border-right: 1px solid #1e293b;
    }

    section[data-testid="stSidebar"] * {
        color: #e2e8f0;
    }

    /* Headers */
    h1, h2, h3, h4 {
        color: #f8fafc !important;
    }

    /* Normal text */
    p, span, label, div {
        color: inherit;
    }

    /* Metric cards */
    .metric-card {
        background: #10161f;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #1f2937;
        margin-bottom: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.25);
    }

    /* News cards */
    .news-card {
        background: #10161f;
        padding: 16px;
        border-radius: 12px;
        border: 1px solid #1f2937;
        margin-bottom: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.20);
    }

    .news-title {
        font-size: 18px;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 6px;
        margin-bottom: 6px;
    }

    .small-text {
        font-size: 13px;
        color: #94a3b8;
    }

    /* Dataframes */
    div[data-testid="stDataFrame"] {
        background-color: #10161f;
        border-radius: 10px;
    }

    /* Expanders */
    div[data-testid="stExpander"] {
        background-color: #10161f;
        border: 1px solid #1f2937;
        border-radius: 10px;
    }

    /* Buttons */
    .stButton > button,
    .stLinkButton > a {
        background-color: #151c26;
        color: #f8fafc !important;
        border: 1px solid #334155;
        border-radius: 8px;
    }

    .stButton > button:hover,
    .stLinkButton > a:hover {
        background-color: #1e293b;
        border-color: #475569;
    }

    /* Selectors */
    div[data-baseweb="select"] > div {
        background-color: #111827;
        border-color: #334155;
    }

    /* Radio buttons */
    div[role="radiogroup"] label {
        color: #e2e8f0 !important;
    }

    /* Slider */
    div[data-testid="stSlider"] {
        color: #e2e8f0;
    }

    /* Alerts / info boxes */
    div[data-testid="stAlert"] {
        background-color: #111827;
        border-radius: 10px;
    }

    /* Horizontal separators */
    hr {
        border-color: #1f2937;
    }

    /* Captions */
    .stCaption {
        color: #94a3b8 !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# API ENDPOINTS
# ============================================================

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
TREASURY_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/"
    "interest-rates/pages/xml"
)
NEWS_URL = "https://newsapi.org/v2/everything"

HEADERS = {
    "User-Agent": "GoldSilverETFTerminalV3/1.0"
}

# ============================================================
# SECURE API KEY READER
# ============================================================

def get_secret(name):
    """
    Priority:
    1. Streamlit Secrets - used on Streamlit Cloud
    2. Environment variable - useful for local deployment
    3. .env - local development
    """

    # Streamlit Cloud Secrets
    try:
        value = st.secrets.get(name)

        if value:
            return str(value).strip()

    except Exception:
        pass

    # Environment / .env
    return os.getenv(name, "").strip()


HEADERS = {
    "User-Agent": "GoldSilverETFTerminalV3/1.0"
}


# ============================================================
# MARKET SYMBOLS
# ============================================================

MARKET = {
    "Gold XAU/USD": "GC=F",
    "Silver XAG/USD": "SI=F",
    "USD/INR": "INR=X",
    "DXY": "DX-Y.NYB",
}


# ============================================================
# INDIAN ETFs
# ============================================================

ETF = {
    "GOLDBEES": "GOLDBEES.NS",
    "SILVERBEES": "SILVERBEES.NS",
    "HDFCGOLD": "HDFCGOLD.NS",
    "HDFCSILVER": "HDFCSILVER.NS",
}


# ============================================================
# FRED SERIES
# ============================================================

FRED = {
    "US 2Y": "DGS2",
    "US 5Y": "DGS5",
    "US 10Y": "DGS10",
    "Fed Funds": "FEDFUNDS",
    "CPI": "CPIAUCSL",
    "Core CPI": "CPILFESL",
    "PCE": "PCEPI",
    "Core PCE": "PCEPILFE",
    "Unemployment": "UNRATE",
    "GDP": "GDPC1",
}


# ============================================================
# TRUSTED NEWS SOURCES
# ============================================================

OFFICIAL_SOURCES = {
    "Reserve Bank of India",
    "RBI",
    "Federal Reserve",
    "Federal Reserve Board",
    "U.S. Federal Reserve",
    "US Federal Reserve",
    "U.S. Treasury",
    "US Treasury",
    "Bureau of Labor Statistics",
    "BLS",
    "Ministry of Finance",
    "Government of India",
    "World Bank",
    "IMF",
    "International Monetary Fund",
    "OECD",
    "European Central Bank",
    "ECB",
}


MAJOR_FINANCIAL_SOURCES = {
    "Reuters",
    "Bloomberg",
    "CNBC",
    "Financial Times",
    "The Wall Street Journal",
    "Wall Street Journal",
    "Economic Times",
    "The Economic Times",
    "Business Standard",
    "Moneycontrol",
    "Mint",
    "Livemint",
}


REJECT_PATTERNS = (
    "twitter",
    "x.com",
    "reddit",
    "youtube",
    "telegram",
    "substack",
    "medium.com",
    "blogspot",
    "wordpress",
)


# ============================================================
# NEWS QUERIES
# ============================================================

NEWS_QUERIES = [
    '"gold" OR "silver"',
    '"gold price" OR "silver price"',
    '"Federal Reserve" OR "Fed" OR "interest rates"',
    '"RBI" OR "rupee" OR "USD/INR"',
    '"US Treasury" OR "Treasury yield" OR "10-year yield"',
    '"inflation" OR "CPI" OR "PCE"',
    '"India gold" OR "India silver" OR "bullion"',
]


# ============================================================
# INDIA TIME
# ============================================================

IST = timezone(timedelta(hours=5, minutes=30))


def now_ist():
    return datetime.now(timezone.utc).astimezone(IST)


def today_ist():
    return now_ist().date()


TODAY = today_ist()
TODAY_STR = TODAY.isoformat()


# ============================================================
# LOCAL JSON STORAGE
# ============================================================

def load_json(path, default):
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass

    return default


def save_json(path, data):
    """
    Safely save JSON data.

    Streamlit Cloud has an ephemeral filesystem.
    Failure to save local history should never crash
    the main dashboard.
    """

    try:
        path = Path(path)

        # Make sure parent directory exists
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        return True

    except Exception as exc:

        # Do not crash the dashboard
        st.warning(
            f"Local history could not be saved: {exc}"
        )

        return False


def day_file(day):
    return HISTORY_DIR / f"{day}.json"


def load_day(day):
    return load_json(
        day_file(day),
        {
            "date": day,
            "snapshot": None,
            "articles": [],
            "events": [],
        },
    )


def save_day(day, data):
    save_json(day_file(day), data)


def rotate_state():
    state = load_json(STATE_FILE, {})

    if state.get("last_date") != TODAY_STR:
        state = {
            "last_date": TODAY_STR,
            "last_snapshot": None,
        }

    save_json(STATE_FILE, state)


rotate_state()


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value):
    try:
        value = float(value)

        if np.isfinite(value):
            return value

    except Exception:
        pass

    return None


# ============================================================
# YAHOO MARKET DATA
# ============================================================

@st.cache_data(ttl=120, show_spinner=False)
def yahoo_quote(symbol):
    response = requests.get(
        YAHOO_URL.format(symbol=symbol),
        params={
            "range": "5d",
            "interval": "5m",
            "includePrePost": "true",
        },
        timeout=12,
        headers=HEADERS,
    )

    response.raise_for_status()

    payload = response.json()

    result_list = payload.get("chart", {}).get("result")

    if not result_list:
        raise ValueError(f"No Yahoo result for {symbol}")

    result = result_list[0]

    timestamps = result.get("timestamp", [])
    quote_data = result.get("indicators", {}).get("quote", [])

    if not quote_data:
        raise ValueError(f"No quote data for {symbol}")

    df = pd.DataFrame(quote_data[0])

    if not timestamps:
        raise ValueError(f"No timestamps for {symbol}")

    df["datetime"] = pd.to_datetime(
        timestamps,
        unit="s",
        utc=True,
    )

    if "close" not in df.columns:
        raise ValueError(f"No close price for {symbol}")

    df["close"] = pd.to_numeric(
        df["close"],
        errors="coerce",
    )

    df = df.dropna(subset=["close"])

    if df.empty:
        raise ValueError(f"No valid price data for {symbol}")

    price = float(df["close"].iloc[-1])

    previous = (
        float(df["close"].iloc[-2])
        if len(df) >= 2
        else price
    )

    pct = (
        (price / previous - 1) * 100
        if previous
        else 0.0
    )

    return {
        "price": price,
        "pct": pct,
        "df": df,
    }


# ============================================================
# FRED
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def fred_series(series_id, limit=24):

    key = get_secret("FRED_API_KEY")

    if not key:
        return pd.DataFrame()

    response = requests.get(
        FRED_URL,
        params={
            "series_id": series_id,
            "api_key": key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        },
        timeout=12,
        headers=HEADERS,
    )

    response.raise_for_status()

    observations = response.json().get(
        "observations",
        [],
    )

    rows = []

    for item in observations:
        if item.get("value") == ".":
            continue

        value = safe_float(item.get("value"))

        if value is None:
            continue

        rows.append(
            {
                "date": item.get("date"),
                "value": value,
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    df = df.dropna(subset=["date"])
    df = df.sort_values("date")

    return df


# ============================================================
# BLS
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def bls_series(
    series_id,
    start_year=None,
    end_year=None,
):
    payload = {
        "seriesid": [series_id],
    }

    if start_year:
        payload["startyear"] = str(start_year)

    if end_year:
        payload["endyear"] = str(end_year)

    response = requests.post(
        BLS_URL,
        json=payload,
        timeout=15,
        headers=HEADERS,
    )

    response.raise_for_status()

    rows = []

    for series in (
        response.json()
        .get("Results", {})
        .get("series", [])
    ):
        for item in series.get("data", []):
            value = safe_float(item.get("value"))

            if value is None:
                continue

            rows.append(
                {
                    "year": item.get("year"),
                    "period": item.get("period"),
                    "value": value,
                }
            )

    return pd.DataFrame(rows)


# ============================================================
# LATEST VALUE
# ============================================================

def latest(df):
    if df is None or df.empty:
        return None

    return safe_float(df["value"].iloc[-1])


# ============================================================
# US TREASURY DATA
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def treasury_yields():
    year = now_ist().year

    response = requests.get(
        TREASURY_URL,
        params={
            "data": "daily_treasury_yield_curve",
            "field_tdr_date_value": year,
        },
        timeout=15,
        headers=HEADERS,
    )

    response.raise_for_status()

    root = ET.fromstring(response.content)

    rows = []

    for entry in root.iter():
        if entry.tag.split("}")[-1] != "entry":
            continue

        row = {}

        for child in entry:
            key = child.tag.split("}")[-1]
            row[key] = child.text

        if row:
            rows.append(row)

    return pd.DataFrame(rows)


def treasury_latest_curve():
    try:
        raw = treasury_yields()

        if raw.empty:
            return {}

        flat = {}

        # Use the latest row.
        row = raw.iloc[-1]

        for key, value in row.items():
            if pd.notna(value):
                flat[str(key).lower()] = value

        def find_value(*names):
            for name in names:
                name = name.lower()

                for key, value in flat.items():
                    if key == name or key.endswith(name):
                        parsed = safe_float(value)

                        if parsed is not None:
                            return parsed

            return None

        return {
            "2Y": find_value(
                "2year",
                "2-year",
                "2_yr",
            ),
            "5Y": find_value(
                "5year",
                "5-year",
                "5_yr",
            ),
            "10Y": find_value(
                "10year",
                "10-year",
                "10_yr",
            ),
            "30Y": find_value(
                "30year",
                "30-year",
                "30_yr",
            ),
        }

    except Exception:
        return {}


# ============================================================
# NEWS SOURCE FILTER
# ============================================================

def source_allowed(source, url):
    name = (source or "").strip()

    low = f"{name} {url}".lower()

    if any(pattern in low for pattern in REJECT_PATTERNS):
        return False

    # Exact known source
    if name in OFFICIAL_SOURCES:
        return True

    if name in MAJOR_FINANCIAL_SOURCES:
        return True

    # Some NewsAPI source names vary slightly.
    normalized = name.lower()

    allowed_keywords = [
        "reuters",
        "bloomberg",
        "cnbc",
        "financial times",
        "wall street journal",
        "economic times",
        "business standard",
        "moneycontrol",
        "mint",
        "livemint",
        "federal reserve",
        "reserve bank",
        "treasury",
        "bureau of labor",
        "world bank",
        "imf",
        "oecd",
    ]

    return any(
        keyword in normalized
        for keyword in allowed_keywords
    )


# ============================================================
# ARTICLE ID
# ============================================================

def article_id(title, url, published):
    raw = f"{title}|{url}|{published}"

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:16]


# ============================================================
# NEWS FETCH
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def fetch_news_today():

    news_api_key = get_secret("NEWS_API_KEY")

    if not news_api_key:
        return (
            pd.DataFrame(),
            "NEWS_API_KEY is missing from Streamlit Secrets.",
        )

    rows = []

    for query in NEWS_QUERIES:

        params = {
            "q": query,
            "apiKey": news_api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 100,
        }

        try:
            response = requests.get(
                NEWS_URL,
                params=params,
                timeout=15,
                headers=HEADERS,
            )

            response.raise_for_status()

            payload = response.json()

            if payload.get("status") != "ok":
                continue

            for article in payload.get(
                "articles",
                [],
            ):
                published = article.get(
                    "publishedAt"
                )

                if not published:
                    continue

                try:
                    dt = (
                        pd.to_datetime(
                            published,
                            utc=True,
                        )
                        .tz_convert("Asia/Kolkata")
                    )

                except Exception:
                    continue

                # IMPORTANT:
                # Only current India calendar date.
                if dt.date() != TODAY:
                    continue

                source = (
                    article
                    .get("source", {})
                    .get("name", "")
                )

                url = article.get(
                    "url",
                    "",
                )

                if not source_allowed(
                    source,
                    url,
                ):
                    continue

                title = (
                    article.get("title")
                    or ""
                )

                description = (
                    article.get("description")
                    or ""
                )

                rows.append(
                    {
                        "id": article_id(
                            title,
                            url,
                            published,
                        ),
                        "PublishedUTC": published,
                        "PublishedIST": dt.strftime(
                            "%Y-%m-%d %H:%M:%S IST"
                        ),
                        "Source": source,
                        "Headline": title,
                        "Description": description,
                        "URL": url,
                    }
                )

        except Exception:
            continue

    if not rows:
        return (
            pd.DataFrame(),
            "No trusted public articles found for today's India date.",
        )

    df = pd.DataFrame(rows)

    df = df.drop_duplicates(
        subset=["id"]
    )

    df["_sort"] = pd.to_datetime(
        df["PublishedUTC"],
        utc=True,
        errors="coerce",
    )

    df = (
        df.sort_values(
            "_sort",
            ascending=False,
        )
        .drop(columns=["_sort"])
        .reset_index(drop=True)
    )

    return df, ""


# ============================================================
# REPORTED NUMBER EXTRACTION
# ============================================================

PATTERNS = {
    "gold_pct": [
        r"(?:gold|bullion)[^.\n]{0,100}?([+-]?\d+(?:\.\d+)?)\s*%",
        r"([+-]?\d+(?:\.\d+)?)\s*%[^.\n]{0,50}?(?:gold|bullion)",
    ],

    "silver_pct": [
        r"(?:silver)[^.\n]{0,100}?([+-]?\d+(?:\.\d+)?)\s*%",
        r"([+-]?\d+(?:\.\d+)?)\s*%[^.\n]{0,50}?silver",
    ],

    "usd_inr": [
        r"(?:USD/?INR|dollar|rupee)[^.\n]{0,100}?(?:₹|Rs\.?|INR)?\s*(\d{2,3}(?:\.\d+)?)",
    ],

    "yield_10y": [
        r"(?:10-year|10 year|10Y)[^.\n]{0,80}?(\d+(?:\.\d+)?)\s*%",
    ],

    "dxy": [
        r"(?:DXY|dollar index)[^.\n]{0,60}?(\d+(?:\.\d+)?)",
    ],
}


def extract_reported_numbers(text):
    result = {}

    text = text or ""

    for key, patterns in PATTERNS.items():

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                flags=re.I,
            )

            if not match:
                continue

            try:
                value = float(
                    match.group(1)
                )

                result[key] = value
                break

            except (
                ValueError,
                TypeError,
            ):
                pass

    return result


# ============================================================
# NEWS EVENT CLASSIFICATION
# ============================================================

def classify_event(article):

    text = (
        f"{article.get('Headline', '')} "
        f"{article.get('Description', '')}"
    ).lower()

    reported = extract_reported_numbers(
        text
    )

    topics = []

    if any(
        x in text
        for x in [
            "gold",
            "bullion",
        ]
    ):
        topics.append("gold")

    if "silver" in text:
        topics.append("silver")

    if any(
        x in text
        for x in [
            "rupee",
            "usd/inr",
            "dollar",
        ]
    ):
        topics.append("inr")

    if any(
        x in text
        for x in [
            "fed",
            "federal reserve",
            "rate cut",
            "rate hike",
            "interest rate",
        ]
    ):
        topics.append("fed")

    if any(
        x in text
        for x in [
            "10-year",
            "10 year",
            "treasury yield",
            "bond yield",
        ]
    ):
        topics.append("yields")

    if any(
        x in text
        for x in [
            "inflation",
            "cpi",
            "pce",
        ]
    ):
        topics.append("inflation")

    if any(
        x in text
        for x in [
            "central bank",
            "reserve bank",
            "rbi",
        ]
    ):
        topics.append("central_bank")

    if any(
        x in text
        for x in [
            "industrial demand",
            "manufacturing",
            "solar",
            "electronics",
        ]
    ):
        topics.append("industrial")

    positive_terms = [
        "rises",
        "rose",
        "surges",
        "surged",
        "gains",
        "gained",
        "climbs",
        "climbed",
        "eases",
        "eased",
        "cuts",
        "cut",
        "dovish",
        "demand",
        "bullish",
    ]

    negative_terms = [
        "falls",
        "fell",
        "drops",
        "dropped",
        "slips",
        "slipped",
        "hawkish",
        "hike",
        "hikes",
        "higher yields",
        "stronger dollar",
        "bearish",
    ]

    pos = sum(
        text.count(x)
        for x in positive_terms
    )

    neg = sum(
        text.count(x)
        for x in negative_terms
    )

    gold = 0
    silver = 0

    reasons = []

    # --------------------------------------------------------
    # Reported gold move
    # --------------------------------------------------------

    if "gold_pct" in reported:

        impact = int(
            np.clip(
                reported["gold_pct"] * 8,
                -12,
                12,
            )
        )

        gold += impact

        reasons.append(
            f"reported gold move "
            f"{reported['gold_pct']:+.2f}%"
        )

    # --------------------------------------------------------
    # Reported silver move
    # --------------------------------------------------------

    if "silver_pct" in reported:

        impact = int(
            np.clip(
                reported["silver_pct"] * 8,
                -14,
                14,
            )
        )

        silver += impact

        reasons.append(
            f"reported silver move "
            f"{reported['silver_pct']:+.2f}%"
        )

    # --------------------------------------------------------
    # INR
    # --------------------------------------------------------

    if "inr" in topics:

        if any(
            x in text
            for x in [
                "rupee weakens",
                "rupee falls",
                "rupee slips",
                "dollar rises",
                "rupee hits record low",
            ]
        ):
            gold += 4
            silver += 4

            reasons.append(
                "INR weakness supports "
                "domestic bullion translation"
            )

        elif any(
            x in text
            for x in [
                "rupee strengthens",
                "rupee gains",
                "rupee rises",
            ]
        ):
            gold -= 4
            silver -= 4

            reasons.append(
                "INR strength can reduce "
                "domestic bullion translation"
            )

    # --------------------------------------------------------
    # FED
    # --------------------------------------------------------

    if "fed" in topics:

        if any(
            x in text
            for x in [
                "rate cut",
                "rate cuts",
                "dovish",
                "lower rates",
            ]
        ):
            gold += 5
            silver += 5

            reasons.append(
                "dovish/rate-cut expectations"
            )

        elif any(
            x in text
            for x in [
                "rate hike",
                "rate hikes",
                "hawkish",
                "higher rates",
            ]
        ):
            gold -= 5
            silver -= 5

            reasons.append(
                "hawkish/rate-hike expectations"
            )

    # --------------------------------------------------------
    # Treasury yields
    # --------------------------------------------------------

    if "yields" in topics:

        if any(
            x in text
            for x in [
                "higher yields",
                "yield rises",
                "yields rise",
                "yield climbed",
                "yields climbed",
            ]
        ):
            gold -= 4
            silver -= 4

            reasons.append(
                "higher Treasury yields"
            )

        elif any(
            x in text
            for x in [
                "yield falls",
                "yields fall",
                "yield declined",
                "yields declined",
            ]
        ):
            gold += 4
            silver += 4

            reasons.append(
                "lower Treasury yields"
            )

    # --------------------------------------------------------
    # Industrial demand
    # --------------------------------------------------------

    if "industrial" in topics:

        if pos > neg:
            silver += 4

            reasons.append(
                "positive industrial-demand language"
            )

        elif neg > pos:
            silver -= 3

            reasons.append(
                "negative industrial-demand language"
            )

    # --------------------------------------------------------
    # General sentiment
    # --------------------------------------------------------

    if not reasons:

        if pos > neg:
            gold += 2
            silver += 2

            reasons.append(
                "positive market language"
            )

        elif neg > pos:
            gold -= 2
            silver -= 2

            reasons.append(
                "negative market language"
            )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    source = article.get(
        "Source",
        "",
    )

    if (
        source in OFFICIAL_SOURCES
        or source in {
            "Reuters",
            "Bloomberg",
        }
    ):
        confidence = 82
    else:
        confidence = 72

    if reported:
        confidence += 8

    if len(reasons) >= 2:
        confidence += 5

    confidence = int(
        np.clip(
            confidence,
            50,
            95,
        )
    )

    return {
        "gold_impact": int(
            np.clip(
                gold,
                -15,
                15,
            )
        ),
        "silver_impact": int(
            np.clip(
                silver,
                -15,
                15,
            )
        ),
        "topics": topics,
        "reported": reported,
        "reasons": reasons,
        "confidence": confidence,
    }


# ============================================================
# EVENT DEDUPLICATION
# ============================================================

def event_key(title):

    stop = {
        "the",
        "a",
        "an",
        "as",
        "to",
        "of",
        "and",
        "in",
        "on",
        "for",
        "is",
        "are",
        "with",
        "from",
        "after",
        "before",
    }

    words = re.findall(
        r"[a-z0-9]+",
        (title or "").lower(),
    )

    words = [
        word
        for word in words
        if word not in stop
        and len(word) > 3
    ]

    return " ".join(
        sorted(words[:10])
    )


def deduplicate_events(articles):

    groups = {}

    for article in articles:

        key = event_key(
            article.get(
                "Headline",
                "",
            )
        )

        groups.setdefault(
            key,
            [],
        ).append(article)

    events = []

    for group in groups.values():

        # Latest article in each event group
        group = sorted(
            group,
            key=lambda x: x.get(
                "PublishedUTC",
                "",
            ),
            reverse=True,
        )

        representative = group[0].copy()

        representative["Sources"] = sorted(
            {
                a.get(
                    "Source",
                    "",
                )
                for a in group
                if a.get("Source")
            }
        )

        representative["SourceCount"] = len(
            representative["Sources"]
        )

        representative.update(
            classify_event(
                representative
            )
        )

        events.append(
            representative
        )

    events.sort(
        key=lambda x: x.get(
            "PublishedUTC",
            "",
        ),
        reverse=True,
    )

    return events


# ============================================================
# BUILD MARKET QUOTES
# ============================================================

def build_quotes():

    quotes = {}
    errors = []

    symbols = {
        **MARKET,
        **ETF,
    }

    for name, symbol in symbols.items():

        try:
            quotes[name] = yahoo_quote(
                symbol
            )

        except Exception as exc:

            errors.append(
                f"{name}: {exc}"
            )

    return quotes, errors


# ============================================================
# BASE SCORE ENGINE
# ============================================================

def calculate_base_scores(quotes):

    required = [
        "Gold XAU/USD",
        "Silver XAG/USD",
        "DXY",
        "USD/INR",
    ]

    if not all(
        key in quotes
        for key in required
    ):
        return 50.0, 50.0, []

    gold_quote = quotes[
        "Gold XAU/USD"
    ]

    silver_quote = quotes[
        "Silver XAG/USD"
    ]

    dxy_quote = quotes[
        "DXY"
    ]

    inr_quote = quotes[
        "USD/INR"
    ]

    gold = 50 + np.clip(
        gold_quote["pct"] * 6,
        -10,
        10,
    )

    silver = 50 + np.clip(
        silver_quote["pct"] * 7,
        -12,
        12,
    )

    # DXY
    gold += np.clip(
        -dxy_quote["pct"] * 5,
        -8,
        8,
    )

    silver += np.clip(
        -dxy_quote["pct"] * 6,
        -9,
        9,
    )

    # INR
    gold += np.clip(
        inr_quote["pct"] * 4,
        -7,
        7,
    )

    silver += np.clip(
        inr_quote["pct"] * 4,
        -7,
        7,
    )

    notes = []

    # --------------------------------------------------------
    # 10Y
    # --------------------------------------------------------

    y10 = fred_series(
        "DGS10",
        6,
    )

    current_10y = latest(y10)

    if len(y10) >= 2:

        delta_10y = (
            y10["value"].iloc[-1]
            - y10["value"].iloc[-2]
        )

        gold += np.clip(
            -delta_10y * 4,
            -7,
            7,
        )

        silver += np.clip(
            -delta_10y * 5,
            -8,
            8,
        )

        notes.append(
            f"US 10Y change "
            f"{delta_10y:+.2f}pp"
        )

    if current_10y is not None:

        if current_10y >= 4.5:

            gold -= 2
            silver -= 2

            notes.append(
                "High US 10Y yield"
            )

        elif current_10y <= 3.5:

            gold += 2
            silver += 2

            notes.append(
                "Low US 10Y yield"
            )

    # --------------------------------------------------------
    # CPI
    # --------------------------------------------------------

    cpi = fred_series(
        "CPIAUCSL",
        6,
    )

    if len(cpi) >= 2:

        mom = (
            cpi["value"].iloc[-1]
            / cpi["value"].iloc[-2]
            - 1
        ) * 100

        gold += np.clip(
            -mom * 1.4,
            -5,
            5,
        )

        silver += np.clip(
            -mom * 1.7,
            -6,
            6,
        )

        notes.append(
            f"CPI MoM {mom:+.2f}%"
        )

    return (
        float(np.clip(gold, 0, 100)),
        float(np.clip(silver, 0, 100)),
        notes,
    )


# ============================================================
# FINAL SCORE
# ============================================================

def final_score(base, impacts):

    delta = int(
        np.clip(
            sum(impacts),
            -20,
            20,
        )
    )

    score = float(
        np.clip(
            base + delta,
            0,
            100,
        )
    )

    return score, delta


# ============================================================
# REGIME
# ============================================================

def regime(score):

    if score >= 75:
        return "🟢 STRONG BULLISH"

    if score >= 60:
        return "🟢 BULLISH"

    if score >= 45:
        return "🟡 NEUTRAL"

    if score >= 30:
        return "🟠 BEARISH"

    return "🔴 STRONG BEARISH"


def bias(score):

    if score >= 60:
        return "bullish"

    if score < 45:
        return "bearish"

    return "neutral"


# ============================================================
# SNAPSHOT
# ============================================================

def make_snapshot(
    quotes,
    gold_score,
    silver_score,
    gold_delta,
    silver_delta,
    events,
):

    market = {}

    for name, quote in quotes.items():

        market[name] = {
            "price": quote.get("price"),
            "pct": quote.get("pct"),
        }

    return {
        "date": TODAY_STR,
        "saved_at_ist": now_ist().isoformat(),

        "gold_score": round(
            gold_score,
            2,
        ),

        "silver_score": round(
            silver_score,
            2,
        ),

        "gold_news_delta": gold_delta,
        "silver_news_delta": silver_delta,

        "gold_regime": regime(
            gold_score
        ),

        "silver_regime": regime(
            silver_score
        ),

        "market": market,

        "event_count": len(events),
    }


# ============================================================
# SAVE TODAY
# ============================================================

def persist_today(
    quotes,
    gold_score,
    silver_score,
    gold_delta,
    silver_delta,
    events,
    articles,
):
    """Save today's snapshot when the runtime filesystem allows it.

    Streamlit Cloud storage is ephemeral, so a storage failure must
    never stop the dashboard.
    """
    try:
        payload = load_day(TODAY_STR)

        payload["snapshot"] = make_snapshot(
            quotes,
            gold_score,
            silver_score,
            gold_delta,
            silver_delta,
            events,
        )

        payload["articles"] = articles
        payload["events"] = []

        for event in events:
            payload["events"].append(
                {
                    key: event.get(key)
                    for key in [
                        "id",
                        "PublishedUTC",
                        "PublishedIST",
                        "Source",
                        "Headline",
                        "Description",
                        "URL",
                        "Sources",
                        "SourceCount",
                        "gold_impact",
                        "silver_impact",
                        "topics",
                        "reported",
                        "reasons",
                        "confidence",
                    ]
                }
            )

        return bool(save_day(TODAY_STR, payload))

    except Exception:
        return False


# ============================================================
# YESTERDAY
# ============================================================

def yesterday_snapshot():
    yesterday = TODAY - timedelta(days=1)
    return load_day(yesterday.isoformat()).get("snapshot")


# ============================================================
# UI CSS
# ============================================================

st.markdown(
    """
    <style>
    .metric-card {
        padding: 18px;
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,0.25);
        margin-bottom: 10px;
    }

    .news-card {
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,0.25);
        margin-bottom: 12px;
    }

    .news-title {
        font-size: 18px;
        font-weight: 700;
        margin-top: 6px;
        margin-bottom: 6px;
    }

    .small-text {
        font-size: 13px;
        opacity: 0.75;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "🥇🥈 Indian Gold & Silver ETF Decision Terminal — V3"
)

st.caption(
    "Daily snapshots, articles and events "
    "are stored as local JSON when the "
    "Streamlit filesystem is available. "
    "Cloud storage is temporary."
)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Controls")

    refresh = st.slider(
        "Refresh seconds",
        30,
        300,
        60,
        30,
    )

    st_autorefresh(
        interval=refresh * 1000,
        key="refresh_v3",
    )

    st.divider()

    st.write("**Terminal date**")

    st.success(
        now_ist().strftime(
            "%d %b %Y"
        )
        + " IST"
    )

    st.caption(
        "Current time: "
        + now_ist().strftime(
            "%H:%M:%S IST"
        )
    )

    st.divider()

    st.write("**News policy**")

    st.info(
        "Today only • trusted sources • "
        "no blogs/social posts • "
        "duplicate events collapsed"
    )

    st.write("**Storage**")

    st.success(
        "Local JSON • no external database"
    )


# ============================================================
# FETCH DATA
# ============================================================

quotes, errors = build_quotes()

news_df, news_error = fetch_news_today()

if news_df.empty:
    articles = []
else:
    articles = news_df.to_dict(
        orient="records"
    )

events = deduplicate_events(
    articles
)


# ============================================================
# SCORE
# ============================================================

base_gold, base_silver, macro_notes = (
    calculate_base_scores(quotes)
)

gold_score, gold_news_delta = final_score(
    base_gold,
    [
        event["gold_impact"]
        for event in events
    ],
)

silver_score, silver_news_delta = final_score(
    base_silver,
    [
        event["silver_impact"]
        for event in events
    ],
)


# ============================================================
# SAVE
# ============================================================

storage_saved = persist_today(
    quotes,
    gold_score,
    silver_score,
    gold_news_delta,
    silver_news_delta,
    events,
    articles,
)


yday = yesterday_snapshot()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def quote_price(name):

    return quotes.get(
        name,
        {},
    ).get(
        "price",
        np.nan,
    )


def quote_pct(name):

    return quotes.get(
        name,
        {},
    ).get(
        "pct",
        np.nan,
    )


def fmt_price(
    value,
    prefix="",
):

    if value is None:
        return "—"

    try:

        if not np.isfinite(value):
            return "—"

    except Exception:
        return "—"

    return f"{prefix}{value:,.2f}"


def score_change(
    current,
    previous,
):

    if previous is None:
        return "—"

    try:
        return (
            f"{current - previous:+.0f} "
            "vs yesterday"
        )

    except Exception:
        return "—"


# ============================================================
# STATUS BAR
# ============================================================

st.markdown(
    f"""
    **Date:** {TODAY.strftime("%d %B %Y")} IST  
    **News window:** {TODAY_STR} only  
    **Events:** {len(events)}  
    **Updated:** {now_ist().strftime("%H:%M:%S IST")}
    """
)


# ============================================================
# 1. ETF DECISION
# ============================================================

st.subheader(
    "1 · 🇮🇳 Indian ETF decision"
)

c1, c2 = st.columns(2)

prev_gold = (
    yday.get("gold_score")
    if yday
    else None
)

prev_silver = (
    yday.get("silver_score")
    if yday
    else None
)


with c1:

    price = quote_price(
        "GOLDBEES"
    )

    change = quote_pct(
        "GOLDBEES"
    )

    st.markdown(
        f"""
        <div class="metric-card">

        <h2>🥇 GOLDBEES</h2>

        <h3>{fmt_price(price, "₹")}</h3>

        <p>
        {
            "—"
            if not np.isfinite(change)
            else f"{change:+.2f}%"
        }
        </p>

        <h3>{regime(gold_score)}</h3>

        <p>
        Score <b>{gold_score:.0f}/100</b>
        • News overlay
        <b>{gold_news_delta:+d}</b>
        • {score_change(gold_score, prev_gold)}
        </p>

        </div>
        """,
        unsafe_allow_html=True,
    )


with c2:

    price = quote_price(
        "SILVERBEES"
    )

    change = quote_pct(
        "SILVERBEES"
    )

    st.markdown(
        f"""
        <div class="metric-card">

        <h2>🥈 SILVERBEES</h2>

        <h3>{fmt_price(price, "₹")}</h3>

        <p>
        {
            "—"
            if not np.isfinite(change)
            else f"{change:+.2f}%"
        }
        </p>

        <h3>{regime(silver_score)}</h3>

        <p>
        Score <b>{silver_score:.0f}/100</b>
        • News overlay
        <b>{silver_news_delta:+d}</b>
        • {score_change(silver_score, prev_silver)}
        </p>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 2. LIVE MARKET DATA
# ============================================================

st.subheader(
    "2 · 📊 Live Market Data"
)

items = [
    (
        "Gold XAU/USD",
        quote_price("Gold XAU/USD"),
        quote_pct("Gold XAU/USD"),
        "USD/oz",
    ),
    (
        "Silver XAG/USD",
        quote_price("Silver XAG/USD"),
        quote_pct("Silver XAG/USD"),
        "USD/oz",
    ),
    (
        "USD/INR",
        quote_price("USD/INR"),
        quote_pct("USD/INR"),
        "",
    ),
    (
        "DXY",
        quote_price("DXY"),
        quote_pct("DXY"),
        "",
    ),
]


cols = st.columns(4)


for col, (
    name,
    value,
    change,
    unit,
) in zip(
    cols,
    items,
):

    display_value = (
        "—"
        if not np.isfinite(value)
        else f"{value:,.2f} {unit}"
    )

    display_change = (
        None
        if not np.isfinite(change)
        else f"{change:+.2f}%"
    )

    col.metric(
        name,
        display_value,
        display_change,
    )


# ============================================================
# 3. DRIVERS
# ============================================================

st.subheader(
    "3 · 📈 Today's calculated drivers"
)

driver_df = pd.DataFrame(
    [
        [
            "International Gold",
            quote_price("Gold XAU/USD"),
            quote_pct("Gold XAU/USD"),
            "Yahoo Finance",
            "Gold ETF",
        ],
        [
            "International Silver",
            quote_price("Silver XAG/USD"),
            quote_pct("Silver XAG/USD"),
            "Yahoo Finance",
            "Silver ETF",
        ],
        [
            "USD/INR",
            quote_price("USD/INR"),
            quote_pct("USD/INR"),
            "Yahoo Finance",
            "Both",
        ],
        [
            "DXY",
            quote_price("DXY"),
            quote_pct("DXY"),
            "Yahoo Finance",
            "Both",
        ],
    ],
    columns=[
        "Driver",
        "Value",
        "Change",
        "Source",
        "ETF relevance",
    ],
)


st.dataframe(
    driver_df,
    use_container_width=True,
    hide_index=True,
)


st.info(
    f"Gold: **{regime(gold_score)} "
    f"{gold_score:.0f}/100** • "
    f"Silver: **{regime(silver_score)} "
    f"{silver_score:.0f}/100**. "
    "News is a bounded overlay; live market data "
    "remains the numerical foundation."
)


# ============================================================
# 4. MACRO
# ============================================================

st.subheader(
    "4 · 🌎 Macro context"
)

y2 = latest(
    fred_series(
        "DGS2",
        6,
    )
)

y5 = latest(
    fred_series(
        "DGS5",
        6,
    )
)

y10 = latest(
    fred_series(
        "DGS10",
        6,
    )
)

ff = latest(
    fred_series(
        "FEDFUNDS",
        6,
    )
)


tcurve = treasury_latest_curve()

t2 = tcurve.get("2Y") or y2
t5 = tcurve.get("5Y") or y5
t10 = tcurve.get("10Y") or y10
t30 = tcurve.get("30Y")

spread = (
    t10 - t2
    if t10 is not None
    and t2 is not None
    else None
)


macro_items = [
    ("Fed Funds", ff),
    ("US 2Y", t2),
    ("US 5Y", t5),
    ("US 10Y", t10),
    ("10Y−2Y", spread),
]


cols = st.columns(
    len(macro_items)
)


for col, (
    name,
    value,
) in zip(
    cols,
    macro_items,
):

    col.metric(
        name,
        "—"
        if value is None
        else f"{value:.2f}",
    )


with st.expander(
    "Signals used by the score engine"
):

    if macro_notes:

        for note in macro_notes:
            st.write(
                "•",
                note,
            )

    else:

        st.write(
            "No additional macro signals available."
        )


st.caption(
    "Macro indicators are supporting signals. "
    "The V3 terminal remains primarily news-driven."
)


# ============================================================
# 5. NEWS
# ============================================================

st.subheader(
    "5 · 📰 Today's trusted news"
)


if news_error and news_df.empty:

    st.warning(
        news_error
    )


if events:

    for event in events:

        gold_impact = event[
            "gold_impact"
        ]

        silver_impact = event[
            "silver_impact"
        ]

        gold_icon = (
            "🟢"
            if gold_impact > 0
            else "🔴"
            if gold_impact < 0
            else "🟡"
        )

        silver_icon = (
            "🟢"
            if silver_impact > 0
            else "🔴"
            if silver_impact < 0
            else "🟡"
        )

        reported = event.get(
            "reported",
            {},
        )

        reported_text = (
            json.dumps(
                reported,
                ensure_ascii=False,
            )
            if reported
            else "None explicitly detected"
        )

        why = (
            "; ".join(
                event.get(
                    "reasons",
                    [],
                )
            )
            or
            "Relevant event detected; "
            "no numerical impact was inferred."
        )

        sources = ", ".join(
            event.get(
                "Sources",
                [],
            )
        )

        url = event.get(
            "URL",
            "",
        )

        st.markdown(
            f"""
            <div class="news-card">

            <div class="small-text">
            {event.get("PublishedIST", "")}
            • {sources}
            </div>

            <div class="news-title">
            {event.get("Headline", "")}
            </div>

            <p>
            {event.get("Description", "")}
            </p>

            <p>
            <b>Extracted reported numbers:</b>
            {reported_text}
            </p>

            <p>
            <b>ETF impact:</b>
            {gold_icon} Gold {gold_impact:+d}
            &nbsp;&nbsp;
            {silver_icon} Silver {silver_impact:+d}
            </p>

            <p>
            <b>Why it matters:</b>
            {why}
            </p>

            <p>
            <b>Confidence:</b>
            {event.get("confidence", 0)}/100
            </p>

            </div>
            """,
            unsafe_allow_html=True,
        )

        if url:

            st.link_button(
                "🔗 Open source article",
                url,
            )

else:

    st.info(
        "No qualifying trusted public articles "
        "were returned for today's India date."
    )


# ============================================================
# 6. DAILY SUMMARY
# ============================================================

st.subheader(
    "6 · 🧠 Today's summary"
)


gold_positive = sum(
    event["gold_impact"] > 0
    for event in events
)

gold_negative = sum(
    event["gold_impact"] < 0
    for event in events
)

silver_positive = sum(
    event["silver_impact"] > 0
    for event in events
)

silver_negative = sum(
    event["silver_impact"] < 0
    for event in events
)


st.markdown(
    f"""
    ### 🥇 Gold ETF view: {regime(gold_score)}

    Gold is currently **{bias(gold_score)}**
    at **{gold_score:.0f}/100**.

    Today's trusted news contains
    **{gold_positive} positive**
    and **{gold_negative} negative**
    gold-impact events.

    News overlay:
    **{gold_news_delta:+d} points**.

    ---

    ### 🥈 Silver ETF view: {regime(silver_score)}

    Silver is currently **{bias(silver_score)}**
    at **{silver_score:.0f}/100**.

    Today's trusted news contains
    **{silver_positive} positive**
    and **{silver_negative} negative**
    silver-impact events.

    News overlay:
    **{silver_news_delta:+d} points**.
    """
)


# ============================================================
# 7. TODAY VS YESTERDAY
# ============================================================

st.subheader(
    "7 · 📅 Today vs yesterday"
)


if yday:

    yesterday_market = yday.get(
        "market",
        {},
    )

    rows = [
        [
            "Gold score",
            yday.get(
                "gold_score"
            ),
            gold_score,
            gold_score
            - yday.get(
                "gold_score",
                gold_score,
            ),
        ],
        [
            "Silver score",
            yday.get(
                "silver_score"
            ),
            silver_score,
            silver_score
            - yday.get(
                "silver_score",
                silver_score,
            ),
        ],
        [
            "GOLDBEES price",
            yesterday_market.get(
                "GOLDBEES",
                {},
            ).get("price"),
            quote_price("GOLDBEES"),
            None,
        ],
        [
            "SILVERBEES price",
            yesterday_market.get(
                "SILVERBEES",
                {},
            ).get("price"),
            quote_price("SILVERBEES"),
            None,
        ],
    ]

    for row in rows[2:]:

        try:

            if (
                row[1] is not None
                and row[2] is not None
            ):
                row[3] = (
                    row[2]
                    - row[1]
                )

        except Exception:

            row[3] = None

    history_df = pd.DataFrame(
        rows,
        columns=[
            "Metric",
            "Yesterday",
            "Today",
            "Change",
        ],
    )

    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Yesterday refers to the previous "
        "India calendar date's local JSON record."
    )

else:

    st.info(
        "No previous-day record exists yet. "
        "It will appear automatically after a "
        "date rollover while V3 is running."
    )


# ============================================================
# 8. PRICE CHARTS
# ============================================================
# ============================================================
# 8. PRICE CHARTS
# Maximum 6 months • Changeable period
# ETF charts shown first
# ============================================================

# ============================================================
# 8. PRICE CHARTS
# ============================================================

st.subheader("8 · 📈 Price Charts")

st.caption(
    "Maximum historical period: 6 months • "
    "Daily closing prices"
)


# ============================================================
# CHART PERIOD SELECTOR
# ============================================================

chart_period = st.radio(
    "Chart period",
    ["1M", "3M", "6M"],
    index=2,
    horizontal=True,
    help="All charts are limited to a maximum of 6 months.",
)

period_map = {
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
}

selected_period = period_map[chart_period]


# ============================================================
# HISTORICAL YAHOO DATA
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def yahoo_history(symbol, period):

    params = {
        "range": period,
        "interval": "1d",
        "includePrePost": "false",
        "events": "history",
    }

    last_error = None

    for base_url in [
        "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
        YAHOO_URL,
    ]:
        try:
            response = requests.get(
                base_url.format(symbol=symbol),
                params=params,
                timeout=15,
                headers={
                    **HEADERS,
                    "Accept": "application/json,text/plain,*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )

            response.raise_for_status()
            payload = response.json()
            break

        except Exception as exc:
            last_error = exc
            payload = None

    if payload is None:
        raise ValueError(
            f"Historical data temporarily unavailable for {symbol}"
        )

    result = (
        payload
        .get("chart", {})
        .get("result")
    )

    if not result:
        raise ValueError(
            f"No historical data returned for {symbol}"
        )

    result = result[0]

    timestamps = result.get(
        "timestamp",
        [],
    )

    quote_data = (
        result
        .get("indicators", {})
        .get("quote", [{}])[0]
    )

    if not timestamps:
        raise ValueError(
            f"No timestamps returned for {symbol}"
        )

    df = pd.DataFrame(quote_data)

    df["Date"] = (
        pd.to_datetime(
            timestamps,
            unit="s",
            utc=True,
        )
        .tz_convert("Asia/Kolkata")
        .date
    )

    df["Date"] = pd.to_datetime(
        df["Date"]
    )

    if "close" not in df.columns:
        raise ValueError(
            f"No closing price returned for {symbol}"
        )

    df["close"] = pd.to_numeric(
        df["close"],
        errors="coerce",
    )

    df = df.dropna(
        subset=["close"]
    )

    if df.empty:
        raise ValueError(
            f"No valid historical prices for {symbol}"
        )

    columns = [
        "Date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    available_columns = [
        column
        for column in columns
        if column in df.columns
    ]

    df = df[
        available_columns
    ].copy()

    df = df.sort_values(
        "Date"
    )

    return df


# ============================================================
# GENERIC CHART FUNCTION
# ============================================================

def create_price_chart(
    symbol,
    title,
    prefix="₹",
):

    try:

        df = yahoo_history(
            symbol,
            selected_period,
        )

        if df.empty:
            return None

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["close"],
                mode="lines",
                name=title,
                line=dict(width=2),
                hovertemplate=(
                    "<b>%{x|%d %b %Y}</b><br>"
                    + title
                    + ": "
                    + prefix
                    + "%{y:,.2f}"
                    + "<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0b0f14",
            plot_bgcolor="#0b0f14",
            font=dict(
                color="#e2e8f0"
            ),
            height=360,

            title={
                "text": (
                    f"{title} · "
                    f"{chart_period}"
                ),
                "x": 0.02,
            },

            margin=dict(
                l=10,
                r=10,
                t=50,
                b=10,
            ),

            hovermode="x unified",

            xaxis=dict(
                title="Date",
                rangeslider=dict(
                    visible=False
                ),
            ),

            yaxis=dict(
                title="Price",
                tickformat=",.2f",
            ),

            showlegend=False,
        )

        return fig

    except Exception as exc:

        st.warning(
            f"{title}: chart unavailable — {exc}"
        )

        return None


# ============================================================
# 8.1 INDIAN GOLD & SILVER ETFs
# ============================================================

st.markdown(
    "### 🇮🇳 Indian Gold & Silver ETFs"
)

st.caption(
    "Indian ETF charts are shown first because "
    "these are the primary instruments tracked by the terminal."
)

etf_col1, etf_col2 = st.columns(2)


# ============================================================
# GOLD ETF — FIRST
# ============================================================

with etf_col1:

    st.markdown("#### 🥇 GOLDBEES")

    gold_etf_fig = create_price_chart(
        "GOLDBEES.NS",
        "GOLDBEES",
        "₹",
    )

    if gold_etf_fig is not None:

        st.plotly_chart(
            gold_etf_fig,
            use_container_width=True,
        )


# ============================================================
# SILVER ETF — SECOND
# ============================================================

with etf_col2:

    st.markdown("#### 🥈 SILVERBEES")

    silver_etf_fig = create_price_chart(
        "SILVERBEES.NS",
        "SILVERBEES",
        "₹",
    )

    if silver_etf_fig is not None:

        st.plotly_chart(
            silver_etf_fig,
            use_container_width=True,
        )


# ============================================================
# 8.2 INTERNATIONAL GOLD & SILVER
# ============================================================

st.markdown(
    "### 🌎 International Gold & Silver"
)

international_col1, international_col2 = (
    st.columns(2)
)


# ============================================================
# INTERNATIONAL GOLD
# ============================================================

with international_col1:

    st.markdown("#### 🥇 Gold XAU/USD")

    gold_fig = create_price_chart(
        "GC=F",
        "Gold XAU/USD",
        "$",
    )

    if gold_fig is not None:

        st.plotly_chart(
            gold_fig,
            use_container_width=True,
        )


# ============================================================
# INTERNATIONAL SILVER
# ============================================================

with international_col2:

    st.markdown("#### 🥈 Silver XAG/USD")

    silver_fig = create_price_chart(
        "SI=F",
        "Silver XAG/USD",
        "$",
    )

    if silver_fig is not None:

        st.plotly_chart(
            silver_fig,
            use_container_width=True,
        )


st.caption(
    f"Selected chart period: {chart_period} • "
    "Maximum available period: 6 months • "
    "Daily closing prices • Yahoo Finance"
)

# ============================================================
# 9. RISK ALERTS
# ============================================================

st.subheader(
    "9 · ⚠️ Risk alerts"
)


alerts = []


dxy_pct = quote_pct(
    "DXY"
)

inr_pct = quote_pct(
    "USD/INR"
)

gold_pct = quote_pct(
    "Gold XAU/USD"
)

silver_pct = quote_pct(
    "Silver XAG/USD"
)


if (
    np.isfinite(dxy_pct)
    and dxy_pct > 0.5
):

    alerts.append(
        "🔴 DXY rising sharply — "
        "potential precious-metal headwind."
    )


if (
    np.isfinite(inr_pct)
    and inr_pct > 0.5
):

    alerts.append(
        "🟢 INR weakness — "
        "domestic bullion translation tailwind."
    )


if (
    np.isfinite(gold_pct)
    and gold_pct < -1
):

    alerts.append(
        "🔴 Gold momentum negative."
    )


if (
    np.isfinite(silver_pct)
    and silver_pct < -1.5
):

    alerts.append(
        "🔴 Silver volatility/momentum "
        "risk elevated."
    )


if not alerts:

    alerts.append(
        "🟡 No major threshold alert triggered."
    )


for alert in alerts:

    st.write(
        alert
    )


# ============================================================
# 10. API STATUS
# ============================================================

st.subheader(
    "10 · 🔌 Data/API status"
)


news_status = (
    "🟢 Data found"
    if not news_df.empty
    else "🟡 No qualifying data"
)


fred_status = (
    "🟢 Configured"
    if get_secret("FRED_API_KEY")
    else "🟡 Key missing"
)

news_api_status = (
    "🟢 Configured"
    if get_secret("NEWS_API_KEY")
    else "🟡 Key missing"
)

news_api_configured = bool(
    get_secret("NEWS_API_KEY")
)

api_rows = [
    [
        "Yahoo Finance",
        "Gold/Silver/USD-INR/DXY + Indian ETFs",
        "🟢 Active"
        if quotes
        else "🔴 Failed",
        "Live market adapter",
    ],
    [
        "FRED",
        "US macro/yields",
        fred_status,
        "US macro adapter",
    ],
    [
        "BLS",
        "US official statistics",
        "🟢 Public API",
        "Official statistics adapter",
    ],
    [
        "US Treasury",
        "Treasury yields",
        "🟢 Attempted",
        "Direct feed with FRED fallback",
    ],
    [
    "NewsAPI",
    "Today's trusted public news",
    "🟢 Configured"
    if news_api_configured
    else "🟡 Key missing",
    "Whitelist + India-date filter",
    ],
]


api_df = pd.DataFrame(
    api_rows,
    columns=[
        "Provider",
        "Purpose",
        "Status",
        "Details",
    ],
)


st.dataframe(
    api_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# 11. LOCAL HISTORY
# ============================================================

# ============================================================
# 11. LOCAL HISTORY
# ============================================================

st.subheader(
    "11 · 💾 Local daily history"
)

st.write(
    f"Today's file: `{day_file(TODAY_STR).name}`"
)

if yday:
    yesterday = TODAY - timedelta(days=1)

    st.write(
        f"Yesterday's file: "
        f"`{day_file(yesterday.isoformat()).name}`"
    )

if storage_saved:
    st.success(
        "Local snapshot saved for this session."
    )
else:
    st.info(
        "Local history storage is unavailable on "
        "the deployed Streamlit environment. "
        "Live market data, news and charts continue normally."
    )

st.caption(
    "Streamlit Cloud uses an ephemeral filesystem. "
    "Local JSON files should not be treated as permanent storage."
)
# ============================================================
# WARNINGS
# ============================================================

if errors:

    with st.expander(
        f"⚠️ Market provider warnings ({len(errors)})"
    ):

        for error in errors:

            st.write(
                "•",
                error,
            )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    f"Updated "
    f"{now_ist().strftime('%Y-%m-%d %H:%M:%S IST')} "
    "• Decision-support only; not investment advice."
)
