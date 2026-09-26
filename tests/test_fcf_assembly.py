import pytest

from equity_valuation.statement_assembly import (
    assemble_nwc_series,
    assemble_delta_nwc_series,
    assemble_effective_tax_rate_series,
    assemble_unlevered_fcf_series,
)


def _entry(val, end, start=None, form="10-K", filed=None):
    e = {"val": val, "end": end, "form": form, "filed": filed or f"{end[:4]}-12-31"}
    if start:
        e["start"] = start
    return e


def _facts_for_nwc_case():
    return {"facts": {"us-gaap": {
        "AssetsCurrent": {"units": {"USD": [_entry(500, "2020-12-31"), _entry(600, "2021-12-31")]}},
        "LiabilitiesCurrent": {"units": {"USD": [_entry(200, "2020-12-31"), _entry(250, "2021-12-31")]}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [_entry(100, "2020-12-31"), _entry(120, "2021-12-31")]}},
    }}}


def test_nwc_hand_calculated_with_no_current_debt_data():
    # 2020: (500 - 100) - (200 - 0) = 400 - 200 = 200
    # 2021: (600 - 120) - (250 - 0) = 480 - 250 = 230
    result = assemble_nwc_series(_facts_for_nwc_case())
    assert result["2020-12-31"] == pytest.approx(200)
    assert result["2021-12-31"] == pytest.approx(230)


def test_delta_nwc_is_increase_when_nwc_grows():
    # NWC grew from 200 to 230 -> delta = +30, a use of cash
    result = assemble_delta_nwc_series(_facts_for_nwc_case())
    assert result["2021-12-31"] == pytest.approx(30)


def test_effective_tax_rate_hand_calculated():
    facts = {"facts": {"us-gaap": {
        "IncomeTaxExpenseBenefit": {"units": {"USD": [_entry(21, "2020-12-31", start="2020-01-01")]}},
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": {
            "units": {"USD": [_entry(100, "2020-12-31", start="2020-01-01")]}
        },
    }}}
    result = assemble_effective_tax_rate_series(facts)
    assert result["2020-12-31"] == pytest.approx(0.21)


def test_effective_tax_rate_excludes_negative_pretax_income():
    facts = {"facts": {"us-gaap": {
        "IncomeTaxExpenseBenefit": {"units": {"USD": [_entry(5, "2020-12-31", start="2020-01-01")]}},
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": {
            "units": {"USD": [_entry(-50, "2020-12-31", start="2020-01-01")]}
        },
    }}}
    result = assemble_effective_tax_rate_series(facts)
    assert "2020-12-31" not in result


def test_unlevered_fcf_hand_calculated():
    # EBIT=1000, tax_rate=0.20, D&A=100, Capex=150, DeltaNWC=30
    # FCF = 1000*(1-0.20) + 100 - 150 - 30 = 800 + 100 - 150 - 30 = 720
    facts = {"facts": {"us-gaap": {
        "OperatingIncomeLoss": {"units": {"USD": [
            _entry(1000, "2021-12-31", start="2021-01-01"),
        ]}},
        "DepreciationDepletionAndAmortization": {"units": {"USD": [
            _entry(100, "2021-12-31", start="2021-01-01"),
        ]}},
        "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": [
            _entry(150, "2021-12-31", start="2021-01-01"),
        ]}},
        "AssetsCurrent": {"units": {"USD": [_entry(500, "2020-12-31"), _entry(600, "2021-12-31")]}},
        "LiabilitiesCurrent": {"units": {"USD": [_entry(200, "2020-12-31"), _entry(250, "2021-12-31")]}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [_entry(100, "2020-12-31"), _entry(120, "2021-12-31")]}},
        "IncomeTaxExpenseBenefit": {"units": {"USD": [_entry(200, "2021-12-31", start="2021-01-01")]}},
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": {
            "units": {"USD": [_entry(1000, "2021-12-31", start="2021-01-01")]}
        },
    }}}
    result = assemble_unlevered_fcf_series(facts)
    assert result["2021-12-31"] == pytest.approx(720)


def test_unlevered_fcf_uses_fallback_tax_rate_when_tax_data_missing():
    # Same as above but NO tax tags at all -> should use fallback_tax_rate=0.25
    # FCF = 1000*(1-0.25) + 100 - 150 - 30 = 750 + 100 - 150 - 30 = 670
    facts = {"facts": {"us-gaap": {
        "OperatingIncomeLoss": {"units": {"USD": [_entry(1000, "2021-12-31", start="2021-01-01")]}},
        "DepreciationDepletionAndAmortization": {"units": {"USD": [_entry(100, "2021-12-31", start="2021-01-01")]}},
        "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": [_entry(150, "2021-12-31", start="2021-01-01")]}},
        "AssetsCurrent": {"units": {"USD": [_entry(500, "2020-12-31"), _entry(600, "2021-12-31")]}},
        "LiabilitiesCurrent": {"units": {"USD": [_entry(200, "2020-12-31"), _entry(250, "2021-12-31")]}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [_entry(100, "2020-12-31"), _entry(120, "2021-12-31")]}},
    }}}
    result = assemble_unlevered_fcf_series(facts, fallback_tax_rate=0.25)
    assert result["2021-12-31"] == pytest.approx(670)