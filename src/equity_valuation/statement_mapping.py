"""
Turns raw EDGAR fact entries into a clean annual time series.

Two separable concerns, kept as two functions:
1. select_annual_facts: which entries represent a real, clean fiscal year
   (as opposed to a quarter, a YTD partial, or a short transition stub).
2. resolve_duplicate_periods: when the same fiscal period appears more
   than once (original filing + later restatements), which version to keep.

DEFAULT CHOICE, STATED EXPLICITLY: duplicate periods are resolved by
preferring the LATEST filing within 2 years of the period's end date,
not the earliest/original filing. Rationale: for a multi-year FCF trend,
we want prior years restated onto a basis consistent with how the
company reports today (post reclassification, discontinued-ops changes,
etc.), not frozen at first-reported values which may since have been
corrected. This is a judgment call, not a neutral default -- an
earliest-as-first-reported alternate could be added later the same way
cost-of-debt got two exposed methods.
"""

from datetime import date, datetime


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def select_annual_facts(entries: list[dict]) -> list[dict]:
    """
    Keep only entries that represent a genuine, clean fiscal-year duration
    from a 10-K (not 10-K/A, not quarters, not short transition stubs).
    """
    kept = []
    for entry in entries:
        if entry.get("form") != "10-K":
            continue
        if "start" not in entry or "end" not in entry:
            continue  # instant-type fact (e.g. balance sheet), not a duration fact
        duration_days = (_parse_date(entry["end"]) - _parse_date(entry["start"])).days
        if 350 <= duration_days <= 380:
            kept.append(entry)
    return kept


def resolve_duplicate_periods(entries: list[dict]) -> list[dict]:
    """
    Given annual entries (already filtered by select_annual_facts, which may
    include the same (start, end) period reported in multiple filings),
    return one entry per unique period: the latest-filed version, but only
    if filed within 2 years of the period's end date (beyond that, treat
    further restatements as not applicable -- companies don't keep
    restating arbitrarily old data).
    """
    best_by_period: dict[tuple[str, str], dict] = {}

    for entry in entries:
        period_end = _parse_date(entry["end"])
        filed = _parse_date(entry["filed"])
        if (filed - period_end).days > 2 * 365:
            continue  # restatement too far removed from its own period, skip

        key = (entry["start"], entry["end"])
        current_best = best_by_period.get(key)
        if current_best is None or filed > _parse_date(current_best["filed"]):
            best_by_period[key] = entry

    # Return sorted oldest-to-newest by period end, for a clean chronological series.
    return sorted(best_by_period.values(), key=lambda e: e["end"])