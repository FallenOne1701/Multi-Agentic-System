from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


@pytest.fixture(autouse=True)
def _offline_llm_by_default(monkeypatch, request):
    """Keep agent tests deterministic unless a test opts into LLM mocks."""
    if request.node.get_closest_marker("llm"):
        return
    monkeypatch.setenv("GROWW_USE_LLM", "0")


@pytest.fixture
def data_dir() -> Path:
    return DATA


@pytest.fixture
def parsed_dir(data_dir: Path) -> Path:
    return data_dir / "parsed"
