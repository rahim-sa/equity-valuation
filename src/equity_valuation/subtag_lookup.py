"""
Sum-of-subtags lookup, for concepts that don't have one consistent
single tag across filers -- total debt being the primary case.

REVISED DESIGN (after real AAPL data exposed the gap): "total debt" is
not cleanly "long-term tag + one current tag." A company's current debt
can be made up of MULTIPLE distinct tags that all genuinely count and
can coexist -- e.g. Apple reports both CommercialPaper and
LongTermDebtCurrent as separate current-debt line items simultaneously.
So this is structured as CATEGORIES, where within a category we SUM
every tag that's actually present (since multiple can coexist), and
across categories we also sum (long-term + current = total).

A category with zero matching tags present is treated as zero, NOT
as "concept not found" -- a company can legitimately have no
short-term debt at all. We only raise if NEITHER category has any
tag present, since that means we found no debt data whatsoever
(which is different from "found long-term debt, current debt is
genuinely zero").
"""

TOTAL_DEBT_COMBINED_TAG = "DebtLongtermAndShorttermCombinedAmount"

# Within each category, sum every tag that's present -- these are not
# mutually exclusive fallbacks, they're genuinely separate line items
# that can coexist on the same balance sheet.
TOTAL_DEBT_CATEGORIES: dict[str, list[str]] = {
    "long_term": ["LongTermDebtNoncurrent"],
    "current": ["LongTermDebtCurrent", "DebtCurrent", "CommercialPaper", "ShortTermBorrowings"],
}


class SubtagConceptNotFoundError(Exception):
    """Raised when no debt data at all -- neither combined tag nor any category tag -- is present."""


def get_total_debt_components(company_facts: dict) -> dict:
    """
    Returns either:
      {"mode": "combined", "tag": <tag_name>, "entries": [...]}
    or:
      {"mode": "summed", "subtag_entries": {tag_name: [...], ...}}
        -- flat dict across BOTH categories; caller sums all of them
           together after period-matching (see statement_assembly.py).
           A tag simply absent from subtag_entries means that category
           had nothing for it, treated as zero for that tag, not an error.
    """
    us_gaap_facts = company_facts.get("facts", {}).get("us-gaap", {})

    combined = us_gaap_facts.get(TOTAL_DEBT_COMBINED_TAG)
    if combined is not None:
        usd_entries = combined.get("units", {}).get("USD", [])
        if usd_entries:
            return {"mode": "combined", "tag": TOTAL_DEBT_COMBINED_TAG, "entries": usd_entries}

    subtag_entries = {}
    for category_tags in TOTAL_DEBT_CATEGORIES.values():
        for tag in category_tags:
            tag_data = us_gaap_facts.get(tag)
            if tag_data is not None:
                usd_entries = tag_data.get("units", {}).get("USD", [])
                if usd_entries:
                    subtag_entries[tag] = usd_entries

    if not subtag_entries:
        raise SubtagConceptNotFoundError(
            f"Neither '{TOTAL_DEBT_COMBINED_TAG}' nor any tag from "
            f"{TOTAL_DEBT_CATEGORIES} were found for total debt"
        )

    return {"mode": "summed", "subtag_entries": subtag_entries}