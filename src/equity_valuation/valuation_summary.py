"""
Combines DCF and comps into a single summary for one target company.

Deliberately does NOT blend the two into one "best estimate" number --
DCF and comps answer different questions (intrinsic value based on
projected cash flows vs. relative value based on how the market currently
prices similar companies) and can legitimately disagree. Collapsing them
into one number would hide that disagreement, which is itself meaningful
information, not noise to average away.

Peer selection remains manual (the peer_tickers argument) -- consistent
with the deliberate design choice made in peer_analysis.py: peer
comparability is a judgment call, not something this tool decides for you.
"""

from dataclasses import dataclass

from equity_valuation.edgar_client import get_ticker_to_cik_map, get_cik_for_ticker, get_company_facts_raw
from equity_valuation.statement_assembly import assemble_unlevered_fcf_series, assemble_total_debt_series, assemble_concept_series
from equity_valuation.yfinance_client import get_current_price_and_shares
from equity_valuation.wacc import CostOfEquityInputs, CostOfDebtInputs, WACCInputs, cost_of_equity_capm, cost_of_debt_effective_rate, wacc
from equity_valuation.dcf import NaiveDCFInputs, run_naive_dcf
from equity_valuation.sensitivity import sensitivity_grid
from equity_valuation.comps_data import build_company_financials
from equity_valuation.peer_analysis import compute_peer_multiples, summarize_multiple, implied_valuation_range, check_fiscal_year_alignment


@dataclass
class DCFSummary:
    base_fcf: float
    discount_rate: float
    point_estimate_value_per_share: float
    sensitivity_low: float   # lowest value_per_share in the sensitivity grid
    sensitivity_high: float  # highest value_per_share in the sensitivity grid


@dataclass
class CompsSummary:
    metric_name: str
    peer_median_multiple: float
    implied_equity_value_low: float
    implied_equity_value_median: float
    implied_equity_value_high: float
    warnings: list[str]


@dataclass
class ValuationSummary:
    ticker: str
    current_market_value_equity: float
    dcf: DCFSummary
    comps: list[CompsSummary]  # one entry per multiple type that had usable peer data


def run_dcf_for_ticker(
    ticker: str, ticker_map: dict,
    growth_rate: float = 0.08, terminal_growth_rate: float = 0.03, projection_years: int = 5,
    beta: float = 1.1, risk_free_rate: float = 0.04, equity_risk_premium: float = 0.05,
    tax_rate: float = 0.21,
) -> DCFSummary:
    """Runs the full real-data DCF pipeline for one ticker. Assumptions
    (growth, beta, ERP) remain manual inputs -- same limitation as
    __main__.py's existing wiring, not resolved here."""
    cik = get_cik_for_ticker(ticker, ticker_map)
    facts = get_company_facts_raw(cik)

    fcf_series = assemble_unlevered_fcf_series(facts)
    debt_series = assemble_total_debt_series(facts)
    cash_series = assemble_concept_series(facts, "cash_and_equivalents")["series"]
    interest_series = assemble_concept_series(facts, "interest_expense")["series"]

    most_recent_year = max(fcf_series.keys())
    base_fcf = fcf_series[most_recent_year]
    most_recent_debt = debt_series[max(debt_series.keys())]
    most_recent_cash = cash_series[max(cash_series.keys())]
    net_debt = most_recent_debt - most_recent_cash

    market_data = get_current_price_and_shares(ticker)
    market_value_equity = market_data["price"] * market_data["shares_outstanding"]

    coe_inputs = CostOfEquityInputs(risk_free_rate=risk_free_rate, beta=beta, equity_risk_premium=equity_risk_premium)
    cost_of_equity = cost_of_equity_capm(coe_inputs)

    if interest_series:
        most_recent_interest_year = max(interest_series.keys())
        cost_of_debt = cost_of_debt_effective_rate(
            CostOfDebtInputs(interest_expense=interest_series[most_recent_interest_year], total_debt=most_recent_debt)
        )
    else:
        cost_of_debt = 0.04  # placeholder, same known limitation as __main__.py

    discount_rate = wacc(WACCInputs(
        market_value_equity=market_value_equity, market_value_debt=most_recent_debt,
        cost_of_equity=cost_of_equity, cost_of_debt=cost_of_debt, tax_rate=tax_rate,
    ))

    dcf_inputs = NaiveDCFInputs(
        base_fcf=base_fcf, growth_rate=growth_rate, discount_rate=discount_rate,
        terminal_growth_rate=terminal_growth_rate, projection_years=projection_years,
        net_debt=net_debt, shares_outstanding=market_data["shares_outstanding"],
    )
    point_result = run_naive_dcf(dcf_inputs)

    # Small sensitivity band around the point estimate for a low/high range
    growth_range = [growth_rate - 0.02, growth_rate, growth_rate + 0.02]
    discount_range = [discount_rate - 0.01, discount_rate, discount_rate + 0.01]
    grid = sensitivity_grid(dcf_inputs, growth_range, discount_range)
    valid_values = [v for v in grid.values() if v is not None]

    return DCFSummary(
        base_fcf=base_fcf, discount_rate=discount_rate,
        point_estimate_value_per_share=point_result["value_per_share"],
        sensitivity_low=min(valid_values), sensitivity_high=max(valid_values),
    )


