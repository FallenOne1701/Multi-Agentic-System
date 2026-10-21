"""Optional Groq classifiers. Corpus facts and signal math stay deterministic."""

from __future__ import annotations

import json
import os

from pydantic import BaseModel

from groww_support.contracts import SchemeId, ThemeId

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

DEFAULT_MODEL = "openai/gpt-oss-120b"

SECTION_TITLES = (
    "Key fund facts",
    "Exit load",
    "Benchmark",
    "Investment objective",
    "Stamp duty and tax",
    "Fund management",
    "Minimum investments",
)


class FactsClassification(BaseModel):
    scheme_id: SchemeId | None = None
    section_title: str | None = None


class ThemeClassification(BaseModel):
    theme_id: ThemeId = "other"


class ComplianceClassification(BaseModel):
    advice: bool = False
    performance_claim: bool = False


def llm_enabled() -> bool:
    flag = os.getenv("GROWW_USE_LLM", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return bool(os.getenv("GROQ_API_KEY", "").strip())


def _model_name() -> str:
    return os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


async def complete_json(system: str, user: str) -> dict | None:
    """Call Groq chat completions and parse a JSON object. Returns None on any failure."""
    if not llm_enabled():
        return None
    try:
        from groq import AsyncGroq
    except ImportError:
        return None

    try:
        client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
        response = await client.chat.completions.create(
            model=_model_name(),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content or ""
        data = json.loads(content)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


async def classify_facts(redacted_text: str) -> FactsClassification | None:
    system = (
        "You classify Groww mutual-fund support complaints for a retrieval system. "
        "Return JSON only with keys scheme_id and section_title. "
        f"scheme_id must be one of: large_cap, mid_cap, small_cap, gold_fof, silver_fof, or null. "
        f"section_title must be one of: {list(SECTION_TITLES)}, or null. "
        "Use null when the complaint is not about one of the five HDFC schemes or seven sections. "
        "Never invent NAV, returns, or advice."
    )
    data = await complete_json(system, redacted_text)
    if data is None:
        return None
    try:
        result = FactsClassification.model_validate(data)
    except Exception:
        return None
    if result.section_title is not None and result.section_title not in SECTION_TITLES:
        result = result.model_copy(update={"section_title": None})
    return result


async def classify_theme(redacted_text: str) -> ThemeClassification | None:
    system = (
        "Classify the support complaint into exactly one theme. Return JSON with key theme_id. "
        "theme_id must be one of: other, trading_charts, money_movement, reliability, fees_brokerage. "
        "fees_brokerage = exit load, brokerage, fees. "
        "money_movement = withdrawal, deposit, payment. "
        "reliability = crash, lag, hang, downtime. "
        "trading_charts = charts, orders, trades. "
        "other = anything else including generic praise."
    )
    data = await complete_json(system, redacted_text)
    if data is None:
        return None
    try:
        return ThemeClassification.model_validate(data)
    except Exception:
        return None


async def classify_compliance(redacted_text: str) -> ComplianceClassification | None:
    system = (
        "Scan the support complaint for compliance risk. Return JSON with boolean keys "
        "advice and performance_claim. "
        "advice=true if the user asks whether to buy, sell, hold, redeem, stay invested, "
        "or if a scheme is good/worth it. "
        "performance_claim=true if the user asks for or asserts returns, CAGR, or performance figures. "
        "Do not invent PII; ignore tokens like [PAN]."
    )
    data = await complete_json(system, redacted_text)
    if data is None:
        return None
    try:
        return ComplianceClassification.model_validate(data)
    except Exception:
        return None
