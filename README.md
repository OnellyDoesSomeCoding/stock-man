# Stockman

A personal website for exploring Thai stocks (SET, the Stock Exchange of Thailand): candlestick charts, key numbers, moving averages, RSI, a watchlist and side-by-side comparison. Every finance term has a plain-language "?" tooltip, so you can learn while you look.

> **Not financial advice.** This is a learning project. Data comes from free, unofficial sources and may be delayed or wrong. Indicators describe the past; they don't predict the future.

## Features

- **Search** Thai stocks by company name (`airports`) or code (`PTT`), with suggestions.
- **Stats card:** price, today's change, market cap and P/E ratio.
  - **Market cap:** price × number of shares, i.e. what the whole company is worth on the market.
  - **P/E ratio:** price ÷ yearly profit per share, i.e. how many baht you pay for each 1 baht of yearly profit.
- **Candlestick chart** (1M / 3M / 6M / 1Y / 5Y) with volume bars.
  - **Candle:** one day's open, high, low and close prices.
  - **Volume:** how many shares were traded that day.
- **Moving averages** (20 / 50 / 200 days): the average closing price over the last N days, drawn as a smooth line that shows the trend.
- **RSI (14 days):** a 0–100 score in its own panel. Above 70 the price rose fast (maybe "overbought"); below 30 it fell fast (maybe "oversold").
- **Compare 2 stocks** as % change since the first day shown, so stocks with very different prices can be compared fairly.
- **Watchlist:** save stocks to follow and see their latest price and change at a glance. It's stored in the backend, so it survives browser restarts.
- **Paper portfolio:** practice buying and selling with 100,000 THB of fake money at real latest prices. It shows what you own, average cost, current value, profit/loss and recent trades.
- **Strategy lab**
  - **Backtest:** replay a simple trading rule over the last 1 or 5 years and compare it with buy-and-hold. Rules: price vs 50-day average, 20 vs 50-day average, RSI 30/70.
    - A rule decides at each day's close and trades at the next day's open, with a 0.15% fee.
    - Results include fees paid, win rate and the biggest drop.
  - **Prediction experiment:** four simple models guess the price 1, 5 or 20 trading days ahead.
    - Each is scored "walk-forward": it only sees data up to the day of each guess.
    - All are compared with "tomorrow = today". On real data that lazy guess usually wins, which is the point of the lesson.
    - It shows a typical price *range* based on past moves, not a single predicted price.
- Light/dark mode (follows your system) and phone-friendly layout.

## How it works

```
Browser (React + Vite, port 5173)
   │  /api/*  (Vite forwards these to the backend)
   ▼
FastAPI backend (port 8000) ──► yfinance ──► Yahoo Finance
   │
   ▼
SQLite (backend/data/cache.db): cached prices, stats, search results + your watchlist and paper trades
```

- Prices are cached so the same data isn't downloaded twice. After the first load, only the newest days are fetched.
- Moving averages and RSI are calculated in the backend over up to 5 years of history. That way even a 1-month chart shows complete lines from its first day.
- If Yahoo is down, the backend serves the last saved copy and marks it as `stale`.

| Data | Kept fresh for |
|---|---|
| Prices, stats | 30 minutes |
| Search results | 1 day |
| Watchlist, paper trades | Forever (until you remove them / press Reset) |

## Tech stack

- **Backend:** Python, FastAPI, uvicorn, yfinance, SQLite
- **Frontend:** React 19, Vite, [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) v5
- Tested with **Python 3.14** and **Node.js 24** on Windows

## Getting started

### 1. First-time setup

```powershell
# Backend (from the project root)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

> If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
> On macOS/Linux, activate with `source .venv/bin/activate`.

### 2. Run it (two terminals)

```powershell
# Terminal 1: backend (project root, venv activated)
uvicorn app.main:app --app-dir backend --reload

# Terminal 2: frontend
cd frontend
npm run dev
```

Open **http://localhost:5173**. Use `localhost`, not `127.0.0.1`: the dev server only listens on `localhost`.

### 3. Optional checks

```powershell
# Check that the data source works: prints PTT.BK's last 5 days and saves ptt_chart.png
python scripts/test_data.py

