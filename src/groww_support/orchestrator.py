from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from groww_support.agents.compliance import run_compliance
from groww_support.agents.facts import run_facts
from groww_support.agents.pattern import run_pattern
from groww_support.contracts import (
    AgentsFiredEntry,
    ComplianceResult,
    Disposition,
    FactsResult,
    OrchestratorOutput,
    PatternResult,
    PatternSignal,
    Priority,
    RoutingNote,
    SessionState,
    ThemeId,
)
from groww_support.ingress import redact

TEAM_BY_THEME: dict[ThemeId, str] = {
    "fees_brokerage": "Fees and mutual fund ops",
    "money_movement": "Payments",
    "trading_charts": "Trading platform",
    "reliability": "App stability",
    "other": "General support",
}

REFUSAL_REPLY = (
    "We cannot provide investment advice or product recommendations. "
    "Please contact Groww support for account help."
)

SURGE_RECENT = 40


class SpecialistState(TypedDict, total=False):
    redacted_text: str
    pii_types: list[Any]
    parsed_dir: str
    themes_path: str
    reviews_path: str
    facts: FactsResult
    pattern: PatternResult
    compliance: ComplianceResult


def team_for_theme(theme_id: ThemeId) -> str:
    return TEAM_BY_THEME.get(theme_id, "General support")


def priority_for(signal: PatternSignal, disposition: Disposition) -> Priority:
    if signal == "rising":
        return "P1"
    if disposition in ("escalate", "disagree") or signal == "recurring":
        return "P2"
    return "P3"


def _decide_disposition(
    facts: FactsResult,
    pattern: PatternResult,
    compliance: ComplianceResult,
    *,
    advice_refusal: bool,
) -> Disposition:
    if (
        advice_refusal
        or "advice" in compliance.flags
        or "performance_claim" in compliance.flags
    ):
        return "refuse"
    if facts.status == "not_covered":
        return "handoff"
    if pattern.signal == "rising" and pattern.recent_count >= SURGE_RECENT:
        return "disagree"
    if pattern.signal in ("recurring", "rising"):
        return "escalate"
    return "reply"


def _covered_reply(facts: FactsResult) -> str:
    return (
        f"{facts.fact} "
        f"Source: {facts.citation}. "
        f"Last checked: {facts.last_checked}."
    )


def _routing_why(
    disposition: Disposition,
    facts: FactsResult,
    pattern: PatternResult,
) -> str:
    if disposition == "refuse":
        return (
            f"Compliance refusal for theme {pattern.theme_id} "
            f"(signal={pattern.signal}, count={pattern.count})."
        )
    if disposition == "handoff":
        searched = ", ".join(facts.searched[:12]) or "none"
        return (
            f"Facts not_covered for theme {pattern.theme_id}. "
            f"Searched: {searched}."
        )
    if disposition == "disagree":
        return (
            f"Corpus has an answer for {facts.scheme_id} {facts.section_title}, "
            f"and {pattern.recent_count} reviews in the recent window match "
            f"{pattern.theme_id}; ticket stays open."
        )
    if disposition == "escalate":
        return (
            f"Facts covered for {facts.scheme_id} {facts.section_title}. "
            f"Pattern {pattern.theme_id} is {pattern.signal} across "
            f"{pattern.count} reviews from {pattern.window.start} to "
            f"{pattern.window.end}, so this ticket stays open."
        )
    return (
        f"Facts covered for {facts.scheme_id} {facts.section_title}. "
        f"Pattern {pattern.theme_id} is {pattern.signal} "
        f"(count={pattern.count})."
    )


