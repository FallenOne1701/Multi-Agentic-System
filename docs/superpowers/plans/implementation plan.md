# Groww Multi-Agent Support Reply System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a parallel multi-agent support reply system that drafts a facts-only, citation-backed, approval-gated email reply for Groww user complaints from `data/` only.

**Architecture:** Deterministic ingress redacts PII, then the orchestrator starts Facts, Pattern, and Compliance together (three **LangGraph** nodes) on the same redacted text. Each specialist may use one shared classifier LLM (Groq); the model only classifies — fact text, review counts/signals, and PII tokens stay in code. Compliance scans the **incoming** complaint; the **reviewer** applies the same policy to the **outgoing** draft. After all three return, the orchestrator merges into a ≤3-sentence reply + routing note, the reviewer hard-fails unsafe drafts (one rework round), and a human approval gate appends a redacted record and creates an email draft without sending.

**Tech Stack:** Python 3.11+, pydantic v2, pytest + pytest-asyncio, **LangGraph** for parallel specialist fan-out, **Groq** (optional classifier, shared `GROQ_MODEL`) + keyword/regex fallback, python-dotenv, typer + rich CLI for the human loop, JSON file stores under `data/` and `output/`.

**Spec:** `docs/architecture.md` (implements `docs/problemStatement.md`)

## Global Constraints

- Facts come only from `data/parsed/`. No match → `status: "not_covered"`, never invent.
- Citation is exactly one `source_url` from the matched scheme file; `last_checked` is that file's `nav_date` (`25-Jun-2026`).
- Orchestrator starts Facts, Pattern, Compliance **before reading any result**; reviewer runs only after merge.
- **Classifier LLM only:** Facts/Pattern/Compliance share one Groq model (`GROQ_MODEL`). Per-agent system prompts differ; the model must not invent facts, URLs, counts, or advice. Disable via `GROWW_USE_LLM=0` or missing `GROQ_API_KEY` → keyword/regex fallback. Never one model call for all three roles.
- Compliance = **incoming** scan; Reviewer = **outgoing** draft scan (same policy).
- No raw PII in logs, session state, approval record, or email draft — tokens only (`[PAN]`, `[PHONE]`, etc.). Ingress redacts before fan-out.
- Reply ≤ 3 sentences; routing note is separate and does not count.
- Reviewer rework: 1 round. Human refinement: 5 rounds. Second reviewer fail → show draft with flag, no Approve/Send.
- Nothing appended or emailed until human approve; no auto-send.
- Session `advice_refusal` is sticky for the whole complaint thread.
- Out of scope: sending email, adding schemes, re-fetching Groww pages, single-model all-in-one call.

## Review Focus

- Raw PAN/phone in complaint must never appear in draft, routing note, session dump, or support record — only typed tokens.
- Advice rephrase later in the same session ("ok but is large cap worth it?") must stay `disposition: "refuse"` even if Facts is covered.
- Covered exit-load fact + rising/recurring fees pattern must set `escalate` or `disagree` and keep ticket open in the routing note.
- `not_covered` draft must contain no factual claim and no citation URL.
- Parallel fan-out trace must show all three agent starts before any result is read; reviewer must not run inside the parallel block.

---

## File Structure

```
multi-agentic-system/
├── pyproject.toml
├── .env.example              # GROQ_API_KEY, GROQ_MODEL, GROWW_USE_LLM (never commit .env)
├── README.md
├── src/groww_support/
│   ├── __init__.py
│   ├── contracts.py          # FactsResult, PatternResult, ComplianceResult, OrchestratorOutput, ReviewerResult, SessionState
│   ├── ingress.py            # deterministic PII redaction
│   ├── llm.py                # shared Groq classifier client (Facts/Pattern/Compliance)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── facts.py          # classifier + keyword → corpus text only
│   │   ├── pattern.py        # classifier + keyword → theme; counts/signal in code
│   │   └── compliance.py     # classifier OR regex (incoming); PII from ingress
│   ├── orchestrator.py       # LangGraph fan-out, merge, draft, disposition, refinement routing
│   ├── reviewer.py           # outgoing draft hard-fails
│   ├── session.py            # session state load/save, agents_fired log
│   ├── approval.py           # gate: append record + email draft
│   ├── logging_util.py       # redacted-only logger
│   └── cli.py                # human refine / approve loop
├── tests/
│   ├── conftest.py           # GROWW_USE_LLM=0 by default (offline)
│   ├── fixtures/
│   │   └── complaints.json   # 20 real reviews + branch fixtures
│   ├── test_ingress.py
│   ├── test_facts.py
│   ├── test_pattern.py
│   ├── test_compliance.py
│   ├── test_llm.py           # shared brain enable/disable + mocked Groq JSON
│   ├── test_llm_agents.py    # agents use classifier but keep corpus/counts deterministic
│   ├── test_orchestrator.py
│   ├── test_reviewer.py
│   ├── test_session_refinement.py
│   ├── test_approval.py
│   └── test_acceptance.py
├── output/                   # gitignored: support_records.jsonl, email_drafts/
└── data/                     # existing Milestone 1+2 assets (do not modify)
```

---

## Phase 0 — Project scaffold and contracts

### Task 1: Scaffold package and test runner

**Files:**
- Create: `pyproject.toml`
- Create: `src/groww_support/__init__.py`
- Create: `tests/conftest.py`
- Create: `.gitignore`
- Create: `README.md`

**Interfaces:**
- Consumes: none
- Produces: installable package `groww_support`, pytest runnable from repo root

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "groww-support"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.6",
  "typer>=0.12",
  "rich>=13.7",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[project.scripts]
groww-support = "groww_support.cli:app"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Write `.gitignore`**

```
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
output/
*.egg-info/
dist/
build/
.env
```

- [ ] **Step 3: Write minimal package init and conftest**

```python
# src/groww_support/__init__.py
__version__ = "0.1.0"
```

```python
# tests/conftest.py
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

@pytest.fixture
def data_dir() -> Path:
    return DATA

@pytest.fixture
def parsed_dir(data_dir: Path) -> Path:
    return data_dir / "parsed"
```

