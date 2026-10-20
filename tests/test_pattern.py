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
