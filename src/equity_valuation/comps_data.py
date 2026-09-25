"""
Assembles a CompanyFinancials snapshot (from comps.py) for a real company,
using its most recent fiscal year of EDGAR data plus current market price.

FLAG: mixing "most recent fiscal year" financials (which can be up to
~12 months stale, depending where we are relative to the company's
fiscal year end) with TODAY's market price/share count is a real,
known inconsistency in this v1 approach -- proper practice often uses
trailing-twelve-month (TTM) financials, blending the most recent annual
figures with the most recent quarterly data to get a rolling 12-month
window closer to today. TTM is NOT implemented here; this uses the
latest full fiscal year only. This matters more for peer comparisons
where two companies have different fiscal year-end dates (comparing a
peer whose "most recent year" ended 2 months ago against one whose
"most recent year" ended 11 months ago is not a clean apples-to-apples
comparison) -- worth being explicit about when interpreting comps
results, not something this function silently corrects.
"""

from equity_valuation.edgar_client import get_ticker_to_cik_map, get_cik_for_ticker, get_company_facts_raw
from equity_valuation.statement_assembly import assemble_concept_series, assemble_total_debt_series, assemble_ebitda_series
from equity_valuation.yfinance_client import get_current_price_and_shares
from equity_valuation.comps import CompanyFinancials


def build_company_financials(ticker: str, ticker_map: dict) -> dict:
    """
    Returns {"fiscal_year_end": str, "financials": CompanyFinancials}
    for the given ticker's most recent fiscal year, using EDGAR for
    financials and yfinance for current price/shares.
    """
    cik = get_cik_for_ticker(ticker, ticker_map)
    facts = get_company_facts_raw(cik)

    revenue = assemble_concept_series(facts, "revenue")["series"]
    ebit = assemble_concept_series(facts, "ebit")["series"]
    ebitda = assemble_ebitda_series(facts)
    cash = assemble_concept_series(facts, "cash_and_equivalents")["series"]
    debt = assemble_total_debt_series(facts)["series"]

    # Net income isn't in our concept set yet -- add it now, since P/E needs it.
    net_income = assemble_concept_series(facts, "net_income")["series"]

    common_years = set(revenue) & set(ebit) & set(ebitda) & set(cash) & set(debt) & set(net_income)
    if not common_years:
        raise ValueError(f"No fiscal year has all required concepts available for {ticker}")
    most_recent_year = max(common_years)

    market_data = get_current_price_and_shares(ticker)
    market_value_equity = market_data["price"] * market_data["shares_outstanding"]

    financials = CompanyFinancials(
        market_value_equity=market_value_equity,
        total_debt=debt[most_recent_year],
        cash_and_equivalents=cash[most_recent_year],
        ebitda=ebitda[most_recent_year],
        ebit=ebit[most_recent_year],
        revenue=revenue[most_recent_year],
        net_income=net_income[most_recent_year],
    )
    return {"fiscal_year_end": most_recent_year, "financials": financials}