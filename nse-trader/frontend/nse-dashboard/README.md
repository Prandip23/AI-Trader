# NSE AI Trader

A self-learning, AI-powered stock trading system for NSE India. Built with Python (FastAPI + XGBoost) backend and React frontend. Uses Claude AI for signal validation, news sentiment analysis, and market context filtering.

---

## What It Does

Every morning at 9:30 AM the system retrains its ML model on fresh market data. At 9:45 AM it runs a full paper trading session — fetching live prices, checking market conditions, reading news, generating signals, and executing virtual trades. Everything runs automatically as long as your PC is on.

---

## Intelligence Stack

Each signal passes through 5 layers before a trade is executed:

```
1. XGBoost ML Model       → learns from 250 days of price/volume patterns
2. Market Filter          → blocks BUY signals when VIX is high or Nifty is bearish
3. News Sentiment         → Claude reads latest headlines for each stock
4. Claude AI Validation   → combines technicals + market context + news into final call
5. Confidence Threshold   → filters out weak signals below 40%
```

---

## Project Structure

```
nse-trader/
├── backend/
│   ├── main.py                        # FastAPI server + scheduler
│   ├── .env                           # ANTHROPIC_API_KEY goes here
│   ├── data/
│   │   ├── fetcher.py                 # NSE data + technical indicators
│   │   ├── market_context.py          # VIX + Nifty trend + breadth
│   │   └── news_fetcher.py            # Google News RSS per stock
│   ├── models/
│   │   └── trainer.py                 # XGBoost model train + retrain
│   ├── engine/
│   │   └── signals.py                 # Signal generation pipeline
│   ├── ai/
│   │   └── claude_analyst.py          # Claude API integration
│   └── trading/
│       ├── paper_trader.py            # Paper trading engine
│       ├── win_tracker.py             # 30-day performance stats
│       └── experiment_tracker.py      # Parameter change history
└── frontend/
    └── nse-dashboard/
        └── src/
            └── App.js                 # React dashboard
```

---

## Prerequisites

- Python 3.11+
- Node.js 20+
- Anthropic API key — get one at console.anthropic.com

---

## Setup

**1. Clone and set up backend**
```bash
cd nse-trader/backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install fastapi uvicorn pandas numpy scikit-learn xgboost yfinance sqlalchemy apscheduler requests anthropic python-dotenv
```

**2. Add your API key**

Create `backend/.env`:
```
ANTHROPIC_API_KEY=your_key_here
```

**3. Train the initial model**
```bash
python models/trainer.py
```

**4. Initialize experiment tracking**
```bash
python trading/experiment_tracker.py
```

**5. Start the backend**
```bash
uvicorn main:app --reload --port 8000
```

**6. Set up and start frontend**
```bash
cd frontend/nse-dashboard
npm install
npm install axios recharts lucide-react
npm start
```

Dashboard opens at http://localhost:3000

---

## Daily Usage

The app runs automatically every day at:
- **9:30 AM** — model retrains on latest market data
- **9:45 AM** — paper trading session executes

To trigger manually:
```bash
# Retrain model
python models/trainer.py

# Run trading session
python trading/paper_trader.py

# Check signals only
python engine/signals.py

# Check news for stocks
python data/news_fetcher.py
```

Or use the **Run Session** and **Retrain Model** buttons in the dashboard.

---

## Dashboard Tabs

**Dashboard**
Shows portfolio value, total P&L, return percentage, cash available, performance chart over time, and all open positions with stop loss and target prices.

**Signals**
Shows today's AI-generated signals with a market context banner (VIX, Nifty trend, breadth, market verdict) at the top. Each signal card shows confidence, RSI, volume, stop loss, target, Claude's reasoning, news sentiment badge, and latest headlines.

**Trades**
Full trade history with entry price, quantity, value, status (OPEN / TARGET_HIT / STOP_LOSS), P&L, and date.

**Performance**
30-day stats including win rate, profit factor, risk/reward ratio, trade summary, win rate by confidence bucket, best and worst trades, and performance breakdown by stock.

---

## Stocks Covered

49 Nifty 50 stocks across sectors:

