import pytest

from equity_valuation.comps import (
    CompanyFinancials,
    enterprise_value,
    ev_to_ebitda,
    ev_to_ebit,
    ev_to_revenue,
    price_to_earnings,
    implied_value_from_peer_multiple,
)


@pytest.fixture
def sample_financials():
    return CompanyFinancials(
        market_value_equity=1000.0,
        total_debt=300.0,
        cash_and_equivalents=100.0,
        ebitda=200.0,
        ebit=150.0,
        revenue=800.0,
        net_income=100.0,
    )


def test_enterprise_value_hand_calculated(sample_financials):
    # 1000 + 300 - 100 = 1200
    assert enterprise_value(sample_financials) == pytest.approx(1200.0)


def test_ev_to_ebitda_hand_calculated(sample_financials):
    # 1200 / 200 = 6.0x
    assert ev_to_ebitda(sample_financials) == pytest.approx(6.0)


def test_ev_to_ebit_hand_calculated(sample_financials):
    # 1200 / 150 = 8.0x
    assert ev_to_ebit(sample_financials) == pytest.approx(8.0)


def test_ev_to_revenue_hand_calculated(sample_financials):
    # 1200 / 800 = 1.5x
    assert ev_to_revenue(sample_financials) == pytest.approx(1.5)


def test_price_to_earnings_hand_calculated(sample_financials):
    # 1000 / 100 = 10.0x
    assert price_to_earnings(sample_financials) == pytest.approx(10.0)


def test_ev_to_ebitda_rejects_negative_ebitda(sample_financials):
    sample_financials.ebitda = -50.0
    with pytest.raises(ValueError):
        ev_to_ebitda(sample_financials)


def test_price_to_earnings_rejects_negative_net_income(sample_financials):
    sample_financials.net_income = -20.0
    with pytest.raises(ValueError):
        price_to_earnings(sample_financials)


def test_implied_value_from_ebitda_multiple():
    # peer trades at 8x EBITDA, target has 50 EBITDA -> implied EV = 400
    assert implied_value_from_peer_multiple(8.0, 50.0, "ebitda") == pytest.approx(400.0)


def test_implied_value_from_pe_multiple():
    # peer trades at 15x earnings, target has 20 net income -> implied equity value = 300
    assert implied_value_from_peer_multiple(15.0, 20.0, "net_income") == pytest.approx(300.0)


def test_implied_value_rejects_invalid_metric_type():
    with pytest.raises(ValueError):
        implied_value_from_peer_multiple(10.0, 50.0, "not_a_real_metric")