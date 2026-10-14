"""Canonical input fingerprint binding candidate artifacts to one case generation.

A run/score pair is only meaningful when it was produced from *this* case
generation (case identity + injected ground truth), *this* selected source
audio, and *this* candidate. Re-`prepare` with a new seed, a re-registration
with a new ``--audio`` selection, a mutated source, or a different tool probe
result all change the fingerprint, so persisted proposals/scores from an older
generation can be detected and refused instead of being silently rescored.

The fingerprint is a sha256 over a canonical JSON dump (``sort_keys=True``) of
exactly the fields below; run, score, b1-va base checks, and the reference
audio cache all derive the same value from the loaded case + registry record.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .manifests import CaseManifest

FINGERPRINT_SCHEMA_VERSION = 1


def fingerprint_payload(
    case: CaseManifest,
    source: dict[str, Any],
    candidate_id: str,
    tool_versions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return the canonical field set the fingerprint commits to.

    ``source`` is the registry record for ``case.source_id`` (media hash +
    persisted audio selection); ``tool_versions`` are the entries relevant to
    this candidate as recorded by the run (empty for tool-free arms).
    """
    return {
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "case": {
            "case_id": case.case_id,
            "source_id": case.source_id,
            "track_id": case.track_id,
            "scenario": case.scenario,
            "seed": case.seed,
            "params": case.params,
            "original_subtitle_sha256": case.original_subtitle_sha256,
            "generated_subtitle_sha256": case.generated_subtitle_sha256,
            "true_breakpoints_us": list(case.true_breakpoints_us),
        },
        "audio": {
            "audio_selected": source.get("audio_selected"),
            "audio_spec": source.get("audio_spec"),
            "media_sha256": source.get("media_sha256"),
        },
        "rights_status": source.get("rights_status"),
        "candidate_id": candidate_id,
        "tool_versions": dict(tool_versions or {}),
    }


def compute_input_fingerprint(
    case: CaseManifest,
    source: dict[str, Any],
    candidate_id: str,
    tool_versions: dict[str, str] | None = None,
) -> str:
    """Deterministic sha256 over the canonical fingerprint payload."""
    payload = fingerprint_payload(case, source, candidate_id, tool_versions)
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
