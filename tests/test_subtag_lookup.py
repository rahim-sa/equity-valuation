import pytest

from equity_valuation.subtag_lookup import (
    get_total_debt_components,
    SubtagConceptNotFoundError,
)


def _fake_company_facts(us_gaap_tags: dict) -> dict:
    return {"facts": {"us-gaap": us_gaap_tags}}


def test_uses_combined_tag_when_present():
    facts = _fake_company_facts({
        "DebtLongtermAndShorttermCombinedAmount": {
            "units": {"USD": [{"val": 5000, "form": "10-K"}]}
        }
    })
    result = get_total_debt_components(facts)
    assert result["mode"] == "combined"
    assert result["entries"][0]["val"] == 5000


def test_sums_long_term_and_current_when_combined_tag_missing():
    facts = _fake_company_facts({
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}},
        "DebtCurrent": {"units": {"USD": [{"val": 500, "form": "10-K"}]}},
    })
    result = get_total_debt_components(facts)
    assert result["mode"] == "summed"
    assert result["subtag_entries"]["LongTermDebtNoncurrent"][0]["val"] == 3000
    assert result["subtag_entries"]["DebtCurrent"][0]["val"] == 500


def test_handles_apple_style_split_commercial_paper_and_current_portion():
    """Real-world case that exposed the original design gap: Apple reports
    CommercialPaper and LongTermDebtCurrent as separate coexisting tags,
    with no 'DebtCurrent' tag at all."""
    facts = _fake_company_facts({
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 90000, "form": "10-K"}]}},
        "LongTermDebtCurrent": {"units": {"USD": [{"val": 10000, "form": "10-K"}]}},
        "CommercialPaper": {"units": {"USD": [{"val": 6000, "form": "10-K"}]}},
    })
    result = get_total_debt_components(facts)
    assert result["mode"] == "summed"
    assert set(result["subtag_entries"].keys()) == {
        "LongTermDebtNoncurrent", "LongTermDebtCurrent", "CommercialPaper"
    }


def test_long_term_only_is_valid_not_an_error():
    """A company with zero short-term debt is legitimate, not a missing-data error."""
    facts = _fake_company_facts({
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}},
    })
    result = get_total_debt_components(facts)
    assert result["mode"] == "summed"
    assert list(result["subtag_entries"].keys()) == ["LongTermDebtNoncurrent"]


def test_prefers_combined_tag_over_subtags_when_both_present():
    facts = _fake_company_facts({
        "DebtLongtermAndShorttermCombinedAmount": {
            "units": {"USD": [{"val": 5000, "form": "10-K"}]}
        },
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}},
    })
    result = get_total_debt_components(facts)
    assert result["mode"] == "combined"


def test_raises_when_no_debt_data_at_all():
    facts = _fake_company_facts({})
    with pytest.raises(SubtagConceptNotFoundError):
        get_total_debt_components(facts)


def test_raises_when_combined_tag_present_but_empty_usd_units_and_no_subtags():
    facts = _fake_company_facts({
        "DebtLongtermAndShorttermCombinedAmount": {"units": {"USD": []}},
    })
    with pytest.raises(SubtagConceptNotFoundError):
        get_total_debt_components(facts)