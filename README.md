# Equity Valuation Tool

A standalone Python engine for DCF and comparable-company valuation, built on real SEC EDGAR financial data. Pure calculation — no LLM involved in computing any number.

## What it does

- **DCF**: real historical free cash flow (from SEC filings), computed WACC (CAPM cost of equity + two cost-of-debt methods), terminal value, and a growth/discount-rate sensitivity table.
- **Comps**: EV/EBITDA, EV/EBIT, EV/Revenue, and P/E multiples for a manually-selected peer group, with implied valuation ranges and fiscal-year misalignment warnings.
- **Combined summary**: both methods, side by side, for one target company — deliberately not blended into a single number.

## Data sources

- **SEC EDGAR** (`data.sec.gov`) — primary source for all historical financial statement data.
- **yfinance** — current share price and shares outstanding only; not used for historical statement line items (see "Known limitations").
- **FRED / Damodaran data** — not yet integrated; risk-free rate, beta, and equity risk premium are currently manual inputs.

## Installation

```powershell
uv sync
```

## Usage

```powershell
uv run equity-valuation AAPL --peers MSFT GOOGL
```

Optional arguments (all have defaults):

```powershell
uv run equity-valuation NVDA --peers AMD QCOM `
    --growth-rate 0.10 --terminal-growth-rate 0.03 --projection-years 5 `
    --beta 1.3 --risk-free-rate 0.04 --equity-risk-premium 0.05 --tax-rate 0.21
```

Run `uv run equity-valuation --help` for the full list.

## Testing

```powershell
uv run pytest -v
```

85 tests, all hand-calculable against known values — see `tests/`.

## Known limitations

- **Peer selection is manual, by design.** This tool does not screen or suggest peers — comparability is a judgment call left to the user.
- **No TTM (trailing-twelve-months) data.** Multiples use each company's own most recent fiscal year, which can differ from a peer's by several months. A fiscal-year-misalignment warning is surfaced when the gap exceeds ~120 days, but the underlying data is not time-aligned.
- **Growth rate, beta, and equity risk premium are manual DCF inputs**, not derived from historical trend analysis or a live source.
- **Cost of debt** falls back to a synthetic credit-rating-based estimate when a company's interest expense data is stale (>400 days older than its debt data) or missing entirely.
- **Effective tax rate** falls back to a flat placeholder (21%) for a year missing tax data.
- Built and tested against US GAAP filers only; not evaluated against foreign private issuers (20-F filers).

## Project structure

```
src/equity_valuation/
    edgar_client.py       # raw SEC EDGAR fetch (ticker->CIK, company facts)
    tag_lookup.py         # single-tag-with-fallback lookup, merged across tag switches
    subtag_lookup.py      # sum-of-subtags lookup (debt, D&A) with combined/split merging
    statement_mapping.py  # period filtering and duplicate-period resolution
    statement_assembly.py # assembles clean multi-year series per concept, incl. FCF
    wacc.py                # CAPM cost of equity, two cost-of-debt methods
    credit_rating.py      # synthetic credit rating -> spread (cost of debt Option B)
    dcf.py                 # naive DCF engine
    sensitivity.py         # growth/discount rate sensitivity grid
    comps.py                # multiples calculations
    comps_data.py          # assembles CompanyFinancials from real data
    peer_analysis.py       # peer summarization, implied ranges, fiscal-year warnings
    valuation_summary.py   # combines DCF + comps for one ticker
    cli.py                  # command-line interface
    yfinance_client.py     # current price/shares (cross-check only)
```