"""
Throwaway diagnostic: see which years each concept has for AMD, same
approach as the earlier MSFT diagnosis. Delete once resolved.
"""

from equity_valuation.edgar_client import get_ticker_to_cik_map, get_cik_for_ticker, get_company_facts_raw
from equity_valuation.statement_assembly import (
    assemble_concept_series, assemble_total_debt_series, assemble_da_series, assemble_ebitda_series
)

ticker_map = get_ticker_to_cik_map()
cik = get_cik_for_ticker("AMD", ticker_map)
facts = get_company_facts_raw(cik)

concepts_to_check = [
    ("revenue", lambda: assemble_concept_series(facts, "revenue")["series"]),
    ("ebit", lambda: assemble_concept_series(facts, "ebit")["series"]),
    ("da", lambda: assemble_da_series(facts)),
    ("ebitda", lambda: assemble_ebitda_series(facts)),
    ("cash", lambda: assemble_concept_series(facts, "cash_and_equivalents")["series"]),
    ("debt", lambda: assemble_total_debt_series(facts)["series"]),
    ("net_income", lambda: assemble_concept_series(facts, "net_income")["series"]),
]

for name, fn in concepts_to_check:
    try:
        series = fn()
        years = sorted(series.keys())
        print(f"{name}: {len(years)} years, most recent 5: {years[-5:] if years else 'NONE'}")
    except Exception as e:
        print(f"{name}: EXCEPTION - {type(e).__name__}: {e}")