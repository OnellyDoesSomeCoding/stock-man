"""READ-ONLY helpers around the MetaTrader5 package.

Nothing in this module sends, changes or closes orders. Order execution comes
in Phase 4, in its own module, on demo only.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5

from .server_time import NY


class MT5Error(RuntimeError):
    pass


def connect(env: dict[str, str]) -> None:
    """Attach to the running MT5 terminal (or log in with .env values if given)."""
    kwargs: dict = {}
    if env.get("MT5_LOGIN"):
        kwargs.update(
            login=int(env["MT5_LOGIN"]),
            password=env.get("MT5_PASSWORD", ""),
            server=env.get("MT5_SERVER", ""),
        )
    path = env.get("MT5_PATH") or None
    ok = mt5.initialize(path, **kwargs) if path else mt5.initialize(**kwargs)
    if not ok:
        err = mt5.last_error()
        mt5.shutdown()
        raise MT5Error(f"Could not connect to MT5 {err}. Is MT5 open and logged in?")
    term = mt5.terminal_info()
    if term is None or not term.connected:
        raise MT5Error("MT5 is open but not connected to the broker (check internet/login).")


def require_demo():
    """Return account_info, or stop if this is not a DEMO account."""
    acc = mt5.account_info()
    if acc is None:
        raise MT5Error(f"Could not read account info {mt5.last_error()}")
    if acc.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise MT5Error("This is NOT a demo account. Stockman only runs on demo. Stopping.")
    return acc


def find_gold_symbol(candidates: list[str]) -> str:
    """Return the broker's name for gold-in-USD and add it to Market Watch."""
    for name in candidates:
        info = mt5.symbol_info(name)
        if info is not None and info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED:
            if mt5.symbol_select(name, True):
                return name

    matches = []
    for s in mt5.symbols_get() or ():
        name = s.name.upper()
        is_gold = (s.currency_base or "").upper() == "XAU" or name.startswith(("XAUUSD", "GOLD"))
        if is_gold and (s.currency_profit or "").upper() == "USD":
            matches.append(s)
    if not matches:
        raise MT5Error("No gold/USD symbol found. Add it to config.yaml symbol_candidates.")
    matches.sort(key=lambda s: (s.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED, not s.visible, len(s.name)))
    name = matches[0].name
    if not mt5.symbol_select(name, True):
        raise MT5Error(f"Found {name} but could not add it to Market Watch {mt5.last_error()}")
    return name


def server_naive(ts: float) -> datetime:
    """MT5 timestamp -> naive datetime on the SERVER clock (not UTC)."""
    return datetime(1970, 1, 1) + timedelta(seconds=ts)


@dataclass
class ServerOffset:
    minutes: int                  # server clock minus UTC
    method: str                   # "live tick" or "estimated"
    last_tick_server: datetime    # naive, server clock
    clock_diff_s: float | None    # PC clock vs server (live only)
    note: str = ""

    @property
    def label(self) -> str:
        sign = "+" if self.minutes >= 0 else "-"
        h, m = divmod(abs(self.minutes), 60)
        return f"UTC{sign}{h}:{m:02d}"


def measure_server_offset(symbol: str, wait_seconds: float = 10.0) -> ServerOffset:
    """Server clock minus UTC, from the newest tick.

    Waits for a fresh tick and compares its time with the PC's UTC clock. If no
    new tick arrives (market closed), estimates instead, assuming the last price
    came just before gold's daily close at 17:00 New York time.
    """
    first = mt5.symbol_info_tick(symbol)
    if first is None:
        raise MT5Error(f"No price for {symbol} {mt5.last_error()}")

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        tick = mt5.symbol_info_tick(symbol)
        if tick is not None and tick.time_msc != first.time_msc:
            raw_s = tick.time_msc / 1000.0 - time.time()
            minutes = round(raw_s / 900) * 15  # offsets come in 15-minute steps
            return ServerOffset(minutes, "live tick", server_naive(tick.time), raw_s - minutes * 60)
        time.sleep(0.2)

    return _estimate_from_close(first)


def _estimate_from_close(tick) -> ServerOffset:
    last = server_naive(tick.time)
    best = None
    for days_back in (0, 1):
        d = (last - timedelta(days=days_back)).date()
        close_utc = (
            datetime(d.year, d.month, d.day, 17, tzinfo=NY).astimezone(timezone.utc).replace(tzinfo=None)
        )
        diff_min = (last - close_utc).total_seconds() / 60
        hours = round(diff_min / 60)
        resid = diff_min - hours * 60
        if abs(hours) <= 14 and (best is None or abs(resid) < abs(best[1])):
            best = (hours, resid)
    if best is None:
        raise MT5Error("Market closed and the last price time makes no sense; re-run when open.")

    minutes = best[0] * 60
    note = (
        f"No new price for 10 s, so the market looks closed. Offset ESTIMATED from the last "
        f"price. Re-run Mon-Fri while gold is trading to measure it for real."
    )
    last_utc = (last - timedelta(minutes=minutes)).replace(tzinfo=timezone.utc)
    if last_utc.astimezone(NY).weekday() != 4:
        note += " Warning: the last price was not on a Friday (holiday?), so the estimate is weaker."
    return ServerOffset(minutes, "estimated", last, None, note)
