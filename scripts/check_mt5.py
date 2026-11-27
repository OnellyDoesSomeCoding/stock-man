"""Check the MT5 connection: account, gold symbol details, server time, spread.

READ-ONLY: this script never places, changes or closes orders.

Run from the repo folder:
    .venv\\Scripts\\python.exe scripts\\check_mt5.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import MetaTrader5 as mt5  # noqa: E402

from stockman.config import load_config, load_env  # noqa: E402
from stockman.mt5_client import (  # noqa: E402
    MT5Error, connect, find_gold_symbol, measure_server_offset, require_demo,
)
from stockman.server_time import CANDIDATES, fixed_model, offset_minutes_at  # noqa: E402

TRADE_MODES = {
    mt5.SYMBOL_TRADE_MODE_DISABLED: "disabled",
    mt5.SYMBOL_TRADE_MODE_LONGONLY: "buy only",
    mt5.SYMBOL_TRADE_MODE_SHORTONLY: "sell only",
    mt5.SYMBOL_TRADE_MODE_CLOSEONLY: "close only",
    mt5.SYMBOL_TRADE_MODE_FULL: "full (buy and sell)",
}


def row(label: str, value) -> None:
    print(f"  {label:<24}: {value}")


def main() -> int:
    cfg = load_config()
    print(f"Stockman check_mt5  (config v{cfg['config_version']})\n")
    try:
        connect(load_env())

        acc = require_demo()
        print("ACCOUNT")
        row("Type", "DEMO")
        row("Broker", acc.company)
        row("Server", acc.server)
        row("Balance", f"{acc.balance:,.2f} {acc.currency}")
        row("Equity", f"{acc.equity:,.2f} {acc.currency}")
        row("Currency", acc.currency)
        row("Leverage", f"1:{acc.leverage}")

        symbol = find_gold_symbol(cfg["mt5"]["symbol_candidates"])
        info = mt5.symbol_info(symbol)
        per_dollar = info.trade_tick_value / info.trade_tick_size  # money per $1 move, 1 lot
        print(f"\nGOLD SYMBOL: {symbol}  ({info.description})")
        row("Price digits", f"{info.digits}  (1 point = {info.point})")
        row("Contract size", f"{info.trade_contract_size:g} per 1.00 lot")
        row("Tick size", f"{info.trade_tick_size}  (smallest price step)")
        row("Tick value", f"{info.trade_tick_value:g} {acc.currency} per tick, per 1.00 lot")
        if info.trade_tick_value_profit != info.trade_tick_value_loss:
            row("  (profit / loss)", f"{info.trade_tick_value_profit:g} / {info.trade_tick_value_loss:g}")
        row("$1 gold move =", f"{per_dollar:,.2f} {acc.currency} per 1.00 lot, "
                              f"{per_dollar * info.volume_min:,.2f} per {info.volume_min} lot")
        row("Min lot / lot step", f"{info.volume_min} / {info.volume_step}")
        row("Max lot", info.volume_max)
        row("Stops level", f"{info.trade_stops_level} points "
                           f"(= {info.trade_stops_level * info.point:.{info.digits}f} in price)")
        row("Freeze level", f"{info.trade_freeze_level} points")
        row("Spread type", "floating" if info.spread_float else "fixed")
        row("Trading allowed", TRADE_MODES.get(info.trade_mode, info.trade_mode))
        row("Margin / profit ccy", f"{info.currency_margin} / {info.currency_profit}")

        off = measure_server_offset(symbol)
        now = datetime.now(timezone.utc)
        print("\nSERVER TIME")
        row("Last price (server)", f"{off.last_tick_server:%a %Y-%m-%d %H:%M:%S}")
        row("Your PC now (UTC)", f"{now:%a %Y-%m-%d %H:%M:%S}")
        row("Method", off.method)
        row("Server clock is", off.label)
        if off.clock_diff_s is not None:
            row("PC clock vs server", f"{off.clock_diff_s:+.1f} s")
        matching = [m for m in CANDIDATES if offset_minutes_at(m, now) == off.minutes]
        row("Zone models that fit", ", ".join(matching + [fixed_model(off.minutes)]))
        if off.note:
            print(f"  NOTE: {off.note}")

        tick = mt5.symbol_info_tick(symbol)
        spread = tick.ask - tick.bid
        points = round(spread / info.point)
        cost_min_lot = spread / info.trade_tick_size * info.trade_tick_value * info.volume_min
        print("\nSPREAD")
        row("Bid / Ask", f"{tick.bid:.{info.digits}f} / {tick.ask:.{info.digits}f}")
        row("Spread", f"{spread:.{info.digits}f} in price = {points} points")
        row("Cost per trade", f"{cost_min_lot:,.2f} {acc.currency} at {info.volume_min} lot")
        if off.method != "live tick":
            print("  NOTE: market closed, so this is the last spread before the close "
                  "(usually wider than normal).")
        return 0
    except MT5Error as e:
        print(f"\nERROR: {e}")
        return 1
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
