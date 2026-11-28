"""Normal spread for each hour of the day.

The spread filter allows a trade only if the current spread is at most 1.5x the
normal spread for that hour, and the backtest needs realistic costs per hour.

Hours are New York clock hours: gold's daily rollover (wide spreads) is always
at 17:00 New York, and the trading window 14:00-23:30 Thailand time (winter,
1h earlier in US summer time) is always 02:00-11:30 New York.

Backtest and live use the same function; `as_of` makes sure only candles from
BEFORE that moment are used (no future data).
"""
from __future__ import annotations

import pandas as pd

from .server_time import NY_NAME

# Trading window in New York hours (start inclusive, end exclusive; 11:30 rounds up)
WINDOW_NY_HOURS = range(2, 12)


def normal_spread_by_hour(candles: pd.DataFrame, as_of: pd.Timestamp, lookback_days: int) -> pd.DataFrame:
    """Typical spread (points) per New York hour over the `lookback_days` before `as_of`.

    candles: needs columns time_utc (tz-aware) and spread (points).
    Spread 0 means "not recorded" and is ignored.
    Returns one row per hour 0-23: median, p10, p90, candles (count).
    """
    t = candles["time_utc"]
    w = candles[(t >= as_of - pd.Timedelta(days=lookback_days)) & (t < as_of) & (candles["spread"] > 0)]
    hour = w["time_utc"].dt.tz_convert(NY_NAME).dt.hour
    g = w.groupby(hour)["spread"]
    table = pd.DataFrame({
        "median": g.median(),
        "p10": g.quantile(0.10),
        "p90": g.quantile(0.90),
        "candles": g.size(),
    }).reindex(range(24))
    table.index.name = "hour_ny"
    table["candles"] = table["candles"].fillna(0).astype(int)
    return table


def looks_fixed(table: pd.DataFrame, min_candles: int = 100) -> bool:
    """True if most hours have p10 == p90, i.e. the spread barely ever changes
    (typical of demo servers with artificial spreads)."""
    busy = table[table["candles"] >= min_candles]
    return len(busy) > 0 and (busy["p10"] == busy["p90"]).mean() >= 0.8


def monthly_medians(candles: pd.DataFrame, as_of: pd.Timestamp, lookback_days: int) -> pd.Series:
    """Median spread per calendar month inside the look-back (zeros ignored).
    A big jump between months means the broker changed its spread level."""
    t = candles["time_utc"]
    w = candles[(t >= as_of - pd.Timedelta(days=lookback_days)) & (t < as_of) & (candles["spread"] > 0)]
    return w.groupby(w["time_utc"].dt.strftime("%Y-%m"))["spread"].median()


def zero_share_by_year(candles: pd.DataFrame) -> pd.Series:
    """Share of candles per year with spread 0 (not recorded)."""
    return (candles["spread"] == 0).groupby(candles["time_utc"].dt.year).mean()
