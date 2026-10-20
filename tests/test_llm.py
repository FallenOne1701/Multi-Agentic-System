import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from groww_support.llm import (
    FactsClassification,
    classify_compliance,
    classify_facts,
    classify_theme,
    llm_enabled,
)


def test_llm_disabled_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GROWW_USE_LLM", "1")
    assert llm_enabled() is False


def test_llm_disabled_by_flag(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GROWW_USE_LLM", "0")
    assert llm_enabled() is False


def test_llm_enabled_with_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GROWW_USE_LLM", "1")
    assert llm_enabled() is True


@pytest.mark.asyncio
async def test_classify_facts_parses_json(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GROWW_USE_LLM", "1")

    message = MagicMock()
    message.content = '{"scheme_id": "large_cap", "section_title": "Exit load"}'
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]

    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)

    with patch("groq.AsyncGroq", return_value=client):
        result = await classify_facts("Why exit load on HDFC Large Cap?")

    assert result == FactsClassification(scheme_id="large_cap", section_title="Exit load")


@pytest.mark.asyncio
async def test_classify_facts_rejects_unknown_section(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GROWW_USE_LLM", "1")

    message = MagicMock()
    message.content = '{"scheme_id": "large_cap", "section_title": "Made up"}'
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]

    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)

    with patch("groq.AsyncGroq", return_value=client):
        result = await classify_facts("something")

    assert result is not None
    assert result.scheme_id == "large_cap"
    assert result.section_title is None


@pytest.mark.asyncio
async def test_classify_theme_and_compliance(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GROWW_USE_LLM", "1")

    theme_msg = MagicMock()
    theme_msg.content = '{"theme_id": "fees_brokerage"}'
    compliance_msg = MagicMock()
    compliance_msg.content = '{"advice": true, "performance_claim": false}'

    def _response(content: str):
        message = MagicMock()
        message.content = content
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        return response

    client = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=[_response(theme_msg.content), _response(compliance_msg.content)]
    )

    with patch("groq.AsyncGroq", return_value=client):
        theme = await classify_theme("exit load fees")
        compliance = await classify_compliance("Should I redeem?")

    assert theme is not None and theme.theme_id == "fees_brokerage"
    assert compliance is not None and compliance.advice is True


@pytest.mark.asyncio
async def test_complete_json_returns_none_when_disabled(monkeypatch):
    monkeypatch.setenv("GROWW_USE_LLM", "0")
    assert await classify_facts("anything") is None
