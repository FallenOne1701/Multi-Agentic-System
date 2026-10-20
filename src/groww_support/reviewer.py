"""Outgoing draft hard-fail reviewer. Optional Gemini OR'd with deterministic rules."""

from __future__ import annotations

import re

from groww_support.contracts import (
    FactsResult,
    OrchestratorOutput,
    ReviewerFailure,
    ReviewerResult,
    RoutingNote,
)
from groww_support.gemini import classify_outgoing, gemini_enabled
from groww_support.ingress import redact

_URL = re.compile(r"https?://[^\s\]\)>]+")

_ADVICE_PHRASES = (
    "you may want to",
    "consider staying",
    "should i",
    "redeem or not",
    "is this scheme good",
    "should i stay",
    "worth it",
    "i recommend",
    "we recommend",
)

# Whole-word investment actions; "redeemed" must not match "redeem".
_ADVICE_ACTION = re.compile(r"(?i)\b(?:buy|sell|hold|redeem)\b")

_PERFORMANCE = (
    "cagr",
    "performance",
    "% return",
)

_RETURN = re.compile(r"(?i)\breturns?\b")

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _sentence_count(text: str) -> int:
    parts = [p.strip() for p in _SENTENCE_END.split(text.strip()) if p.strip()]
    return max(len(parts), 1 if text.strip() else 0)


def _detect_advice(text: str) -> bool:
    lowered = text.lower()
    if any(phrase in lowered for phrase in _ADVICE_PHRASES):
        return True
    return bool(_ADVICE_ACTION.search(text))


def _detect_performance(text: str) -> bool:
    lowered = text.lower()
    if any(phrase in lowered for phrase in _PERFORMANCE):
        return True
    return bool(_RETURN.search(text))


def _scan_pii(text: str) -> list[str]:
    return list(redact(text).pii_types)


def _citation_failures(
    draft: OrchestratorOutput,
    facts: FactsResult | None,
) -> list[ReviewerFailure]:
    failures: list[ReviewerFailure] = []
    urls = _URL.findall(draft.reply)
    covered_path = draft.disposition in ("reply", "escalate", "disagree")

    if len(urls) > 1:
        failures.append(
            ReviewerFailure(check="citation", detail=f"multiple links: {len(urls)}")
        )

    if covered_path and not draft.citation:
        failures.append(
            ReviewerFailure(check="citation", detail="factual covered draft missing citation")
        )
    elif draft.citation is None and urls:
        failures.append(
            ReviewerFailure(check="citation", detail="link in reply but citation field null")
        )

    if facts is not None and facts.status == "covered" and facts.citation:
        if draft.citation and draft.citation != facts.citation:
            failures.append(
                ReviewerFailure(
                    check="citation",
                    detail="draft citation does not match Facts source_url",
                )
            )
        if urls and any(u.rstrip(".,);") != facts.citation for u in urls):
            failures.append(
                ReviewerFailure(
                    check="citation",
                    detail="reply link is not the Facts source_url",
                )
            )

    if draft.disposition in ("handoff", "refuse") and urls:
        failures.append(
            ReviewerFailure(
                check="citation",
                detail="not_covered/refuse draft must not include source links",
            )
        )

    return failures


def _shape_failures(
    draft: OrchestratorOutput,
    facts: FactsResult | None,
) -> list[ReviewerFailure]:
    failures: list[ReviewerFailure] = []
    if _sentence_count(draft.reply) > 3:
        failures.append(
            ReviewerFailure(check="shape", detail="reply exceeds 3 sentences")
        )

    covered = (
        draft.disposition in ("reply", "escalate", "disagree")
        or (facts is not None and facts.status == "covered")
    )
    if covered:
        if not draft.last_checked:
            failures.append(
                ReviewerFailure(check="shape", detail="covered draft missing last_checked")
            )
        elif draft.last_checked not in draft.reply:
            failures.append(
                ReviewerFailure(
                    check="shape",
                    detail="covered reply must include last_checked date",
                )
            )
    return failures


