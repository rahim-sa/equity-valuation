import pytest

from equity_valuation.peer_analysis import PeerMultiples, summarize_multiple, implied_valuation_range


def _peer(ticker, ev_ebitda=None, ev_ebit=None, ev_revenue=None, pe=None):
    return PeerMultiples(
        ticker=ticker, fiscal_year_end="2024-12-31",
        ev_ebitda=ev_ebitda, ev_ebit=ev_ebit, ev_revenue=ev_revenue, pe=pe,
    )


def test_summarize_multiple_hand_calculated_median_and_mean():
    peers = [_peer("A", ev_ebitda=8.0), _peer("B", ev_ebitda=10.0), _peer("C", ev_ebitda=12.0)]
    summary = summarize_multiple(peers, "ev_ebitda")
    assert summary.median == pytest.approx(10.0)
    assert summary.mean == pytest.approx(10.0)
    assert summary.minimum == pytest.approx(8.0)
    assert summary.maximum == pytest.approx(12.0)


def test_summarize_multiple_excludes_none_values_explicitly():
    peers = [_peer("A", ev_ebitda=8.0), _peer("B", ev_ebitda=None), _peer("C", ev_ebitda=12.0)]
    summary = summarize_multiple(peers, "ev_ebitda")
    assert summary.values == [8.0, 12.0]
    assert summary.excluded_tickers == ["B"]


def test_summarize_multiple_raises_when_no_peer_has_meaningful_value():
    peers = [_peer("A", ev_ebitda=None), _peer("B", ev_ebitda=None)]
    with pytest.raises(ValueError):
        summarize_multiple(peers, "ev_ebitda")


def test_summarize_multiple_median_differs_from_mean_with_outlier():
    """Confirms outlier sensitivity is visible: mean should be pulled up
    by the outlier while median stays near the cluster."""
    peers = [_peer("A", ev_ebitda=8.0), _peer("B", ev_ebitda=9.0), _peer("C", ev_ebitda=40.0)]
    summary = summarize_multiple(peers, "ev_ebitda")
    assert summary.median == pytest.approx(9.0)
    assert summary.mean == pytest.approx(19.0)
    assert summary.mean > summary.median


def test_implied_valuation_range_hand_calculated_for_ev_metric():
    peers = [_peer("A", ev_ebitda=8.0), _peer("B", ev_ebitda=10.0), _peer("C", ev_ebitda=12.0)]
    summary = summarize_multiple(peers, "ev_ebitda")
    # target EBITDA = 100 -> low = 8*100=800, median=10*100=1000, high=12*100=1200
    result = implied_valuation_range(summary, target_metric_value=100.0)
    assert result["low"] == pytest.approx(800.0)
    assert result["median"] == pytest.approx(1000.0)
    assert result["high"] == pytest.approx(1200.0)


def test_implied_valuation_range_hand_calculated_for_pe_metric():
    peers = [_peer("A", pe=15.0), _peer("B", pe=20.0), _peer("C", pe=25.0)]
    summary = summarize_multiple(peers, "pe")
    # target net income = 50 -> low=15*50=750, median=20*50=1000, high=25*50=1250
    result = implied_valuation_range(summary, target_metric_value=50.0)
    assert result["low"] == pytest.approx(750.0)
    assert result["median"] == pytest.approx(1000.0)
    assert result["high"] == pytest.approx(1250.0)