"""
Throwaway script: check real AAPL unlevered FCF against known reality.
Delete once confirmed working.
"""

from equity_valuation.edgar_client import get_ticker_to_cik_map, get_cik_for_ticker, get_company_facts_raw
from equity_valuation.statement_assembly import (
    assemble_nwc_series,
    assemble_delta_nwc_series,
    assemble_effective_tax_rate_series,
    assemble_unlevered_fcf_series,
)

ticker_map = get_ticker_to_cik_map()
cik = get_cik_for_ticker("AAPL", ticker_map)
facts = get_company_facts_raw(cik)

print("NWC by year:")
for year, val in sorted(assemble_nwc_series(facts).items()):
    print(f"  {year}: {val:,.0f}")

print("\nDelta NWC by year:")
for year, val in sorted(assemble_delta_nwc_series(facts).items()):
    print(f"  {year}: {val:,.0f}")

print("\nEffective tax rate by year:")
for year, val in sorted(assemble_effective_tax_rate_series(facts).items()):
    print(f"  {year}: {val:.2%}")

print("\nUnlevered FCF by year:")
for year, val in sorted(assemble_unlevered_fcf_series(facts).items()):
    print(f"  {year}: {val:,.0f}")