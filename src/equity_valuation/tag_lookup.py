  

"""
Single-tag-with-fallback lookup for concepts that map to XBRL tags,
merged across ALL fallback tags -- not just the first one with data.

REVISED (after real AAPL data exposed the gap): a company can switch
which tag it uses for the same concept partway through its filing
history (e.g. Apple moved from 'Revenues' to
'RevenueFromContractWithCustomerExcludingAssessedTax' when it adopted
ASC 606 in fiscal 2018). Stopping at the first tag with ANY data would
silently truncate the series at the switch point. So every fallback tag
that has data is merged together; downstream duplicate-period resolution
(statement_mapping.py) picks the right entry per period regardless of
which tag it came from.

tags_used is now a LIST, not a single string -- callers should expect
and report which tag(s) actually contributed data, since seeing more
than one tag in the list for one company IS the signal that a
tag-switch happened, worth surfacing rather than hiding.
"""

TAG_FALLBACKS: dict[str, list[str]] = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ],
    "ebit": [
        "OperatingIncomeLoss",
    ],
    "depreciation_and_amortization": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "DepreciationAndAmortization",
    ],

    
    # KNOWN LIMITATION: some filers (e.g. Apple, starting FY2024) stop
    # reporting interest expense as a standalone tag and fold it into a
    # combined "other income/expense, net" line instead. When that
    # happens, get_raw_entries_for_concept will simply return fewer
    # years than other concepts for that company -- it will NOT raise
    # an error, since the tag genuinely isn't there, that's a fact about
    # the filing, not a bug. Downstream (WACC), when a recent year's
    # interest_expense is missing, fall back to either: the synthetic
    # credit rating method (credit_rating.py, Option B) which doesn't
    # need interest_expense at all for cost of debt, or the last
    # available year's effective rate as a proxy. Do not silently treat
    # a missing recent year as zero interest expense.
    "interest_expense": [
        "InterestExpense",
        "InterestExpenseDebt",
    ],    

 
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
    ],


        "current_assets": [
        "AssetsCurrent",
    ],
    "current_liabilities": [
        "LiabilitiesCurrent",
    ],
    "income_tax_expense": [
        "IncomeTaxExpenseBenefit",
    ],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],

    
}

# Concepts that are balance-sheet snapshots (instant), not period durations.
# Drives which statement_mapping functions assembly should use for each.
#INSTANT_CONCEPTS: set[str] = {"cash_and_equivalents"}
INSTANT_CONCEPTS: set[str] = {"cash_and_equivalents", "current_assets", "current_liabilities"}


class ConceptNotFoundError(Exception):
    """Raised when none of a concept's fallback tags exist in the company's facts."""


def get_raw_entries_for_concept(company_facts: dict, concept: str) -> tuple[list[dict], list[str]]:
    """
    Returns (raw_entries, tags_used) -- raw_entries merged across every
    fallback tag that had data, tags_used listing which ones contributed.
    Raises ConceptNotFoundError if none of the fallback tags are present.

    Still unfiltered -- select_annual_facts/select_annual_instant_facts
    and the matching resolve_duplicate_* function still need to run on
    top of this, same as before.
    """
    if concept not in TAG_FALLBACKS:
        raise ValueError(f"Unknown concept '{concept}' -- not in TAG_FALLBACKS")

    us_gaap_facts = company_facts.get("facts", {}).get("us-gaap", {})

    combined_entries: list[dict] = []
    tags_used: list[str] = []

    for tag in TAG_FALLBACKS[concept]:
        tag_data = us_gaap_facts.get(tag)
        if tag_data is not None:
            usd_entries = tag_data.get("units", {}).get("USD", [])
            if usd_entries:
                combined_entries.extend(usd_entries)
                tags_used.append(tag)

    if not combined_entries:
        raise ConceptNotFoundError(
            f"None of the fallback tags {TAG_FALLBACKS[concept]} were found "
            f"for concept '{concept}' in this company's facts"
        )

    return combined_entries, tags_used