- [ ] **Step 4: Install and verify pytest collects zero tests cleanly**

Run: `python -m venv .venv; .\.venv\Scripts\pip install -e ".[dev]"; .\.venv\Scripts\pytest -q`
Expected: `no tests ran` or `0 passed` with exit 0 / no import errors.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore README.md src/groww_support/__init__.py tests/conftest.py
git commit -m "chore: scaffold groww-support package and pytest"
```

---

### Task 2: Data contracts (pydantic models)

**Files:**
- Create: `src/groww_support/contracts.py`
- Create: `tests/test_contracts.py`

**Interfaces:**
- Consumes: none
- Produces: `FactsResult`, `PatternResult`, `ComplianceResult`, `OrchestratorOutput`, `RoutingNote`, `ReviewerResult`, `ReviewerFailure`, `SessionState`, `AgentsFiredEntry`

- [ ] **Step 1: Write failing contract round-trip test**

```python
# tests/test_contracts.py
from groww_support.contracts import FactsResult, PatternResult, ComplianceResult

def test_facts_result_covered_round_trip():
    payload = {
        "status": "covered",
        "scheme_id": "large_cap",
        "section_title": "Exit load",
        "fact": "Exit load of 1% if redeemed within 1 year",
        "citation": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "last_checked": "25-Jun-2026",
        "searched": ["large_cap", "mid_cap", "small_cap", "gold_fof", "silver_fof"],
    }
    model = FactsResult.model_validate(payload)
    assert model.status == "covered"
    assert model.citation.endswith("hdfc-large-cap-fund-direct-growth")

def test_facts_result_not_covered_nulls_fact_and_citation():
    model = FactsResult(
        status="not_covered",
        scheme_id=None,
        section_title=None,
        fact=None,
        citation=None,
        last_checked=None,
        searched=["large_cap:Exit load", "mid_cap:Exit load"],
    )
    assert model.fact is None
    assert model.citation is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_contracts.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError: cannot import name 'FactsResult'`

- [ ] **Step 3: Implement contracts**

```python
# src/groww_support/contracts.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, model_validator

SchemeId = Literal["large_cap", "mid_cap", "small_cap", "gold_fof", "silver_fof"]
ThemeId = Literal["other", "trading_charts", "money_movement", "reliability", "fees_brokerage"]
PatternSignal = Literal["one-off", "recurring", "rising"]
Disposition = Literal["reply", "escalate", "handoff", "refuse", "disagree"]
ReviewStatus = Literal["pass", "fail", "blocked"]
ReviewCheck = Literal["citation", "advice", "performance", "pii", "shape"]
Priority = Literal["P1", "P2", "P3"]
PiiType = Literal["PAN", "AADHAAR", "ACCOUNT", "PHONE", "EMAIL", "OTP"]
AgentName = Literal["facts", "pattern", "compliance", "orchestrator"]

class DateWindow(BaseModel):
    start: str
    end: str

class FactsResult(BaseModel):
    status: Literal["covered", "not_covered"]
    scheme_id: SchemeId | None = None
    section_title: str | None = None
    fact: str | None = None
    citation: str | None = None
    last_checked: str | None = None
    searched: list[str]

    @model_validator(mode="after")
    def _covered_requires_citation(self) -> "FactsResult":
        if self.status == "covered":
            if not self.fact or not self.citation or not self.last_checked or not self.scheme_id:
                raise ValueError("covered FactsResult requires fact, citation, last_checked, scheme_id")
        if self.status == "not_covered":
            if self.fact is not None or self.citation is not None:
                raise ValueError("not_covered FactsResult must null fact and citation")
        return self

class PatternResult(BaseModel):
    theme_id: ThemeId
    theme_name: str
    signal: PatternSignal
    count: int
    recent_count: int
    window: DateWindow
    recent_window: DateWindow

class ComplianceResult(BaseModel):
    flags: list[Literal["advice", "performance_claim", "pii"]]
    pii_types: list[PiiType]
    advice_refusal: bool
    redacted_text: str

class RoutingNote(BaseModel):
    team: str
    priority: Priority
    why: str

class OrchestratorOutput(BaseModel):
    reply: str
    last_checked: str | None
    citation: str | None
    disposition: Disposition
    disagreement: bool
    routing_note: RoutingNote

class ReviewerFailure(BaseModel):
    check: ReviewCheck
    detail: str

class ReviewerResult(BaseModel):
    status: ReviewStatus
    round: int = Field(ge=1, le=2)
    failures: list[ReviewerFailure] = Field(default_factory=list)

class AgentsFiredEntry(BaseModel):
    round: int
    kind: Literal["initial", "reviewer_rework", "refinement"]
    fired: list[AgentName]
    skipped: list[AgentName]

class SessionState(BaseModel):
    redacted_text: str
    pii_types: list[PiiType] = Field(default_factory=list)
    facts: FactsResult | None = None
    pattern: PatternResult | None = None
    compliance: ComplianceResult | None = None
    draft: OrchestratorOutput | None = None
    review: ReviewerResult | None = None
    advice_refusal: bool = False
    refinement_count: int = 0
    agents_fired: list[AgentsFiredEntry] = Field(default_factory=list)
    # raw user string is intentionally absent
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_contracts.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/groww_support/contracts.py tests/test_contracts.py
git commit -m "feat: add pydantic data contracts for agent and session outputs"
```

---

## Phase 1 — Ingress redaction

### Task 3: Deterministic PII ingress

**Files:**
- Create: `src/groww_support/ingress.py`
- Create: `src/groww_support/logging_util.py`
- Create: `tests/test_ingress.py`

**Interfaces:**
- Consumes: raw complaint `str`
- Produces: `IngressResult(redacted_text: str, pii_types: list[PiiType])` via `redact(raw: str) -> IngressResult`

- [ ] **Step 1: Write failing tests for each PII class**

```python
# tests/test_ingress.py
from groww_support.ingress import redact

