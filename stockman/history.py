"""Download candle history from MT5, convert to UTC, save, and check for gaps."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

from .server_time import NY_NAME, to_utc_periods

TIMEFRAMES = {"M1": mt5.TIMEFRAME_M1, "M15": mt5.TIMEFRAME_M15, "H4": mt5.TIMEFRAME_H4}
TF_MINUTES = {"M1": 1, "M15": 15, "H4": 240}
RAW_COLS = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]


def fetch_raw(symbol: str, tf_name: str, chunk_days: int, stop_after_empty: int, log=print) -> pd.DataFrame:
    """Walk back in time chunk by chunk until the broker has nothing older.

    Returned 'time' is the raw MT5 value: seconds on the SERVER clock.
    """
    tf = TIMEFRAMES[tf_name]
    end = datetime.now(timezone.utc) + timedelta(days=2)  # server clock can be ahead of UTC
    floor = datetime(1990, 1, 1, tzinfo=timezone.utc)
    step = timedelta(days=chunk_days)
    frames, empty_run, total = [], 0, 0
    oldest = None  # oldest bar time received so far

    while end > floor:
        start = end - step
        rates = None
        for _ in range(3):  # MT5 may need a moment to pull history from the server
            rates = mt5.copy_rates_range(symbol, tf, start, end)
            if rates is not None and len(rates):
                break
            time.sleep(1.0)
        # Past the start of history MT5 keeps returning the same oldest bar,
        # so a chunk only counts if it reaches further back than before.
        if rates is None or not len(rates) or (oldest is not None and rates["time"].min() >= oldest):
            empty_run += 1
            if empty_run >= stop_after_empty:
                break
        else:
            empty_run = 0
            oldest = int(rates["time"].min())
            frames.append(pd.DataFrame(rates)[RAW_COLS])
            total += len(rates)
            log(f"    {tf_name}: back to {start:%Y-%m-%d}, {total:,} bars so far", end="\r")
        end = start
    log(" " * 70, end="\r")

    if not frames:
        return pd.DataFrame(columns=RAW_COLS)
    df = pd.concat(frames, ignore_index=True)
    return df.drop_duplicates("time", keep="last").sort_values("time").reset_index(drop=True)


def csv_path(data_dir: Path, symbol: str, tf_name: str) -> Path:
    return data_dir / f"{symbol}_{tf_name}.csv"


def merge_with_saved(new_raw: pd.DataFrame, path: Path) -> tuple[pd.DataFrame, int]:
    """Keep bars saved on earlier runs that the broker no longer serves.

    Returns (merged raw frame, number of bars that came only from the old file).
    """
    if not path.exists():
        return new_raw, 0
    old = pd.read_csv(path)
    old = old.rename(columns={"time_server_raw": "time"})[RAW_COLS]
    only_old = int((~old["time"].isin(new_raw["time"])).sum())
    merged = pd.concat([old, new_raw], ignore_index=True)
    merged = merged.drop_duplicates("time", keep="last").sort_values("time").reset_index(drop=True)
    return merged, only_old


def to_utc_frame(raw: pd.DataFrame, periods: list[dict]) -> tuple[pd.DataFrame, int]:
    """Raw MT5 bars -> frame with time_utc first. Returns (frame, bars dropped)."""
    server = pd.to_datetime(raw["time"].astype("int64"), unit="s").reset_index(drop=True)
    out = pd.DataFrame({"time_utc": to_utc_periods(server, periods)})
    for c in RAW_COLS[1:]:
        out[c] = raw[c].values
    out["time_server_raw"] = raw["time"].astype("int64").values
    bad = out["time_utc"].isna()
    return out[~bad].reset_index(drop=True), int(bad.sum())


def sanity_problems(df: pd.DataFrame) -> dict[str, int]:
    body_hi = df[["open", "close"]].max(axis=1)
    body_lo = df[["open", "close"]].min(axis=1)
    return {
        "duplicate times": int(df["time_utc"].duplicated().sum()),
        "high below open/close": int((df["high"] < body_hi).sum()),
        "low above open/close": int((df["low"] > body_lo).sum()),
        "zero/negative prices": int((df[["open", "high", "low", "close"]] <= 0).any(axis=1).sum()),
    }


def find_gaps(times_utc: pd.Series, tf_name: str) -> pd.DataFrame:
    """List every stretch of missing bars and label why it is (probably) missing."""
    step = pd.Timedelta(minutes=TF_MINUTES[tf_name])
    t = pd.Series(times_utc).reset_index(drop=True)
    idx = t.index[t.diff() > step]
    if len(idx) == 0:
        return pd.DataFrame(columns=["gap_start_utc", "gap_end_utc", "missing_bars", "hours", "start_ny", "kind"])

    start = t.iloc[idx - 1].reset_index(drop=True) + step   # first missing bar
    end = t.iloc[idx].reset_index(drop=True)                 # first bar after the gap
    dur = end - start
    g = pd.DataFrame({
        "gap_start_utc": start,
        "gap_end_utc": end,
        "missing_bars": (dur / step).astype(int),
        "hours": (dur / pd.Timedelta(hours=1)).round(2),
    })

    s_ny = start.dt.tz_convert(NY_NAME)
    e_ny = end.dt.tz_convert(NY_NAME)
    g["start_ny"] = s_ny.dt.strftime("%a %Y-%m-%d %H:%M")

    days_span = (e_ny.dt.normalize().dt.tz_localize(None) - s_ny.dt.normalize().dt.tz_localize(None)).dt.days
    covers_saturday = days_span >= (5 - s_ny.dt.day_of_week) % 7
    start_min = s_ny.dt.hour * 60 + s_ny.dt.minute
    near_daily_close = start_min.between(16 * 60, 18 * 60) & (dur <= pd.Timedelta(hours=2))

    g["kind"] = np.select(
        [
            covers_saturday & (dur <= pd.Timedelta(hours=54)),
            covers_saturday,
            near_daily_close,
            dur <= pd.Timedelta(minutes=30),
        ],
        ["weekend", "long weekend/holiday", "daily break", "short (no trades)"],
        default="other (check)",
    )
    return g
