import pytest

from equity_valuation.credit_rating import (
    interest_coverage_ratio,
    synthetic_rating,
    cost_of_debt_synthetic_rating,
)


def test_interest_coverage_ratio_hand_calculated():
    # EBIT 500 / interest 100 = 5.0x
    assert interest_coverage_ratio(ebit=500.0, interest_expense=100.0) == pytest.approx(5.0)


def test_interest_coverage_rejects_zero_interest():
    with pytest.raises(ValueError):
        interest_coverage_ratio(ebit=500.0, interest_expense=0.0)


def test_synthetic_rating_matches_expected_bracket():
    # 5.0x coverage should fall in the 4.5-6.0 bracket -> "A-"
    bracket = synthetic_rating(5.0)
    assert bracket.rating == "A-"
    assert bracket.default_spread == pytest.approx(0.0140)


def test_synthetic_rating_boundary_is_inclusive_on_lower_bound():
    # exactly 4.5 should fall into the A- bracket (min_coverage inclusive), not BBB
    bracket = synthetic_rating(4.5)
    assert bracket.rating == "A-"


def test_synthetic_rating_worst_bracket_for_low_coverage():
    bracket = synthetic_rating(0.2)
    assert bracket.rating == "D"


def test_synthetic_rating_best_bracket_for_high_coverage():
    bracket = synthetic_rating(50.0)
    assert bracket.rating == "AAA"


def test_cost_of_debt_synthetic_rating_hand_calculated():
    # coverage = 500/100 = 5.0x -> A- bracket, spread 1.40%
    # risk_free_rate 4% -> cost_of_debt = 4% + 1.40% = 5.40%
    cost, bracket = cost_of_debt_synthetic_rating(
        ebit=500.0, interest_expense=100.0, risk_free_rate=0.04
    )
    assert cost == pytest.approx(0.054)
    assert bracket.rating == "A-"


def test_higher_coverage_never_produces_higher_cost_of_debt():
    """Monotonicity check: better coverage should never increase cost of debt."""
    low_coverage_cost, _ = cost_of_debt_synthetic_rating(
        ebit=150.0, interest_expense=100.0, risk_free_rate=0.04
    )
    high_coverage_cost, _ = cost_of_debt_synthetic_rating(
        ebit=1000.0, interest_expense=100.0, risk_free_rate=0.04
    )
    assert high_coverage_cost <= low_coverage_cost