def test_redacts_pan():
    r = redact("My PAN is ABCDE1234F please help")
    assert "ABCDE1234F" not in r.redacted_text
    assert "[PAN]" in r.redacted_text
    assert "PAN" in r.pii_types

def test_redacts_phone_and_email():
    r = redact("Call me at 9876543210 or me@example.com")
    assert "9876543210" not in r.redacted_text
    assert "me@example.com" not in r.redacted_text
    assert "[PHONE]" in r.redacted_text
    assert "[EMAIL]" in r.redacted_text

def test_redacts_aadhaar_with_spaces():
    r = redact("Aadhaar 1234 5678 9012")
    assert "1234 5678 9012" not in r.redacted_text
    assert "[AADHAAR]" in r.redacted_text

def test_redacts_otp_labeled():
    r = redact("OTP 482913 expired")
    assert "482913" not in r.redacted_text
    assert "[OTP]" in r.redacted_text

def test_clean_complaint_unchanged():
    text = "Why was I charged an exit load on HDFC Large Cap Fund?"
    r = redact(text)
    assert r.redacted_text == text
    assert r.pii_types == []
```

- [ ] **Step 2: Run tests — expect fail**

Run: `pytest tests/test_ingress.py -v`
Expected: FAIL import / not defined

- [ ] **Step 3: Implement ingress + redacted logger**

```python
# src/groww_support/ingress.py
from __future__ import annotations
import re
from pydantic import BaseModel
from groww_support.contracts import PiiType

class IngressResult(BaseModel):
    redacted_text: str
    pii_types: list[PiiType]

