# 🥇🥈 Indian Gold & Silver ETF Decision Terminal V3

A **Streamlit-based financial market terminal** designed to monitor Indian Gold and Silver ETFs using live market data, macroeconomic indicators, trusted financial news, and a news-driven decision scoring system.

## 🚀 Features

* 📊 Indian Gold & Silver ETF monitoring
* 🥇 Gold ETFs including GOLDBEES and HDFCGOLD
* 🥈 Silver ETFs including SILVERBEES and HDFCSILVER
* 📈 Gold and Silver international prices
* 💱 USD/INR and DXY tracking
* 📰 Current-day financial news from trusted sources
* 🧠 News-based Gold and Silver impact scoring
* 📉 US Treasury yields and macroeconomic indicators
* 📅 Today vs yesterday comparison
* 📊 Interactive ETF and commodity charts
* 🔄 Automatic dashboard refresh
* 💾 Local JSON-based daily history
* ⚠️ Risk alerts based on market movements
* 🔌 API/data-source status monitoring

## 📰 News System

The terminal focuses on **current-date news** and filters articles using a trusted-source policy.

It prioritizes sources such as:

* Reuters
* Bloomberg
* CNBC
* Financial Times
* Economic Times
* Business Standard
* Moneycontrol
* Mint
* RBI
* Federal Reserve
* U.S. Treasury
* Bureau of Labor Statistics
* Other official government and financial institutions

Social media posts, blogs and other non-trusted sources are excluded.

## 📊 Data Sources

The project can use:

* **Yahoo Finance** — market prices and ETF data
* **FRED** — US macroeconomic and interest-rate data
* **BLS** — official US economic statistics
* **U.S. Treasury** — Treasury yield data
* **NewsAPI** — financial news discovery

API keys are stored locally in a `.env` file and should **not be committed to GitHub**.

## 🧠 Decision Engine

The dashboard combines market and news information to calculate separate scores for:

**Gold ETF Score:** 0–100
**Silver ETF Score:** 0–100

The score considers factors such as:

* Gold/Silver price movement
* USD/INR movement
* DXY movement
* US Treasury yields
* Inflation indicators
* Federal Reserve expectations
* Gold/Silver-related news
* Industrial demand signals for Silver

The result is classified as:

* 🟢 Strong Bullish
* 🟢 Bullish
* 🟡 Neutral
* 🟠 Bearish
* 🔴 Strong Bearish

The scoring system is intended as a **decision-support indicator**, not a guaranteed prediction of future prices.

## 📅 Historical Data

The application automatically creates local daily JSON files:

```text
data/
├── history/
│   ├── 2026-08-10.json
│   ├── 2026-08-11.json
│   └── ...
└── state.json
```

Daily snapshots contain market data, ETF scores, news articles and calculated events.

## 🖥️ Run Locally

Clone the repository:

```bash
git clone <your-repository-url>
cd <repository-folder>
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
NEWS_API_KEY=your_newsapi_key
FRED_API_KEY=your_fred_api_key
```

Run the application:

```bash
streamlit run app_v3.py
```

## ☁️ Streamlit Deployment

The project can be deployed using **Streamlit Community Cloud**.

Basic deployment flow:

1. Push the project to GitHub.
2. Open Streamlit Community Cloud.
3. Connect your GitHub repository.
4. Select `app_v3.py` as the main file.
5. Add API keys through Streamlit Secrets.
6. Deploy the application.

Do **not** upload `.env` or API keys to the public GitHub repository.

## 📁 Project Structure

```text
Indian-Gold-Silver-ETF-Terminal/
│
├── app_v3.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env
│
└── data/
    ├── state.json
    └── history/
```

## ⚠️ Disclaimer

This project is built for **market monitoring, research and decision support**. It does not provide financial advice, guaranteed predictions or recommendations to buy or sell securities.

Always verify market data and conduct your own research before making investment decisions.
