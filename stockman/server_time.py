"""Convert MT5 server-clock times to UTC.

MT5 bar and tick times are the broker's wall-clock time with no time zone
attached. Most brokers run "New York time + 7 hours" or Eastern European time:
UTC+2 in winter, UTC+3 in summer, but switching on US or EU daylight-saving
dates. Brokers also change their rule over the years, so history is split into
periods, each converted with its own rule.

A "model" (clock rule) is one of:
  "ny7"            New York time + 7h (switches on US dates)
  "fixed:+2"       constant offset in hours, no daylight saving
  "Europe/Athens"  any IANA time zone name (EU dates for European zones)

A "period" is {"from": None | "YYYY-MM-DD HH:MM" (server clock), "model": str}.
Periods are listed oldest first; the first has from=None (covers everything before).
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

NY_NAME = "America/New_York"
NY = ZoneInfo(NY_NAME)

# Named rules tried by auto-detection, in order of preference when tied.
CANDIDATES = ("ny7", "Europe/Athens", "Europe/London", "Europe/Berlin", "UTC")

# Gold (CME and almost every CFD broker) reopens on Sunday at 18:00 New York time.
GOLD_REOPEN_NY_MIN = 18 * 60


def fixed_model(offset_minutes: int) -> str:
    """Name of the constant-offset rule, e.g. 120 -> 'fixed:+2'."""
    return f"fixed:{offset_minutes / 60:+g}"


ALL_MODELS = list(CANDIDATES) + [fixed_model(h * 60) for h in range(-12, 15) if h != 0]


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
        return (s - pd.Timedelta(minutes=offset_minutes_at(model, datetime.now()))).dt.tz_localize("UTC")
    return s.dt.tz_localize(model, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")


def to_utc_periods(server_naive: pd.Series, periods: list[dict]) -> pd.Series:
    """Like to_utc, but each period of history uses its own rule."""
    s = pd.to_datetime(pd.Series(server_naive))
    starts = [pd.Timestamp(p["from"]) if p.get("from") else None for p in periods]
    parts = []
    for i, p in enumerate(periods):
        mask = pd.Series(True, index=s.index)
        if starts[i] is not None:
            mask &= s >= starts[i]
        if i + 1 < len(periods):
            mask &= s < starts[i + 1]
        if mask.any():
            parts.append(to_utc(s[mask], p["model"]))
    if not parts:
        return to_utc(s, periods[-1]["model"])
    return pd.concat(parts).reindex(s.index)


# ---------------------------------------------------------------- detection

def weekly_opens(server_naive: pd.Series) -> pd.Series:
    """First bar after each weekend (a gap longer than 36 hours)."""
    s = pd.to_datetime(pd.Series(server_naive)).sort_values().reset_index(drop=True)
    return s[s.diff() > pd.Timedelta(hours=36)]


def _ny_open_minutes(opens: pd.Series, model: str) -> pd.Series:
    """New York clock time of each weekly open, in minutes, rounded to 15 min
    (brokers often open a few minutes late, e.g. 18:05)."""
    ny = to_utc(opens, model).dropna().dt.tz_convert(NY_NAME)
    m = ny.dt.hour * 60 + ny.dt.minute
    return ((m / 15).round() * 15).astype(int) % (24 * 60)


def score(opens: pd.Series, model: str) -> dict:
    """How often this rule puts the weekly open on the same New York time.

    The right rule gives (nearly) the same time every week; a wrong one makes it
    jump by an hour when daylight saving changes.
    """
    m = _ny_open_minutes(opens, model)
    if len(m) < 4:
        return {"model": model, "weeks": len(m), "share": float("nan"), "ny_open": "?", "miss": 0}
    counts = m.value_counts()
    mode = int(counts.index[0])
    d = abs(mode - GOLD_REOPEN_NY_MIN)
    return {
        "model": model,
        "weeks": len(m),
        "share": float(counts.iloc[0] / len(m)),
        "ny_open": f"{mode // 60:02d}:{mode % 60:02d}",
        "miss": min(d, 24 * 60 - d),  # minutes away from 18:00 NY
    }


def _rank(r: dict):
    if r["share"] != r["share"]:  # NaN: not enough weeks
        return (-1.0, 0, 0)
    pref = ALL_MODELS.index(r["model"]) if r["model"] in ALL_MODELS else len(ALL_MODELS)
    return (round(r["share"], 2), -r["miss"], -pref)


def _models_for(offset_minutes_now: int | None, now_utc: datetime) -> list[str]:
    if offset_minutes_now is None:
        return ALL_MODELS
    named = [m for m in CANDIDATES if offset_minutes_at(m, now_utc) == offset_minutes_now]
    return named + [fixed_model(offset_minutes_now)]


def _refine_boundary(opens: pd.Series, old: str, new: str, year: int) -> str | None:
    """Find the exact week the broker switched from `old` to `new`.

    Only weeks where the two rules disagree can tell them apart. The switch is
    the first such week that fits `new`, after the last one that fits `old`.
    Any point in between gives identical UTC times, so this is exact.
    """
    w = opens[(opens.dt.year >= year - 1) & (opens.dt.year <= year)]
    df = pd.DataFrame({"t": w, "a": _ny_open_minutes(w, old), "b": _ny_open_minutes(w, new)}).dropna()
    if df.empty:
        return None
    mode_a, mode_b = df["a"].mode().iloc[0], df["b"].mode().iloc[0]
    disc = df[df["a"] != df["b"]]
    fits_old = disc.loc[disc["a"] == mode_a, "t"]
    fits_new = disc.loc[disc["b"] == mode_b, "t"]
    if len(fits_old):
        fits_new = fits_new[fits_new > fits_old.max()]
    if fits_new.empty:
        return None
    return fits_new.min().strftime("%Y-%m-%d %H:%M")


def detect_periods(
    server_naive: pd.Series, offset_minutes_now: int | None, now_utc: datetime
) -> tuple[list[dict], list[dict]]:
    """Work out which clock rule the broker used in each part of history.

    offset_minutes_now: a LIVE-measured offset restricts the newest year to
    rules that match it. Pass None when it is only an estimate (market closed).

    Returns (periods, report). report has one row per period with its scores.
    """
    opens = weekly_opens(server_naive).reset_index(drop=True)
    years = sorted(opens.dt.year.unique(), reverse=True)

    # 1) Best rule per year, newest first. Near-ties keep the newer year's rule.
    picks: dict[int, str] = {}
    prev = None
    for i, y in enumerate(years):
        o = opens[opens.dt.year == y]
        scores = {m: score(o, m) for m in _models_for(offset_minutes_now if i == 0 else None, now_utc)}
        best = max(scores.values(), key=_rank)
        keep = scores.get(prev) if prev else None
        if keep is not None and keep["model"] != best["model"]:
            weak = best["share"] != best["share"]
            close = (keep["share"] == keep["share"] and best["share"] - keep["share"] <= 0.02
                     and keep["miss"] <= best["miss"])
            if weak or close:
                best = keep
        picks[int(y)] = prev = best["model"]

    # 2) Merge neighbouring years with the same rule; 3) pin each switch to its week.
    periods: list[dict] = []
    for y in sorted(picks):
        if not periods or periods[-1]["model"] != picks[y]:
            periods.append({"from": f"{y}-01-01 00:00" if periods else None, "model": picks[y]})
    for i in range(1, len(periods)):
        year = int(periods[i]["from"][:4])
        periods[i]["from"] = _refine_boundary(opens, periods[i - 1]["model"], periods[i]["model"], year) \
            or periods[i]["from"]

    # 4) Report: chosen rule vs best alternative within each period.
    report = []
    for i, p in enumerate(periods):
        lo = pd.Timestamp(p["from"]) if p["from"] else opens.min()
        hi = pd.Timestamp(periods[i + 1]["from"]) if i + 1 < len(periods) else opens.max() + pd.Timedelta(1, "s")
        o = opens[(opens >= lo) & (opens < hi)]
        scores = sorted((score(o, m) for m in ALL_MODELS), key=_rank, reverse=True)
        chosen = next(s for s in scores if s["model"] == p["model"])
        other = next(s for s in scores if s["model"] != p["model"])
        report.append({
            "from": o.min().strftime("%Y-%m-%d"), "to": o.max().strftime("%Y-%m-%d"),
            "model": p["model"], "weeks": chosen["weeks"], "share": chosen["share"],
            "ny_open": chosen["ny_open"], "runner_up": other["model"], "runner_up_share": other["share"],
            "runner_up_ny_open": other["ny_open"],
        })
    return periods, report