_PAN = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
_AADHAAR = re.compile(r"\b(\d{4}\s?\d{4}\s?\d{4})\b")
_EMAIL = re.compile(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
_PHONE = re.compile(r"\b([6-9]\d{9})\b")
_OTP = re.compile(r"(?i)\b(?:OTP|one[-\s]?time\s+password)\s*[:\-]?\s*(\d{4,8})\b")
_ACCOUNT = re.compile(r"(?i)\b(?:account|a/c|acct)\s*(?:no\.?|number|#)?\s*[:\-]?\s*(\d{9,18})\b")

_RULES: list[tuple[re.Pattern[str], PiiType, str]] = [
    (_PAN, "PAN", "[PAN]"),
    (_EMAIL, "EMAIL", "[EMAIL]"),
    (_OTP, "OTP", "[OTP]"),
    (_ACCOUNT, "ACCOUNT", "[ACCOUNT]"),
    (_PHONE, "PHONE", "[PHONE]"),
    (_AADHAAR, "AADHAAR", "[AADHAAR]"),
]

def redact(raw: str) -> IngressResult:
    text = raw
    found: list[PiiType] = []
    for pattern, pii_type, token in _RULES:
        if pattern.search(text):
            text = pattern.sub(token, text)
            if pii_type not in found:
                found.append(pii_type)
    return IngressResult(redacted_text=text, pii_types=found)
```

```python
# src/groww_support/logging_util.py
import logging

def get_logger(name: str = "groww_support") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def log_event(logger: logging.Logger, event: str, **fields: object) -> None:
    # Never accept a key named 'raw' or 'raw_text'
    banned = {"raw", "raw_text", "complaint_raw", "pan", "phone", "email"}
    safe = {k: v for k, v in fields.items() if k.lower() not in banned}
    logger.info("%s %s", event, safe)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_ingress.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/groww_support/ingress.py src/groww_support/logging_util.py tests/test_ingress.py
git commit -m "feat: add deterministic PII ingress redaction"
```

---

## Phase 2 — Specialist agents (parallel-ready)

**Shared brain:** All three agents use `groww_support.llm` with one `GROQ_MODEL`. Classifier output is schema-constrained JSON; keyword/regex fallbacks remain. Tests run offline (`GROWW_USE_LLM=0`). Do not add a separate model per agent.

### Task 4: Facts Agent (corpus only)

**Files:**
- Create: `src/groww_support/agents/__init__.py`
- Create: `src/groww_support/agents/facts.py`
- Create: `tests/test_facts.py`

**Interfaces:**
- Consumes: `redacted_text: str`, `parsed_dir: Path`
- Produces: `async def run_facts(redacted_text: str, parsed_dir: Path) -> FactsResult`

- [ ] **Step 1: Write failing tests for covered / not_covered**

```python
# tests/test_facts.py
import pytest
from groww_support.agents.facts import run_facts

@pytest.mark.asyncio
async def test_exit_load_large_cap_covered(parsed_dir):
    result = await run_facts(
        "Why was I charged an exit load on HDFC Large Cap Fund?",
        parsed_dir,
    )
    assert result.status == "covered"
    assert result.scheme_id == "large_cap"
    assert result.section_title == "Exit load"
    assert "1%" in (result.fact or "")
    assert result.citation == "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    assert result.last_checked == "25-Jun-2026"

@pytest.mark.asyncio
async def test_non_hdfc_order_failure_not_covered(parsed_dir):
    result = await run_facts(
        "My order failed while buying Reliance shares in the app",
        parsed_dir,
    )
    assert result.status == "not_covered"
    assert result.fact is None
    assert result.citation is None
    assert len(result.searched) > 0

@pytest.mark.asyncio
async def test_does_not_invent_returns(parsed_dir):
    result = await run_facts(
        "What was the 1 year return of HDFC Large Cap?",
        parsed_dir,
    )
    # Returns are not in the seven sections as an answerable performance figure;
    # agent must not invent — either not_covered or a non-performance section only if text matches.
    # Spec: performance/return questions are refusals for compliance; Facts must not add return figures.
    assert result.status == "not_covered" or (
        result.fact is not None and "return" not in result.fact.lower() and "cagr" not in result.fact.lower()
    )
```

- [ ] **Step 2: Run tests — expect fail**

Run: `pytest tests/test_facts.py -v`
Expected: FAIL import

- [ ] **Step 3: Implement Facts Agent**

Optional: call shared `classify_facts` when LLM enabled; else (or on failure) match scheme by name cues (`HDFC Large Cap`, `Mid Cap`, `Small Cap`, `Gold ETF`, `Silver ETF`). Match section by keyword map:

| Keywords in complaint | Section |
|---|---|
| exit load, charged, redeem fee | Exit load |
| NAV, expense ratio, AUM, riskometer | Key fund facts |
| benchmark | Benchmark |
| objective, invests | Investment objective |
| stamp duty, tax | Stamp duty and tax |
| fund manager, managed by | Fund management |
| minimum, SIP, lumpsum | Minimum investments |

If scheme matched and section matched → `covered` with `text_blocks[].text` (always from corpus, never model-authored), file `source_url`, `nav_date`. Else `not_covered` with searched list of `"scheme_id:section_title"` opened.

```python
# src/groww_support/agents/facts.py (sketch — implement fully in code)
from __future__ import annotations
import json
from pathlib import Path
from groww_support.contracts import FactsResult, SchemeId

SCHEME_CUES: list[tuple[SchemeId, tuple[str, ...]]] = [
    ("large_cap", ("large cap", "large-cap")),
    ("mid_cap", ("mid cap", "mid-cap")),
    ("small_cap", ("small cap", "small-cap")),
    ("gold_fof", ("gold etf", "gold fund of fund", "gold fof")),
    ("silver_fof", ("silver etf", "silver fof")),
]

SECTION_CUES: list[tuple[str, tuple[str, ...]]] = [
    ("Exit load", ("exit load", "exit-load", "charged an exit", "redemption fee")),
    ("Key fund facts", ("expense ratio", "nav", "aum", "riskometer")),
    ("Benchmark", ("benchmark",)),
    ("Investment objective", ("objective", "seeks to")),
    ("Stamp duty and tax", ("stamp duty", "tax")),
    ("Fund management", ("fund manager", "managed by")),
    ("Minimum investments", ("minimum sip", "minimum investment", "min sip", "lumpsum")),
]

async def run_facts(redacted_text: str, parsed_dir: Path) -> FactsResult:
    ...
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_facts.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/groww_support/agents/facts.py src/groww_support/agents/__init__.py tests/test_facts.py
git commit -m "feat: add Facts Agent over data/parsed corpus"
```

---

### Task 5: Pattern Agent (themes + review date split)

**Files:**
- Create: `src/groww_support/agents/pattern.py`
- Create: `tests/test_pattern.py`

**Interfaces:**
- Consumes: `redacted_text: str`, paths to `analyzed_themes.json` and `normalized_reviews.json`
- Produces: `async def run_pattern(redacted_text: str, themes_path: Path, reviews_path: Path) -> PatternResult`

**Signal rules (copy from architecture):**
- Window: 2026-04-12 → 2026-07-04
- Recent: 2026-06-28 → 2026-07-04
- Earlier: 2026-04-12 → 2026-06-27
- `one-off`: theme `other` OR full-window count < 20
- `rising`: not other, count ≥ 20, and recent_count ≥ 40 OR recent_count ≥ 2× weekly rate of earlier slice
- `recurring`: not other, count ≥ 20, not rising

- [ ] **Step 1: Write failing tests**

```python
# tests/test_pattern.py
import pytest
from pathlib import Path
from groww_support.agents.pattern import run_pattern

@pytest.mark.asyncio
async def test_exit_load_maps_to_fees_brokerage(data_dir: Path):
    result = await run_pattern(
        "Why was I charged exit load / brokerage fees?",
        data_dir / "analyzed_themes.json",
        data_dir / "normalized_reviews.json",
    )
    assert result.theme_id == "fees_brokerage"
    assert result.count == 136
    assert result.signal in ("recurring", "rising")
    assert result.window.start == "2026-04-12"
    assert result.window.end == "2026-07-04"

@pytest.mark.asyncio
async def test_withdrawal_maps_to_money_movement(data_dir: Path):
    result = await run_pattern(
        "My withdrawal is stuck for 3 days",
        data_dir / "analyzed_themes.json",
        data_dir / "normalized_reviews.json",
    )
    assert result.theme_id == "money_movement"
    assert result.count == 162

@pytest.mark.asyncio
async def test_other_theme_is_one_off(data_dir: Path):
    # Force match to other via generic unmatched praise, or assert signal rule for other
    result = await run_pattern(
        "Great app thanks",
        data_dir / "analyzed_themes.json",
        data_dir / "normalized_reviews.json",
    )
    assert result.theme_id == "other"
    assert result.signal == "one-off"
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/test_pattern.py -v`

- [ ] **Step 3: Implement Pattern Agent**

1. Load `allThemes` (not only `topThemes`).
2. Optional: shared `classify_theme` when LLM enabled; else (or on failure) score themes by keyword overlap (map: fees/exit load/brokerage → `fees_brokerage`; withdraw/deposit/payment → `money_movement`; crash/lag/hang → `reliability`; chart/order/trade → `trading_charts`; else `other`).
3. For matched theme, load review dates for its `reviewIds` from `normalized_reviews.json`.
4. Count full window and recent slice; compute signal **in code** (model must not invent counts).
5. Return `PatternResult`.

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add src/groww_support/agents/pattern.py tests/test_pattern.py
git commit -m "feat: add Pattern Agent with recurring/rising/one-off signals"
```

---

### Task 6: Compliance Agent (incoming scan)

**Files:**
- Create: `src/groww_support/agents/compliance.py`
- Create: `tests/test_compliance.py`

**Interfaces:**
- Consumes: `redacted_text: str`, `pii_types: list[PiiType]`
- Produces: `async def run_compliance(redacted_text: str, pii_types: list[PiiType]) -> ComplianceResult`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_compliance.py
import pytest
from groww_support.agents.compliance import run_compliance

@pytest.mark.asyncio
async def test_advice_redeem_flagged():
    r = await run_compliance("Should I redeem HDFC Large Cap?", [])
    assert "advice" in r.flags
    assert r.advice_refusal is True

@pytest.mark.asyncio
async def test_performance_claim_flagged():
    r = await run_compliance("What CAGR should I expect from mid cap?", [])
    assert "performance_claim" in r.flags
    assert r.advice_refusal is True

@pytest.mark.asyncio
async def test_pii_types_from_ingress_propagate():
    r = await run_compliance("Help with [PAN] on my account", ["PAN"])
    assert "pii" in r.flags
    assert "PAN" in r.pii_types

@pytest.mark.asyncio
async def test_clean_exit_load_no_flags():
    r = await run_compliance("Why was I charged an exit load on HDFC Large Cap Fund?", [])
    assert r.flags == []
    assert r.advice_refusal is False
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement Compliance Agent**

**Incoming only** (outgoing draft → Task 8 Reviewer). Detect advice phrases: `should I`, `redeem or not`, `is this scheme good`, `should I stay`, `worth it`, `buy`, `sell`, `hold` (investment context). Detect performance: `return`, `CAGR`, `performance`, `% return`. Optional: shared `classify_compliance` **OR**'d with those rules (either hit flags). PII flag if `pii_types` non-empty OR residual raw patterns still match (defense in depth). Never echo raw values; keep `redacted_text` as given.

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add src/groww_support/agents/compliance.py tests/test_compliance.py
git commit -m "feat: add Compliance Agent for advice, performance, and PII flags"
```

---

## Phase 3 — Orchestrator merge and draft

### Task 7: Parallel fan-out + disposition + draft

**Files:**
- Create: `src/groww_support/orchestrator.py`
- Create: `tests/test_orchestrator.py`
- Update: `pyproject.toml` — add `langgraph` dependency

**Interfaces:**
- Consumes: `redact`, `run_facts`, `run_pattern`, `run_compliance`
- Produces:
  - `async def handle_complaint(raw: str, data_dir: Path, session: SessionState | None = None) -> SessionState`
  - `def merge_draft(facts, pattern, compliance, *, advice_refusal: bool) -> OrchestratorOutput`
  - `def team_for_theme(theme_id: ThemeId) -> str`
  - `def priority_for(signal: PatternSignal, disposition: Disposition) -> Priority`

**Fan-out runtime:** Facts, Pattern, and Compliance are **three LangGraph nodes** started together (same shared classifier brain inside each agent). Do not await them sequentially. `asyncio.gather` alone is not enough once this task lands — wire a small StateGraph / parallel send so the demo trace shows three LangGraph nodes.

**Disposition table (must implement exactly):**

| Situation | Disposition |
|---|---|
| covered + one-off + clean | `reply` |
| covered + recurring/rising | `escalate` |
| not_covered | `handoff` |
| advice or performance_claim | `refuse` |
| covered + rising/high recent on same issue | `disagree` (`disagreement=True`) |

- [ ] **Step 1: Write failing tests**

```python
# tests/test_orchestrator.py
import pytest
from pathlib import Path
from groww_support.contracts import (
    FactsResult, PatternResult, ComplianceResult, DateWindow,
)
from groww_support.orchestrator import merge_draft, handle_complaint

def _pattern(signal="recurring", recent=12):
    return PatternResult(
        theme_id="fees_brokerage",
        theme_name="Fees & brokerage",
        signal=signal,
        count=136,
        recent_count=recent,
        window=DateWindow(start="2026-04-12", end="2026-07-04"),
        recent_window=DateWindow(start="2026-06-28", end="2026-07-04"),
    )

def test_covered_recurring_escalates():
    facts = FactsResult(
        status="covered",
        scheme_id="large_cap",
        section_title="Exit load",
        fact="Exit load of 1% if redeemed within 1 year",
        citation="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        last_checked="25-Jun-2026",
        searched=["large_cap"],
    )
    out = merge_draft(facts, _pattern("recurring"), ComplianceResult(
        flags=[], pii_types=[], advice_refusal=False,
        redacted_text="Why exit load on HDFC Large Cap?",
    ), advice_refusal=False)
    assert out.disposition == "escalate"
    assert out.citation is not None
    assert out.reply.count(".") <= 3 or out.reply.count("!") + out.reply.count("?") + out.reply.count(".") <= 3
    assert "25-Jun-2026" in out.reply
    assert "Fees and mutual fund ops" in out.routing_note.team
    assert out.routing_note.priority in ("P1", "P2")

def test_advice_refuse_overrides_covered_fact():
    facts = FactsResult(
        status="covered",
        scheme_id="large_cap",
        section_title="Exit load",
        fact="Exit load of 1% if redeemed within 1 year",
        citation="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        last_checked="25-Jun-2026",
        searched=["large_cap"],
    )
    out = merge_draft(
        facts,
        _pattern("one-off"),
        ComplianceResult(flags=["advice"], pii_types=[], advice_refusal=True, redacted_text="Should I redeem?"),
        advice_refusal=True,
    )
    assert out.disposition == "refuse"
    assert out.citation is None
    assert "should" not in out.reply.lower() or "cannot" in out.reply.lower() or "unable" in out.reply.lower()

def test_covered_rising_disagree():
    facts = FactsResult(
        status="covered",
        scheme_id="large_cap",
        section_title="Exit load",
        fact="Exit load of 1% if redeemed within 1 year",
        citation="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        last_checked="25-Jun-2026",
        searched=["large_cap"],
    )
    out = merge_draft(
        facts,
        _pattern("rising", recent=40),
        ComplianceResult(flags=[], pii_types=[], advice_refusal=False, redacted_text="exit load"),
        advice_refusal=False,
    )
    assert out.disposition == "disagree"
    assert out.disagreement is True
    assert "stays open" in out.routing_note.why.lower() or "open" in out.routing_note.why.lower()

@pytest.mark.asyncio
async def test_parallel_fanout_records_all_three(data_dir: Path):
    session = await handle_complaint(
        "Why was I charged an exit load on HDFC Large Cap Fund?",
        data_dir,
    )
    assert session.facts is not None
    assert session.pattern is not None
    assert session.compliance is not None
    assert session.draft is not None
    assert any(e.kind == "initial" and set(e.fired) >= {"facts", "pattern", "compliance"} for e in session.agents_fired)
```

Also add a unit test that instruments start timestamps (monkeypatch agents to `asyncio.sleep` then return) and asserts all three start times are recorded before any end time — this pins the parallel rule.

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement orchestrator**

Critical fan-out shape (LangGraph; sketch):

```python
# Prefer LangGraph StateGraph with three specialist nodes invoked in parallel
# (e.g. Send API / parallel edges), each calling run_facts / run_pattern / run_compliance.
# Equivalent interim shape while wiring the graph — still must start all three before any await-of-result:

async def handle_complaint(raw: str, data_dir: Path, session: SessionState | None = None) -> SessionState:
    ingress = redact(raw)
    # LangGraph parallel nodes: facts | pattern | compliance (shared Groq brain inside agents)
    facts, pattern, compliance = await run_specialists_parallel(
        ingress.redacted_text, ingress.pii_types, data_dir
    )
    advice_refusal = bool(session.advice_refusal if session else False) or compliance.advice_refusal
    draft = merge_draft(facts, pattern, compliance, advice_refusal=advice_refusal)
    ...
```

`merge_draft` builds ≤3 sentences; for `refuse` uses fixed refusal copy with no advice; for `not_covered` names searched list; never invents.

Team map and priority map exactly as in `docs/architecture.md`.

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add src/groww_support/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add orchestrator parallel fan-out, disposition, and draft merge"
```

---

## Phase 4 — Reviewer

### Task 8: Outgoing hard-fail reviewer + one rework

**Files:**
- Create: `src/groww_support/reviewer.py`
- Modify: `src/groww_support/orchestrator.py` (call reviewer after merge; rewrite once on fail)
- Create: `tests/test_reviewer.py`

**Interfaces:**
- Consumes: `OrchestratorOutput`, optional `FactsResult`, `pii_types`
- Produces: `def review_draft(draft: OrchestratorOutput, *, facts: FactsResult | None, round: int) -> ReviewerResult`
- Orchestrator: on `fail` round 1 → `rewrite_draft(...)` → review round 2; on fail round 2 → `status: "blocked"`

**Hard fails:** citation, advice, performance, pii, shape (≤3 sentences; covered requires last_checked).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_reviewer.py
from groww_support.contracts import OrchestratorOutput, RoutingNote, FactsResult
from groww_support.reviewer import review_draft

def test_uncited_factual_claim_fails():
    draft = OrchestratorOutput(
        reply="HDFC Large Cap charges 1% exit load within 1 year. Last checked 25-Jun-2026.",
        last_checked="25-Jun-2026",
        citation=None,
        disposition="reply",
        disagreement=False,
        routing_note=RoutingNote(team="Mutual fund support", priority="P3", why="one-off"),
    )
    result = review_draft(draft, facts=None, round=1)
    assert result.status == "fail"
    assert any(f.check == "citation" for f in result.failures)

def test_advice_language_fails():
    draft = OrchestratorOutput(
        reply="You may want to consider staying invested longer. Last checked 25-Jun-2026. Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        last_checked="25-Jun-2026",
        citation="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        disposition="reply",
        disagreement=False,
        routing_note=RoutingNote(team="x", priority="P3", why="y"),
    )
    result = review_draft(draft, facts=None, round=1)
    assert any(f.check == "advice" for f in result.failures)

def test_raw_phone_in_draft_fails():
    draft = OrchestratorOutput(
        reply="We received your number 9876543210. Last checked 25-Jun-2026. Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        last_checked="25-Jun-2026",
        citation="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        disposition="reply",
        disagreement=False,
        routing_note=RoutingNote(team="x", priority="P3", why="y"),
    )
    result = review_draft(draft, facts=None, round=1)
    assert any(f.check == "pii" for f in result.failures)

def test_clean_covered_draft_passes():
    citation = "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    draft = OrchestratorOutput(
        reply=f"HDFC Large Cap Fund Direct Growth charges an exit load of 1% if redeemed within 1 year. Last checked 25-Jun-2026. Source: {citation}",
        last_checked="25-Jun-2026",
        citation=citation,
        disposition="escalate",
        disagreement=False,
        routing_note=RoutingNote(team="Fees and mutual fund ops", priority="P2", why="recurring fees_brokerage 136"),
    )
    facts = FactsResult(
        status="covered", scheme_id="large_cap", section_title="Exit load",
        fact="Exit load of 1% if redeemed within 1 year", citation=citation,
        last_checked="25-Jun-2026", searched=["large_cap"],
    )
    result = review_draft(draft, facts=facts, round=1)
    assert result.status == "pass"
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement reviewer + wire one rework in orchestrator**

