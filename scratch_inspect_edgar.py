"""
Throwaway script to inspect real EDGAR data shape before building
parsing logic. Not part of the package -- delete once step 1 is confirmed working.
"""

from equity_valuation.edgar_client import get_ticker_to_cik_map, get_cik_for_ticker, get_company_facts_raw

ticker_map = get_ticker_to_cik_map()
print(f"Loaded {len(ticker_map)} tickers")

cik = get_cik_for_ticker("AAPL", ticker_map)
print(f"AAPL CIK: {cik}")

facts = get_company_facts_raw(cik)
print(f"Company name: {facts['entityName']}")
print(f"Top-level taxonomies: {list(facts['facts'].keys())}")

# Look at one concept's shape so we understand what we're parsing next step
revenue_concept = facts["facts"]["us-gaap"].get("Revenues")
if revenue_concept:
    print("\nSample 'Revenues' concept structure:")
    print(f"  label: {revenue_concept['label']}")
    print(f"  units: {list(revenue_concept['units'].keys())}")
    print(f"  first few USD entries: {revenue_concept['units']['USD'][:3]}")
else:
    print("\nNo 'Revenues' tag found for this company -- this itself is useful "
          "to know, since it confirms tag-name inconsistency is real, not theoretical.")