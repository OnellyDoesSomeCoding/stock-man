"""Business logic: serve from the SQLite cache, refresh from Yahoo when stale."""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

from . import backtest, cache, forecast, yahoo
from .indicators import relative_strength_index, simple_moving_average

PRICE_TTL = timedelta(minutes=30)  # how long cached data counts as "fresh"
STATS_TTL = timedelta(minutes=30)
SEARCH_TTL = timedelta(days=1)  # company names rarely change
SEARCH_LIMIT = 10
WATCHLIST_MAX = 30
STARTING_CASH = 100_000.0  # fake THB every paper portfolio starts with
MAX_SHARES_PER_TRADE = 10_000_000
RECENT_TRADES = 20
RANGE_DAYS = {"1m": 31, "3m": 92, "6m": 183, "1y": 366, "5y": 1827}
SMA_MIN, SMA_MAX, SMA_MAX_COUNT = 2, 250, 3

_TICKER_RE = re.compile(r"^[A-Z0-9&.\-]{1,15}$")


class TickerNotFound(Exception):
    pass


class SourceUnavailable(Exception):
    pass


def normalize_ticker(raw: str) -> str:
    """'ptt' -> 'PTT.BK'. Anything already containing a dot is kept as-is."""
    ticker = raw.strip().upper()
    if not _TICKER_RE.match(ticker):
        raise ValueError(f"Invalid ticker: {raw!r}")
    return ticker if "." in ticker else f"{ticker}.BK"


def _is_fresh(fetched_at: datetime | None, ttl: timedelta) -> bool:
    return fetched_at is not None and datetime.now(timezone.utc) - fetched_at < ttl


def parse_sma_periods(raw: str | None) -> list[int]:
    """'20,50,200' -> [20, 50, 200]."""
    if not raw:
        return []
    try:
        periods = sorted({int(p) for p in raw.split(",")})
    except ValueError:
        raise ValueError("sma must be numbers separated by commas, e.g. 20,50,200") from None
    if len(periods) > SMA_MAX_COUNT or not all(SMA_MIN <= p <= SMA_MAX for p in periods):
        raise ValueError(f"sma: up to {SMA_MAX_COUNT} periods, each {SMA_MIN}-{SMA_MAX} days")
    return periods


def range_start(range_key: str) -> str:
    """'1y' -> the date one year ago, as YYYY-MM-DD."""
    return (date.today() - timedelta(days=RANGE_DAYS[range_key])).isoformat()


def load_history(ticker: str) -> tuple[list[dict], datetime, bool]:
    """
    All cached daily candles for a ticker (up to 5 years), refreshed from Yahoo when stale.
    Returns (candles oldest-first, when they were fetched, stale?).
    """
    fetched_at, _ = cache.last_fetched(ticker, "prices")
    stale = False

    if not _is_fresh(fetched_at, PRICE_TTL):
        last_date = cache.last_price_date(ticker)
        try:
            # Already have data? Only download from the last stored day onward.
            candles = yahoo.fetch_history(ticker, start=last_date)
        except Exception as exc:
            if fetched_at is None:
                raise SourceUnavailable(str(exc)) from exc
            stale = True  # Yahoo is down: serve what we have
        else:
            if not candles and last_date is None:
                raise TickerNotFound(ticker)
            cache.upsert_prices(ticker, candles)
            fetched_at = cache.mark_fetched(ticker, "prices")

    return cache.get_prices(ticker, since="0000-00-00"), fetched_at, stale


def get_candles(
    ticker: str, range_key: str, sma_raw: str | None = None, rsi_period: int | None = None
) -> dict:
    sma_periods = parse_sma_periods(sma_raw)
    history, fetched_at, stale = load_history(ticker)

    # Indicators use ALL cached history (up to 5 years), so a 200-day line is complete
    # even on a 1-month chart (and RSI has plenty of warm-up). Then everything is cut to the range.
    since = range_start(range_key)

    def in_range(points: list[dict]) -> list[dict]:
        return [p for p in points if p["time"] >= since]

    return {
        "ticker": ticker,
        "range": range_key,
        "updated_at": fetched_at.isoformat(),
        "stale": stale,
        "candles": in_range(history),
        "sma": {str(p): in_range(simple_moving_average(history, p)) for p in sma_periods},
        "rsi": in_range(relative_strength_index(history, rsi_period)) if rsi_period else [],
    }


