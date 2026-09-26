"""
End-to-end DCF using real EDGAR-derived financials for one company.

Beta, risk-free rate, and equity risk premium are still manually
specified placeholders -- live sourcing from FRED/Damodaran is planned
future work, not part of this step. Everything else (FCF history,
interest expense, total debt, shares/price) now comes from real data.
"""

from equity_valuation.edgar_client import get_ticker_to_cik_map, get_cik_for_ticker, get_company_facts_raw
from equity_valuation.statement_assembly import assemble_unlevered_fcf_series, assemble_total_debt_series, assemble_concept_series
from equity_valuation.yfinance_client import get_current_price_and_shares
from equity_valuation.wacc import (
    CostOfEquityInputs, CostOfDebtInputs, WACCInputs,
    cost_of_equity_capm, cost_of_debt_effective_rate, wacc,
)
from equity_valuation.dcf import NaiveDCFInputs, run_naive_dcf
from equity_valuation.sensitivity import sensitivity_grid, format_grid

TICKER = "AAPL"

# --- Pull and assemble real data ---
ticker_map = get_ticker_to_cik_map()
cik = get_cik_for_ticker(TICKER, ticker_map)
facts = get_company_facts_raw(cik)

fcf_series = assemble_unlevered_fcf_series(facts)
debt_series = assemble_total_debt_series(facts)
interest_series = assemble_concept_series(facts, "interest_expense")["series"]
cash_series = assemble_concept_series(facts, "cash_and_equivalents")["series"]

most_recent_year = max(fcf_series.keys())
base_fcf = fcf_series[most_recent_year]
most_recent_debt = debt_series[max(debt_series.keys())]
most_recent_cash = cash_series[max(cash_series.keys())]
net_debt = most_recent_debt - most_recent_cash

print(f"Most recent fiscal year used: {most_recent_year}")
print(f"Base FCF: {base_fcf:,.0f}")
print(f"Most recent total debt: {most_recent_debt:,.0f}")
print(f"Most recent cash: {most_recent_cash:,.0f}")
print(f"Net debt: {net_debt:,.0f}")

# --- Current market data ---
market_data = get_current_price_and_shares(TICKER)
share_price = market_data["price"]
shares_outstanding = market_data["shares_outstanding"]
market_value_equity = share_price * shares_outstanding

print(f"\nCurrent share price: {share_price}")
print(f"Shares outstanding: {shares_outstanding:,.0f}")
print(f"Market value of equity: {market_value_equity:,.0f}")

# --- WACC (still using manual beta/risk-free/ERP placeholders) ---
risk_free_rate = 0.04
coe_inputs = CostOfEquityInputs(risk_free_rate=risk_free_rate, beta=1.2, equity_risk_premium=0.05)
cost_of_equity = cost_of_equity_capm(coe_inputs)

most_recent_interest_year = max(interest_series.keys()) if interest_series else None
if most_recent_interest_year is not None:
    cod_inputs = CostOfDebtInputs(
        interest_expense=interest_series[most_recent_interest_year],
        total_debt=most_recent_debt,
    )
    cost_of_debt = cost_of_debt_effective_rate(cod_inputs)
    print(f"\nCost of debt computed from FY{most_recent_interest_year} interest expense")
else:
    # KNOWN LIMITATION (see tag_lookup.py comment): recent interest expense
    # may be unavailable for companies that stopped breaking it out as a
    # standalone tag. Falling back to a placeholder here is a deliberate,
    # visible simplification -- Option B (synthetic rating) would be the
    # better real fallback, not implemented in this wiring step yet.
    cost_of_debt = 0.04
    print("\nWARNING: no interest expense data found -- using placeholder cost of debt")

wacc_inputs = WACCInputs(
    market_value_equity=market_value_equity,
    market_value_debt=most_recent_debt,
    cost_of_equity=cost_of_equity,
    cost_of_debt=cost_of_debt,
    tax_rate=0.21,
)
discount_rate = wacc(wacc_inputs)

print(f"cost_of_equity: {cost_of_equity:.4f}")
print(f"cost_of_debt: {cost_of_debt:.4f}")
print(f"computed WACC (discount_rate): {discount_rate:.4f}")

# --- DCF using real base FCF and computed WACC ---
# growth_rate and terminal_growth_rate are still manual assumptions --
# a real projection would derive growth from historical trend analysis,
# not a single hardcoded forward-looking guess. Out of scope for this
# wiring step specifically.
dcf_inputs = NaiveDCFInputs(
    base_fcf=base_fcf,
    growth_rate=0.08,
    discount_rate=discount_rate,
    terminal_growth_rate=0.03,
    projection_years=5,
    net_debt=net_debt,
    shares_outstanding=shares_outstanding,
)

result = run_naive_dcf(dcf_inputs)
print("\n--- DCF result ---")
for key, value in result.items():
    print(f"{key}: {value}")

# --- Sensitivity table ---
growth_rates = [0.04, 0.06, 0.08, 0.10, 0.12]
discount_rates = [discount_rate - 0.02, discount_rate - 0.01, discount_rate, discount_rate + 0.01, discount_rate + 0.02]

grid = sensitivity_grid(dcf_inputs, growth_rates, discount_rates)
print("\nSensitivity table (value per share):")
print(format_grid(grid, growth_rates, discount_rates))