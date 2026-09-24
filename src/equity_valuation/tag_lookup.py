"""
Single-tag-with-fallback lookup for concepts that map to one XBRL tag
at a time, tried in order of preference (fallbacks exist because filers
are not consistent about which tag they use for an economically
equivalent line item).

Separate from statement_mapping.py deliberately: that module answers
"which entries within a tag's data represent a clean annual period."
This module answers "which tag do we even look under, for a given
concept, for a given company." Different concern, different function.

FLAG: which tag a company actually used is recorded and returned
alongside the result, not discarded -- if two peer companies (comps
work, later) end up using different underlying tags for the same
concept, that's informative, not something to silently paper over.
"""

# Ordered fallback lists: primary tag first, then progressively less
# common alternates. Extend as real companies expose new gaps.
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
}


class ConceptNotFoundError(Exception):
    """Raised when none of a concept's fallback tags exist in the company's facts."""


def get_raw_entries_for_concept(company_facts: dict, concept: str) -> tuple[list[dict], str]:
    """
    Returns (raw_entries, tag_used) for the given concept, trying each
    fallback tag in order. Raises ConceptNotFoundError if none are present.

    'raw_entries' is unfiltered -- still needs select_annual_facts and
    resolve_duplicate_periods applied on top, from statement_mapping.py.
    """
    if concept not in TAG_FALLBACKS:
        raise ValueError(f"Unknown concept '{concept}' -- not in TAG_FALLBACKS")

    us_gaap_facts = company_facts.get("facts", {}).get("us-gaap", {})

    for tag in TAG_FALLBACKS[concept]:
        tag_data = us_gaap_facts.get(tag)
        if tag_data is not None:
            usd_entries = tag_data.get("units", {}).get("USD", [])
            if usd_entries:
                return usd_entries, tag

    raise ConceptNotFoundError(
        f"None of the fallback tags {TAG_FALLBACKS[concept]} were found "
        f"for concept '{concept}' in this company's facts"
    )