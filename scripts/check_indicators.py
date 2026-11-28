"""Gate 1 check: do Stockman's indicators match MT5's own values?

Step 1: in MT5, run the script Stockman > StockmanExportIndicators on a gold chart.
Step 2: run this (MT5 does not need to be open for this step):
    .venv\\Scripts\\python.exe scripts\\check_indicators.py

Compares the last 20 finished M15 and H4 candles that both sides have.
READ-ONLY: this script never places, changes or closes orders.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from stockman.config import ROOT, load_config  # noqa: E402
from stockman.history import csv_path  # noqa: E402
from stockman.indicators import add_indicators  # noqa: E402

EXPORT = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal" / "Common" / "Files" / "stockman_indicators.csv"
N_COMPARE = 20
PRICE_TOL = 0.005   # half a cent: price-based indicators (EMA, ATR)
SCORE_TOL = 0.01    # 0-100 scores (RSI, ADX, DI)

# (ours, MT5's, tolerance, needed for the gate?)
PAIRS = [
    ("ema20", "ema20", PRICE_TOL, True),
    ("ema50", "ema50", PRICE_TOL, True),
    ("ema200", "ema200", PRICE_TOL, True),
    ("rsi14", "rsi14", SCORE_TOL, True),
    ("adx14", "adxw14", SCORE_TOL, True),
    ("pdi14", "pdi14", SCORE_TOL, True),
    ("ndi14", "ndi14", SCORE_TOL, True),
    ("atr14_sma", "atr14", PRICE_TOL, False),   # MT5's iATR = plain average
    ("atr14", "atr14", PRICE_TOL, False),       # Wilder ATR (the plan's choice)
    ("adx14", "adx14_plain", SCORE_TOL, False), # MT5's plain iADX is a different formula
]


def main() -> int:
    cfg = load_config()
    data_dir = ROOT / cfg["data"]["dir"]
    print(f"Stockman check_indicators  (config v{cfg['config_version']})\n")

    if not EXPORT.exists():
        print(f"ERROR: {EXPORT} not found.\nRun the MT5 script Stockman > StockmanExportIndicators first.")
        return 1
    mt = pd.read_csv(EXPORT)
    symbol = mt["symbol"].iloc[0]
    print(f"MT5 export: {symbol}, written {datetime.fromtimestamp(EXPORT.stat().st_mtime):%Y-%m-%d %H:%M} (PC time)")

    gate_ok, rows_out = True, []
    for tf in ["M15", "H4"]:
        m = mt[mt["tf"] == tf].copy()
        m = m[m["time_server_raw"] < m["time_server_raw"].max()]  # MT5's newest candle may still be forming
        ours = pd.read_csv(csv_path(data_dir, symbol, tf),
                           usecols=["time_utc", "open", "high", "low", "close", "time_server_raw"])
        ours = add_indicators(ours)
        j = m.merge(ours, on="time_server_raw", suffixes=("_mt5", "")).tail(N_COMPARE)
        if len(j) < N_COMPARE:
            print(f"\n{tf}: only {len(j)} shared candles. Re-run download_history.py, then this.")
            gate_ok = False
            continue

        print(f"\n{tf}: last {len(j)} shared candles, {j['time_utc'].iloc[0][:16]} -> {j['time_utc'].iloc[-1][:16]} UTC")
        close_diff = (j["close"] - j["close_mt5"]).abs().max()
        print(f"  Same candles?  close prices max difference {close_diff:.5f}"
              + ("  OK" if close_diff < 1e-6 else "  MISMATCH: data differs from MT5's chart"))
        gate_ok &= close_diff < 1e-6
        print(f"  {'ours':<10} {'MT5':<12} {'max diff':>10}  result")
        for ours_col, mt_col, tol, needed in PAIRS:
            diff = (j[ours_col] - j[mt_col + ("_mt5" if mt_col in ours.columns else "")]).abs().max()
            ok = diff <= tol
            label = ("PASS" if ok else "FAIL") if needed else ("matches" if ok else "differs") + " (info)"
            print(f"  {ours_col:<10} {mt_col:<12} {diff:>10.5f}  {label}")
            if needed:
                gate_ok &= bool(ok)
        keep = j[["time_utc", "time_server_raw"]].copy()
        keep["tf"] = tf
        for ours_col, mt_col, _, _ in PAIRS:
            keep[f"{ours_col}_ours"] = j[ours_col]
            keep[f"{mt_col}_mt5"] = j[mt_col + ("_mt5" if mt_col in ours.columns else "")]
        rows_out.append(keep.loc[:, ~keep.columns.duplicated()])

        last = j.iloc[-1]
        print(f"  Example, candle {last['time_utc'][:16]} UTC: EMA20 {last['ema20']:.2f} vs MT5 "
              f"{last['ema20_mt5']:.2f}; RSI {last['rsi14']:.2f} vs {last['rsi14_mt5']:.2f}; "
              f"ADX {last['adx14']:.2f} vs {last['adxw14']:.2f}")

    if rows_out:
        out = data_dir / f"{symbol}_indicator_check.csv"
        res = pd.concat(rows_out, ignore_index=True)
        res["config_version"] = cfg["config_version"]
        res.to_csv(out, index=False)
        print(f"\nSaved the compared values to {out.relative_to(ROOT)}")
    print(f"\nGATE 1 (indicators match MT5 on {N_COMPARE} values): {'PASS' if gate_ok else 'FAIL'}")
    return 0 if gate_ok else 1


if __name__ == "__main__":
    sys.exit(main())
