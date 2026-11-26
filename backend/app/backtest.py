"""
Backtester: replay a simple trading rule over past prices with fake money,
and compare it with just buying on day one and holding (buy-and-hold).

No peeking at the future: each rule decides using a day's closing price,
and the trade happens at the NEXT day's opening price.
"""

from .indicators import relative_strength_index, simple_moving_average

STARTING_CASH = 100_000.0
FEE_RATE = 0.0015  # ~0.15% of each trade: a typical Thai online broker fee (before VAT)

STRATEGIES = {
    "price_above_ma50": {
        "name": "Price vs 50-day average",
        "rule": "Own the stock while its close is above its 50-day average; sell when it closes below.",
    },
    "ma20_above_ma50": {
        "name": "20-day vs 50-day average",
        "rule": "Own the stock while the 20-day average is above the 50-day average "
        '(a "golden cross"); sell when it drops below (a "death cross").',
    },
    "rsi_30_70": {
        "name": "RSI 30 / 70",
        "rule": "Buy when RSI falls below 30 (maybe oversold); sell when it rises above 70 (maybe overbought).",
    },
}


def _desired_positions(strategy: str, history: list[dict]) -> dict[str, bool]:
    """For each day the rule can decide on: should we own the stock after that day's close?"""
    if strategy == "price_above_ma50":
        ma = {p["time"]: p["value"] for p in simple_moving_average(history, 50)}
        return {c["time"]: c["close"] > ma[c["time"]] for c in history if c["time"] in ma}

    if strategy == "ma20_above_ma50":
        fast = {p["time"]: p["value"] for p in simple_moving_average(history, 20)}
        slow = {p["time"]: p["value"] for p in simple_moving_average(history, 50)}
        return {t: fast[t] > slow[t] for t in slow if t in fast}

    if strategy == "rsi_30_70":
        holding, wanted = False, {}
        for p in relative_strength_index(history, 14):
            if not holding and p["value"] < 30:
                holding = True
            elif holding and p["value"] > 70:
                holding = False
            wanted[p["time"]] = holding
        return wanted

    raise ValueError(f"Unknown strategy {strategy!r}. Choose one of: {', '.join(STRATEGIES)}")


def _max_drawdown_pct(values: list[float]) -> float:
    """Biggest fall from a previous high, in % (e.g. 100k -> 80k = 20%)."""
    peak, worst = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        worst = max(worst, (peak - v) / peak)
    return round(worst * 100, 2)


def run_backtest(history: list[dict], strategy: str, since: str) -> dict:
    wanted = _desired_positions(strategy, history)
    # Start on the first day in the range where the rule can decide (its averages need history).
    days = [c for c in history if c["time"] >= since and c["time"] in wanted]
    if len(days) < 20:
        raise ValueError("Not enough price history for this range. Try a longer one.")

    cash, shares, entry_cost, fees = STARTING_CASH, 0, 0.0, 0.0
    trades, equity, days_held, closed = [], [], 0, []

    for i, day in enumerate(days):
        if i > 0:  # act on YESTERDAY's decision, at TODAY's opening price
            want = wanted[days[i - 1]["time"]]
            price = day["open"]
            if want and shares == 0:
                n = int(cash / (price * (1 + FEE_RATE)))  # as many whole shares as cash (plus fee) allows
                if n > 0:
                    cost, fee = n * price, n * price * FEE_RATE
                    cash -= cost + fee
                    shares, entry_cost, fees = n, cost + fee, fees + fee
                    trades.append({"time": day["time"], "side": "buy", "shares": n, "price": price})
            elif not want and shares > 0:
                proceeds, fee = shares * price, shares * price * FEE_RATE
                cash += proceeds - fee
                profit = proceeds - fee - entry_cost
                closed.append(profit)
                fees += fee
                trades.append({"time": day["time"], "side": "sell", "shares": shares, "price": price,
                               "profit": round(profit, 2)})
                shares = 0
        days_held += shares > 0
        equity.append({"time": day["time"], "value": round(cash + shares * day["close"], 2)})

    # Buy-and-hold: buy on the first day the strategy could have traded (day 2's open), never sell.
    first = days[1]
    bh_shares = int(STARTING_CASH / (first["open"] * (1 + FEE_RATE)))
    bh_cash = STARTING_CASH - bh_shares * first["open"] * (1 + FEE_RATE)
    buy_hold = [{"time": days[0]["time"], "value": STARTING_CASH}] + [
        {"time": d["time"], "value": round(bh_cash + bh_shares * d["close"], 2)} for d in days[1:]
    ]

    def summary(curve: list[dict]) -> dict:
        final = curve[-1]["value"]
        return {
            "final_value": final,
            "return_pct": round((final / STARTING_CASH - 1) * 100, 2),
            "max_drawdown_pct": _max_drawdown_pct([p["value"] for p in curve]),
        }

    return {
        "strategy": strategy,
        **STRATEGIES[strategy],
        "start": days[0]["time"],
        "end": days[-1]["time"],
        "starting_cash": STARTING_CASH,
        "fee_rate_pct": FEE_RATE * 100,
        "result": {
            **summary(equity),
            "trades": len(trades),
            "round_trips": len(closed),
            "win_rate_pct": round(sum(p > 0 for p in closed) / len(closed) * 100, 1) if closed else None,
            "fees_paid": round(fees, 2),
            "time_in_market_pct": round(days_held / len(days) * 100, 1),
            "holding_at_end": shares > 0,
        },
        "buy_hold": summary(buy_hold),
        "equity": equity,
        "buy_hold_equity": buy_hold,
        "trades": trades,
    }
