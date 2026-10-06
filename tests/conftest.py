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
