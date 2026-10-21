"""Manual end-to-end verification of the multi-agent support flow.

Runs: ingress → Facts / Pattern / Compliance (parallel, LLM classifiers) →
orchestrator merge → reviewer → prints every stage with latency.

Usage (from repo root, with .env configured):

    python scripts/verify_e2e.py
    python scripts/verify_e2e.py "your custom complaint"
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from groww_support.agents.compliance import run_compliance
from groww_support.agents.facts import run_facts
from groww_support.agents.pattern import run_pattern
from groww_support.contracts import AgentsFiredEntry, SessionState
from groww_support.ingress import redact
from groww_support.llm import llm_enabled
from groww_support.orchestrator import (
    _review_with_optional_rework,
    merge_draft,
)

DEFAULT_COMPLAINT = (
    "why was I charged an exit load on HDFC Gold Mutual Fund? "
    "What was the amount and why was I charged?"
)

DATA_DIR = ROOT / "data"
OUT_PATH = ROOT / "output" / "verify_e2e_session.json"


def _banner(title: str) -> None:
    line = "=" * 72
    print(f"\n{line}\n  {title}\n{line}")


def _section(title: str) -> None:
    print(f"\n--- {title} ---")


def _ms(seconds: float) -> str:
    return f"{seconds * 1000:.0f} ms"


async def _timed(coro):
    t0 = time.perf_counter()
    result = await coro
    return result, time.perf_counter() - t0


async def main(complaint: str) -> int:
    _banner("Groww multi-agent E2E verification")
    print(f"complaint: {complaint}")
    print(f"data_dir:  {DATA_DIR}")
    print(f"GROWW_USE_LLM={os.getenv('GROWW_USE_LLM', '(unset)')}")
    print(f"GROQ_MODEL={os.getenv('GROQ_MODEL', '(default)')}")
    print(f"llm_enabled: {llm_enabled()}")

    if not llm_enabled():
        print(
            "\nWARNING: LLM classifiers are OFF "
            "(set GROQ_API_KEY and GROWW_USE_LLM=1 in .env). "
            "Falling back to keyword/regex classifiers."
        )

    wall_t0 = time.perf_counter()

    # 1. Ingress
    t0 = time.perf_counter()
    ingress = redact(complaint)
    ingress_s = time.perf_counter() - t0

    # 2-4. Specialists in parallel (same as orchestrator fan-out)
    parallel_t0 = time.perf_counter()
    (facts, facts_s), (pattern, pattern_s), (compliance, compliance_s) = (
        await asyncio.gather(
            _timed(run_facts(ingress.redacted_text, DATA_DIR / "parsed")),
            _timed(
                run_pattern(
                    ingress.redacted_text,
                    DATA_DIR / "analyzed_themes.json",
                    DATA_DIR / "normalized_reviews.json",
                )
            ),
            _timed(run_compliance(ingress.redacted_text, list(ingress.pii_types))),
        )
    )
    parallel_s = time.perf_counter() - parallel_t0

    # 5. Orchestrator merge
    t0 = time.perf_counter()
    draft = merge_draft(
        facts, pattern, compliance, advice_refusal=compliance.advice_refusal
    )
    merge_s = time.perf_counter() - t0

    # 6. Reviewer (+ optional rework)
    prior = [
        AgentsFiredEntry(
            round=1,
            kind="initial",
            fired=["facts", "pattern", "compliance", "orchestrator"],
            skipped=[],
        )
    ]
    t0 = time.perf_counter()
    draft, review, prior = _review_with_optional_rework(
        draft, facts=facts, agents_fired=prior, round_num=1
    )
    review_s = time.perf_counter() - t0

    wall_s = time.perf_counter() - wall_t0

    session = SessionState(
        redacted_text=ingress.redacted_text,
        pii_types=list(ingress.pii_types),
        facts=facts,
        pattern=pattern,
        compliance=compliance,
        draft=draft,
        review=review,
        advice_refusal=compliance.advice_refusal,
        refinement_count=0,
        agents_fired=prior,
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(session.model_dump_json(indent=2), encoding="utf-8")

    _section("1. Ingress (PII redaction)")
    print(f"latency:       {_ms(ingress_s)}")
    print(f"redacted_text: {session.redacted_text}")
    print(f"pii_types:     {session.pii_types or '[]'}")

    _section("2. Facts Agent")
    print(f"latency:       {_ms(facts_s)}")
    print(f"status:        {facts.status}")
    print(f"scheme_id:     {facts.scheme_id}")
    print(f"section:       {facts.section_title}")
    print(f"fact:          {facts.fact}")
    print(f"citation:      {facts.citation}")
    print(f"last_checked:  {facts.last_checked}")
    if facts.searched:
        print(f"searched:      {', '.join(facts.searched[:8])}...")

    _section("3. Pattern Agent")
    print(f"latency:       {_ms(pattern_s)}")
    print(f"theme_id:      {pattern.theme_id}")
    print(f"signal:        {pattern.signal}")
    print(f"count:         {pattern.count}")
    print(f"recent_count:  {pattern.recent_count}")
    print(f"window:        {pattern.window.start} -> {pattern.window.end}")

    _section("4. Compliance Agent")
    print(f"latency:       {_ms(compliance_s)}")
    print(f"flags:           {compliance.flags or '[]'}")
    print(f"advice_refusal:  {compliance.advice_refusal}")

    _section("5. Orchestrator draft")
    print(f"latency:       {_ms(merge_s)}")
    print(f"disposition:   {draft.disposition}")
    print(f"disagreement:  {draft.disagreement}")
    print(f"reply:\n{draft.reply}")
    print(f"citation:      {draft.citation}")
    print(f"last_checked:  {draft.last_checked}")
    note = draft.routing_note
    print(f"routing:       team={note.team}  priority={note.priority}")
    print(f"why:           {note.why}")

    _section("6. Reviewer")
    print(f"latency:       {_ms(review_s)}")
    print(f"status:  {review.status}  (round {review.round})")
    if any(e.kind == "reviewer_rework" for e in prior):
        print("  (reworked after first-pass fail)")
    if review.failures:
        for f in review.failures:
            print(f"  FAIL  {f.check}: {f.detail}")
    else:
        print("  (no failures)")

    _section("7. Agents fired")
    for entry in session.agents_fired:
        print(
            f"  round={entry.round} kind={entry.kind} "
            f"fired={entry.fired} skipped={entry.skipped}"
        )

    _section("Latency summary")
    print(f"  ingress:              {_ms(ingress_s)}")
    print(f"  facts (LLM):          {_ms(facts_s)}")
    print(f"  pattern (LLM):        {_ms(pattern_s)}")
    print(f"  compliance (LLM):     {_ms(compliance_s)}")
    print(f"  specialists wall:     {_ms(parallel_s)}  (parallel fan-out)")
    print(f"  orchestrator merge:   {_ms(merge_s)}")
    print(f"  reviewer:             {_ms(review_s)}")
    print(f"  TOTAL wall-clock:     {_ms(wall_s)}  ({wall_s:.2f}s)")

    _banner(f"Done in {wall_s:.2f}s - session saved: {OUT_PATH}")
    summary = {
        "facts_status": facts.status,
        "scheme_id": facts.scheme_id,
        "theme_id": pattern.theme_id,
        "signal": pattern.signal,
        "disposition": draft.disposition,
        "review": review.status,
        "reply": draft.reply,
        "latency_ms": {
            "ingress": round(ingress_s * 1000),
            "facts": round(facts_s * 1000),
            "pattern": round(pattern_s * 1000),
            "compliance": round(compliance_s * 1000),
            "specialists_wall": round(parallel_s * 1000),
            "orchestrator_merge": round(merge_s * 1000),
            "reviewer": round(review_s * 1000),
            "total_wall": round(wall_s * 1000),
        },
    }
    print(json.dumps(summary, indent=2))
    return 0 if review.status == "pass" else 1


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]).strip() or DEFAULT_COMPLAINT
    raise SystemExit(asyncio.run(main(text)))
