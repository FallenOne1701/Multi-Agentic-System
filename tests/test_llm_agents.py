"""Agent integration with mocked Groq classifiers (no network)."""

from unittest.mock import AsyncMock, patch

import pytest

from groww_support.agents.compliance import run_compliance
from groww_support.agents.facts import run_facts
from groww_support.agents.pattern import run_pattern
from groww_support.llm import (
    ComplianceClassification,
    FactsClassification,
    ThemeClassification,
)


@pytest.mark.asyncio
async def test_facts_uses_llm_match_but_corpus_text(parsed_dir, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GROWW_USE_LLM", "1")

    with patch(
        "groww_support.agents.facts.classify_facts",
        new=AsyncMock(
            return_value=FactsClassification(scheme_id="large_cap", section_title="Exit load")
        ),
    ):
        # Wording that keyword cues might miss for section
        result = await run_facts("HDFC Large Cap fee when I cashed out early", parsed_dir)

    assert result.status == "covered"
    assert result.scheme_id == "large_cap"
    assert "1%" in (result.fact or "")
    assert result.citation.endswith("hdfc-large-cap-fund-direct-growth")


@pytest.mark.asyncio
async def test_pattern_uses_llm_theme(data_dir, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GROWW_USE_LLM", "1")

    with patch(
        "groww_support.agents.pattern.classify_theme",
        new=AsyncMock(return_value=ThemeClassification(theme_id="fees_brokerage")),
    ):
        result = await run_pattern(
            "They took money when I left the fund",
            data_dir / "analyzed_themes.json",
            data_dir / "normalized_reviews.json",
        )

    assert result.theme_id == "fees_brokerage"
    assert result.count == 136


@pytest.mark.asyncio
async def test_compliance_ors_llm_advice(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GROWW_USE_LLM", "1")

    with patch(
        "groww_support.agents.compliance.classify_compliance",
        new=AsyncMock(
            return_value=ComplianceClassification(advice=True, performance_claim=False)
        ),
    ):
        # Soft phrasing that keyword list may miss
        result = await run_compliance("Is staying in large cap the right move for me?", [])

    assert "advice" in result.flags
    assert result.advice_refusal is True