def review_draft(
    draft: OrchestratorOutput,
    *,
    facts: FactsResult | None,
    round: int,
) -> ReviewerResult:
    failures: list[ReviewerFailure] = []
    failures.extend(_citation_failures(draft, facts))
    failures.extend(_shape_failures(draft, facts))

    scan_text = f"{draft.reply}\n{draft.routing_note.why}"
    advice = _detect_advice(scan_text)
    performance = _detect_performance(scan_text)

    if gemini_enabled():
        classified = classify_outgoing(draft.reply, draft.routing_note.why)
        if classified is not None:
            advice = advice or classified.advice
            performance = performance or classified.performance_claim

    if advice:
        failures.append(ReviewerFailure(check="advice", detail="advice language in draft"))
    if performance:
        failures.append(
            ReviewerFailure(check="performance", detail="performance claim in draft")
        )

    pii_hits = _scan_pii(draft.reply) + _scan_pii(draft.routing_note.why)
    if pii_hits:
        failures.append(
            ReviewerFailure(
                check="pii",
                detail=f"raw PII residual: {', '.join(sorted(set(pii_hits)))}",
            )
        )

    # Deduplicate by check name (first detail wins).
    seen: set[str] = set()
    unique: list[ReviewerFailure] = []
    for failure in failures:
        if failure.check in seen:
            continue
        seen.add(failure.check)
        unique.append(failure)

    if not unique:
        status: str = "pass"
    elif round >= 2:
        status = "blocked"
    else:
        status = "fail"

    return ReviewerResult(status=status, round=round, failures=unique)


def _strip_advice(text: str) -> str:
    out = text
    for phrase in _ADVICE_PHRASES:
        out = re.sub(re.escape(phrase), "", out, flags=re.IGNORECASE)
    out = _ADVICE_ACTION.sub("", out)
    return re.sub(r"\s{2,}", " ", out).strip()


def _truncate_sentences(text: str, limit: int = 3) -> str:
    parts = [p.strip() for p in _SENTENCE_END.split(text.strip()) if p.strip()]
    if len(parts) <= limit:
        return text.strip()
    return " ".join(parts[:limit])


def rewrite_draft(
    draft: OrchestratorOutput,
    *,
    facts: FactsResult | None,
    failures: list[ReviewerFailure],
) -> OrchestratorOutput:
    """Deterministic one-shot rewrite from the same specialist results."""
    reply = draft.reply
    citation = draft.citation
    last_checked = draft.last_checked
    why = draft.routing_note.why
    checks = {f.check for f in failures}

    if "advice" in checks or "performance" in checks:
        reply = _strip_advice(reply)
        for token in ("cagr", "performance", "% return"):
            reply = re.sub(re.escape(token), "", reply, flags=re.IGNORECASE)
        reply = _RETURN.sub("", reply)
        reply = re.sub(r"\s{2,}", " ", reply).strip()

    if "citation" in checks and facts is not None and facts.status == "covered":
        citation = facts.citation
        last_checked = facts.last_checked
        reply = (
            f"{facts.fact} "
            f"Source: {facts.citation}. "
            f"Last checked: {facts.last_checked}."
        )

    if "shape" in checks:
        if facts is not None and facts.status == "covered" and facts.last_checked:
            last_checked = facts.last_checked
            if last_checked not in reply:
                reply = f"{reply.rstrip('.')} Last checked: {last_checked}."
        reply = _truncate_sentences(reply, 3)

    if "pii" in checks or _scan_pii(reply) or _scan_pii(why):
        reply = redact(reply).redacted_text
        why = redact(why).redacted_text

    reply = _truncate_sentences(reply, 3)

    return OrchestratorOutput(
        reply=reply,
        last_checked=last_checked,
        citation=citation,
        disposition=draft.disposition,
        disagreement=draft.disagreement,
        routing_note=RoutingNote(
            team=draft.routing_note.team,
            priority=draft.routing_note.priority,
            why=why,
        ),
    )
