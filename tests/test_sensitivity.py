import pytest

from equity_valuation.dcf import NaiveDCFInputs
from equity_valuation.sensitivity import sensitivity_grid


@pytest.fixture
def base_inputs():
    return NaiveDCFInputs(
        base_fcf=100.0,
        growth_rate=0.10,       # overwritten per grid cell
        discount_rate=0.10,     # overwritten per grid cell
        terminal_growth_rate=0.03,
        projection_years=5,
        net_debt=200.0,
        shares_outstanding=50.0,
    )


def test_grid_reproduces_known_naive_dcf_point(base_inputs):
    """
    growth=10%, discount=10% is the exact case verified by hand in the
    naive DCF step (each explicit-year PV = 100.0). Cross-check that the
    grid reproduces the same value_per_share as calling run_naive_dcf directly.
    """
    from equity_valuation.dcf import run_naive_dcf

    direct = run_naive_dcf(base_inputs)["value_per_share"]

    grid = sensitivity_grid(base_inputs, growth_rates=[0.10], discount_rates=[0.10])

    assert grid[(0.10, 0.10)] == pytest.approx(direct)


def test_infeasible_combination_returns_none(base_inputs):
    """terminal_growth_rate is 3% in base_inputs; a 2% discount rate is invalid."""
    grid = sensitivity_grid(base_inputs, growth_rates=[0.10], discount_rates=[0.02])
    assert grid[(0.10, 0.02)] is None


def test_higher_discount_rate_lowers_value(base_inputs):
    """All else equal, a higher discount rate must produce a lower value per share."""
    grid = sensitivity_grid(base_inputs, growth_rates=[0.10], discount_rates=[0.08, 0.12])
    assert grid[(0.10, 0.08)] > grid[(0.10, 0.12)]


def test_higher_growth_rate_raises_value(base_inputs):
    """All else equal, a higher explicit-period growth rate must produce a higher value per share."""
    grid = sensitivity_grid(base_inputs, growth_rates=[0.08, 0.12], discount_rates=[0.10])
    assert grid[(0.08, 0.10)] < grid[(0.12, 0.10)]