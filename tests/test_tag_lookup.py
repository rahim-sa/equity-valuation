import pytest

from equity_valuation.tag_lookup import get_raw_entries_for_concept, ConceptNotFoundError


def _fake_company_facts(us_gaap_tags: dict) -> dict:
    """Builds a minimal synthetic companyfacts-shaped dict for testing."""
    return {"facts": {"us-gaap": us_gaap_tags}}


def test_finds_primary_tag_when_present():
    facts = _fake_company_facts({
        "Revenues": {"units": {"USD": [{"val": 1000, "form": "10-K"}]}}
    })
    entries, tag_used = get_raw_entries_for_concept(facts, "revenue")
    assert tag_used == "Revenues"
    assert entries[0]["val"] == 1000


def test_falls_back_to_second_tag_when_primary_missing():
    facts = _fake_company_facts({
        "RevenueFromContractWithCustomerExcludingAssessedTax": {
            "units": {"USD": [{"val": 2000, "form": "10-K"}]}
        }
    })
    entries, tag_used = get_raw_entries_for_concept(facts, "revenue")
    assert tag_used == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert entries[0]["val"] == 2000


def test_falls_back_to_third_tag_when_first_two_missing():
    facts = _fake_company_facts({
        "SalesRevenueNet": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}}
    })
    entries, tag_used = get_raw_entries_for_concept(facts, "revenue")
    assert tag_used == "SalesRevenueNet"


def test_prefers_primary_tag_over_fallback_when_both_present():
    facts = _fake_company_facts({
        "Revenues": {"units": {"USD": [{"val": 1000, "form": "10-K"}]}},
        "SalesRevenueNet": {"units": {"USD": [{"val": 9999, "form": "10-K"}]}},
    })
    entries, tag_used = get_raw_entries_for_concept(facts, "revenue")
    assert tag_used == "Revenues"
    assert entries[0]["val"] == 1000


def test_raises_concept_not_found_when_no_fallback_tag_present():
    facts = _fake_company_facts({})
    with pytest.raises(ConceptNotFoundError):
        get_raw_entries_for_concept(facts, "revenue")


def test_raises_concept_not_found_when_tag_present_but_empty_usd_units():
    facts = _fake_company_facts({
        "Revenues": {"units": {"USD": []}}
    })
    with pytest.raises(ConceptNotFoundError):
        get_raw_entries_for_concept(facts, "revenue")


def test_raises_value_error_for_unknown_concept():
    facts = _fake_company_facts({"Revenues": {"units": {"USD": [{"val": 1}]}}})
    with pytest.raises(ValueError):
        get_raw_entries_for_concept(facts, "not_a_real_concept")