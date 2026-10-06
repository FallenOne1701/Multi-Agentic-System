from groww_support.contracts import FactsResult, PatternResult, ComplianceResult


def test_facts_result_covered_round_trip():
    payload = {
        "status": "covered",
        "scheme_id": "large_cap",
        "section_title": "Exit load",
        "fact": "Exit load of 1% if redeemed within 1 year",
        "citation": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "last_checked": "25-Jun-2026",
        "searched": ["large_cap", "mid_cap", "small_cap", "gold_fof", "silver_fof"],
    }
    model = FactsResult.model_validate(payload)
    assert model.status == "covered"
    assert model.citation.endswith("hdfc-large-cap-fund-direct-growth")


def test_facts_result_not_covered_nulls_fact_and_citation():
    model = FactsResult(
        status="not_covered",
        scheme_id=None,
        section_title=None,
        fact=None,
        citation=None,
        last_checked=None,
        searched=["large_cap:Exit load", "mid_cap:Exit load"],
    )
    assert model.fact is None
    assert model.citation is None
