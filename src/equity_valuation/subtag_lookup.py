"""
Sum-of-subtags lookup, for concepts that don't have one consistent
single tag across filers -- total debt being the primary case.

Different shape from tag_lookup.py's single-tag-with-fallback, not a
variant of it: this tries a preferred COMBINED tag first (some filers
do report one), and only falls back to SUMMING separate subtags if the
combined tag isn't present. The two subtags being summed must both be
looked up for the *same period* -- summing without period-matching
would silently combine, e.g., 2019's short-term debt with 2020's
long-term debt if we're not careful. This module returns raw entries
per subtag; period-matching happens at the assembly step (later),
not here.

FLAG: some filers report an even more granular breakdown -- e.g.
separate "current portion of long-term debt" vs "short-term
borrowings" as genuinely distinct line items that both need summing.
The subtag list below is the common 2-part case (long-term + current
portion of all debt); it will need extending for filers reporting a
3-way split. Extend TOTAL_DEBT_SUBTAGS if/when a real company exposes this gap.
"""

# Preferred combined tag, tried first.
TOTAL_DEBT_COMBINED_TAG = "DebtLongtermAndShorttermCombinedAmount"

# If the combined tag isn't present, sum these instead.
TOTAL_DEBT_SUBTAGS = [
    "LongTermDebtNoncurrent",
    "DebtCurrent",
]


class SubtagConceptNotFoundError(Exception):
    """Raised when neither the combined tag nor a usable set of subtags is present."""


def get_total_debt_components(company_facts: dict) -> dict:
    """
    Returns either:
      {"mode": "combined", "tag": <tag_name>, "entries": [...]}
    or:
      {"mode": "summed", "subtag_entries": {subtag_name: [...], ...}}

    Caller (a later assembly step) is responsible for period-matching
    and actually summing subtag_entries values for the same fiscal period --
    this function only locates and returns the raw data, consistent with
    tag_lookup.py's separation of "find the right raw data" from
    "interpret/combine it into a clean series."
    """
    us_gaap_facts = company_facts.get("facts", {}).get("us-gaap", {})

    combined = us_gaap_facts.get(TOTAL_DEBT_COMBINED_TAG)
    if combined is not None:
        usd_entries = combined.get("units", {}).get("USD", [])
        if usd_entries:
            return {"mode": "combined", "tag": TOTAL_DEBT_COMBINED_TAG, "entries": usd_entries}

    subtag_entries = {}
    for subtag in TOTAL_DEBT_SUBTAGS:
        tag_data = us_gaap_facts.get(subtag)
        if tag_data is not None:
            usd_entries = tag_data.get("units", {}).get("USD", [])
            if usd_entries:
                subtag_entries[subtag] = usd_entries

    if len(subtag_entries) == len(TOTAL_DEBT_SUBTAGS):
        return {"mode": "summed", "subtag_entries": subtag_entries}

    raise SubtagConceptNotFoundError(
        f"Neither '{TOTAL_DEBT_COMBINED_TAG}' nor the full subtag set "
        f"{TOTAL_DEBT_SUBTAGS} were found for total debt "
        f"(found subtags: {list(subtag_entries.keys())})"
    )