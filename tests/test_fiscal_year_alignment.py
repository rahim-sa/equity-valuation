import pytest

from equity_valuation.peer_analysis import PeerMultiples, check_fiscal_year_alignment


def _peer(ticker, fiscal_year_end):
    return PeerMultiples(
        ticker=ticker, fiscal_year_end=fiscal_year_end,
        ev_ebitda=10.0, ev_ebit=10.0, ev_revenue=10.0, pe=10.0,
    )


def test_no_warning_when_fiscal_years_closely_aligned():
    peers = [_peer("A", "2024-12-31")]
    warnings = check_fiscal_year_alignment("2024-12-15", peers)
    assert warnings == []


def test_warns_when_fiscal_year_gap_exceeds_threshold():
    peers = [_peer("A", "2024-06-30")]  # ~6 months from 2024-12-31
    warnings = check_fiscal_year_alignment("2024-12-31", peers)
    assert len(warnings) == 1
    assert "A" in warnings[0]


def test_no_warning_exactly_at_threshold_boundary():
    # Exactly 120 days apart -- boundary is > threshold, not >=, so this should NOT warn
    peers = [_peer("A", "2024-09-02")]  # 2024-12-31 minus 120 days = 2024-09-02
    warnings = check_fiscal_year_alignment("2024-12-31", peers, warning_threshold_days=120)
    assert warnings == []


def test_warns_for_multiple_misaligned_peers_independently():
    peers = [_peer("A", "2024-06-30"), _peer("B", "2024-01-31")]
    warnings = check_fiscal_year_alignment("2024-12-31", peers)
    assert len(warnings) == 2


def test_custom_threshold_is_respected():
    peers = [_peer("A", "2024-11-30")]  # 31 days from 2024-12-31
    warnings_strict = check_fiscal_year_alignment("2024-12-31", peers, warning_threshold_days=30)
    warnings_loose = check_fiscal_year_alignment("2024-12-31", peers, warning_threshold_days=60)
    assert len(warnings_strict) == 1
    assert len(warnings_loose) == 0