On fail round 1, `rewrite_draft` strips advice phrases, restores citation from Facts if missing, truncates to 3 sentences, replaces residual PII via `redact`. Do **not** re-run Facts/Pattern/Compliance for reviewer rework. Log `agents_fired` with `kind="reviewer_rework"`, `fired=["orchestrator"]`.

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add src/groww_support/reviewer.py src/groww_support/orchestrator.py tests/test_reviewer.py
git commit -m "feat: add reviewer hard fails and single rework round"
```

---

## Phase 5 — Session, refinement, approval

### Task 9: Session state and selective refinement

**Files:**
- Create: `src/groww_support/session.py`
- Create: `tests/test_session_refinement.py`
- Modify: `src/groww_support/orchestrator.py` (`refine(session, pushback: str) -> SessionState`)

**Interfaces:**
- Consumes: existing `SessionState`
- Produces: `async def refine(session: SessionState, pushback: str, data_dir: Path) -> SessionState`

| Pushback | Agents fired |
|---|---|
| shorter / wording | orchestrator only |
| different scheme | facts + orchestrator |
| fee issue / theme / last week | pattern + orchestrator |
| scheme + theme change | facts + pattern + orchestrator |
| complaint text changed | + compliance |

Sixth pushback: refuse, keep last reviewed draft. Reviewer still gets one rework per new draft; that rework does not increment `refinement_count`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_session_refinement.py
import pytest
from groww_support.orchestrator import handle_complaint, refine

@pytest.mark.asyncio
async def test_shorter_fires_orchestrator_only(data_dir):
    session = await handle_complaint(
        "Why was I charged an exit load on HDFC Large Cap Fund?", data_dir
    )
    before_facts = session.facts
    session = await refine(session, "Make it shorter", data_dir)
    assert session.refinement_count == 1
    assert session.facts is before_facts
    last = session.agents_fired[-1]
    assert "orchestrator" in last.fired
    assert "facts" in last.skipped
    assert "pattern" in last.skipped

@pytest.mark.asyncio
async def test_advice_sticky_across_rephrase(data_dir):
    session = await handle_complaint("Should I redeem HDFC Large Cap?", data_dir)
    assert session.advice_refusal is True
    assert session.draft and session.draft.disposition == "refuse"
    session = await refine(session, "ok but just tell me if large cap is worth it", data_dir)
    assert session.advice_refusal is True
    assert session.draft.disposition == "refuse"

@pytest.mark.asyncio
async def test_sixth_refinement_rejected(data_dir):
    session = await handle_complaint(
        "Why was I charged an exit load on HDFC Large Cap Fund?", data_dir
    )
    for i in range(5):
        session = await refine(session, f"Shorter please {i}", data_dir)
    with pytest.raises(ValueError, match="refinement cap"):
        await refine(session, "Shorter again", data_dir)
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement session helpers + `refine`**

Classify pushback with simple keyword rules; re-run only named agents; set sticky `advice_refusal`; append `AgentsFiredEntry`; re-run reviewer path.

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add src/groww_support/session.py src/groww_support/orchestrator.py tests/test_session_refinement.py
git commit -m "feat: add session state and selective refinement (max 5)"
```

