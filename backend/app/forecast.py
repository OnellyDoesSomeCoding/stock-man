"""
Prediction experiment: simple models try to guess the closing price N trading days ahead.

Each model is scored "walk-forward": for every past day it only sees prices up to that day,
makes its guess, and is checked against what really happened N days later.
Every model is compared with the simplest guess of all: "the price won't change".
"""

import numpy as np

LOOKBACK = 20  # days used by the average and trend-line models
LAGS = 5  # past daily moves the regression model looks at
TRAIN_WINDOW = 500  # regression learns from (at most) the last ~2 years before each day
MIN_TRAIN = 100
HORIZONS = (1, 5, 20)  # trading days ahead: tomorrow, ~1 week, ~1 month

MODELS = {
    "naive": {
        "name": "Tomorrow = today",
        "about": "Guesses the price will not change. The baseline every other model must beat.",
    },
    "average": {
        "name": "20-day average",
        "about": "Guesses the price will drift back to its average of the last 20 days.",
    },
    "trend": {
        "name": "20-day trend line",
        "about": "Draws a straight line through the last 20 closes and extends it forward.",
    },
    "regression": {
        "name": "Pattern model (regression)",
        "about": "Learns how the last 5 daily moves related to the move N days later, "
        "then applies that to today. Re-learns every day using only earlier data.",
    },
}


def run_forecast(history: list[dict], horizon: int, since: str) -> dict:
    if horizon not in HORIZONS:
        raise ValueError(f"horizon must be one of {', '.join(map(str, HORIZONS))} (trading days ahead)")
    closes = np.array([c["close"] for c in history], dtype=float)
    times = [c["time"] for c in history]
    n = len(closes)
    log_ret = np.zeros(n)
    log_ret[1:] = np.log(closes[1:] / closes[:-1])  # daily moves (log returns)

    # All models are scored on the same days: the guess is made on day t, about day t + horizon.
    first_t = max(LOOKBACK - 1, LAGS + horizon + MIN_TRAIN)
    days = [t for t in range(first_t, n - horizon) if times[t + horizon] >= since]
    if len(days) < 20:
        raise ValueError("Not enough price history for this range and horizon. Try a longer range.")

    x_line = np.arange(LOOKBACK)
    preds = {m: [] for m in MODELS}
    for t in days:
        window = closes[t - LOOKBACK + 1 : t + 1]
        preds["naive"].append(closes[t])
        preds["average"].append(window.mean())
        slope, intercept = np.polyfit(x_line, window, 1)
        preds["trend"].append(intercept + slope * (LOOKBACK - 1 + horizon))

        # Regression: rows s whose answer (s + horizon) was already known on day t.
        s = np.arange(max(LAGS, t - horizon - TRAIN_WINDOW + 1), t - horizon + 1)
        features = np.column_stack([np.ones(len(s))] + [log_ret[s - k] for k in range(LAGS)])
        target = np.log(closes[s + horizon] / closes[s])
        beta, *_ = np.linalg.lstsq(features, target, rcond=None)
        today = np.concatenate([[1.0], [log_ret[t - k] for k in range(LAGS)]])
        preds["regression"].append(closes[t] * np.exp(today @ beta))

    start = np.array([closes[t] for t in days])
    actual = np.array([closes[t + horizon] for t in days])
    moved = actual != start
    naive_mae = float(np.mean(np.abs(actual - start)))

    models = []
    for key, info in MODELS.items():
        p = np.array(preds[key])
        mae = float(np.mean(np.abs(p - actual)))
        direction = None
        if key != "naive" and moved.any():
            direction = float(np.mean(np.sign(p - start)[moved] == np.sign(actual - start)[moved]) * 100)
        models.append({
            "id": key,
            **info,
            "mae": round(mae, 3),  # average miss in THB
            "mape_pct": round(float(np.mean(np.abs(p - actual) / actual)) * 100, 2),  # average miss in %
            "vs_naive_pct": round((mae / naive_mae - 1) * 100, 1) if naive_mae else None,  # + = worse
            "direction_pct": round(direction, 1) if direction is not None else None,
            "points": [{"time": times[t + horizon], "value": round(float(v), 2)} for t, v in zip(days, p)],
        })

    # Honest outlook: how far the price really moved over `horizon` days in this period.
    changes = actual / start - 1
    low, mid, high = np.percentile(changes, [10, 50, 90])
    last = closes[-1]
    return {
        "horizon": horizon,
        "start": times[days[0] + horizon],
        "end": times[days[-1] + horizon],
        "samples": len(days),
        "up_pct": round(float(np.mean(actual > start)) * 100, 1),  # how often it actually went up
        # Fair yardstick for direction guesses: always guessing the more common direction
        # (counted only on days the price moved, like the models' direction scores).
        "common_direction": "up" if np.mean(actual[moved] > start[moved]) >= 0.5 else "down",
        "common_direction_pct": round(
            float(max(np.mean(actual[moved] > start[moved]), np.mean(actual[moved] < start[moved]))) * 100, 1
        ) if moved.any() else None,
        "models": models,
        "actual": [{"time": times[t + horizon], "value": round(float(v), 2)} for t, v in zip(days, actual)],
        "outlook": {
            "from_date": times[-1],
            "from_price": round(float(last), 2),
            "low_pct": round(float(low) * 100, 2),
            "mid_pct": round(float(mid) * 100, 2),
            "high_pct": round(float(high) * 100, 2),
            "low": round(float(last * (1 + low)), 2),
            "high": round(float(last * (1 + high)), 2),
        },
    }
