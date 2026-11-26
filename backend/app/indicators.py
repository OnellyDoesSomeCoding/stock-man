"""Chart indicators computed from daily candles ({time, open, high, low, close, volume})."""


def simple_moving_average(candles: list[dict], period: int) -> list[dict]:
    """Average close of the last `period` days, for every day that has enough history."""
    points, total = [], 0.0
    for i, candle in enumerate(candles):
        total += candle["close"]
        if i >= period:
            total -= candles[i - period]["close"]  # drop the day that left the window
        if i >= period - 1:
            points.append({"time": candle["time"], "value": round(total / period, 2)})
    return points


def relative_strength_index(candles: list[dict], period: int = 14) -> list[dict]:
    """
    RSI (Wilder's method), 0-100: compares the size of recent up-days with recent down-days.
    1. Average gain and average loss over the first `period` day-to-day changes.
    2. After that, each day nudges both averages: new = (old * (period - 1) + today) / period.
    3. RSI = 100 - 100 / (1 + avg_gain / avg_loss).
    """
    if len(candles) <= period:
        return []

    def rsi(avg_gain: float, avg_loss: float) -> float:
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0  # only up-days -> 100; flat -> neutral
        return round(100 - 100 / (1 + avg_gain / avg_loss), 2)

    changes = [candles[i]["close"] - candles[i - 1]["close"] for i in range(1, len(candles))]
    avg_gain = sum(max(c, 0) for c in changes[:period]) / period
    avg_loss = sum(max(-c, 0) for c in changes[:period]) / period
    points = [{"time": candles[period]["time"], "value": rsi(avg_gain, avg_loss)}]

    for i in range(period, len(changes)):
        change = changes[i]
        avg_gain = (avg_gain * (period - 1) + max(change, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0)) / period
        points.append({"time": candles[i + 1]["time"], "value": rsi(avg_gain, avg_loss)})
    return points