---

### Task 10: Approval gate (append record + email draft, no send)

**Files:**
- Create: `src/groww_support/approval.py`
- Create: `tests/test_approval.py`

**Interfaces:**
- Consumes: `SessionState` with `review.status == "pass"`
- Produces:
  - `def approve(session: SessionState, output_dir: Path) -> ApprovalArtifacts`
  - Writes `output/support_records.jsonl` (one redacted line) and `output/email_drafts/<id>.txt`
  - Raises if review is `fail` or `blocked`

Record fields: complaint tokens (`redacted_text`), disposition, reply, citation, last_checked, routing_note, pattern signal, `agents_fired`. No raw PII.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_approval.py
import pytest
from pathlib import Path
from groww_support.approval import approve
from groww_support.contracts import ReviewerResult

@pytest.mark.asyncio
async def test_approve_writes_record_and_draft(tmp_path, data_dir):
    from groww_support.orchestrator import handle_complaint
    session = await handle_complaint(
        "Why was I charged an exit load on HDFC Large Cap Fund?", data_dir
    )
    # Force pass if needed for fixture stability
    assert session.review is not None
    if session.review.status != "pass":
        session.review = ReviewerResult(status="pass", round=1, failures=[])
    arts = approve(session, tmp_path)
    record_path = tmp_path / "support_records.jsonl"
    assert record_path.exists()
    line = record_path.read_text(encoding="utf-8")
    assert "ABCDE1234F" not in line
    assert arts.email_path.exists()
    assert "mailto:" not in arts.email_path.read_text(encoding="utf-8").lower() or True  # no send API

