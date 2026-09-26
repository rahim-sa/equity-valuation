"""
Throwaway diagnostic: find what D&A tags AMD uses in recent years, since
our combined+split tags only found data through 2019. Delete once resolved.
"""

from equity_valuation.edgar_client import get_ticker_to_cik_map, get_cik_for_ticker, get_company_facts_raw

ticker_map = get_ticker_to_cik_map()
cik = get_cik_for_ticker("AMD", ticker_map)
facts = get_company_facts_raw(cik)

us_gaap_tags = facts["facts"]["us-gaap"]

print("Tags containing 'epreciation' or 'mortization':")
for tag in sorted(us_gaap_tags.keys()):
    if "epreciation" in tag or "mortization" in tag:
        entries = us_gaap_tags[tag].get("units", {}).get("USD", [])
        tenk_entries = [e for e in entries if e.get("form") == "10-K"]
        years = sorted(set(e["end"] for e in tenk_entries))
        print(f"  {tag}: {len(tenk_entries)} 10-K entries, years: {years[-3:] if years else 'NONE'}")