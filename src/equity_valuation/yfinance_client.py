"""
yfinance data access, for cross-checking EDGAR-derived figures only --
NOT a primary data source for this project (see data-source assessment
at project start: yfinance's cash flow statement fields are the least
reliable, history is typically limited to ~4 years, and field
availability can be inconsistent).

Used here specifically to compare its reported figures against our
EDGAR-derived ones for the same company/years, surfacing discrepancies
rather than trusting either source blindly.
"""

import yfinance as yf


def get_yfinance_annual_financials(ticker: str) -> dict:
    """
    Returns a dict of DataFrames: {"income_stmt": df, "cash_flow": df,
    "balance_sheet": df}, each indexed by line item with columns as
    fiscal year-end dates (most recent first, typically ~4 years).
    """
    t = yf.Ticker(ticker)
    return {
        "income_stmt": t.income_stmt,
        "cash_flow": t.cash_flow,
        "balance_sheet": t.balance_sheet,
    }