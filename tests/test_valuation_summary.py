import pytest

from equity_valuation.valuation_summary import CompsSummary, DCFSummary, ValuationSummary, format_valuation_summary


def test_format_valuation_summary_includes_all_sections():
    summary = ValuationSummary(
        ticker="TEST",
        current_market_value_equity=1000.0,
        dcf=DCFSummary(
            base_fcf=100.0, discount_rate=0.10,
            point_estimate_value_per_share=50.0,
            sensitivity_low=40.0, sensitivity_high=60.0,
        ),
        comps=[
            CompsSummary(
                metric_name="ev_ebitda", peer_median_multiple=8.0,
                implied_equity_value_low=700.0, implied_equity_value_median=800.0,
                implied_equity_value_high=900.0, warnings=[],
            ),
        ],
    )
    output = format_valuation_summary(summary)
    assert "TEST" in output
    assert "DCF" in output
    assert "Comps" in output
    assert "50.00" in output  # point estimate
    assert "ev_ebitda" in output


def test_format_valuation_summary_includes_warnings_when_present():
    summary = ValuationSummary(
        ticker="TEST", current_market_value_equity=1000.0,
        dcf=DCFSummary(base_fcf=100.0, discount_rate=0.10, point_estimate_value_per_share=50.0,
                       sensitivity_low=40.0, sensitivity_high=60.0),
        comps=[
            CompsSummary(
                metric_name="pe", peer_median_multiple=15.0,
                implied_equity_value_low=700.0, implied_equity_value_median=800.0,
                implied_equity_value_high=900.0,
                warnings=["WARNING: test peer misalignment"],
            ),
        ],
    )
    output = format_valuation_summary(summary)
    assert "WARNING: test peer misalignment" in output


def test_format_valuation_summary_handles_no_comps_data():
    """If every metric was skipped (no usable peer data at all), comps
    list is empty -- format function should not crash."""
    summary = ValuationSummary(
        ticker="TEST", current_market_value_equity=1000.0,
        dcf=DCFSummary(base_fcf=100.0, discount_rate=0.10, point_estimate_value_per_share=50.0,
                       sensitivity_low=40.0, sensitivity_high=60.0),
        comps=[],
    )
    output = format_valuation_summary(summary)
    assert "TEST" in output
    assert "DCF" in output