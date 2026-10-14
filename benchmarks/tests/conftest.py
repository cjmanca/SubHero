from __future__ import annotations

import sys
from pathlib import Path

import pytest

BENCH_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH_ROOT))

FX00 = BENCH_ROOT / "fixtures" / "Fx00"


@pytest.fixture
def fixture_dir() -> Path:
    assert FX00.is_dir(), (
        "Fx00 synthetic fixture set missing; regenerate it before running tests"
    )
    return FX00
