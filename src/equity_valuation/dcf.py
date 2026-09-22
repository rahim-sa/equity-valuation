

"""
Naive DCF v1 — hardcoded inputs, single company, hand-verifiable.

Deliberately simplified. Known shortcuts taken here that will be
revisited in later stages (see flags below) — not mistakes, but
things a real valuation should not leave as-is:

FLAG 1: End-of-year discounting is used here. Convention in practice
is often mid-year discounting (cash flows assumed to arrive evenly
through the year, not in a lump at year-end), which changes the
result by a few percent. Using end-of-year here only because it's
the easier version to verify by hand first.

FLAG 2: A single constant growth rate is applied to every projection
year. Real FCF projections should build up from revenue growth,
margin assumptions, and reinvestment (capex + working capital)
separately per year, not a single blended growth number.

FLAG 3: The discount rate is a hardcoded placeholder, not a computed
WACC. Stage 3 replaces this.

FLAG 4: Terminal value uses Gordon growth off the *final projected*
FCF. This is sensitive to whatever that final year happens to be —
if the final explicit year is unusually high or low, the terminal
value inherits that distortion. Worth sanity-checking against an
exit-multiple terminal value later as a cross-check, not a fix.
"""

from dataclasses import dataclass


@dataclass
class NaiveDCFInputs:
    base_fcf: float              # most recent actual FCF
    growth_rate: float           # constant annual growth, explicit period
    discount_rate: float         # placeholder WACC
    terminal_growth_rate: float  # perpetuity growth rate, must be < discount_rate
    projection_years: int
    net_debt: float              # total debt minus cash & equivalents
    shares_outstanding: float


def project_fcf(base_fcf: float, growth_rate: float, years: int) -> list[float]:
    """Year 1..N projected FCF, each grown from the prior year."""
    fcfs = []
    prior = base_fcf
    for _ in range(years):
        current = prior * (1 + growth_rate)
        fcfs.append(current)
        prior = current
    return fcfs


def terminal_value(final_year_fcf: float, discount_rate: float, terminal_growth_rate: float) -> float:
    if terminal_growth_rate >= discount_rate:
        raise ValueError(
            "terminal_growth_rate must be strictly less than discount_rate "
            "(Gordon growth formula diverges/inverts otherwise)"
        )
    return final_year_fcf * (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)


def discount_cashflows(cashflows: list[float], discount_rate: float) -> list[float]:
    """PV of each cash flow, end-of-year convention: year 1 discounted by (1+r)^1, etc."""
    return [cf / (1 + discount_rate) ** (i + 1) for i, cf in enumerate(cashflows)]


def run_naive_dcf(inputs: NaiveDCFInputs) -> dict:
    explicit_fcfs = project_fcf(inputs.base_fcf, inputs.growth_rate, inputs.projection_years)
    tv = terminal_value(explicit_fcfs[-1], inputs.discount_rate, inputs.terminal_growth_rate)

    # Terminal value arrives at the end of the final projection year,
    # so it's discounted back the same number of periods as that year's FCF.
    pv_explicit = discount_cashflows(explicit_fcfs, inputs.discount_rate)
    pv_terminal = tv / (1 + inputs.discount_rate) ** inputs.projection_years

    enterprise_value = sum(pv_explicit) + pv_terminal
    equity_value = enterprise_value - inputs.net_debt
    value_per_share = equity_value / inputs.shares_outstanding

    return {
        "explicit_fcfs": explicit_fcfs,
        "pv_explicit_fcfs": pv_explicit,
        "terminal_value": tv,
        "pv_terminal_value": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "value_per_share": value_per_share,
    }