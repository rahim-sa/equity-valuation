"""
WACC Option B: synthetic credit rating -> default spread, used to derive
an alternative cost of debt. Exposed alongside Option A (effective rate
from financials, in wacc.py), not a replacement for it.

METHOD: compute interest coverage ratio (EBIT / interest_expense), map it
to a synthetic rating bracket, read off that bracket's default spread,
add the spread to the risk-free rate to get cost of debt.

FLAG - DATA STALENESS: the table below is a hardcoded snapshot in the
style of data Aswath Damodaran publishes and periodically updates
(coverage-ratio-to-rating-to-spread, for larger/more established
companies specifically -- there is a separate table with different
thresholds for smaller/riskier firms, not implemented here). These
spread numbers move with credit market conditions and WILL go stale.
This must eventually be replaced with a live-pulled table in the
real-data stage, not left hardcoded indefinitely. Treat every number
in RATING_TABLE below as illustrative, not current market fact, until
cross-checked against a live source.

FLAG - APPLICABILITY: this table is for larger/more mature companies.
Applying it to a small-cap or highly cyclical company will misprice
the credit spread -- smaller companies' coverage ratios map to worse
ratings at the same coverage level than large companies' do, because
smaller firms are inherently riskier at a given coverage ratio. A
size-appropriate second table is a deliberate follow-up, not done here.

FLAG - EBIT vs EBITDA: interest coverage here uses EBIT (operating
income), which is the standard definition. Using EBITDA instead
systematically overstates coverage (ignores D&A as a real cash-adjacent
burden on debt service capacity for capital-intensive firms) and would
bias the resulting rating upward -- do not substitute EBITDA here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RatingBracket:
    min_coverage: float  # inclusive lower bound; use -inf for the worst bracket
    max_coverage: float  # exclusive upper bound; use +inf for the best bracket
    rating: str
    default_spread: float  # spread over risk-free rate


# Illustrative snapshot, large/mature company table, coverage ratio = EBIT / interest expense.
# Source style: Damodaran-published synthetic rating tables. NOT live data -- see FLAG above.
RATING_TABLE: list[RatingBracket] = [
    RatingBracket(-float("inf"), 0.5, "D", 0.1500),
    RatingBracket(0.5, 0.8, "C", 0.1000),
    RatingBracket(0.8, 1.25, "CC", 0.0800),
    RatingBracket(1.25, 1.5, "CCC", 0.0650),
    RatingBracket(1.5, 2.0, "B-", 0.0500),
    RatingBracket(2.0, 2.5, "B", 0.0400),
    RatingBracket(2.5, 3.0, "B+", 0.0325),
    RatingBracket(3.0, 4.0, "BB", 0.0250),
    RatingBracket(4.0, 4.5, "BBB", 0.0180),
    RatingBracket(4.5, 6.0, "A-", 0.0140),
    RatingBracket(6.0, 7.5, "A", 0.0110),
    RatingBracket(7.5, 9.5, "A+", 0.0090),
    RatingBracket(9.5, 12.5, "AA", 0.0070),
    RatingBracket(12.5, float("inf"), "AAA", 0.0050),
]


def interest_coverage_ratio(ebit: float, interest_expense: float) -> float:
    if interest_expense <= 0:
        raise ValueError("interest_expense must be positive to compute coverage ratio")
    return ebit / interest_expense


def synthetic_rating(coverage_ratio: float) -> RatingBracket:
    for bracket in RATING_TABLE:
        if bracket.min_coverage <= coverage_ratio < bracket.max_coverage:
            return bracket
    raise ValueError(f"coverage_ratio {coverage_ratio} did not match any bracket -- table gap")


def cost_of_debt_synthetic_rating(
    ebit: float, interest_expense: float, risk_free_rate: float
) -> tuple[float, RatingBracket]:
    """Returns (cost_of_debt, matched_bracket) so the caller can see which rating was used."""
    coverage = interest_coverage_ratio(ebit, interest_expense)
    bracket = synthetic_rating(coverage)
    return risk_free_rate + bracket.default_spread, bracket