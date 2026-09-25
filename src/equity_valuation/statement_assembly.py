
"""
Assembles a clean multi-year annual series per concept, chaining:
  raw entries (tag_lookup, merged across fallback tags)
    -> annual-only filter (duration OR instant, depending on concept)
    -> duplicate-period resolution
    -> clean {fiscal_year_end: value} series

Debt is always instant (balance sheet), regardless of combined-vs-summed mode.
"""
from equity_valuation.tag_lookup import get_raw_entries_for_concept, INSTANT_CONCEPTS, ConceptNotFoundError
from equity_valuation.subtag_lookup import get_total_debt_components, get_current_debt_only_components
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


def assemble_current_debt_series(company_facts: dict) -> dict:
    """Returns {fiscal_year_end: value}, current (short-term) debt only. See
    get_current_debt_only_components for why an empty result means 'unavailable',
    not necessarily zero."""
    components = get_current_debt_only_components(company_facts)
    per_tag_series = {}
    for tag_name, entries in components["subtag_entries"].items():
        annual = select_annual_instant_facts(entries)
        resolved = resolve_duplicate_instant_periods(annual)
        per_tag_series[tag_name] = {entry["end"]: entry["val"] for entry in resolved}

    if not per_tag_series:
        return {}

    all_years = set.union(*(set(s.keys()) for s in per_tag_series.values()))
    return {year: sum(series.get(year, 0) for series in per_tag_series.values()) for year in all_years}


def assemble_nwc_series(company_facts: dict) -> dict:
    """
    Non-cash net working capital per fiscal year end:
        NWC = (current_assets - cash) - (current_liabilities - current_debt)

    Only years present in ALL FOUR component series are included -- a year
    missing from any one component is dropped entirely rather than assumed,
    since NWC computed from partial data is not trustworthy.

    FLAG: current_debt uses assemble_current_debt_series, which returns {}
    (empty) for companies that only report combined debt with no current/
    long-term split. In that case current_debt is unavailable for ALL years,
    so it's treated as 0 for every year here -- this slightly OVERSTATES
    the (current_liabilities - current_debt) subtraction, meaning NWC would
    be slightly understated for such companies. Acceptable simplification,
    not eliminated.
    """
    current_assets = assemble_concept_series(company_facts, "current_assets")["series"]
    current_liabilities = assemble_concept_series(company_facts, "current_liabilities")["series"]
    cash = assemble_concept_series(company_facts, "cash_and_equivalents")["series"]
    current_debt = assemble_current_debt_series(company_facts)  # may be {}

    common_years = set(current_assets) & set(current_liabilities) & set(cash)
    nwc_series = {}
    for year in common_years:
        debt_for_year = current_debt.get(year, 0)  # 0 if unavailable, see FLAG above
        nwc_series[year] = (current_assets[year] - cash[year]) - (current_liabilities[year] - debt_for_year)
    return nwc_series


def assemble_delta_nwc_series(company_facts: dict) -> dict:
    """
    Change in NWC, year over year, keyed by the LATER year's fiscal year end.
    Positive delta = NWC increased = a USE of cash (subtracted in FCF).
    Negative delta = NWC decreased = a SOURCE of cash (added back in FCF).

    Consecutive years are matched by chronological order of available
    fiscal year ends, NOT by exact 1-year gaps -- if a year is missing
    from assemble_nwc_series (e.g. due to a fiscal year change stub, or
    missing balance sheet data), the delta spans whatever gap remains,
    which will overstate that single delta. This is flagged rather than
    silently smoothed over.
    """
    nwc = assemble_nwc_series(company_facts)
    sorted_years = sorted(nwc.keys())
    deltas = {}
    for prior, current in zip(sorted_years, sorted_years[1:]):
        deltas[current] = nwc[current] - nwc[prior]
    return deltas


def assemble_effective_tax_rate_series(company_facts: dict) -> dict:
    """
    Effective tax rate per fiscal year: income_tax_expense / pretax_income.
    Years where pretax_income is zero or negative are excluded (a negative
    pretax income makes 'effective tax rate' economically meaningless --
    a tax expense divided by a loss produces a nonsensical or wildly
    distorted ratio, not a usable rate).

    Returns {} (empty, not an error) if EITHER concept has no matching tag
    at all for this company -- that's a legitimate "no tax rate data
    available" case, and callers (assemble_unlevered_fcf_series) are
    expected to fall back to a default rate for such years, not crash.
    """
    try:
        tax_expense = assemble_concept_series(company_facts, "income_tax_expense")["series"]
        pretax_income = assemble_concept_series(company_facts, "pretax_income")["series"]
    except ConceptNotFoundError:
        return {}

    common_years = set(tax_expense) & set(pretax_income)
    rates = {}
    for year in common_years:
        if pretax_income[year] > 0:
            rates[year] = tax_expense[year] / pretax_income[year]
    return rates


def assemble_unlevered_fcf_series(company_facts: dict, fallback_tax_rate: float = 0.21) -> dict:
    """
    Unlevered FCF per fiscal year:
        FCF = EBIT * (1 - effective_tax_rate) + D&A - Capex - Delta_NWC

    Only years present in EBIT, D&A, capex, and delta_NWC are included.
    Effective tax rate uses that year's own computed rate when available;
    falls back to fallback_tax_rate (flat statutory-style default) for a
    year missing tax data specifically -- this is a real, named
    approximation for that one input, not silently assumed as identical
    for every company.
    """
    ebit = assemble_concept_series(company_facts, "ebit")["series"]
    da = assemble_concept_series(company_facts, "depreciation_and_amortization")["series"]
    capex = assemble_concept_series(company_facts, "capex")["series"]
    delta_nwc = assemble_delta_nwc_series(company_facts)
    tax_rates = assemble_effective_tax_rate_series(company_facts)

    common_years = set(ebit) & set(da) & set(capex) & set(delta_nwc)
    fcf_series = {}
    for year in common_years:
        tax_rate = tax_rates.get(year, fallback_tax_rate)
        fcf_series[year] = ebit[year] * (1 - tax_rate) + da[year] - capex[year] - delta_nwc[year]
    return fcf_series