def merge_draft(
    facts: FactsResult,
    pattern: PatternResult,
    compliance: ComplianceResult,
    *,
    advice_refusal: bool,
) -> OrchestratorOutput:
    disposition = _decide_disposition(
        facts, pattern, compliance, advice_refusal=advice_refusal
    )
    disagreement = disposition == "disagree"
    priority = priority_for(pattern.signal, disposition)
    team = team_for_theme(pattern.theme_id)
    why = _routing_why(disposition, facts, pattern)

    if disposition == "refuse":
        reply = REFUSAL_REPLY
        citation = None
        last_checked = None
    elif disposition == "handoff":
        searched = ", ".join(facts.searched[:12]) or "no sections"
        reply = (
            f"This question is not covered by our scheme corpus. "
            f"Searched: {searched}."
        )
        citation = None
        last_checked = None
    else:
        reply = _covered_reply(facts)
        citation = facts.citation
        last_checked = facts.last_checked

    return OrchestratorOutput(
        reply=reply,
        last_checked=last_checked,
        citation=citation,
        disposition=disposition,
        disagreement=disagreement,
        routing_note=RoutingNote(team=team, priority=priority, why=why),
    )


async def _facts_node(state: SpecialistState) -> dict[str, Any]:
    facts = await run_facts(state["redacted_text"], Path(state["parsed_dir"]))
    return {"facts": facts}


async def _pattern_node(state: SpecialistState) -> dict[str, Any]:
    pattern = await run_pattern(
        state["redacted_text"],
        Path(state["themes_path"]),
        Path(state["reviews_path"]),
    )
    return {"pattern": pattern}


async def _compliance_node(state: SpecialistState) -> dict[str, Any]:
    compliance = await run_compliance(state["redacted_text"], state["pii_types"])
    return {"compliance": compliance}


async def _join_node(state: SpecialistState) -> dict[str, Any]:
    return {}


def build_specialist_graph():
    graph = StateGraph(SpecialistState)
    graph.add_node("facts", _facts_node)
    graph.add_node("pattern", _pattern_node)
    graph.add_node("compliance", _compliance_node)
    graph.add_node("join", _join_node)
    graph.add_edge(START, "facts")
    graph.add_edge(START, "pattern")
    graph.add_edge(START, "compliance")
    graph.add_edge("facts", "join")
    graph.add_edge("pattern", "join")
    graph.add_edge("compliance", "join")
    graph.add_edge("join", END)
    return graph.compile()


_SPECIALIST_GRAPH = None


def _graph():
    global _SPECIALIST_GRAPH
    if _SPECIALIST_GRAPH is None:
        _SPECIALIST_GRAPH = build_specialist_graph()
    return _SPECIALIST_GRAPH


async def run_specialists_parallel(
    redacted_text: str,
    pii_types: list,
    data_dir: Path,
) -> tuple[FactsResult, PatternResult, ComplianceResult]:
    state = await _graph().ainvoke(
        {
            "redacted_text": redacted_text,
            "pii_types": list(pii_types),
            "parsed_dir": str(data_dir / "parsed"),
            "themes_path": str(data_dir / "analyzed_themes.json"),
            "reviews_path": str(data_dir / "normalized_reviews.json"),
        }
    )
    return state["facts"], state["pattern"], state["compliance"]


async def handle_complaint(
    raw: str,
    data_dir: Path,
    session: SessionState | None = None,
) -> SessionState:
    ingress = redact(raw)
    facts, pattern, compliance = await run_specialists_parallel(
        ingress.redacted_text,
        ingress.pii_types,
        data_dir,
    )
    advice_refusal = bool(session.advice_refusal if session else False) or (
        compliance.advice_refusal
    )
    draft = merge_draft(
        facts, pattern, compliance, advice_refusal=advice_refusal
    )

    prior = list(session.agents_fired) if session else []
    round_num = (prior[-1].round + 1) if prior else 1
    prior.append(
        AgentsFiredEntry(
            round=round_num,
            kind="initial",
            fired=["facts", "pattern", "compliance", "orchestrator"],
            skipped=[],
        )
    )

    return SessionState(
        redacted_text=ingress.redacted_text,
        pii_types=list(ingress.pii_types),
        facts=facts,
        pattern=pattern,
        compliance=compliance,
        draft=draft,
        review=session.review if session else None,
        advice_refusal=advice_refusal,
        refinement_count=session.refinement_count if session else 0,
        agents_fired=prior,
    )
