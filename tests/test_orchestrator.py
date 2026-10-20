import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from groww_support.contracts import (
    ComplianceResult,
    DateWindow,
    FactsResult,
    PatternResult,
)
from groww_support.orchestrator import handle_complaint, merge_draft


def _pattern(signal="recurring", recent=12):
    return PatternResult(
        theme_id="fees_brokerage",
        theme_name="Fees & brokerage",
        signal=signal,
        count=136,
        recent_count=recent,
        window=DateWindow(start="2026-04-12", end="2026-07-04"),
        recent_window=DateWindow(start="2026-06-28", end="2026-07-04"),
    )


def test_covered_recurring_escalates():
    facts = FactsResult(
        status="covered",
        scheme_id="large_cap",
        section_title="Exit load",
        fact="Exit load of 1% if redeemed within 1 year",
        citation="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        last_checked="25-Jun-2026",
        searched=["large_cap"],
    )
    out = merge_draft(
        facts,
        _pattern("recurring"),
        ComplianceResult(
            flags=[],
            pii_types=[],
            advice_refusal=False,
            redacted_text="Why exit load on HDFC Large Cap?",
        ),
        advice_refusal=False,
    )
    assert out.disposition == "escalate"
    assert out.citation is not None
    assert (
        out.reply.count(".") <= 3
        or out.reply.count("!") + out.reply.count("?") + out.reply.count(".") <= 3
    )
    assert "25-Jun-2026" in out.reply
    assert "Fees and mutual fund ops" in out.routing_note.team
    assert out.routing_note.priority in ("P1", "P2")


def test_advice_refuse_overrides_covered_fact():
    facts = FactsResult(
        status="covered",
        scheme_id="large_cap",
        section_title="Exit load",
        fact="Exit load of 1% if redeemed within 1 year",
        citation="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        last_checked="25-Jun-2026",
        searched=["large_cap"],
    )
    out = merge_draft(
        facts,
        _pattern("one-off"),
        ComplianceResult(
            flags=["advice"],
            pii_types=[],
            advice_refusal=True,
            redacted_text="Should I redeem?",
        ),
        advice_refusal=True,
    )
    assert out.disposition == "refuse"
    assert out.citation is None
    assert (
        "should" not in out.reply.lower()
        or "cannot" in out.reply.lower()
        or "unable" in out.reply.lower()
    )


def test_covered_rising_disagree():
    facts = FactsResult(
        status="covered",
        scheme_id="large_cap",
        section_title="Exit load",
        fact="Exit load of 1% if redeemed within 1 year",
        citation="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        last_checked="25-Jun-2026",
        searched=["large_cap"],
    )
    out = merge_draft(
        facts,
        _pattern("rising", recent=40),
        ComplianceResult(
            flags=[],
            pii_types=[],
            advice_refusal=False,
            redacted_text="exit load",
        ),
        advice_refusal=False,
    )
    assert out.disposition == "disagree"
    assert out.disagreement is True
    assert "stays open" in out.routing_note.why.lower() or "open" in out.routing_note.why.lower()


@pytest.mark.asyncio
async def test_parallel_fanout_records_all_three(data_dir: Path):
    session = await handle_complaint(
        "Why was I charged an exit load on HDFC Large Cap Fund?",
        data_dir,
    )
    assert session.facts is not None
    assert session.pattern is not None
    assert session.compliance is not None
    assert session.draft is not None
    assert any(
        e.kind == "initial" and set(e.fired) >= {"facts", "pattern", "compliance"}
        for e in session.agents_fired
    )


@pytest.mark.asyncio
async def test_specialists_start_before_any_finish(data_dir: Path, monkeypatch):
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
        return _pattern("one-off")

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
    monkeypatch.setattr("groww_support.orchestrator.run_compliance", _slow_compliance)

    await handle_complaint("timing probe", data_dir)

    assert set(starts) == {"facts", "pattern", "compliance"}
    assert set(ends) == {"facts", "pattern", "compliance"}
    assert max(starts.values()) < min(ends.values())
