from unittest.mock import MagicMock, patch

from groww_support.gemini import OutgoingCompliance, classify_outgoing, gemini_enabled


def test_gemini_disabled_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GROWW_USE_LLM", "1")
    assert gemini_enabled() is False


def test_gemini_disabled_by_flag(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROWW_USE_LLM", "0")
    assert gemini_enabled() is False


def test_classify_outgoing_parses_schema(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROWW_USE_LLM", "1")

    response = MagicMock()
    response.parsed = OutgoingCompliance(advice=True, performance_claim=False)
    response.text = ""

    client = MagicMock()
    client.models.generate_content.return_value = response

    with patch("google.genai.Client", return_value=client):
        result = classify_outgoing(
            "You may want to consider staying invested.",
            "one-off",
        )

    assert result is not None
    assert result.advice is True
    assert result.performance_claim is False
