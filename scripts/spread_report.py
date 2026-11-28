"""Normal spread for each hour of the day, from the saved M1 candles.

Run download_history.py first. MT5 is optional: if it is open, the script also
checks what the candle spread means by comparing it with real ticks.
READ-ONLY: this script never places, changes or closes orders.

Run from the repo folder:
    .venv\\Scripts\\python.exe scripts\\spread_report.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import MetaTrader5 as mt5  # noqa: E402
import pandas as pd  # noqa: E402

from stockman.config import ROOT, load_config, load_env  # noqa: E402
from stockman.history import csv_path  # noqa: E402
from stockman.mt5_client import MT5Error, connect, require_demo  # noqa: E402
from stockman.spread import (  # noqa: E402
    WINDOW_NY_HOURS, looks_fixed, monthly_medians, normal_spread_by_hour, zero_share_by_year,
)

MIN_CANDLES = 100  # fewer candles in an hour = market closed then, not a real 'normal'


def tick_check(symbol: str, last_server_raw: int) -> tuple[float | None, str]:
    """Compare candle spread with real tick spreads over the last 4 trading hours.

    Returns (point size or None, one-line verdict). Needs MT5 open.
    """
    try:
        connect(load_env())
        require_demo()
        info = mt5.symbol_info(symbol)
        end = datetime.fromtimestamp(last_server_raw + 60, tz=timezone.utc)  # server-clock epoch
        start = end - timedelta(hours=4)
        ticks = mt5.copy_ticks_range(symbol, start, end, mt5.COPY_TICKS_INFO)
        bars = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
    except MT5Error as e:
        return None, f"skipped ({e})"
    finally:
        mt5.shutdown()
    if info is None or ticks is None or not len(ticks) or bars is None or not len(bars):
        return (info.point if info else None), "skipped (no tick history returned)"

    tk = pd.DataFrame(ticks)
    tk["minute"] = tk["time"] // 60 * 60
    tk["spr"] = ((tk["ask"] - tk["bid"]) / info.point).round()
    g = tk.groupby("minute")["spr"].agg(["min", "median", "max", "last"])
    j = pd.DataFrame(bars).set_index("time")[["spread"]].join(g, how="inner")
    if j.empty:
        return info.point, "skipped (ticks and candles did not overlap)"
    if (j["min"] == j["max"]).mean() > 0.95:
        return info.point, (f"spread hardly changed within minutes ({tk['spr'].median():.0f} points), "
                            "so it can't tell min from typical. Looks like an artificial demo spread.")
    match = {c: (j["spread"] == j[c]).mean() for c in ["min", "median", "max", "last"]}
    best = max(match, key=match.get)
    return info.point, (f"candle spread = the {best.upper()} tick spread in that minute "
                        f"({match[best]:.0%} of {len(j)} minutes)")


def main() -> int:
    cfg = load_config()
    data_dir = ROOT / cfg["data"]["dir"]
    lookback = cfg["spread"]["lookback_days"]
    print(f"Stockman spread_report  (config v{cfg['config_version']})\n")

    metas = sorted(data_dir.glob("*_download_meta.json"))
    if not metas:
        print("ERROR: no downloaded data. Run scripts\\download_history.py first.")
        return 1
    meta = json.loads(metas[-1].read_text(encoding="utf-8"))
    symbol = meta["symbol"]
    candles = pd.read_csv(csv_path(data_dir, symbol, "M1"),
                          usecols=["time_utc", "spread", "time_server_raw"], parse_dates=["time_utc"])

    as_of = candles["time_utc"].iloc[-1] + pd.Timedelta(minutes=1)
    table = normal_spread_by_hour(candles, as_of, lookback)
    point, verdict = tick_check(symbol, int(candles["time_server_raw"].iloc[-1]))

    print(f"{symbol} on {meta['broker_server']}: last {lookback} days before {as_of:%Y-%m-%d %H:%M} UTC")
    print("Spread in points" + (f" (1 point = {point} in price)" if point else "") + "; * = trading window\n")
    print("  NY hour  Thai winter  Thai summer   median    p90   candles")
    for h, r in table.iterrows():
        mark = "*" if h in WINDOW_NY_HOURS else " "
        n = int(r["candles"])
        if n < MIN_CANDLES:
            print(f" {mark} {h:02d}:00       {(h + 12) % 24:02d}:00        {(h + 11) % 24:02d}:00   "
                  f"(closed: {n} candles)")
            continue
        price = f" (${r['median'] * point:.2f})" if point else ""
        print(f" {mark} {h:02d}:00       {(h + 12) % 24:02d}:00        {(h + 11) % 24:02d}:00   "
              f"{r['median']:>6.0f}{price}  {r['p90']:>5.0f}  {n:>8,}")

    print("\nCHECKS")
    win = table.loc[list(WINDOW_NY_HOURS)]
    open_hours = table[table["candles"] >= MIN_CANDLES]
    widest = int(open_hours["median"].idxmax())
    print(f"  Trading-window median spread: {win['median'].median():.0f} points; widest open hour "
          f"{widest:02d}:00 NY = {(widest + 12) % 24:02d}:00 Thai winter ({open_hours['median'].max():.0f} points)")
    months = monthly_medians(candles, as_of, lookback)
    if len(months) > 1 and months.max() >= 2 * months.min():
        print(f"  WARNING: spread level changed a lot inside the look-back "
              f"(monthly medians {months.min():.0f} to {months.max():.0f} points: "
              + ", ".join(f"{m} {v:.0f}" for m, v in months.items()) + ")")
    zeros = zero_share_by_year(candles)
    missing = [str(y) for y, s in zeros.items() if s > 0.95]
    if missing:
        print(f"  No spread recorded in: {missing[0]}-{missing[-1]} ({len(missing)} years); "
              "backtests can't use real costs there")
    print(f"  Candle spread vs real ticks: {verdict}")
    if looks_fixed(table):
        print("  WARNING: the spread barely changes hour to hour. This server's spreads look artificial;")
        print("           use your real broker's data for backtest costs.")

    out = data_dir / f"{symbol}_spread_by_hour.csv"
    saved = table.reset_index()
    saved["config_version"] = cfg["config_version"]
    saved["as_of_utc"] = as_of.isoformat()
    saved["lookback_days"] = lookback
    saved.to_csv(out, index=False)
    print(f"\nSaved {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
