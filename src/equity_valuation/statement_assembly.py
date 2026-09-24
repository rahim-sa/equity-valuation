
"""
Assembles a clean multi-year annual series per concept, chaining:
  raw entries (tag_lookup, merged across fallback tags)
    -> annual-only filter (duration OR instant, depending on concept)
    -> duplicate-period resolution
    -> clean {fiscal_year_end: value} series

Debt is always instant (balance sheet), regardless of combined-vs-summed mode.
"""

from equity_valuation.tag_lookup import get_raw_entries_for_concept, INSTANT_CONCEPTS
from equity_valuation.subtag_lookup import get_total_debt_components
from equity_valuation.statement_mapping import (
    select_annual_facts,
    resolve_duplicate_periods,
    select_annual_instant_facts,
    resolve_duplicate_instant_periods,
)


def assemble_concept_series(company_facts: dict, concept: str) -> dict:
    """
    Returns {"tags_used": list[str], "series": {fiscal_year_end (str): value (float)}}.
    """
    raw_entries, tags_used = get_raw_entries_for_concept(company_facts, concept)

    if concept in INSTANT_CONCEPTS:
        annual = select_annual_instant_facts(raw_entries)
        resolved = resolve_duplicate_instant_periods(annual)
    else:
        annual = select_annual_facts(raw_entries)
        resolved = resolve_duplicate_periods(annual)

    series = {entry["end"]: entry["val"] for entry in resolved}
    return {"tags_used": tags_used, "series": series}


def assemble_total_debt_series(company_facts: dict) -> dict:
    """
    Returns {"mode": "combined"|"summed", "series": {fiscal_year_end: value}}.
    Debt entries are instant facts -- always uses the instant filter/resolver.
    """
    components = get_total_debt_components(company_facts)

    if components["mode"] == "combined":
        annual = select_annual_instant_facts(components["entries"])
        resolved = resolve_duplicate_instant_periods(annual)
        series = {entry["end"]: entry["val"] for entry in resolved}
        return {"mode": "combined", "series": series}

    per_tag_series = {}
    for tag_name, entries in components["subtag_entries"].items():
        annual = select_annual_instant_facts(entries)
        resolved = resolve_duplicate_instant_periods(annual)
        per_tag_series[tag_name] = {entry["end"]: entry["val"] for entry in resolved}

    all_years = set.union(*(set(s.keys()) for s in per_tag_series.values())) if per_tag_series else set()
    summed_series = {
        year: sum(series.get(year, 0) for series in per_tag_series.values())
        for year in all_years
    }
    return {"mode": "summed", "series": summed_series}