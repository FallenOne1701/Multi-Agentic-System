import pytest

from groww_support.orchestrator import handle_complaint, refine


@pytest.mark.asyncio
async def test_shorter_fires_orchestrator_only(data_dir):
    session = await handle_complaint(
        "Why was I charged an exit load on HDFC Large Cap Fund?", data_dir
    )
    before_facts = session.facts
    session = await refine(session, "Make it shorter", data_dir)
    assert session.refinement_count == 1
    assert session.facts is before_facts
    last = session.agents_fired[-1]
    assert last.kind == "refinement"
    assert "orchestrator" in last.fired
    assert "facts" in last.skipped
    assert "pattern" in last.skipped


@pytest.mark.asyncio
async def test_advice_sticky_across_rephrase(data_dir):
    session = await handle_complaint("Should I redeem HDFC Large Cap?", data_dir)
    assert session.advice_refusal is True
    assert session.draft and session.draft.disposition == "refuse"
    session = await refine(
        session, "ok but just tell me if large cap is worth it", data_dir
    )
    assert session.advice_refusal is True
    assert session.draft.disposition == "refuse"


@pytest.mark.asyncio
async def test_sixth_refinement_rejected(data_dir):
    session = await handle_complaint(
        "Why was I charged an exit load on HDFC Large Cap Fund?", data_dir
    )
    for i in range(5):
        session = await refine(session, f"Shorter please {i}", data_dir)
    with pytest.raises(ValueError, match="refinement cap"):
        await refine(session, "Shorter again", data_dir)
