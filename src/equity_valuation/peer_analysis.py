"""
Peer group comps analysis. Peer selection itself is a manual, deliberate
judgment call by the user -- this module does NOT suggest or screen for
peers algorithmically. See module-level rationale: an algorithm can match
on industry code or size band without understanding whether two companies
are actually comparable businesses (different margin structures, different
growth stages, different capital intensity) -- that judgment is preserved
here as an explicit human input (the peer ticker list), not automated away.

FLAG: every peer's multiple here reflects ITS OWN "most recent fiscal
year," which can differ by several months across peers with different
fiscal year ends (confirmed concretely with AAPL/MSFT/GOOGL -- up to a
9-month spread). This module does not correct for that; it's a known,
named limitation carried over from comps_data.py, worth remembering when
interpreting results, especially in fast-moving sectors or volatile
periods where a several-month gap could mean real fundamental change.

FLAG: outlier peers can distort a mean far more than a median -- this
module reports both deliberately, so a single unusually priced peer
doesn't silently dominate the "typical" multiple without being visible.
"""

import statistics
from dataclasses import dataclass

from equity_valuation.comps import (
    ev_to_ebitda, ev_to_ebit, ev_to_revenue, price_to_earnings,
    implied_value_from_peer_multiple,
)
from equity_valuation.comps_data import build_company_financials


@dataclass
class PeerMultiples:
    ticker: str
    fiscal_year_end: str
    ev_ebitda: float | None
    ev_ebit: float | None
    ev_revenue: float | None
    pe: float | None


def compute_peer_multiples(ticker: str, ticker_map: dict) -> PeerMultiples:
    """
    Computes all four multiples for one peer. A multiple that isn't
    meaningful for this company (e.g. negative EBITDA) is recorded as
    None, not silently excluded or defaulted to zero -- callers must
    handle None explicitly when aggregating.
    """
    result = build_company_financials(ticker, ticker_map)
    f = result["financials"]

    def _safe(fn):
        try:
            return fn(f)
        except ValueError:
            return None

    return PeerMultiples(
        ticker=ticker,
        fiscal_year_end=result["fiscal_year_end"],
        ev_ebitda=_safe(ev_to_ebitda),
        ev_ebit=_safe(ev_to_ebit),
        ev_revenue=_safe(ev_to_revenue),
        pe=_safe(price_to_earnings),
    )


@dataclass
class MultipleSummary:
    metric_name: str
    values: list[float]          # only the peers where this multiple was meaningful
    excluded_tickers: list[str]  # peers excluded because this multiple wasn't meaningful for them
    median: float
    mean: float
    minimum: float
    maximum: float


def summarize_multiple(peer_multiples: list[PeerMultiples], metric_name: str) -> MultipleSummary:
    """
    metric_name: one of "ev_ebitda", "ev_ebit", "ev_revenue", "pe" --
    must match a PeerMultiples field name.
    """
    values = []
    excluded = []
    for pm in peer_multiples:
        val = getattr(pm, metric_name)
        if val is None:
            excluded.append(pm.ticker)
        else:
            values.append(val)

    if not values:
        raise ValueError(f"No peer had a meaningful '{metric_name}' multiple -- cannot summarize")

    return MultipleSummary(
        metric_name=metric_name,
        values=values,
        excluded_tickers=excluded,
        median=statistics.median(values),
        mean=statistics.mean(values),
        minimum=min(values),
        maximum=max(values),
    )


def implied_valuation_range(summary: MultipleSummary, target_metric_value: float) -> dict:
    """
    Applies the peer group's median, min, and max multiple to the target
    company's own metric, giving a RANGE of implied values rather than a
    single point -- comps should present a range, not false precision
    from picking one "representative" multiple.

    Returns raw implied values (EV for ev_* metrics, equity value for pe) --
    same convention as implied_value_from_peer_multiple; caller still
    handles the EV-to-equity-value bridge for EV-based metrics, same as
    the DCF side.
    """
    metric_type_map = {"ev_ebitda": "ebitda", "ev_ebit": "ebit", "ev_revenue": "revenue", "pe": "net_income"}
    metric_type = metric_type_map[summary.metric_name]

    return {
        "low": implied_value_from_peer_multiple(summary.minimum, target_metric_value, metric_type),
        "median": implied_value_from_peer_multiple(summary.median, target_metric_value, metric_type),
        "high": implied_value_from_peer_multiple(summary.maximum, target_metric_value, metric_type),
    }


from datetime import date, datetime


def check_fiscal_year_alignment(
    target_fiscal_year_end: str, peer_multiples: list[PeerMultiples], warning_threshold_days: int = 120
) -> list[str]:
    """
    Returns a list of human-readable warnings for any peer whose fiscal
    year end is more than warning_threshold_days away from the target's.

    This does NOT fix the underlying misalignment (that would require
    TTM data -- a separate, larger piece of work, deliberately deferred).
    It only makes the misalignment impossible to silently miss when
    reading comps output. Default threshold of 120 days (~4 months) is
    a judgment call, not a rigorous cutoff -- shorter gaps are common
    and less concerning; a gap approaching or exceeding a full quarter
    starts to risk real fundamental drift between the two "snapshots"
    being compared, especially in fast-moving sectors.
    """
    def _parse(s: str) -> date:
        return datetime.strptime(s, "%Y-%m-%d").date()

    target_date = _parse(target_fiscal_year_end)
    warnings = []

    for pm in peer_multiples:
        peer_date = _parse(pm.fiscal_year_end)
        gap_days = abs((target_date - peer_date).days)
        if gap_days > warning_threshold_days:
            warnings.append(
                f"WARNING: {pm.ticker}'s fiscal year end ({pm.fiscal_year_end}) is "
                f"{gap_days} days from the target's ({target_fiscal_year_end}). "
                f"Multiples are not time-aligned -- treat this comparison with caution."
            )
    return warnings