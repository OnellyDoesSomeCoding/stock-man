"""Convert MT5 server-clock times to UTC.

MT5 bar and tick times are the broker's wall-clock time with no time zone
attached. Most brokers run "New York time + 7 hours" (so the trading day starts
at midnight server time): UTC+2 in winter, UTC+3 in summer, switching on US
daylight-saving dates. Converting with one fixed offset would shift half the
year by an hour, so we model the zone properly.

A "model" is one of:
  "ny7"            New York time + 7h
  "fixed:+2"       constant offset in hours, no daylight saving
  "Europe/Athens"  any IANA time zone name
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

NY_NAME = "America/New_York"
NY = ZoneInfo(NY_NAME)

# Models tried by auto-detection, in order of preference when tied.
CANDIDATES = ("ny7", "Europe/Athens", "Europe/London", "Europe/Berlin", "UTC")


def fixed_model(offset_minutes: int) -> str:
    return f"fixed:{offset_minutes / 60:+g}"


def offset_minutes_at(model: str, utc_dt: datetime) -> int:
    """Server clock minus UTC, in minutes, at the given moment."""
    if model == "ny7":
        return int(utc_dt.astimezone(NY).utcoffset().total_seconds() // 60) + 7 * 60
    if model.startswith("fixed:"):
        return int(round(float(model[6:]) * 60))
    return int(utc_dt.astimezone(ZoneInfo(model)).utcoffset().total_seconds() // 60)


def to_utc(server_naive: pd.Series, model: str) -> pd.Series:
    """Naive server-clock datetimes -> tz-aware UTC. Impossible times become NaT."""
    s = pd.to_datetime(pd.Series(server_naive))
    if model == "ny7":
        local = s - pd.Timedelta(hours=7)
        return local.dt.tz_localize(NY_NAME, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    if model.startswith("fixed:"):
        minutes = offset_minutes_at(model, datetime.now(timezone.utc))
        return (s - pd.Timedelta(minutes=minutes)).dt.tz_localize("UTC")
    return s.dt.tz_localize(model, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")


def weekly_opens(server_naive: pd.Series) -> pd.Series:
    """First bar after each weekend (a gap longer than 36 hours)."""
    s = pd.to_datetime(pd.Series(server_naive)).sort_values().reset_index(drop=True)
    return s[s.diff() > pd.Timedelta(hours=36)]


def weekly_open_consistency(server_naive: pd.Series, model: str) -> dict:
    """How often the weekly open lands on the same New York clock time.

    Gold reopens every Sunday at a fixed New York time, so the correct model
    gives (nearly) the same New York time every week; a wrong model makes it
    jump by an hour when daylight saving changes.
    """
    opens = weekly_opens(server_naive)
    ny = to_utc(opens, model).dropna().dt.tz_convert(NY_NAME)
    if len(ny) < 4:
        return {"model": model, "weeks": len(ny), "share": float("nan"), "ny_open": "?"}
    minutes = ny.dt.hour * 60 + ny.dt.minute
    counts = minutes.value_counts()
    mode = int(counts.index[0])
    return {
        "model": model,
        "weeks": len(ny),
        "share": counts.iloc[0] / len(ny),
        "ny_open": f"{mode // 60:02d}:{mode % 60:02d}",
    }


def detect_model(server_naive: pd.Series, offset_minutes_now: int, now_utc: datetime) -> tuple[str, list[dict]]:
    """Pick the model that matches today's offset AND past weekly opens best."""
    models = [m for m in CANDIDATES if offset_minutes_at(m, now_utc) == offset_minutes_now]
    models.append(fixed_model(offset_minutes_now))
    scores = [weekly_open_consistency(server_naive, m) for m in models]

    def rank(r: dict):
        share = r["share"] if r["share"] == r["share"] else -1.0  # NaN -> worst
        return (round(share, 4), -models.index(r["model"]))

    best = max(scores, key=rank)
    return best["model"], scores
