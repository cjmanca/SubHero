"""Versioned JSON manifest formats (source / case / candidate / result / proposal / score).

These are benchmark artifact contracts, not a production data model.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
STATUSES = ("success", "not_run", "unsupported", "failed", "timeout", "invalid_output")


@dataclass
class SourceManifest:
    source_id: str
    media_path: str
    subtitle_specs: dict[str, str]
    media_sha256: str
    subtitle_sha256: dict[str, str]
    duration_us: int | None = None
    streams: list[dict[str, Any]] = field(default_factory=list)
    rights_status: str = "private-local"
    notes: str = ""
    schema_version: int = SCHEMA_VERSION

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class CaseManifest:
    case_id: str
    source_id: str
    scenario: str
    seed: int
    track_id: str
    fmt: str
    grid_us: int
    params: dict[str, Any]
    transform: dict[str, Any]
    expected_inverse: dict[str, Any]
    injected_cue_deltas: dict[str, tuple[int, int]]
    original_times_us: dict[str, tuple[int, int]]
    true_breakpoints_us: list[int]
    original_subtitle_sha256: str
    generated_subtitle_sha256: str
    generated_path: str
    gold_classification_path: str | None = None
    notes: str = ""
    schema_version: int = SCHEMA_VERSION

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class CandidateManifest:
    candidate_id: str
    algorithm: str
    executable: str
    version: str
    flags: list[str]
    runtime: str
    local: bool = True
    schema_version: int = SCHEMA_VERSION

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class ResultRecord:
    run_id: str
    case_id: str
    candidate_id: str
    status: str
    reason: str = ""
    wall_seconds: float | None = None
    preprocessing_seconds: float | None = None
    candidate_seconds: float | None = None
    asr_seconds: float | None = None
    asr_calls: int | None = None
    input_sha256: str = ""
    output_sha256: dict[str, str] = field(default_factory=dict)
    tool_versions: dict[str, str] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class ProposalRecord:
    case_id: str
    candidate_id: str
    mapping_status: str
    regions: list[dict[str, Any]]
    proposed_times_us: dict[str, tuple[int, int]]
    unmapped_cue_ids: list[str]
    notes: str = ""
    schema_version: int = SCHEMA_VERSION

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class AcceptanceRecord:
    case_id: str
    candidate_id: str
    validated_candidate_id: str
    status: str
    accepted_regions: list[dict[str, Any]]
    rejected_regions: list[dict[str, Any]]
    abstained_regions: list[dict[str, Any]]
    accepted_times_us: dict[str, tuple[int, int]]
    sample_cue_ids: list[str]
    asr_seconds: float
    asr_calls: int
    notes: str = ""
    schema_version: int = SCHEMA_VERSION

    def to_json(self) -> dict:
        return asdict(self)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    from .paths import ensure_scratch_path

    ensure_scratch_path(path)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
