"""
Comparable company multiples: EV/EBITDA, EV/EBIT, EV/Revenue, P/E.

Pure calculation functions here -- no data fetching, no peer selection
logic yet (that's a separate, later step). Each function takes already-
assembled financial figures for one company and computes its multiples.

FLAG: EV/EBITDA and EV/EBIT use enterprise value (capital-structure-
neutral), while P/E uses equity value / net income (capital-structure-
sensitive). Mixing these up -- e.g. comparing one company's EV/EBITDA
to another's P/E as if they were the same kind of thing -- is a common
error. Keep them conceptually separate even though they're all called
"multiples."

FLAG: using GAAP net income for P/E without checking for one-off items
(impairments, tax benefits, gains on sale) is one of the most common
comps distortions -- a single unusual quarter/year can make P/E look
absurdly high or low, misleadingly. This module does not attempt to
"clean" net income automatically; that requires judgment about what
counts as non-recurring, which isn't something to silently automate.
Flagging outlier multiples is a separate, later concern.
"""

from dataclasses import dataclass


@dataclass
class CompanyFinancials:
    """Snapshot of one company's figures needed for multiples, one period."""
    market_value_equity: float   # share_price * shares_outstanding
    total_debt: float
    cash_and_equivalents: float
    ebitda: float
    ebit: float
    revenue: float
    net_income: float


def enterprise_value(financials: CompanyFinancials) -> float:
    """EV = market value of equity + total debt - cash & equivalents."""
    return financials.market_value_equity + financials.total_debt - financials.cash_and_equivalents


def ev_to_ebitda(financials: CompanyFinancials) -> float:
    if financials.ebitda <= 0:
        raise ValueError("EV/EBITDA is not meaningful for zero or negative EBITDA")
    return enterprise_value(financials) / financials.ebitda


def ev_to_ebit(financials: CompanyFinancials) -> float:
    if financials.ebit <= 0:
        raise ValueError("EV/EBIT is not meaningful for zero or negative EBIT")
    return enterprise_value(financials) / financials.ebit


def ev_to_revenue(financials: CompanyFinancials) -> float:
    if financials.revenue <= 0:
        raise ValueError("EV/Revenue is not meaningful for zero or negative revenue")
    return enterprise_value(financials) / financials.revenue


def price_to_earnings(financials: CompanyFinancials) -> float:
    if financials.net_income <= 0:
        raise ValueError("P/E is not meaningful for zero or negative net income")
    return financials.market_value_equity / financials.net_income


def implied_value_from_peer_multiple(peer_multiple: float, target_metric: float, metric_type: str) -> float:
    """
    Apply a peer-derived multiple to the target company's own metric to get
    an implied valuation.

    metric_type: "ebitda", "ebit", or "revenue" -> returns implied ENTERPRISE
    VALUE (caller must still subtract net debt to get equity value, same as
    the DCF side). "net_income" -> returns implied EQUITY VALUE directly
    (P/E already operates at the equity level, no net-debt adjustment needed).

    FLAG: returning EV for the first three and equity value for P/E directly,
    rather than always returning the same "kind" of value, is intentional --
    collapsing them into one undifferentiated "implied value" would hide
    exactly the capital-structure distinction flagged in the module docstring.
    """
    valid_metric_types = {"ebitda", "ebit", "revenue", "net_income"}
    if metric_type not in valid_metric_types:
        raise ValueError(f"metric_type must be one of {valid_metric_types}")
    return peer_multiple * target_metric