- **Financial** — HDFCBANK, ICICIBANK, KOTAKBANK, SBIN, AXISBANK, BAJFINANCE, BAJAJFINSV, HDFCLIFE, SBILIFE, ICICIPRULI
- **IT** — TCS, INFY, WIPRO, HCLTECH, TECHM, LTM
- **Energy** — RELIANCE, ONGC, BPCL, POWERGRID, NTPC, COALINDIA
- **Consumer** — HINDUNILVR, ITC, NESTLEIND, BRITANNIA, TATACONSUM
- **Auto** — MARUTI, BAJAJ-AUTO, HEROMOTOCO, EICHERMOT
- **Pharma** — SUNPHARMA, DRREDDY, CIPLA, DIVISLAB
- **Metals** — TATASTEEL, JSWSTEEL, HINDALCO, ULTRACEMCO, GRASIM
- **Others** — BHARTIARTL, ADANIENT, ADANIPORTS, LT, ASIANPAINT, TITAN, INDUSINDBK, M&M, APOLLOHOSP

---

## Technical Indicators Used by ML Model

| Category | Indicators |
|---|---|
| Trend | SMA20, SMA50, EMA12, EMA26 |
| Momentum | MACD, MACD Signal, MACD Histogram, RSI |
| Volatility | Bollinger Upper, Lower, Width |
| Volume | Volume MA, Volume Ratio |
| Price Action | Return 1d, 5d, 10d |

---

## Market Filter Logic

Before any BUY signal is executed, the system scores market conditions:

| Condition | Score |
|---|---|
| VIX < 15 (Low Fear) | +2 |
| VIX 15–20 (Normal) | +1 |
| VIX 20–25 (Caution) | -1 |
| VIX > 25 (High Fear) | -3 |
| Nifty above SMA20 + SMA50 | +2 |
| Nifty below both | -2 |
| Breadth > 60% bullish | +1 |
| Breadth < 40% bullish | -1 |

**Score ≥ 3** → STRONG_BUY, full position size
**Score 1–2** → CAUTIOUS_BUY, 75% position size
**Score 0** → NEUTRAL, 50% position size
**Score < 0** → AVOID_BUY, all BUY signals blocked

---

## Paper Trading Rules

- Starting capital: ₹10,00,000
- Max 5% of portfolio per trade
- No duplicate positions — one open position per stock at a time
- Stop loss and target auto-set by Claude based on risk level
- Positions auto-close when stop loss or target is hit

---

## Experiment Tracking

Every parameter change is logged to SQLite with before/after context so you can measure the impact of each tuning decision. Tracked changes so far:

1. Confidence threshold: 0.50 → 0.40
2. Claude prompt: strict → moderate
3. Market filter: None → VIX + Nifty + Breadth
4. News sentiment: None → Google News RSS via Claude

View experiment history at: http://localhost:8000/experiments

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/portfolio` | GET | Portfolio value, cash, open positions |
| `/signals` | GET | Generate today's signals with AI |
| `/trades` | GET | Trade history |
| `/history` | GET | Daily P&L history |
| `/winrate` | GET | 30-day performance stats |
| `/experiments` | GET | Parameter change history |
| `/session/run` | POST | Manually trigger trading session |
| `/model/retrain` | POST | Manually retrain ML model |

---

## Auto Start on Windows Boot

Create `start_trader.bat` in the `nse-trader` folder:
```bat
@echo off
cd C:\path\to\nse-trader\backend
call venv\Scripts\activate.bat
start "NSE Backend" cmd /k "venv\Scripts\activate.bat && uvicorn main:app --port 8000"
timeout /t 5
cd ..\frontend\nse-dashboard
start "NSE Frontend" cmd /k "npm start"
```

Add to Windows Startup folder (`Win + R` → `shell:startup`) to run on boot.

Make sure Sleep is disabled in Power Settings so the scheduler runs uninterrupted.

---

## Roadmap

- [ ] F&O module — options signals with Greeks
- [ ] Intraday patterns — 15-min candle analysis
- [ ] Sector rotation analysis
- [ ] Email/WhatsApp morning alerts
- [ ] Zerodha Kite integration for real money trading
- [ ] Backtesting engine
- [ ] Experiment dashboard in React UI