from __future__ import annotations

import re
from typing import Literal

from groww_support.contracts import ComplianceResult, PiiType
from groww_support.ingress import redact
from groww_support.llm import classify_compliance, llm_enabled

Flag = Literal["advice", "performance_claim", "pii"]

_ADVICE_PHRASES = (
    "should i",
    "redeem or not",
    "is this scheme good",
    "should i stay",
    "worth it",
)

_ADVICE_ACTION = re.compile(r"(?i)\b(?:buy|sell|hold|redeem)\b")

_PERFORMANCE = (
    "cagr",
    "performance",
    "% return",
)

_RETURN = re.compile(r"(?i)\breturns?\b")


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


async def run_compliance(redacted_text: str, pii_types: list[PiiType]) -> ComplianceResult:
    flags: list[Flag] = []
    advice = _detect_advice(redacted_text)
    performance = _detect_performance(redacted_text)

    # OR with Groq so phrasing the regex misses still flags, without dropping keyword hits.
    if llm_enabled():
        classified = await classify_compliance(redacted_text)
        if classified is not None:
            advice = advice or classified.advice
            performance = performance or classified.performance_claim

    if advice:
        flags.append("advice")
    if performance:
        flags.append("performance_claim")

    # Defense in depth: scan for residual raw PII without changing the given text.
    residual = redact(redacted_text).pii_types
    merged_pii: list[PiiType] = list(pii_types)
    for pii_type in residual:
        if pii_type not in merged_pii:
            merged_pii.append(pii_type)

    if merged_pii:
        flags.append("pii")

    return ComplianceResult(
        flags=flags,
        pii_types=merged_pii,
        advice_refusal=advice or performance,
        redacted_text=redacted_text,
    )