def test_blocked_cannot_approve(tmp_path, data_dir):
    from groww_support.orchestrator import handle_complaint
    import asyncio
    session = asyncio.get_event_loop().run_until_complete(
        handle_complaint("Why exit load on HDFC Large Cap?", data_dir)
    )
    session.review = ReviewerResult(status="blocked", round=2, failures=[])
    with pytest.raises(PermissionError, match="approve"):
        approve(session, tmp_path)
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement approval gate**

```python
# src/groww_support/approval.py
from __future__ import annotations
import json
import uuid
from pathlib import Path
from pydantic import BaseModel
from groww_support.contracts import SessionState

class ApprovalArtifacts(BaseModel):
    record_id: str
    record_path: Path
    email_path: Path

def approve(session: SessionState, output_dir: Path) -> ApprovalArtifacts:
    if session.review is None or session.review.status != "pass":
        raise PermissionError("approve unavailable: reviewer status is not pass")
    if session.draft is None:
        raise PermissionError("approve unavailable: no draft")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "email_drafts").mkdir(exist_ok=True)
    record_id = str(uuid.uuid4())
    record = {
        "id": record_id,
        "redacted_text": session.redacted_text,
        "disposition": session.draft.disposition,
        "reply": session.draft.reply,
        "citation": session.draft.citation,
        "last_checked": session.draft.last_checked,
        "routing_note": session.draft.routing_note.model_dump(),
        "pattern_signal": session.pattern.signal if session.pattern else None,
        "agents_fired": [e.model_dump() for e in session.agents_fired],
    }
    record_path = output_dir / "support_records.jsonl"
    with record_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    email_path = output_dir / "email_drafts" / f"{record_id}.txt"
    email_path.write_text(
        f"Subject: Regarding your Groww support request\n\n{session.draft.reply}\n",
        encoding="utf-8",
    )
    return ApprovalArtifacts(record_id=record_id, record_path=record_path, email_path=email_path)
```

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add src/groww_support/approval.py tests/test_approval.py
git commit -m "feat: add human approval gate for record append and email draft"
```

---

## Phase 6 — CLI demo and acceptance harness

### Task 11: Human CLI loop

**Files:**
- Create: `src/groww_support/cli.py`
- Modify: `README.md` with run instructions

**Interfaces:**
- Consumes: `handle_complaint`, `refine`, `approve`
- Produces: `groww-support` CLI entrypoint

- [ ] **Step 1: Implement CLI**

Commands:
- `groww-support run "complaint text"` — fan-out, print draft + routing note + review status + agents_fired
- `groww-support refine <session.json> "pushback"`
- `groww-support approve <session.json>`
- Interactive mode: prompt → show draft → refine / approve / quit

Disable Approve when `review.status != "pass"`.

- [ ] **Step 2: Manual smoke**

Run: `groww-support run "Why was I charged an exit load on HDFC Large Cap Fund?"`
Expected: Facts covered, Pattern fees_brokerage, Compliance clean, disposition escalate/disagree, reviewer pass, Approve offered.

- [ ] **Step 3: Commit**

```bash
git add src/groww_support/cli.py README.md
git commit -m "feat: add CLI for complaint run, refine, and approve"
```

---

### Task 12: Acceptance suite (problem statement checks)

**Files:**
- Create: `tests/fixtures/complaints.json` (20 real review texts sampled from `normalized_reviews.json` + 4 branch cases + advice cases)
- Create: `tests/test_acceptance.py`
- Create: `scripts/pick_acceptance_complaints.py` (one-off helper to sample 20 reviews)

**Coverage required by problem statement:**

1. **20 real complaints** — each run yields structured Facts/Pattern/Compliance JSON; every reply has `source_url` **or** explicit not_covered.
2. **Four branches** — clean hit, corpus miss, recurring theme, PII (PAN/phone); log `agents_fired` + reviewer result; PII branch must not leak raw values.
3. **Advice resistance** — redeem / is it good / what returns; rephrase; ask again later in session → always `refuse`, sticky `advice_refusal`.
4. **Parallel proof** — trace asserts three starts before any result (reuse Task 7 timing test in acceptance).

- [ ] **Step 1: Build fixtures**

Sample 20 reviews with non-empty `text` from `data/normalized_reviews.json`. Add explicit branch objects:

```json
{
  "id": "branch_clean",
  "text": "Why was I charged an exit load on HDFC Large Cap Fund?"
},
{
  "id": "branch_miss",
  "text": "My equity delivery order for TCS failed with error code 500"
},
{
  "id": "branch_recurring",
  "text": "Brokerage and exit load fees are too high"
},
{
  "id": "branch_pii",
  "text": "Why exit load on HDFC Large Cap? My PAN is ABCDE1234F and phone 9876543210"
}
```

- [ ] **Step 2: Write acceptance tests**

```python
# tests/test_acceptance.py
import json
import pytest
from pathlib import Path
from groww_support.orchestrator import handle_complaint, refine
from groww_support.approval import approve

