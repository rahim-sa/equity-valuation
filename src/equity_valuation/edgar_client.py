"""
Raw SEC EDGAR data access, stage 1 of data pipeline.

This module ONLY fetches and returns raw JSON. No parsing, no tag
mapping, no statement assembly -- that's a deliberately separate
later step, so we can verify the fetch itself works and inspect
real raw data before building interpretation logic on top of it.

SEC EDGAR requires a descriptive User-Agent identifying the requester
(name/email or app name) -- requests without one are blocked or
rate-limited more aggressively. See: https://www.sec.gov/os/webmaster-faq#developers

FLAG: the ticker -> CIK mapping file (company_tickers.json) is itself
maintained by SEC and can be stale for very recent listings/ticker
changes. For this project's scope (established public companies)
that's not a practical concern, but it's not instantaneous.
"""

import time

import requests

SEC_HEADERS = {
    # Replace with your own identifying info -- SEC explicitly asks for this,
    # not a generic/browser-spoofing User-Agent.
    "User-Agent": "equity-valuation-tool your-email@example.com"
}

TICKER_CIK_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANY_FACTS_URL_TEMPLATE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:0>10}.json"


def get_ticker_to_cik_map() -> dict[str, int]:
    """Returns {ticker_upper: cik_int}."""
    response = requests.get(TICKER_CIK_URL, headers=SEC_HEADERS, timeout=10)
    response.raise_for_status()
    raw = response.json()  # dict of {index: {"cik_str": int, "ticker": str, "title": str}}
    return {entry["ticker"].upper(): entry["cik_str"] for entry in raw.values()}


def get_cik_for_ticker(ticker: str, ticker_map: dict[str, int]) -> int:
    cik = ticker_map.get(ticker.upper())
    if cik is None:
        raise ValueError(f"Ticker '{ticker}' not found in SEC ticker-to-CIK mapping")
    return cik


def get_company_facts_raw(cik: int) -> dict:
    """Returns the full raw companyfacts JSON for a given CIK, unparsed."""
    url = COMPANY_FACTS_URL_TEMPLATE.format(cik=cik)
    response = requests.get(url, headers=SEC_HEADERS, timeout=10)
    response.raise_for_status()
    time.sleep(0.15)  # stay well under SEC's ~10 req/sec guidance
    return response.json()