# Frontend lint and production build
cd frontend
npm run lint
npm run build
```

Interactive API docs are available at **http://127.0.0.1:8000/docs** while the backend runs.

## API

Tickers can be typed loosely: `ptt`, `PTT` and `PTT.BK` all work (`.BK` is added when there's no dot).

| Method | Endpoint | What it returns |
|---|---|---|
| GET | `/api/health` | `{"status": "ok"}` |
| GET | `/api/search?q=airports` | Matching Thai stocks, best match first |
| GET | `/api/stocks/{ticker}/prices?range=1y&sma=20,50&rsi=14` | Daily candles, plus optional moving averages and RSI. `range`: `1m` `3m` `6m` `1y` `5y` |
| GET | `/api/stocks/{ticker}/stats` | Name, price, change, market cap, P/E |
| GET | `/api/stocks/{ticker}/backtest?strategy=price_above_ma50&range=5y` | Rule vs buy-and-hold: values over time, trades, stats. `strategy`: `price_above_ma50`, `ma20_above_ma50`, `rsi_30_70` |
| GET | `/api/stocks/{ticker}/forecast?horizon=5&range=1y` | Prediction models scored on past data (`horizon`: 1, 5 or 20 trading days), plus a typical price range |
| GET | `/api/watchlist` | Saved stocks with their stats |
| POST | `/api/watchlist/{ticker}` | Add a stock (checked to exist first; max 30) |
| DELETE | `/api/watchlist/{ticker}` | Remove a stock |
| GET | `/api/portfolio` | Paper portfolio: cash, holdings at current prices, profit/loss, last 20 trades |
| POST | `/api/portfolio/trades` | Body `{"ticker": "PTT", "side": "buy", "shares": 100}`: trades at the latest price |
| POST | `/api/portfolio/reset` | Delete all paper trades (back to 100,000 THB) |

## Project structure

```
backend/app/
  main.py        HTTP endpoints
  stocks.py      Caching rules, watchlist, paper portfolio
  indicators.py  Moving average and RSI math
  backtest.py    Replays trading rules with fake money
  forecast.py    Prediction experiment (walk-forward scoring)
  yahoo.py       The only file that talks to yfinance
  cache.py       SQLite tables and queries
frontend/src/
  App.jsx        Page layout and state
  api.js         All calls to the backend
  glossary.js    Text for every "?" tooltip (edit wording here)
  indicators.js  Moving-average / RSI settings and colors
  components/    PriceChart, LineChart, StatsCard, Watchlist, LabCard, PortfolioCard, TickerSearch, InfoTip, ...
scripts/
  test_data.py   Step 0: data-source check
```

## Known limitations

- **yfinance is unofficial.** It scrapes Yahoo Finance and can break or get rate-limited without warning.
- **Data may be delayed** (often ~15 minutes) and prices are in Thai baht (THB).
- **Search** depends on Yahoo:
  - Broad words like "energy" find few Thai stocks.
  - Thai script (ปตท) finds nothing.
  - Some company names appear in CAPITALS or cut short.
- **History is capped at 5 years.** On the 5Y chart, the 200-day average starts about 10 months in.
- **% change ignores dividends** (cash payments to shareholders), so it understates the total return of high-dividend stocks.
- **Paper trading is simplified:** no broker fees, no market-hours check, and the trade price is the latest free (possibly delayed) price.
- **No login.** The watchlist and paper portfolio are shared by anyone who can reach the backend. That's fine on your own computer, but not if the site is put online.

## Hosting

The app is built to run on your own computer. Putting it online needs some changes first:

- **Frontend:** can be hosted anywhere that serves static files (Vercel, Netlify, Cloudflare Pages).
- **Backend:** needs a host with a persistent disk for the SQLite file (e.g. Render, Railway, Fly.io). Alternatively, switch to a hosted database to run it on serverless platforms such as Vercel.
- **Before going public:**
  - add a login, or at least protect the watchlist endpoints
  - show the "not financial advice" note
  - check the data source's terms of use (Yahoo's data is for personal use; SET's official API is paid)

## Roadmap

- [x] **Step 0:** data-source check script
- [x] **Phase 1:** ticker search, candlestick chart, stats card, "?" tooltips
- [x] **Phase 2:** moving averages, RSI, compare 2 stocks, watchlist
- [ ] **Phase 3:**
  - [x] paper portfolio (practice trading with fake money)
  - [x] strategy lab: backtester and prediction experiment (added beyond the original plan)
  - [ ] company financials charts
  - [ ] news feed
  - [ ] AI "explain simply" button
