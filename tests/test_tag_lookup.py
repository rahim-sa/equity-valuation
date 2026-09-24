import pytest

from equity_valuation.tag_lookup import get_raw_entries_for_concept, ConceptNotFoundError


def _fake_company_facts(us_gaap_tags: dict) -> dict:
    return {"facts": {"us-gaap": us_gaap_tags}}


def test_finds_primary_tag_when_present():
    facts = _fake_company_facts({
        "Revenues": {"units": {"USD": [{"val": 1000, "form": "10-K"}]}}
    })
    entries, tags_used = get_raw_entries_for_concept(facts, "revenue")
    assert tags_used == ["Revenues"]
    assert entries[0]["val"] == 1000


def test_falls_back_to_second_tag_when_primary_missing():
    facts = _fake_company_facts({
        "RevenueFromContractWithCustomerExcludingAssessedTax": {
            "units": {"USD": [{"val": 2000, "form": "10-K"}]}
        }
    })
    entries, tags_used = get_raw_entries_for_concept(facts, "revenue")
    assert tags_used == ["RevenueFromContractWithCustomerExcludingAssessedTax"]


def test_merges_across_tags_when_company_switched_mid_history():
    """The real-world case that caused the original bug: a company using
    one tag for early years and a different tag for later years must have
    BOTH sets of entries returned, not just the first tag found."""
    facts = _fake_company_facts({
        "Revenues": {"units": {"USD": [{"val": 1000, "form": "10-K", "end": "2017-12-31"}]}},
        "RevenueFromContractWithCustomerExcludingAssessedTax": {
            "units": {"USD": [{"val": 2000, "form": "10-K", "end": "2018-12-31"}]}
        },
    })
    entries, tags_used = get_raw_entries_for_concept(facts, "revenue")
    assert set(tags_used) == {"Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"}
    assert len(entries) == 2


def test_raises_concept_not_found_when_no_fallback_tag_present():
    facts = _fake_company_facts({})
    with pytest.raises(ConceptNotFoundError):
        get_raw_entries_for_concept(facts, "revenue")


def test_raises_concept_not_found_when_tag_present_but_empty_usd_units():
    facts = _fake_company_facts({"Revenues": {"units": {"USD": []}}})
    with pytest.raises(ConceptNotFoundError):
        get_raw_entries_for_concept(facts, "revenue")


def test_raises_value_error_for_unknown_concept():
    facts = _fake_company_facts({"Revenues": {"units": {"USD": [{"val": 1}]}}})
    with pytest.raises(ValueError):
        get_raw_entries_for_concept(facts, "not_a_real_concept")