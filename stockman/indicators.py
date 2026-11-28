"""Indicators: EMA, RSI, ATR, ADX, matching MetaTrader 5's own formulas.

Plain-word meaning:
  EMA  average price that weights recent candles more (trend direction)
  RSI  0-100 score of how much price rose vs fell lately (momentum)
  ATR  average candle size including gaps (how wild the market is)
  ADX  0-100 trend strength, no direction (+DI / -DI give the direction)

"Wilder smoothing" is a slow average: new = (old x (n-1) + value) / n.
Values need warm-up: use 200+ candles before the first value you trust.
Each function works on finished candles only; the caller must not pass the
candle that is still forming.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(close: pd.Series, n: int) -> pd.Series:
    """Exponential moving average, like MT5 iMA(MODE_EMA): starts at the first price."""
    return close.ewm(span=n, adjust=False).mean()


def wilder(x: pd.Series, n: int) -> pd.Series:
    """Wilder smoothing: first value = simple average of the first n values,
    then new = (previous x (n-1) + value) / n."""
    x = x.astype(float)
    valid = x.notna().to_numpy().nonzero()[0]
    out = pd.Series(np.nan, index=x.index)
    if len(valid) < n:
        return out
    i0 = valid[0]
    seed = i0 + n - 1
    s = x.copy()
    s.iloc[:seed] = np.nan
    s.iloc[seed] = x.iloc[i0:seed + 1].mean()
    return s.ewm(alpha=1.0 / n, adjust=False).mean()  # = (prev*(n-1) + x)/n


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """RSI with Wilder smoothing, like MT5 iRSI."""
    diff = close.diff()
    gain = wilder(diff.clip(lower=0), n)
    loss = wilder((-diff).clip(lower=0), n)
    out = 100 - 100 / (1 + gain / loss)
    out = out.where(loss != 0, np.where(gain != 0, 100.0, 50.0))  # MT5's rule when no losses
    return out.where(gain.notna())


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Candle range including any gap from the previous close. First candle has none."""
    prev = close.shift(1)
    return pd.concat([high, prev], axis=1).max(axis=1, skipna=False) - \
        pd.concat([low, prev], axis=1).min(axis=1, skipna=False)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14, method: str = "wilder") -> pd.Series:
    """Average true range. method="wilder" (Wilder's original) or "sma" (plain average,
    which is what MT5's built-in iATR uses)."""
    tr = true_range(high, low, close)
    if method == "sma":
        return tr.rolling(n).mean()
    return wilder(tr, n)


def adx_wilder(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.DataFrame:
    """ADX with Wilder smoothing, like MT5 iADXWilder (NOT the plain iADX).

    Returns columns adx, pdi (+DI, buyers' strength), ndi (-DI, sellers' strength).
    """
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0).where(up.notna())
    minus_dm = down.where((down > up) & (down > 0), 0.0).where(down.notna())
    tr_s = wilder(true_range(high, low, close), n)
    pdi = (100 * wilder(plus_dm, n) / tr_s).where(tr_s != 0, 0.0).where(tr_s.notna())
    ndi = (100 * wilder(minus_dm, n) / tr_s).where(tr_s != 0, 0.0).where(tr_s.notna())
    total = pdi + ndi
    dx = (100 * (pdi - ndi).abs() / total).where(total != 0, 0.0).where(total.notna())
    return pd.DataFrame({"adx": wilder(dx, n), "pdi": pdi, "ndi": ndi})


def add_indicators(df: pd.DataFrame, n: int = 14, emas: tuple[int, ...] = (20, 50, 200)) -> pd.DataFrame:
    """Return a copy of a candle frame (open/high/low/close) with the plan's fixed set:
    ema20, ema50, ema200, rsi14, atr14 (Wilder), atr14_sma, adx14, pdi14, ndi14."""
    out = df.copy()
    for p in emas:
        out[f"ema{p}"] = ema(df["close"], p)
    out[f"rsi{n}"] = rsi(df["close"], n)
    out[f"atr{n}"] = atr(df["high"], df["low"], df["close"], n, "wilder")
    out[f"atr{n}_sma"] = atr(df["high"], df["low"], df["close"], n, "sma")
    a = adx_wilder(df["high"], df["low"], df["close"], n)
    out[f"adx{n}"], out[f"pdi{n}"], out[f"ndi{n}"] = a["adx"], a["pdi"], a["ndi"]
    return out
