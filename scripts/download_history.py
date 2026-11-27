"""Download gold candles (M1, M15, H4) as far back as the broker allows.

Saves data/<SYMBOL>_<TF>.csv with times in UTC, plus a gap report per timeframe.
Re-running keeps bars from earlier runs, so history only grows.
READ-ONLY: this script never places, changes or closes orders.

Run from the repo folder:
    .venv\\Scripts\\python.exe scripts\\download_history.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import MetaTrader5 as mt5  # noqa: E402
import pandas as pd  # noqa: E402

from stockman.config import ROOT, load_config, load_env  # noqa: E402
from stockman.history import (  # noqa: E402
    TF_MINUTES, csv_path, fetch_raw, find_gaps, merge_with_saved, sanity_problems, to_utc_frame,
)
from stockman.mt5_client import (  # noqa: E402
    MT5Error, connect, find_gold_symbol, measure_server_offset, require_demo,
)
from stockman.server_time import detect_model, offset_minutes_at, weekly_opens  # noqa: E402


def pick_timezone(cfg_value: str, raw: dict[str, pd.DataFrame], offset_minutes: int, now: datetime):
    """Return (model, scores). Uses the finest timeframe with the most weekends."""
    series = [
        pd.to_datetime(df["time"].astype("int64"), unit="s")
        for tf, df in raw.items() if TF_MINUTES[tf] <= 60 and len(df)
    ]
    if not series:
        raise MT5Error("Need M1 or M15 data to detect the server time zone.")
    best = max(series, key=lambda s: len(weekly_opens(s)))
    model, scores = detect_model(best, offset_minutes, now)
    if cfg_value != "auto":
        model = cfg_value
        if offset_minutes_at(model, now) != offset_minutes:
            print(f"  WARNING: config says {model}, which does not match today's offset.")
    return model, scores


def main() -> int:
    cfg = load_config()
    dcfg = cfg["data"]
    data_dir = ROOT / dcfg["dir"]
    data_dir.mkdir(exist_ok=True)
    print(f"Stockman download_history  (config v{cfg['config_version']})\n")

    try:
        connect(load_env())
        acc = require_demo()
        symbol = find_gold_symbol(cfg["mt5"]["symbol_candidates"])
        info = mt5.symbol_info(symbol)
        term = mt5.terminal_info()
        off = measure_server_offset(symbol)
        now = datetime.now(timezone.utc)
        print(f"Symbol {symbol} on {acc.server}; server clock {off.label} ({off.method})")
        if off.note:
            print(f"  NOTE: {off.note}")

        # 1) Download raw bars (server clock), merged with anything saved before.
        print("\nDOWNLOADING")
        raw, kept_old, fetched = {}, {}, {}
        for tf in dcfg["timeframes"]:
            new = fetch_raw(symbol, tf, dcfg["chunk_days"][tf], dcfg["stop_after_empty_chunks"])
            fetched[tf] = len(new)
            raw[tf], kept_old[tf] = merge_with_saved(new, csv_path(data_dir, symbol, tf))
            print(f"  {tf:>3}: {len(new):>10,} bars from broker"
                  + (f", +{kept_old[tf]:,} kept from earlier runs" if kept_old[tf] else ""))
            if term.maxbars and len(new) >= 0.95 * term.maxbars:
                print(f"       WARNING: hit MT5's 'Max bars in chart' limit ({term.maxbars:,}). "
                      "See instructions to raise it.")

        # 2) Work out how the server clock maps to UTC.
        model, scores = pick_timezone(cfg["mt5"]["server_timezone"], raw, off.minutes, now)
        print("\nSERVER TIME ZONE  (weekly open should land on the same New York time every week)")
        for s in scores:
            share = "n/a" if s["share"] != s["share"] else f"{s['share']:.0%}"
            mark = "  <- using" if s["model"] == model else ""
            print(f"  {s['model']:<15} same NY open time in {share:>4} of {s['weeks']} weeks "
                  f"(usual open {s['ny_open']} NY){mark}")

        # 3) Convert, check, save.
        summary = {}
        for tf, r in raw.items():
            df, dropped = to_utc_frame(r, model)
            print(f"\n{tf}: {len(df):,} bars, {df['time_utc'].iloc[0]:%Y-%m-%d %H:%M} -> "
                  f"{df['time_utc'].iloc[-1]:%Y-%m-%d %H:%M} UTC"
                  f"  (~{(df['time_utc'].iloc[-1] - df['time_utc'].iloc[0]).days / 365.25:.1f} years)")
            if dropped:
                print(f"  WARNING: {dropped} bars had impossible server times and were dropped")
            problems = {k: v for k, v in sanity_problems(df).items() if v}
            print(f"  Bad bars: {problems if problems else 'none'}")

            gaps = find_gaps(df["time_utc"], tf)
            if len(gaps):
                counts = gaps.groupby("kind").agg(n=("hours", "size"), hours=("hours", "sum"))
                print("  Gaps (stretches with no bars):")
                for kind, c in counts.iterrows():
                    print(f"    {kind:<22} {int(c.n):>6,} gaps, {c.hours:>9,.1f} hours total")
                odd = gaps[gaps["kind"].isin(["other (check)", "long weekend/holiday"])]
                if len(odd):
                    print("  Biggest unusual gaps (start in New York time):")
                    for _, g in odd.nlargest(8, "hours").iterrows():
                        print(f"    {g.start_ny}  {g.hours:>7.1f} h  {g.kind}")
            else:
                print("  Gaps: none")

            path = csv_path(data_dir, symbol, tf)
            df.to_csv(path, index=False, float_format=f"%.{info.digits}f")
            gaps.to_csv(data_dir / f"{symbol}_{tf}_gaps.csv", index=False)
            print(f"  Saved {path.relative_to(ROOT)} (+ _gaps.csv)")
            summary[tf] = {
                "bars": len(df), "from_broker": fetched[tf], "kept_from_earlier_runs": kept_old[tf],
                "first_utc": str(df["time_utc"].iloc[0]), "last_utc": str(df["time_utc"].iloc[-1]),
                "gaps_by_kind": gaps["kind"].value_counts().to_dict() if len(gaps) else {},
            }

        meta = {
            "config_version": cfg["config_version"],
            "downloaded_at_utc": now.isoformat(timespec="seconds"),
            "symbol": symbol,
            "broker_server": acc.server,
            "server_offset_now": off.label,
            "server_offset_method": off.method,
            "server_timezone_model": model,
            "timezone_scores": scores,
            "terminal_maxbars": term.maxbars,
            "timeframes": summary,
        }
        meta_path = data_dir / f"{symbol}_download_meta.json"
        meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
        print(f"\nDone. Details in {meta_path.relative_to(ROOT)}")
        return 0
    except MT5Error as e:
        print(f"\nERROR: {e}")
        return 1
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