def get_backtest(ticker: str, strategy: str, range_key: str) -> dict:
    history, _, stale = load_history(ticker)
    return {"ticker": ticker, "range": range_key, "stale": stale,
            **backtest.run_backtest(history, strategy, range_start(range_key))}


def get_forecast(ticker: str, horizon: int, range_key: str) -> dict:
    history, _, stale = load_history(ticker)
    return {"ticker": ticker, "range": range_key, "stale": stale,
            **forecast.run_forecast(history, horizon, range_start(range_key))}


def _rank(query: str, results: list[dict]) -> list[dict]:
    """Exact code match first ('ptt' -> PTT.BK), then codes starting with it, then Yahoo's order."""
    code = query.upper().replace(" ", "")

    def score(item: dict) -> int:
        base = item["ticker"].removesuffix(".BK")
        return 0 if base == code else 1 if base.startswith(code) else 2

    return sorted(results, key=score)  # sorted() is stable: ties keep Yahoo's order


def search(raw_query: str) -> dict:
    query = " ".join(raw_query.split()).lower()  # "  CP   All " -> "cp all"
    if not 1 <= len(query) <= 50:
        raise ValueError("Search text must be 1-50 characters.")

    fetched_at, payload = cache.get_search(query)
    if _is_fresh(fetched_at, SEARCH_TTL):
        return {"query": query, "results": json.loads(payload)}

    try:
        results = _rank(query, yahoo.search(query))[:SEARCH_LIMIT]
    except Exception as exc:
        if payload is not None:
            return {"query": query, "results": json.loads(payload)}  # old results beat none
        raise SourceUnavailable(str(exc)) from exc

    if results:  # don't remember "no results": it may be a temporary Yahoo glitch
        cache.save_search(query, json.dumps(results))
    return {"query": query, "results": results}


def get_stats(ticker: str) -> dict:
    fetched_at, payload = cache.last_fetched(ticker, "stats")
    if _is_fresh(fetched_at, STATS_TTL):
        return {**json.loads(payload), "updated_at": fetched_at.isoformat(), "stale": False}

    try:
        stats = yahoo.fetch_stats(ticker)
    except Exception as exc:
        if payload is None:
            raise SourceUnavailable(str(exc)) from exc
        return {**json.loads(payload), "updated_at": fetched_at.isoformat(), "stale": True}

    if stats is None:
        raise TickerNotFound(ticker)
    stats = {"ticker": ticker, **stats}
    fetched_at = cache.mark_fetched(ticker, "stats", json.dumps(stats))
    return {**stats, "updated_at": fetched_at.isoformat(), "stale": False}


def _watch_item(ticker: str) -> dict:
    """Stats for one watchlist row. One broken stock shouldn't break the whole list."""
    try:
        return get_stats(ticker)
    except (TickerNotFound, SourceUnavailable):
        return {"ticker": ticker, "error": "Price unavailable right now"}


def get_watchlist() -> list[dict]:
    tickers = cache.watchlist_tickers()
    # Fetch in parallel: 10 stocks with cold caches would otherwise take ~10x as long.
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(_watch_item, tickers))


def add_to_watchlist(ticker: str) -> dict:
    current = cache.watchlist_tickers()
    if ticker not in current and len(current) >= WATCHLIST_MAX:
        raise ValueError(f"The watchlist is full ({WATCHLIST_MAX} stocks). Remove one first.")
    stats = get_stats(ticker)  # raises TickerNotFound for made-up tickers -> nothing saved
    cache.add_to_watchlist(ticker)
    return stats


def remove_from_watchlist(ticker: str) -> None:
    cache.remove_from_watchlist(ticker)


# ---------- Paper portfolio (fake money) ----------


