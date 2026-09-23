import pytest

from equity_valuation.wacc import (
    CostOfEquityInputs,
    CostOfDebtInputs,
    WACCInputs,
    cost_of_equity_capm,
    cost_of_debt_effective_rate,
    wacc,
)


def test_cost_of_equity_capm_hand_calculated():
    # 3% + 1.2 * 5% = 3% + 6% = 9%
    inputs = CostOfEquityInputs(risk_free_rate=0.03, beta=1.2, equity_risk_premium=0.05)
    assert cost_of_equity_capm(inputs) == pytest.approx(0.09)


def test_cost_of_debt_effective_rate_hand_calculated():
    # 50 interest / 1000 debt = 5%
    inputs = CostOfDebtInputs(interest_expense=50.0, total_debt=1000.0)
    assert cost_of_debt_effective_rate(inputs) == pytest.approx(0.05)


def test_cost_of_debt_rejects_zero_debt():
    inputs = CostOfDebtInputs(interest_expense=50.0, total_debt=0.0)
    with pytest.raises(ValueError):
        cost_of_debt_effective_rate(inputs)


def test_wacc_hand_calculated_60_40_split():
    # Equity 600, Debt 400 -> weights 60%/40%
    # cost_of_equity = 10%, cost_of_debt = 5%, tax_rate = 20%
    # after_tax_cost_of_debt = 5% * (1 - 0.20) = 4%
    # WACC = 0.6*10% + 0.4*4% = 6% + 1.6% = 7.6%
    inputs = WACCInputs(
        market_value_equity=600.0,
        market_value_debt=400.0,
        cost_of_equity=0.10,
        cost_of_debt=0.05,
        tax_rate=0.20,
    )
    assert wacc(inputs) == pytest.approx(0.076)


def test_wacc_all_equity_equals_cost_of_equity():
    # No debt -> WACC should collapse to cost of equity exactly
    inputs = WACCInputs(
        market_value_equity=1000.0,
        market_value_debt=0.0,
        cost_of_equity=0.11,
        cost_of_debt=0.05,
        tax_rate=0.20,
    )
    assert wacc(inputs) == pytest.approx(0.11)


def test_wacc_rejects_zero_total_capital():
    inputs = WACCInputs(
        market_value_equity=0.0,
        market_value_debt=0.0,
        cost_of_equity=0.10,
        cost_of_debt=0.05,
        tax_rate=0.20,
    )
    with pytest.raises(ValueError):
        wacc(inputs)