from __future__ import annotations

import json
from pathlib import Path

from groww_support.contracts import FactsResult, SchemeId
from groww_support.llm import classify_facts, llm_enabled

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


def _match_scheme(text: str) -> SchemeId | None:
    lowered = text.lower()
    for scheme_id, cues in SCHEME_CUES:
        if any(cue in lowered for cue in cues):
            return scheme_id
    return None


def _match_section(text: str) -> str | None:
    lowered = text.lower()
    for section_title, cues in SECTION_CUES:
        if any(cue in lowered for cue in cues):
            return section_title
    return None


def _load_scheme(parsed_dir: Path, scheme_id: SchemeId) -> dict:
    path = parsed_dir / f"{scheme_id}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _all_scheme_ids(parsed_dir: Path) -> list[SchemeId]:
    ids: list[SchemeId] = []
    for scheme_id, _ in SCHEME_CUES:
        if (parsed_dir / f"{scheme_id}.json").exists():
            ids.append(scheme_id)
    return ids


def _searched_entries(parsed_dir: Path, scheme_ids: list[SchemeId]) -> list[str]:
    searched: list[str] = []
    for scheme_id in scheme_ids:
        data = _load_scheme(parsed_dir, scheme_id)
        for block in data.get("text_blocks", []):
            title = block.get("section_title")
            if title:
                searched.append(f"{scheme_id}:{title}")
    return searched


def _section_text(data: dict, section_title: str) -> str | None:
    for block in data.get("text_blocks", []):
        if block.get("section_title") == section_title:
            return block.get("text")
    return None


async def run_facts(redacted_text: str, parsed_dir: Path) -> FactsResult:
    scheme_id = _match_scheme(redacted_text)
    section_title = _match_section(redacted_text)

    if llm_enabled():
        classified = await classify_facts(redacted_text)
        if classified is not None:
            if classified.scheme_id is not None:
                scheme_id = classified.scheme_id
            if classified.section_title is not None:
                section_title = classified.section_title

    if scheme_id is not None and section_title is not None:
        data = _load_scheme(parsed_dir, scheme_id)
        fact = _section_text(data, section_title)
        if fact:
            return FactsResult(
                status="covered",
                scheme_id=scheme_id,
                section_title=section_title,
                fact=fact,
                citation=data["source_url"],
                last_checked=data["nav_date"],
                searched=[f"{scheme_id}:{section_title}"],
            )

    search_ids = [scheme_id] if scheme_id is not None else _all_scheme_ids(parsed_dir)
    return FactsResult(
        status="not_covered",
        scheme_id=None,
        section_title=None,
        fact=None,
        citation=None,
        last_checked=None,
        searched=_searched_entries(parsed_dir, search_ids),
    )
