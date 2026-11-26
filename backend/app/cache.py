"""SQLite storage: a cache of fetched prices/stats (so we don't re-download them) and the watchlist."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cache.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,          -- YYYY-MM-DD
    open   REAL, high REAL, low REAL, close REAL,
    volume INTEGER,
    PRIMARY KEY (ticker, date)
);
-- When did we last fetch something for a ticker? ('prices' or 'stats')
CREATE TABLE IF NOT EXISTS fetches (
    ticker     TEXT NOT NULL,
    kind       TEXT NOT NULL,
    fetched_at TEXT NOT NULL,      -- ISO timestamp, UTC
    payload    TEXT,               -- JSON for 'stats', NULL for 'prices'
    PRIMARY KEY (ticker, kind)
);
-- Search results, keyed by the (lower-cased) text the user typed.
CREATE TABLE IF NOT EXISTS searches (
    query      TEXT PRIMARY KEY,
    fetched_at TEXT NOT NULL,      -- ISO timestamp, UTC
    results    TEXT NOT NULL       -- JSON list
);
-- Stocks the user chose to follow. Not a cache: never expires.
CREATE TABLE IF NOT EXISTS watchlist (
    ticker   TEXT PRIMARY KEY,
    added_at TEXT NOT NULL         -- ISO timestamp, UTC
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        with conn:  # commits on success, rolls back on error
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)


def last_fetched(ticker: str, kind: str) -> tuple[datetime | None, str | None]:
    with connect() as conn:
        row = conn.execute(
            "SELECT fetched_at, payload FROM fetches WHERE ticker = ? AND kind = ?",
            (ticker, kind),
        ).fetchone()
    if row is None:
        return None, None
    return datetime.fromisoformat(row["fetched_at"]), row["payload"]


def mark_fetched(ticker: str, kind: str, payload: str | None = None) -> datetime:
    now = datetime.now(timezone.utc)
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO fetches (ticker, kind, fetched_at, payload) VALUES (?, ?, ?, ?)",
            (ticker, kind, now.isoformat(), payload),
        )
    return now


def get_search(query: str) -> tuple[datetime | None, str | None]:
    with connect() as conn:
        row = conn.execute("SELECT fetched_at, results FROM searches WHERE query = ?", (query,)).fetchone()
    if row is None:
        return None, None
    return datetime.fromisoformat(row["fetched_at"]), row["results"]


def save_search(query: str, results: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO searches (query, fetched_at, results) VALUES (?, ?, ?)",
            (query, datetime.now(timezone.utc).isoformat(), results),
        )


def watchlist_tickers() -> list[str]:
    with connect() as conn:
        rows = conn.execute("SELECT ticker FROM watchlist ORDER BY added_at").fetchall()
    return [r["ticker"] for r in rows]


def add_to_watchlist(ticker: str) -> None:
    with connect() as conn:
        conn.execute(  # adding twice keeps the original position in the list
            "INSERT OR IGNORE INTO watchlist (ticker, added_at) VALUES (?, ?)",
            (ticker, datetime.now(timezone.utc).isoformat()),
        )


def remove_from_watchlist(ticker: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))


def last_price_date(ticker: str) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT MAX(date) AS d FROM prices WHERE ticker = ?", (ticker,)).fetchone()
    return row["d"]


def upsert_prices(ticker: str, candles: list[dict]) -> None:
    with connect() as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO prices (ticker, date, open, high, low, close, volume)
               VALUES (:ticker, :time, :open, :high, :low, :close, :volume)""",
            [{**c, "ticker": ticker} for c in candles],
        )


def get_prices(ticker: str, since: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT date AS time, open, high, low, close, volume FROM prices
               WHERE ticker = ? AND date >= ? ORDER BY date""",
            (ticker, since),
        ).fetchall()
    return [dict(r) for r in rows]
