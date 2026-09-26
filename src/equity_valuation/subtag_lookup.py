"""
Sum-of-subtags / combined-tag lookup for total debt and D&A.

REVISED (second time -- AMD exposed a deeper version of the same gap
Microsoft exposed): "combined tag present with SOME 10-K data" is not
the same as "combined tag covers the years we actually need." AMD's
DepreciationDepletionAndAmortization has real 10-K entries, but only
through 2019 -- an early "does it have any 10-K entry" check let that
stale tag win and silently block the (complete, current) split tags.

Design now: return BOTH the combined-tag entries and the split-tag
entries (whichever exist), and let the assembly layer in
statement_assembly.py merge them per YEAR -- using the combined tag's
value for any year it actually covers, falling back to summed split
tags for years it doesn't. Neither source is chosen exclusively upfront.
"""

TOTAL_DEBT_COMBINED_TAG = "DebtLongtermAndShorttermCombinedAmount"
TOTAL_DEBT_CATEGORIES: dict[str, list[str]] = {
    "long_term": ["LongTermDebtNoncurrent"],
    "current": ["LongTermDebtCurrent", "DebtCurrent", "CommercialPaper", "ShortTermBorrowings"],
}

DA_COMBINED_TAGS = [
    "DepreciationDepletionAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
    "DepreciationAndAmortization",
]
DA_SPLIT_TAGS = [
    "Depreciation",
    "AmortizationOfIntangibleAssets",
]


class SubtagConceptNotFoundError(Exception):
    """Raised when no usable data at all -- neither combined tag nor any subtag -- is present."""


def _get_usd_entries(us_gaap_facts: dict, tag: str) -> list[dict]:
    tag_data = us_gaap_facts.get(tag)
    if tag_data is None:
        return []
    return tag_data.get("units", {}).get("USD", [])


def get_total_debt_components(company_facts: dict) -> dict:
    """
    Returns {"combined_entries": [...], "subtag_entries": {tag: [...]}}.
    Either or both can be non-empty; assembly merges them per year.
    Raises SubtagConceptNotFoundError only if BOTH are entirely empty.
    """
    us_gaap_facts = company_facts.get("facts", {}).get("us-gaap", {})

    combined_entries = _get_usd_entries(us_gaap_facts, TOTAL_DEBT_COMBINED_TAG)

    subtag_entries = {}
    for category_tags in TOTAL_DEBT_CATEGORIES.values():
        for tag in category_tags:
            entries = _get_usd_entries(us_gaap_facts, tag)
            if entries:
                subtag_entries[tag] = entries

    if not combined_entries and not subtag_entries:
        raise SubtagConceptNotFoundError(
            f"Neither '{TOTAL_DEBT_COMBINED_TAG}' nor any tag from "
            f"{TOTAL_DEBT_CATEGORIES} were found for total debt"
        )

    return {"combined_entries": combined_entries, "subtag_entries": subtag_entries}


def get_current_debt_only_components(company_facts: dict) -> dict:
    """Returns {"subtag_entries": {tag: [...]}} for current-debt category tags only."""
    us_gaap_facts = company_facts.get("facts", {}).get("us-gaap", {})
    subtag_entries = {}
    for tag in TOTAL_DEBT_CATEGORIES["current"]:
        entries = _get_usd_entries(us_gaap_facts, tag)
        if entries:
            subtag_entries[tag] = entries
    return {"subtag_entries": subtag_entries}


def get_da_components(company_facts: dict) -> dict:
    """
    Returns {"combined_entries": [...], "subtag_entries": {tag: [...]}},
    trying every DA_COMBINED_TAGS entry (merged, same as revenue's
    tag-fallback merging) plus every DA_SPLIT_TAGS entry present.
    """
    us_gaap_facts = company_facts.get("facts", {}).get("us-gaap", {})

    combined_entries = []
    for tag in DA_COMBINED_TAGS:
        combined_entries.extend(_get_usd_entries(us_gaap_facts, tag))

    subtag_entries = {}
    for tag in DA_SPLIT_TAGS:
        entries = _get_usd_entries(us_gaap_facts, tag)
        if entries:
            subtag_entries[tag] = entries

    if not combined_entries and not subtag_entries:
        raise SubtagConceptNotFoundError(
            f"Neither any of {DA_COMBINED_TAGS} nor any of {DA_SPLIT_TAGS} "
            f"were found for depreciation and amortization"
        )

    return {"combined_entries": combined_entries, "subtag_entries": subtag_entries}