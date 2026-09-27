import pytest

from equity_valuation.cli import build_arg_parser, main


def test_parser_requires_ticker():
    parser = build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--peers", "MSFT"])  # missing required ticker


def test_parser_requires_peers():
    parser = build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["AAPL"])  # missing required --peers


def test_parser_accepts_valid_minimal_args():
    parser = build_arg_parser()
    args = parser.parse_args(["AAPL", "--peers", "MSFT", "GOOGL"])
    assert args.ticker == "AAPL"
    assert args.peers == ["MSFT", "GOOGL"]
    assert args.growth_rate == 0.08  # default


def test_parser_accepts_custom_assumptions():
    parser = build_arg_parser()
    args = parser.parse_args(["NVDA", "--peers", "AMD", "--beta", "1.3", "--growth-rate", "0.10"])
    assert args.beta == 1.3
    assert args.growth_rate == 0.10


def test_main_returns_error_code_for_invalid_ticker(monkeypatch):
    """A ticker not in SEC's mapping should exit cleanly with an error
    code, not crash with an unhandled traceback."""
    def _raise_value_error(*args, **kwargs):
        raise ValueError("Ticker 'ZZZZZZZ' not found in SEC ticker-to-CIK mapping")

    import equity_valuation.cli as cli_module
    monkeypatch.setattr(cli_module, "build_valuation_summary", _raise_value_error)

    exit_code = main(["ZZZZZZZ", "--peers", "MSFT"])
    assert exit_code == 1