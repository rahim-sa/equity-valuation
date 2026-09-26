import pytest

from equity_valuation.subtag_lookup import (
    get_total_debt_components,
    get_current_debt_only_components,
    get_da_components,
    SubtagConceptNotFoundError,
)


def _fake_company_facts(us_gaap_tags: dict) -> dict:
    return {"facts": {"us-gaap": us_gaap_tags}}


# --- Total debt ---

def test_total_debt_returns_combined_entries_when_present():
    facts = _fake_company_facts({
        "DebtLongtermAndShorttermCombinedAmount": {
            "units": {"USD": [{"val": 5000, "form": "10-K"}]}
        }
    })
    result = get_total_debt_components(facts)
    assert result["combined_entries"][0]["val"] == 5000
    assert result["subtag_entries"] == {}


def test_total_debt_returns_subtag_entries_when_combined_missing():
    facts = _fake_company_facts({
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}},
        "DebtCurrent": {"units": {"USD": [{"val": 500, "form": "10-K"}]}},
    })
    result = get_total_debt_components(facts)
    assert result["combined_entries"] == []
    assert result["subtag_entries"]["LongTermDebtNoncurrent"][0]["val"] == 3000
    assert result["subtag_entries"]["DebtCurrent"][0]["val"] == 500


def test_total_debt_handles_apple_style_split_commercial_paper_and_current_portion():
    facts = _fake_company_facts({
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 90000, "form": "10-K"}]}},
        "LongTermDebtCurrent": {"units": {"USD": [{"val": 10000, "form": "10-K"}]}},
        "CommercialPaper": {"units": {"USD": [{"val": 6000, "form": "10-K"}]}},
    })
    result = get_total_debt_components(facts)
    assert set(result["subtag_entries"].keys()) == {
        "LongTermDebtNoncurrent", "LongTermDebtCurrent", "CommercialPaper"
    }


def test_total_debt_long_term_only_is_valid_not_an_error():
    facts = _fake_company_facts({
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}},
    })
    result = get_total_debt_components(facts)
    assert list(result["subtag_entries"].keys()) == ["LongTermDebtNoncurrent"]


def test_total_debt_returns_both_combined_and_subtags_when_both_present():
    """New behavior: both sources are returned, not one chosen exclusively --
    the assembly layer decides per-year which to use."""
    facts = _fake_company_facts({
        "DebtLongtermAndShorttermCombinedAmount": {
            "units": {"USD": [{"val": 5000, "form": "10-K"}]}
        },
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}},
    })
    result = get_total_debt_components(facts)
    assert result["combined_entries"][0]["val"] == 5000
    assert result["subtag_entries"]["LongTermDebtNoncurrent"][0]["val"] == 3000


def test_total_debt_raises_when_no_debt_data_at_all():
    facts = _fake_company_facts({})
    with pytest.raises(SubtagConceptNotFoundError):
        get_total_debt_components(facts)


def test_total_debt_empty_combined_tag_does_not_prevent_finding_subtags():
    facts = _fake_company_facts({
        "DebtLongtermAndShorttermCombinedAmount": {"units": {"USD": []}},
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}},
    })
    result = get_total_debt_components(facts)
    assert result["combined_entries"] == []
    assert result["subtag_entries"]["LongTermDebtNoncurrent"][0]["val"] == 3000


# --- Current debt only (for NWC) ---

def test_current_debt_only_returns_current_category_tags():
    facts = _fake_company_facts({
        "LongTermDebtNoncurrent": {"units": {"USD": [{"val": 3000, "form": "10-K"}]}},
        "ShortTermBorrowings": {"units": {"USD": [{"val": 200, "form": "10-K"}]}},
    })
    result = get_current_debt_only_components(facts)
    assert "LongTermDebtNoncurrent" not in result["subtag_entries"]
    assert result["subtag_entries"]["ShortTermBorrowings"][0]["val"] == 200


def test_current_debt_only_returns_empty_when_none_present():
    facts = _fake_company_facts({})
    result = get_current_debt_only_components(facts)
    assert result["subtag_entries"] == {}


# --- D&A ---

def test_da_returns_combined_entries_when_present():
    facts = _fake_company_facts({
        "DepreciationDepletionAndAmortization": {
            "units": {"USD": [{"val": 800, "form": "10-K"}]}
        }
    })
    result = get_da_components(facts)
    assert result["combined_entries"][0]["val"] == 800


def test_da_returns_subtag_entries_for_split_style_filer():
    """Microsoft/AMD-style: separate Depreciation and AmortizationOfIntangibleAssets tags."""
    facts = _fake_company_facts({
        "Depreciation": {"units": {"USD": [{"val": 500, "form": "10-K"}]}},
        "AmortizationOfIntangibleAssets": {"units": {"USD": [{"val": 100, "form": "10-K"}]}},
    })
    result = get_da_components(facts)
    assert result["combined_entries"] == []
    assert result["subtag_entries"]["Depreciation"][0]["val"] == 500
    assert result["subtag_entries"]["AmortizationOfIntangibleAssets"][0]["val"] == 100


def test_da_returns_both_when_both_present():
    """AMD's real case: an old combined tag AND current split tags both exist."""
    facts = _fake_company_facts({
        "DepreciationDepletionAndAmortization": {
            "units": {"USD": [{"val": 800, "form": "10-K"}]}
        },
        "Depreciation": {"units": {"USD": [{"val": 500, "form": "10-K"}]}},
        "AmortizationOfIntangibleAssets": {"units": {"USD": [{"val": 100, "form": "10-K"}]}},
    })
    result = get_da_components(facts)
    assert result["combined_entries"][0]["val"] == 800
    assert result["subtag_entries"]["Depreciation"][0]["val"] == 500


def test_da_raises_when_nothing_present():
    facts = _fake_company_facts({})
    with pytest.raises(SubtagConceptNotFoundError):
        get_da_components(facts)