def _replay(trades: list[dict]) -> tuple[float, float, dict[str, dict]]:
    """
    Rebuild the portfolio from its trade history.
    Returns (cash, realized profit, holdings) where holdings = {ticker: {shares, cost}}.
    'cost' is what the shares still held cost in total, so average cost = cost / shares.
    Selling uses the average cost: profit = (sell price - average cost) x shares sold.
    """
    cash, realized = STARTING_CASH, 0.0
    holdings: dict[str, dict] = {}
    for t in trades:
        h = holdings.setdefault(t["ticker"], {"shares": 0, "cost": 0.0})
        amount = t["shares"] * t["price"]
        if t["side"] == "buy":
            cash -= amount
            h["shares"] += t["shares"]
            h["cost"] += amount
        else:
            avg_cost = h["cost"] / h["shares"]
            cash += amount
            realized += (t["price"] - avg_cost) * t["shares"]
            h["cost"] -= avg_cost * t["shares"]
            h["shares"] -= t["shares"]
            if h["shares"] == 0:
                del holdings[t["ticker"]]
    return cash, realized, holdings


def _pct(part: float | None, whole: float) -> float | None:
    return round(part / whole * 100, 2) if part is not None and whole else None


def get_portfolio() -> dict:
    trades = cache.list_trades()
    cash, realized, holdings = _replay(trades)

    with ThreadPoolExecutor(max_workers=8) as pool:  # current prices, in parallel
        stats = dict(zip(holdings, pool.map(_watch_item, holdings)))

    positions, holdings_value = [], 0.0
    for ticker, h in holdings.items():
        s = stats[ticker]
        price = s.get("price")
        avg_cost = h["cost"] / h["shares"]
        value = price * h["shares"] if price is not None else None
        unrealized = value - h["cost"] if value is not None else None
        holdings_value += value if value is not None else h["cost"]  # no price: count it at cost
        positions.append({
            "ticker": ticker,
            "name": s.get("name"),
            "shares": h["shares"],
            "avg_cost": round(avg_cost, 2),
            "cost": round(h["cost"], 2),
            "price": price,
            "market_value": round(value, 2) if value is not None else None,
            "unrealized_pl": round(unrealized, 2) if unrealized is not None else None,
            "unrealized_pl_pct": _pct(unrealized, h["cost"]),
        })
    positions.sort(key=lambda p: -(p["market_value"] or p["cost"]))  # biggest first

    total = cash + holdings_value
    return {
        "starting_cash": STARTING_CASH,
        "cash": round(cash, 2),
        "holdings_value": round(holdings_value, 2),
        "total_value": round(total, 2),
        "total_pl": round(total - STARTING_CASH, 2),
        "total_pl_pct": _pct(total - STARTING_CASH, STARTING_CASH),
        "realized_pl": round(realized, 2),
        "positions": positions,
        "trades": [
            {**t, "amount": round(t["shares"] * t["price"], 2)} for t in reversed(trades[-RECENT_TRADES:])
        ],
        "trade_count": len(trades),
    }


def place_trade(ticker: str, side: str, shares: int) -> dict:
    """Buy or sell at the latest price. Refuses if the price is stale, cash is short, or shares are missing."""
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' or 'sell'")
    if not 1 <= shares <= MAX_SHARES_PER_TRADE:
        raise ValueError(f"Shares must be a whole number from 1 to {MAX_SHARES_PER_TRADE:,}.")

    stats = get_stats(ticker)  # unknown ticker -> TickerNotFound (404)
    if stats["stale"] or stats.get("price") is None:
        raise SourceUnavailable("no fresh price")  # don't trade on an old price
    price = stats["price"]

    cash, _, holdings = _replay(cache.list_trades())
    code = ticker.removesuffix(".BK")
    if side == "buy" and shares * price > cash + 1e-6:
        raise ValueError(
            f"Not enough cash: {shares:,} {code} x {price:,.2f} = {shares * price:,.2f} THB, "
            f"but you have {cash:,.2f} THB."
        )
    owned = holdings.get(ticker, {"shares": 0})["shares"]
    if side == "sell" and shares > owned:
        raise ValueError(f"You can't sell {shares:,} {code}: you own {owned:,}.")

    trade = cache.add_trade(ticker, side, shares, price)
    return {"trade": {**trade, "amount": round(shares * price, 2)}, "portfolio": get_portfolio()}


def reset_portfolio() -> None:
    cache.delete_all_trades()
