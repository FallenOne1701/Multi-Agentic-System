from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from groww_support.contracts import DateWindow, PatternResult, PatternSignal, ThemeId

WINDOW_START = date(2026, 4, 12)
WINDOW_END = date(2026, 7, 4)
RECENT_START = date(2026, 6, 28)
RECENT_END = date(2026, 7, 4)
EARLIER_START = date(2026, 4, 12)
EARLIER_END = date(2026, 6, 27)

THEME_CUES: list[tuple[ThemeId, tuple[str, ...]]] = [
    ("fees_brokerage", ("fees", "fee", "exit load", "brokerage", "broker")),
    ("money_movement", ("withdraw", "deposit", "payment")),
    ("reliability", ("crash", "lag", "hang")),
    ("trading_charts", ("chart", "order", "trade")),
]


def _parse_review_date(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def _in_range(day: date, start: date, end: date) -> bool:
    return start <= day <= end


def _match_theme(text: str) -> ThemeId:
    lowered = text.lower()
    best: ThemeId = "other"
    best_score = 0
    for theme_id, cues in THEME_CUES:
        score = sum(1 for cue in cues if cue in lowered)
        if score > best_score:
            best = theme_id
            best_score = score
    return best


def _signal(theme_id: ThemeId, count: int, recent_count: int, earlier_count: int) -> PatternSignal:
    if theme_id == "other" or count < 20:
        return "one-off"
    earlier_days = (EARLIER_END - EARLIER_START).days + 1
    weekly_rate = earlier_count / (earlier_days / 7)
    if recent_count >= 40 or recent_count >= 2 * weekly_rate:
        return "rising"
    return "recurring"


async def run_pattern(redacted_text: str, themes_path: Path, reviews_path: Path) -> PatternResult:
    themes_data = json.loads(themes_path.read_text(encoding="utf-8"))
    themes_by_id = {theme["id"]: theme for theme in themes_data["allThemes"]}
    theme_id = _match_theme(redacted_text)
    theme = themes_by_id[theme_id]

    reviews_by_id = {
        review["id"]: review for review in json.loads(reviews_path.read_text(encoding="utf-8"))
    }

    count = 0
    recent_count = 0
    earlier_count = 0
    for review_id in theme["reviewIds"]:
        review = reviews_by_id.get(review_id)
        if review is None:
            continue
        day = _parse_review_date(review["date"])
        if _in_range(day, WINDOW_START, WINDOW_END):
            count += 1
        if _in_range(day, RECENT_START, RECENT_END):
            recent_count += 1
        if _in_range(day, EARLIER_START, EARLIER_END):
            earlier_count += 1

    return PatternResult(
        theme_id=theme_id,
        theme_name=theme["name"],
        signal=_signal(theme_id, count, recent_count, earlier_count),
        count=count,
        recent_count=recent_count,
        window=DateWindow(start=WINDOW_START.isoformat(), end=WINDOW_END.isoformat()),
        recent_window=DateWindow(start=RECENT_START.isoformat(), end=RECENT_END.isoformat()),
    )
