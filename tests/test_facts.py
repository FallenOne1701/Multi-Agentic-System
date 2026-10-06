import pytest
from groww_support.agents.facts import run_facts


@pytest.mark.asyncio
async def test_exit_load_large_cap_covered(parsed_dir):
    result = await run_facts(
        "Why was I charged an exit load on HDFC Large Cap Fund?",
        parsed_dir,
    )
    assert result.status == "covered"
    assert result.scheme_id == "large_cap"
    assert result.section_title == "Exit load"
    assert "1%" in (result.fact or "")
    assert result.citation == "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    assert result.last_checked == "25-Jun-2026"


@pytest.mark.asyncio
async def test_non_hdfc_order_failure_not_covered(parsed_dir):
    result = await run_facts(
        "My order failed while buying Reliance shares in the app",
        parsed_dir,
    )
    assert result.status == "not_covered"
    assert result.fact is None
    assert result.citation is None
    assert len(result.searched) > 0


@pytest.mark.asyncio
async def test_does_not_invent_returns(parsed_dir):
    result = await run_facts(
        "What was the 1 year return of HDFC Large Cap?",
        parsed_dir,
    )
    # Returns are not in the seven sections as an answerable performance figure;
    # agent must not invent — either not_covered or a non-performance section only if text matches.
    # Spec: performance/return questions are refusals for compliance; Facts must not add return figures.
    assert result.status == "not_covered" or (
        result.fact is not None and "return" not in result.fact.lower() and "cagr" not in result.fact.lower()
    )
