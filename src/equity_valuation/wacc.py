"""
WACC calculation, stage 1 of 2.

Cost of equity: CAPM (risk_free_rate + beta * equity_risk_premium).
Cost of debt: Option A, "effective rate" — interest_expense / total_debt,
    taken straight from the company's own financials. This is the simpler
    of two legitimate methods; a second method (synthetic credit rating
    spread) is a planned follow-up, exposed alongside this one, not a
    replacement for it.
Weights: market value of equity and debt, NOT book value.

FLAG: using market value of equity (share price x shares outstanding) is
required, not optional. Book value of equity is an accounting artifact
(historical cost, retained earnings) and can be wildly different from
what the market actually thinks the equity is worth. Using book value
here is one of the most common WACC implementation shortcuts, and it
silently distorts the equity/debt weighting.

FLAG: this is a single-point WACC, not adjusted for target/optimal
capital structure. A company's current market-value mix is used as-is.
Real practice sometimes uses a target structure instead — noted here,
not implemented, since that requires a judgment call this tool doesn't
make for you.

FLAG: total_debt should be the market value of debt where available.
In practice book value of debt is commonly used as a proxy because debt
market values are harder to observe than equity market values — this is
a more defensible shortcut than the book-value-of-equity one above, but
it's still a proxy, not a theoretically clean input.
"""

from dataclasses import dataclass


@dataclass
class CostOfEquityInputs:
    risk_free_rate: float
    beta: float
    equity_risk_premium: float


def cost_of_equity_capm(inputs: CostOfEquityInputs) -> float:
    return inputs.risk_free_rate + inputs.beta * inputs.equity_risk_premium


@dataclass
class CostOfDebtInputs:
    interest_expense: float
    total_debt: float  # book value proxy for market value of debt


def cost_of_debt_effective_rate(inputs: CostOfDebtInputs) -> float:
    if inputs.total_debt <= 0:
        raise ValueError("total_debt must be positive to compute an effective rate")
    return inputs.interest_expense / inputs.total_debt


@dataclass
class WACCInputs:
    market_value_equity: float   # share_price * shares_outstanding
    market_value_debt: float     # book value used as proxy, see module docstring
    cost_of_equity: float
    cost_of_debt: float
    tax_rate: float


def wacc(inputs: WACCInputs) -> float:
    total_capital = inputs.market_value_equity + inputs.market_value_debt
    if total_capital <= 0:
        raise ValueError("market_value_equity + market_value_debt must be positive")

    weight_equity = inputs.market_value_equity / total_capital
    weight_debt = inputs.market_value_debt / total_capital

    after_tax_cost_of_debt = inputs.cost_of_debt * (1 - inputs.tax_rate)

    return (weight_equity * inputs.cost_of_equity) + (weight_debt * after_tax_cost_of_debt)