"""
Command-line interface for the equity valuation tool.

Usage:
    uv run equity-valuation AAPL --peers MSFT GOOGL
    uv run equity-valuation NVDA --peers AMD QCOM --growth-rate 0.10 --beta 1.3

This is a thin wrapper around valuation_summary.py -- no new financial
logic here, purely argument parsing and output formatting/error handling
for a standalone command-line experience.
"""

import argparse
import sys

from equity_valuation.valuation_summary import build_valuation_summary, format_valuation_summary
from equity_valuation.tag_lookup import ConceptNotFoundError
from equity_valuation.subtag_lookup import SubtagConceptNotFoundError


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="equity-valuation",
        description="Real-data DCF and comps valuation for a US public company.",
    )
    parser.add_argument("ticker", help="Target company ticker, e.g. AAPL")
    parser.add_argument(
        "--peers", nargs="+", required=True,
        help="One or more peer tickers for comps, e.g. --peers MSFT GOOGL. "
             "Peer selection is manual and deliberate -- this tool does not "
             "suggest or screen peers automatically.",
    )
    parser.add_argument("--growth-rate", type=float, default=0.08,
                         help="DCF explicit-period annual growth rate (default: 0.08)")
    parser.add_argument("--terminal-growth-rate", type=float, default=0.03,
                         help="DCF terminal (perpetuity) growth rate (default: 0.03)")
    parser.add_argument("--projection-years", type=int, default=5,
                         help="Number of explicit DCF projection years (default: 5)")
    parser.add_argument("--beta", type=float, default=1.1,
                         help="Beta used in CAPM cost of equity (default: 1.1, a manual placeholder)")
    parser.add_argument("--risk-free-rate", type=float, default=0.04,
                         help="Risk-free rate used in CAPM (default: 0.04)")
    parser.add_argument("--equity-risk-premium", type=float, default=0.05,
                         help="Equity risk premium used in CAPM (default: 0.05)")
    parser.add_argument("--tax-rate", type=float, default=0.21,
                         help="Tax rate used in WACC's after-tax cost of debt (default: 0.21)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary = build_valuation_summary(
            ticker=args.ticker,
            peer_tickers=args.peers,
            growth_rate=args.growth_rate,
            terminal_growth_rate=args.terminal_growth_rate,
            projection_years=args.projection_years,
            beta=args.beta,
            risk_free_rate=args.risk_free_rate,
            equity_risk_premium=args.equity_risk_premium,
            tax_rate=args.tax_rate,
        )
    except (ConceptNotFoundError, SubtagConceptNotFoundError) as e:
        print(f"Error: could not assemble required financial data -- {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(format_valuation_summary(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
    