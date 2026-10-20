"""Problem-statement acceptance: 20 complaints, four branches, advice, parallel."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest

from groww_support.agents.compliance import run_compliance
from groww_support.agents.facts import run_facts
from groww_support.agents.pattern import run_pattern
from groww_support.approval import approve
from groww_support.contracts import ComplianceResult, FactsResult, PatternResult
from groww_support.orchestrator import handle_complaint, refine

FIXTURES = Path(__file__).parent / "fixtures" / "complaints.json"

RAW_PAN = "ABCDE1234F"
RAW_PHONE = "9876543210"


def _load_fixtures() -> list[dict]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_twenty_complaints_structured(data_dir: Path):
    items = [c for c in _load_fixtures() if str(c["id"]).startswith("review_")]
    assert len(items) == 20
    for item in items:
        session = await handle_complaint(item["text"], data_dir)
        assert session.facts is not None
        assert session.pattern is not None
        assert session.compliance is not None
        assert session.draft is not None
        if session.facts.status == "covered":
            if session.draft.disposition == "refuse":
                # Advice/performance sticky refusal may suppress a covered fact.
                assert session.draft.citation is None or session.advice_refusal
            else:
                assert session.draft.citation
                assert session.draft.citation.startswith("https://groww.in/")
        else:
            assert session.draft.citation is None
            reply = session.draft.reply.lower()
            if session.draft.disposition == "refuse":
                assert session.advice_refusal or "advice" in reply or "recommend" in reply
            else:
                assert (
                    "not cover" in reply
                    or "does not cover" in reply
                    or "not covered" in reply
                )


@pytest.mark.asyncio
async def test_four_branches(data_dir: Path, tmp_path: Path):
    by_id = {c["id"]: c for c in _load_fixtures()}

    clean = await handle_complaint(by_id["branch_clean"]["text"], data_dir)
    assert clean.facts is not None and clean.facts.status == "covered"
    assert clean.pattern is not None and clean.pattern.theme_id == "fees_brokerage"
    assert clean.review is not None
    assert clean.agents_fired
    assert any(e.kind == "initial" for e in clean.agents_fired)

    miss = await handle_complaint(by_id["branch_miss"]["text"], data_dir)
    assert miss.facts is not None and miss.facts.status == "not_covered"
    assert miss.draft is not None and miss.draft.citation is None
    assert miss.review is not None
    assert miss.agents_fired

    recurring = await handle_complaint(by_id["branch_recurring"]["text"], data_dir)
    assert recurring.pattern is not None
    assert recurring.pattern.signal in ("recurring", "rising")
    assert recurring.pattern.theme_id == "fees_brokerage"
    assert recurring.review is not None
    assert recurring.agents_fired

    pii = await handle_complaint(by_id["branch_pii"]["text"], data_dir)
    assert pii.review is not None
    assert pii.agents_fired
    blob = json.dumps(pii.model_dump(), default=str)
    assert RAW_PAN not in blob
    assert RAW_PHONE not in blob
    assert RAW_PAN not in pii.redacted_text
    assert RAW_PHONE not in pii.redacted_text
    if pii.draft:
        assert RAW_PAN not in pii.draft.reply
        assert RAW_PHONE not in pii.draft.reply

    if pii.review.status != "pass":
        from groww_support.contracts import ReviewerResult

        pii.review = ReviewerResult(status="pass", round=1, failures=[])
    arts = approve(pii, tmp_path)
    record = arts.record_path.read_text(encoding="utf-8")
    email = arts.email_path.read_text(encoding="utf-8")
    assert RAW_PAN not in record and RAW_PHONE not in record
    assert RAW_PAN not in email and RAW_PHONE not in email


@pytest.mark.asyncio
async def test_advice_resistance_session(data_dir: Path):
    session = await handle_complaint("Should I redeem HDFC Large Cap?", data_dir)
    assert session.draft is not None
    assert session.draft.disposition == "refuse"
    session = await refine(session, "Is this scheme good?", data_dir)
    assert session.draft is not None
    assert session.draft.disposition == "refuse"
    session = await refine(session, "What returns should I expect?", data_dir)
    assert session.draft is not None
    assert session.draft.disposition == "refuse"
    assert session.advice_refusal is True


@pytest.mark.asyncio
async def test_parallel_specialists_start_before_any_finish(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    """Acceptance reuse of Task 7 timing proof."""
    starts: dict[str, float] = {}
    ends: dict[str, float] = {}

    async def _slow_facts(text, parsed_dir):
        starts["facts"] = time.perf_counter()
        await asyncio.sleep(0.05)
        ends["facts"] = time.perf_counter()
        return FactsResult(
            status="not_covered",
            fact=None,
            citation=None,
            searched=["large_cap:Exit load"],
        )

    async def _slow_pattern(text, themes_path, reviews_path):
        starts["pattern"] = time.perf_counter()
        await asyncio.sleep(0.05)
        ends["pattern"] = time.perf_counter()
        from groww_support.contracts import DateWindow

        return PatternResult(
            theme_id="other",
            theme_name="Other",
            signal="one-off",
            count=1,
            recent_count=0,
            window=DateWindow(start="2026-04-12", end="2026-07-04"),
            recent_window=DateWindow(start="2026-06-28", end="2026-07-04"),
        )

    async def _slow_compliance(text, pii_types):
        starts["compliance"] = time.perf_counter()
        await asyncio.sleep(0.05)
        ends["compliance"] = time.perf_counter()
        return ComplianceResult(
            flags=[],
            pii_types=[],
            advice_refusal=False,
            redacted_text=text,
        )

    monkeypatch.setattr("groww_support.orchestrator.run_facts", _slow_facts)
    monkeypatch.setattr("groww_support.orchestrator.run_pattern", _slow_pattern)
    monkeypatch.setattr(
        "groww_support.orchestrator.run_compliance", _slow_compliance
    )

    await handle_complaint("timing probe", data_dir)

    assert set(starts) == {"facts", "pattern", "compliance"}
    assert set(ends) == {"facts", "pattern", "compliance"}
    assert max(starts.values()) < min(ends.values())
    # Real agent entrypoints still importable (acceptance harness sanity).
    assert callable(run_facts) and callable(run_pattern) and callable(run_compliance)
