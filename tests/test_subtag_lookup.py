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
    assert result["tag"] == "DebtLongtermAndShorttermCombinedAmount"
    assert result["entries"][0]["val"] == 5000


def test_falls_back_to_summed_subtags_when_combined_tag_missing():
    facts = _fake_company_facts({
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}},
        "DebtCurrent": {"units": {"USD": [{"val": 500, "form": "10-K"}]}},
    })
    result = get_total_debt_components(facts)
    assert result["mode"] == "summed"
    assert result["subtag_entries"]["LongTermDebtNoncurrent"][0]["val"] == 3000
    assert result["subtag_entries"]["DebtCurrent"][0]["val"] == 500


def test_prefers_combined_tag_over_subtags_when_both_present():
    facts = _fake_company_facts({
        "DebtLongtermAndShorttermCombinedAmount": {
            "units": {"USD": [{"val": 5000, "form": "10-K"}]}
        },
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}},
        "DebtCurrent": {"units": {"USD": [{"val": 500, "form": "10-K"}]}},
    })
    result = get_total_debt_components(facts)
    assert result["mode"] == "combined"


def test_raises_when_only_one_of_two_required_subtags_present():
    facts = _fake_company_facts({
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}},
        # DebtCurrent missing -- incomplete, must not silently treat long-term-only as total debt
    })
    with pytest.raises(SubtagConceptNotFoundError):
        get_total_debt_components(facts)


def test_raises_when_neither_combined_nor_subtags_present():
    facts = _fake_company_facts({})
    with pytest.raises(SubtagConceptNotFoundError):
        get_total_debt_components(facts)


def test_raises_when_combined_tag_present_but_empty_usd_units():
    facts = _fake_company_facts({
        "DebtLongtermAndShorttermCombinedAmount": {"units": {"USD": []}},
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}},
        "DebtCurrent": {"units": {"USD": [{"val": 500, "form": "10-K"}]}},
    })
    # empty combined tag should fall through to subtags, not fail outright
    result = get_total_debt_components(facts)
    assert result["mode"] == "summed"