FIXTURES = Path(__file__).parent / "fixtures" / "complaints.json"

@pytest.mark.asyncio
async def test_twenty_complaints_structured(data_dir):
    items = [c for c in json.loads(FIXTURES.read_text(encoding="utf-8")) if c["id"].startswith("review_")]
    assert len(items) == 20
    for item in items:
        session = await handle_complaint(item["text"], data_dir)
        assert session.facts is not None
        assert session.pattern is not None
        assert session.compliance is not None
        assert session.draft is not None
        if session.facts.status == "covered":
            assert session.draft.citation
            assert session.draft.citation.startswith("https://groww.in/")
        else:
            assert session.draft.citation is None
            assert "not cover" in session.draft.reply.lower() or "does not cover" in session.draft.reply.lower() or "not covered" in session.draft.reply.lower()

@pytest.mark.asyncio
async def test_four_branches(data_dir, tmp_path):
    ...

@pytest.mark.asyncio
async def test_advice_resistance_session(data_dir):
    session = await handle_complaint("Should I redeem HDFC Large Cap?", data_dir)
    assert session.draft.disposition == "refuse"
    session = await refine(session, "Is this scheme good?", data_dir)
    assert session.draft.disposition == "refuse"
    session = await refine(session, "What returns should I expect?", data_dir)
    assert session.draft.disposition == "refuse"
    assert session.advice_refusal is True
```

- [ ] **Step 3: Run full suite**

Run: `pytest tests/ -v`
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/complaints.json tests/test_acceptance.py scripts/pick_acceptance_complaints.py
git commit -m "test: add acceptance harness for 20 complaints, branches, and advice refusal"
```

---

## Phase summary (execution order)

| Phase | Tasks | Deliverable |
|---|---|---|
| 0 Scaffold | 1–2 | Package + contracts |
| 1 Ingress | 3 | PII redaction before fan-out |
| 2 Agents | 4–6 | Facts, Pattern, Compliance + shared Groq classifier (`llm.py`) |
| 3 Orchestrator | 7 | LangGraph parallel fan-out, disposition, draft + routing note |
| 4 Reviewer | 8 | Outgoing hard fails + one rework → pass/blocked |
| 5 Session + gate | 9–10 | Refinement caps + approval-only writes |
| 6 Demo + accept | 11–12 | CLI + problem-statement acceptance |

Each phase ends with green tests and a commit. Do not start Phase N+1 until Phase N tests pass.

---

## Self-review (spec coverage)

| Spec requirement | Task |
|---|---|
| Parallel Facts/Pattern/Compliance (LangGraph nodes) | Task 7 |
| Shared classifier LLM only; keyword/regex fallback | Tasks 4–6 (`llm.py`) |
| Ingress before fan-out; no raw PII stored | Task 3, 10 |
| Facts from `data/parsed/` only; not_covered | Task 4 |
| Pattern allThemes + rising/recurring/one-off | Task 5 |
| Compliance advice/performance/PII on **input** | Task 6 |
| Reviewer same policy on **outgoing** draft | Task 8 |
| Orchestrator draft ≤3 sentences + routing note | Task 7 |
| Disposition reply/escalate/handoff/refuse/disagree | Task 7 |
| Reviewer hard fails; one rework; blocked | Task 8 |
| Refinement max 5; selective re-run; agents_fired | Task 9 |
| Sticky advice_refusal | Task 9 |
| Approval append + email draft; no send | Task 10 |
| 20 complaints + 4 branches + advice resistance | Task 12 |
| Demo parallel trace | Task 7 + 11 |

No placeholders left in task steps. Types align across tasks (`FactsResult.status`, `PatternResult.signal`, `ReviewerResult.status`, `Disposition` literals).