def run_comps_for_ticker(ticker: str, peer_tickers: list[str], ticker_map: dict) -> list[CompsSummary]:
    """Runs peer comps for one ticker against a manually-supplied peer list.
    Returns one CompsSummary per multiple type that had usable peer data --
    a multiple type with zero usable peers is skipped, not force-included.

    EV-based metrics (ev_ebitda, ev_ebit, ev_revenue) produce an implied
    ENTERPRISE value from implied_valuation_range -- net debt is subtracted
    here to convert to equity value, so every row in the output is on a
    consistent, comparable equity-value basis. P/E already operates at the
    equity level and needs no adjustment.
    """
    target_result = build_company_financials(ticker, ticker_map)
    target_financials = target_result["financials"]
    net_debt = target_financials.total_debt - target_financials.cash_and_equivalents

    peer_multiples = [compute_peer_multiples(t, ticker_map) for t in peer_tickers]
    warnings = check_fiscal_year_alignment(target_result["fiscal_year_end"], peer_multiples)

    metric_map = {
        "ev_ebitda": target_financials.ebitda,
        "ev_ebit": target_financials.ebit,
        "ev_revenue": target_financials.revenue,
        "pe": target_financials.net_income,
    }
    ev_based_metrics = {"ev_ebitda", "ev_ebit", "ev_revenue"}

    summaries = []
    for metric_name, target_metric_value in metric_map.items():
        try:
            summary = summarize_multiple(peer_multiples, metric_name)
        except ValueError:
            continue  # no peer had a meaningful value for this metric -- skip, don't force it
        implied = implied_valuation_range(summary, target_metric_value)

        if metric_name in ev_based_metrics:
            # implied values are ENTERPRISE value here -- subtract net debt to get equity value
            low = implied["low"] - net_debt
            median = implied["median"] - net_debt
            high = implied["high"] - net_debt
        else:
            low, median, high = implied["low"], implied["median"], implied["high"]

        summaries.append(CompsSummary(
            metric_name=metric_name, peer_median_multiple=summary.median,
            implied_equity_value_low=low, implied_equity_value_median=median,
            implied_equity_value_high=high, warnings=warnings,
        ))
    return summaries


def build_valuation_summary(ticker: str, peer_tickers: list[str], **dcf_kwargs) -> ValuationSummary:
    """Top-level entry point: DCF + comps for one target company."""
    ticker_map = get_ticker_to_cik_map()
    dcf_summary = run_dcf_for_ticker(ticker, ticker_map, **dcf_kwargs)
    comps_summaries = run_comps_for_ticker(ticker, peer_tickers, ticker_map)
    market_data = get_current_price_and_shares(ticker)

    return ValuationSummary(
        ticker=ticker,
        current_market_value_equity=market_data["price"] * market_data["shares_outstanding"],
        dcf=dcf_summary,
        comps=comps_summaries,
    )


def format_valuation_summary(summary: ValuationSummary) -> str:
    """Plain-text formatted output, side by side, no blending."""
    lines = [f"=== Valuation Summary: {summary.ticker} ===", ""]
    lines.append(f"Current market value of equity: {summary.current_market_value_equity:,.0f}")
    lines.append("")
    lines.append("--- DCF ---")
    lines.append(f"  Discount rate (WACC): {summary.dcf.discount_rate:.2%}")
    lines.append(f"  Point estimate value per share: {summary.dcf.point_estimate_value_per_share:.2f}")
    lines.append(f"  Sensitivity range: {summary.dcf.sensitivity_low:.2f} - {summary.dcf.sensitivity_high:.2f}")
    lines.append("")
    lines.append("--- Comps ---")
    for c in summary.comps:
        lines.append(f"  {c.metric_name} (peer median {c.peer_median_multiple:.2f}x):")
        lines.append(f"    Implied equity value: {c.implied_equity_value_low:,.0f} - {c.implied_equity_value_high:,.0f} "
                      f"(median {c.implied_equity_value_median:,.0f})")
    if summary.comps and summary.comps[0].warnings:
        lines.append("")
        for w in summary.comps[0].warnings:
            lines.append(f"  {w}")
    return "\n".join(lines)