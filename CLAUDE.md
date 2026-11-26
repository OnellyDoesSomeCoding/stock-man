# Project: SET Stock Analysis Website

## About me
- I have ZERO finance/trading knowledge. Explain any finance term in plain words the first time it appears.
- Keep answers short: bullet points or diagrams over paragraphs.

## Rules
- NEVER run `git commit` or `git push` unless I explicitly say so.
- Ask before installing big dependencies or changing the stack.
- Build in small steps; after each step, tell me how to run/test it.

## Goal
A personal website to analyze Thai stocks (SET market) and learn the basics while building it. US stocks may come later.

## Stack
- Backend: Python + FastAPI
- Data: yfinance (tickers end in `.BK`, e.g. `PTT.BK`, `AOT.BK`); later settfex / thaifin for fundamentals. All are free but unofficial: expect occasional breakage.
- Cache: SQLite (store fetched prices; avoid re-fetching)
- Frontend: React (Vite) + TradingView Lightweight Charts for candlesticks
- API keys (if any) stay in the backend, in `.env` (never commit it)

## Architecture
User → React frontend → FastAPI backend → yfinance / SET data
                                ↕
                           SQLite cache

## Roadmap
- Step 0: script that fetches 1 year of PTT.BK daily prices and plots it (checks the data source works)
- Phase 1 (MVP): ticker search → candlestick chart, stats card (price, % change, market cap, P/E), "?" tooltip explaining every term
- Phase 2: moving average + RSI on the chart, compare 2 stocks, watchlist
- Phase 3: company financials charts, news feed, paper portfolio (fake money), AI "explain simply" button

## Key terms (use these in tooltips)
- Ticker: short stock code (PTT.BK = PTT on SET)
- Candle (OHLC): one day's open, high, low, close
- Volume: shares traded that day
- Market cap: price × number of shares = company's total value
- P/E ratio: price ÷ yearly profit per share
- Moving average: average price over last N days (shows trend)
- RSI: 0–100 score; >70 maybe overbought, <30 maybe oversold

## Gotchas
- Prices are in Thai baht (THB); free data may be delayed
- Indicators describe the past; they don't predict
- If the site ever goes public: add a "not financial advice" note and check data-source terms (SET's official API is paid)