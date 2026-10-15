"""Canonical input fingerprint binding candidate artifacts to one case generation.

A run/score pair is only meaningful when it was produced from *this* case
generation (case identity + injected ground truth), *this* selected source
audio, *this* subtitle input, *this* oracle/gold material, and *this*
candidate. Re-`prepare` with a new seed, a re-registration with a new
``--audio`` selection, a mutated source, an edited ground-truth annotation,
a changed gold-classification file, or a different tool probe result all
change the fingerprint, so persisted proposals/scores from an older
generation can be detected and refused instead of being silently rescored.

Contract v2 (third-review F02): the payload binds the **canonical semantic
case inputs** (timing grid/format, per-cue original times, injected cue
deltas, transform and expected inverse) and the **oracle input material**
(gold-classification file content hash, selected subtitle source identity),
not only the seed and artifact hashes. Editing a private ``.case.json``'s
ground truth or rewriting a gold classification file therefore invalidates
every dependent cached proposal/score even when the corrupted subtitle bytes
are unchanged. No mutable output locations and no secrets enter the payload.

The fingerprint is a sha256 over a canonical JSON dump (``sort_keys=True``) of
exactly the fields below; run, score, b1-va base/acceptance checks, and the
report's generation binding all derive the same value from the loaded case +
registry record + live gold file content.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .manifests import CaseManifest

FINGERPRINT_SCHEMA_VERSION = 2

GOLD_FILE_MISSING = "missing"


def _canonical_pair_map(mapping: dict[str, Any]) -> list[list[Any]]:
    return [[cid, [int(v[0]), int(v[1])]] for cid, v in sorted(mapping.items())]


def fingerprint_payload(
    case: CaseManifest,
    source: dict[str, Any],
    candidate_id: str,
    tool_versions: dict[str, str] | None = None,
    gold_classification_sha256: str | None = None,
) -> dict[str, Any]:
    """Return the canonical field set the fingerprint commits to.

    ``source`` is the registry record for ``case.source_id`` (media hash +
    persisted audio selection); ``tool_versions`` are the entries relevant to
    this candidate as recorded by the run (empty for tool-free arms);
    ``gold_classification_sha256`` is the LIVE content hash of the case's
    gold-classification file (``GOLD_FILE_MISSING`` when the manifest names a
    file that cannot be read, ``None`` when the case has no gold input).
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
            "fmt": case.fmt,
            "grid_us": case.grid_us,
            "original_times_us": _canonical_pair_map(case.original_times_us),
            "injected_cue_deltas": _canonical_pair_map(case.injected_cue_deltas),
            "transform": case.transform,
            "expected_inverse": case.expected_inverse,
        },
        "subtitle_input": {
            # Keyed by the REGISTERED track id persisted in the case manifest
            # (M1). The CLI refuses manifests whose ``track_id`` is not a
            # registered id BEFORE computing any fingerprint, so for every
            # run/score/report binding this lookup resolves to the track's real
            # spec (and sha256 when registered); a None lookup is never hashed
            # as a valid subtitle binding.
            "spec": (source.get("subtitle_specs") or {}).get(case.track_id),
            "sha256": (source.get("subtitle_sha256") or {}).get(case.track_id),
        },
        "gold_classification_sha256": gold_classification_sha256,
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
    gold_classification_sha256: str | None = None,
) -> str:
    """Deterministic sha256 over the canonical fingerprint payload."""
    payload = fingerprint_payload(
        case, source, candidate_id, tool_versions, gold_classification_sha256
    )
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
