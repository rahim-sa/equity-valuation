from equity_valuation.statement_mapping import select_annual_facts, resolve_duplicate_periods


def test_select_annual_facts_keeps_clean_annual_10k_entry():
    entries = [
        {"form": "10-K", "start": "2019-01-01", "end": "2019-12-31", "filed": "2020-02-01", "val": 100},
    ]
    result = select_annual_facts(entries)
    assert len(result) == 1
    assert result[0]["val"] == 100


def test_select_annual_facts_drops_quarterly_entry():
    entries = [
        {"form": "10-K", "start": "2019-10-01", "end": "2019-12-31", "filed": "2020-02-01", "val": 25},
    ]
    assert select_annual_facts(entries) == []


def test_select_annual_facts_drops_10k_amendment():
    entries = [
        {"form": "10-K/A", "start": "2019-01-01", "end": "2019-12-31", "filed": "2020-03-01", "val": 100},
    ]
    assert select_annual_facts(entries) == []


def test_select_annual_facts_drops_instant_type_entries():
    entries = [
        {"form": "10-K", "end": "2019-12-31", "filed": "2020-02-01", "val": 500},  # no "start" -> instant
    ]
    assert select_annual_facts(entries) == []


def test_select_annual_facts_drops_short_transition_stub():
    # ~4 month fiscal year change stub
    entries = [
        {"form": "10-K", "start": "2019-09-01", "end": "2019-12-31", "filed": "2020-02-01", "val": 40},
    ]
    assert select_annual_facts(entries) == []


def test_select_annual_facts_keeps_53_week_fiscal_year():
    # 53-week fiscal year is a few days over 365, must still be kept
    entries = [
        {"form": "10-K", "start": "2019-01-01", "end": "2020-01-04", "filed": "2020-02-15", "val": 100},
    ]
    assert len(select_annual_facts(entries)) == 1


def test_resolve_duplicate_periods_prefers_latest_filing_within_two_years():
    entries = [
        {"start": "2019-01-01", "end": "2019-12-31", "filed": "2020-02-01", "val": 100},  # original
        {"start": "2019-01-01", "end": "2019-12-31", "filed": "2021-02-01", "val": 105},  # restated, within 2yr
    ]
    result = resolve_duplicate_periods(entries)
    assert len(result) == 1
    assert result[0]["val"] == 105


def test_resolve_duplicate_periods_ignores_restatement_beyond_two_years():
    entries = [
        {"start": "2019-01-01", "end": "2019-12-31", "filed": "2020-02-01", "val": 100},  # original, kept
        {"start": "2019-01-01", "end": "2019-12-31", "filed": "2023-02-01", "val": 999},  # too far out, ignored
    ]
    result = resolve_duplicate_periods(entries)
    assert len(result) == 1
    assert result[0]["val"] == 100


def test_resolve_duplicate_periods_returns_sorted_chronological_series():
    entries = [
        {"start": "2020-01-01", "end": "2020-12-31", "filed": "2021-02-01", "val": 200},
        {"start": "2019-01-01", "end": "2019-12-31", "filed": "2020-02-01", "val": 100},
    ]
    result = resolve_duplicate_periods(entries)
    assert [e["val"] for e in result] == [100, 200]