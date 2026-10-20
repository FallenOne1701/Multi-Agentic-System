"""Session pushback classification for selective refinement."""

from __future__ import annotations

from dataclasses import dataclass

from groww_support.contracts import AgentName

MAX_REFINEMENTS = 5


@dataclass(frozen=True)
class RefinePlan:
    """Which specialists to re-run; orchestrator always runs."""

    facts: bool = False
    pattern: bool = False
    compliance: bool = False


def classify_pushback(pushback: str) -> RefinePlan:
    """Keyword rules mapping human pushback → agents that must re-run."""
    text = pushback.lower()

    want_facts = any(
        cue in text
        for cue in (
            "different scheme",
            "another scheme",
            "wrong scheme",
            "other scheme",
            "large cap",
            "mid cap",
            "small cap",
            "gold",
            "silver",
        )
    )
    want_pattern = any(
        cue in text
        for cue in (
            "fee",
            "fees",
            "brokerage",
            "theme",
            "last week",
            "recurring",
            "rising",
            "pattern",
        )
    )
    # New complaint wording / advice rephrase → re-scan compliance.
    want_compliance = any(
        cue in text
        for cue in (
            "worth it",
            "should i",
            "redeem",
            "new complaint",
            "actually the complaint",
            "they said",
            "user said",
            "changed the complaint",
        )
    )

    # Pure wording/length tweaks leave specialists skipped.
    wording_only = any(
        cue in text
        for cue in (
            "shorter",
            "longer",
            "wording",
            "rephrase the reply",
            "make it",
            "please",
        )
    )
    if wording_only and not (want_facts or want_pattern or want_compliance):
        return RefinePlan()

    return RefinePlan(facts=want_facts, pattern=want_pattern, compliance=want_compliance)


def agents_for_plan(plan: RefinePlan) -> tuple[list[AgentName], list[AgentName]]:
    fired: list[AgentName] = []
    skipped: list[AgentName] = []
    for name, needed in (
        ("facts", plan.facts),
        ("pattern", plan.pattern),
        ("compliance", plan.compliance),
    ):
        if needed:
            fired.append(name)  # type: ignore[arg-type]
        else:
            skipped.append(name)  # type: ignore[arg-type]
    fired.append("orchestrator")
    return fired, skipped
