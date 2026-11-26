"""FastAPI app: the HTTP endpoints the React frontend will call."""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import cache, stocks


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache.init_db()
    yield


app = FastAPI(title="Stockman API", lifespan=lifespan)

# Let the Vite dev server (React, port 5173) call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


def _run(fn, raw_ticker: str, *args):
    """Normalize the ticker and turn our errors into HTTP status codes."""
    try:
        return fn(stocks.normalize_ticker(raw_ticker), *args)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except stocks.TickerNotFound as exc:
        raise HTTPException(404, f"No data found for {exc}. Check the ticker.")
    except stocks.SourceUnavailable:
        raise HTTPException(502, "Data source (Yahoo Finance) is unavailable. Try again later.")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/search")
def search(q: str = Query(..., min_length=1, max_length=50)):
    """Thai (SET) stocks matching a company name or ticker code, best match first."""
    try:
        return stocks.search(q)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except stocks.SourceUnavailable:
        raise HTTPException(502, "Data source (Yahoo Finance) is unavailable. Try again later.")


@app.get("/api/stocks/{ticker}/prices")
def prices(
    ticker: str,
    range_: Literal["1m", "3m", "6m", "1y", "5y"] = Query("1y", alias="range"),
    sma: str | None = Query(None, description="Moving-average periods in days, e.g. 20,50,200"),
    rsi: int | None = Query(None, ge=2, le=50, description="RSI period in days (usually 14)"),
):
    """Daily candles (open/high/low/close/volume) for the chart, plus optional indicators."""
    return _run(stocks.get_candles, ticker, range_, sma, rsi)


@app.get("/api/stocks/{ticker}/backtest")
def backtest(
    ticker: str,
    strategy: str = Query("price_above_ma50", description="price_above_ma50, ma20_above_ma50 or rsi_30_70"),
    range_: Literal["6m", "1y", "5y"] = Query("5y", alias="range"),
):
    """Replay a trading rule with 100,000 fake THB and compare it with buy-and-hold."""
    return _run(stocks.get_backtest, ticker, strategy, range_)


@app.get("/api/stocks/{ticker}/forecast")
def forecast(
    ticker: str,
    horizon: int = Query(5, description="Trading days ahead to predict: 1, 5 or 20"),
    range_: Literal["6m", "1y", "5y"] = Query("1y", alias="range"),
):
    """Prediction experiment: simple models scored on past data against 'the price won't change'."""
    return _run(stocks.get_forecast, ticker, horizon, range_)


@app.get("/api/stocks/{ticker}/stats")
def stats(ticker: str):
    """Price, % change, market cap and P/E for the stats card."""
    return _run(stocks.get_stats, ticker)


@app.get("/api/watchlist")
def watchlist():
    """Saved stocks with their latest price and change, oldest first."""
    return {"items": stocks.get_watchlist()}


@app.post("/api/watchlist/{ticker}", status_code=201)
def watch(ticker: str):
    """Add a stock (checked to exist first). Returns its stats, ready to show as a row."""
    return _run(stocks.add_to_watchlist, ticker)


@app.delete("/api/watchlist/{ticker}", status_code=204)
def unwatch(ticker: str):
    """Remove a stock. Removing one that isn't there is fine (nothing happens)."""
    _run(stocks.remove_from_watchlist, ticker)
    return Response(status_code=204)


class TradeRequest(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    shares: int = Field(ge=1, le=stocks.MAX_SHARES_PER_TRADE)


@app.get("/api/portfolio")
def portfolio():
    """Paper portfolio: fake cash, holdings valued at current prices, profit/loss, recent trades."""
    return stocks.get_portfolio()


@app.post("/api/portfolio/trades", status_code=201)
def trade(body: TradeRequest):
    """Buy or sell at the latest price. Returns the trade and the updated portfolio."""
    return _run(stocks.place_trade, body.ticker, body.side, body.shares)


@app.post("/api/portfolio/reset")
def reset_portfolio():
    """Delete every paper trade: back to the starting cash."""
    stocks.reset_portfolio()
    return stocks.get_portfolio()
