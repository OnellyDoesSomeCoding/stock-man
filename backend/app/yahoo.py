"""Thin wrapper around yfinance. The only file that talks to Yahoo."""

import math
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf


def _num(value, digits: int = 2) -> float | None:
    """Round a number; turn missing/NaN values into None (JSON null)."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), digits)


def fetch_history(ticker: str, start: str | None = None) -> list[dict]:
    """Daily candles. With no start date, grab 5 years (first fetch for a ticker)."""
    t = yf.Ticker(ticker)
    if start:
        df = t.history(start=start, interval="1d", auto_adjust=False)
    else:
        df = t.history(period="5y", interval="1d", auto_adjust=False)

    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    return [
        {
            "time": idx.strftime("%Y-%m-%d"),
            "open": _num(row["Open"]),
            "high": _num(row["High"]),
            "low": _num(row["Low"]),
            "close": _num(row["Close"]),
            "volume": int(row["Volume"]),
        }
        for idx, row in df.iterrows()
    ]


def fetch_stats(ticker: str) -> dict | None:
    """Headline numbers for the stats card. Returns None if Yahoo has no price."""
    info = yf.Ticker(ticker).info or {}
    price = info.get("regularMarketPrice") or info.get("currentPrice")
    if price is None:
        return None

    prev = info.get("regularMarketPreviousClose") or info.get("previousClose")
    change = price - prev if prev else None
    return {
        "name": info.get("longName") or info.get("shortName"),
        "currency": info.get("currency"),
        "price": _num(price),
        "previous_close": _num(prev),
        "change": _num(change),
        "change_pct": _num(change / prev * 100) if change is not None else None,
        "market_cap": info.get("marketCap"),
        "pe_ratio": _num(info.get("trailingPE")),
    }


def _is_plain_set_stock(symbol: str) -> bool:
    """PTT.BK yes. PTT-R.BK (NVDR twin), -F (foreign board), -W1 (warrant): no."""
    return symbol.endswith(".BK") and "-" not in symbol.removesuffix(".BK")


def _clean_name(symbol: str, short: str | None) -> str | None:
    """Yahoo's short names look like 'PTTEP_PTT EXPLORATION AND': drop the 'PTTEP_' part."""
    if not short:
        return None
    prefix = symbol.removesuffix(".BK") + "_"
    return short.removeprefix(prefix).strip() or None


def search(query: str) -> list[dict]:
    """
    Thai stocks matching a company name or code.
    Yahoo has two search APIs, each with blind spots, so we ask both (in parallel)
    and keep only stocks listed on SET.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        quick = pool.submit(lambda: yf.Search(query, max_results=10, news_count=0, lists_count=0).quotes)
        # Lookup returns worldwide matches; Thai ones can rank low, so ask for plenty.
        lookup = pool.submit(lambda: yf.Lookup(query).get_stock(count=250))

    candidates = []  # (symbol, full name or None, short name or None)
    errors = []
    try:
        for q in quick.result():
            if q.get("quoteType") == "EQUITY":
                candidates.append((q["symbol"], q.get("longname"), q.get("shortname")))
    except Exception as exc:
        errors.append(exc)
    try:
        for symbol, row in lookup.result().iterrows():
            candidates.append((symbol, None, row.get("shortName")))
    except Exception as exc:
        errors.append(exc)
    if len(errors) == 2:
        raise errors[0]

    names: dict[str, str | None] = {}  # keeps first-seen order = Yahoo's relevance order
    for symbol, long_name, short_name in candidates:
        if not _is_plain_set_stock(symbol):
            continue
        if symbol not in names:
            names[symbol] = long_name or _clean_name(symbol, short_name)
        elif long_name:  # a full name beats a cleaned-up short one
            names[symbol] = long_name
    return [{"ticker": symbol, "name": name} for symbol, name in names.items()]
