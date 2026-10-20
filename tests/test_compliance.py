import pytest
from groww_support.agents.compliance import run_compliance


@pytest.mark.asyncio
async def test_advice_redeem_flagged():
    r = await run_compliance("Should I redeem HDFC Large Cap?", [])
    assert "advice" in r.flags
    assert r.advice_refusal is True


@pytest.mark.asyncio
async def test_performance_claim_flagged():
    r = await run_compliance("What CAGR should I expect from mid cap?", [])
    assert "performance_claim" in r.flags
    assert r.advice_refusal is True


@pytest.mark.asyncio
async def test_pii_types_from_ingress_propagate():
    r = await run_compliance("Help with [PAN] on my account", ["PAN"])
    assert "pii" in r.flags
    assert "PAN" in r.pii_types


@pytest.mark.asyncio
async def test_clean_exit_load_no_flags():
    r = await run_compliance("Why was I charged an exit load on HDFC Large Cap Fund?", [])
    assert r.flags == []
    assert r.advice_refusal is False
