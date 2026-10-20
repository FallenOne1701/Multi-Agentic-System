"""Optional Gemini classifier for the outgoing reviewer (not Groq)."""

from __future__ import annotations

import json
import os

from pydantic import BaseModel

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


class OutgoingCompliance(BaseModel):
    advice: bool = False
    performance_claim: bool = False


def gemini_enabled() -> bool:
    flag = os.getenv("GROWW_USE_LLM", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def _model_name() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL


def classify_outgoing(reply: str, routing_why: str) -> OutgoingCompliance | None:
    """Scan an outgoing draft for advice / performance. Returns None on any failure."""
    if not gemini_enabled():
        return None
    try:
        from google import genai
    except ImportError:
        return None

    system = (
        "You review an outgoing Groww support draft for compliance. "
        "Return JSON only with boolean keys advice and performance_claim. "
        "advice=true if the draft recommends buying, selling, holding, redeeming, "
        "staying invested, or uses phrases like 'you may want to' or 'consider staying'. "
        "performance_claim=true if the draft asserts returns, CAGR, or performance figures. "
        "Tokens like [PAN] are not PII leaks. Do not invent facts."
    )
    user = f"Draft reply:\n{reply}\n\nRouting note why:\n{routing_why}"

    try:
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model=_model_name(),
            contents=user,
            config={
                "system_instruction": system,
                "temperature": 0,
                "response_mime_type": "application/json",
                "response_schema": OutgoingCompliance,
            },
        )
        if getattr(response, "parsed", None) is not None:
            parsed = response.parsed
            if isinstance(parsed, OutgoingCompliance):
                return parsed
            return OutgoingCompliance.model_validate(parsed)
        text = (response.text or "").strip()
        data = json.loads(text)
        return OutgoingCompliance.model_validate(data)
    except Exception:
        return None
