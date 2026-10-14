"""B1 candidate adapters: subprocess arrays, explicit timeouts, captured errors.

Unavailable executables/models produce `not_run`/`unsupported` records, never
fabricated benchmark results. Tools provide timing proposals only; original
subtitle files are never mutated.
"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import pysubs2

from .manifests import CaseManifest, ProposalRecord
from .paths import ensure_scratch_path, require_safe_id
from .proxy import ProxyMapping, build_proxy, fit_regions
from .validator import normalize_text

CANDIDATES: dict[str, tuple[str, str, dict]] = {
    "b1-n": ("noop", "No-op baseline", {"oracle": False, "default": True}),
    "b1-fg": (
        "ffsubsync-global",
        "ffsubsync global synchronization",
        {"oracle": False, "default": True},
    ),
    "b1-fp": (
        "ffsubsync-piecewise",
        "ffsubsync experimental piecewise (--split-penalty)",
        {"oracle": False, "default": True},
    ),
    "b1-al": ("alass", "ALASS synchronization", {"oracle": False, "default": True}),
    "b1-px-fg": (
        "proxy-ffsubsync-global",
        "dialogue-only proxy + ffsubsync global",
        {"oracle": False, "default": True},
    ),
    "b1-px-fp": (
        "proxy-ffsubsync-piecewise",
        "dialogue-only proxy + ffsubsync piecewise",
        {"oracle": False, "default": True},
    ),
    "b1-pxo-fg": (
        "proxy-ffsubsync-global-gold-labels",
        "DIAGNOSTIC: dialogue proxy with GOLD cue labels + ffsubsync global",
        {"oracle": True, "default": False},
    ),
    "b1-pxo-fp": (
        "proxy-ffsubsync-piecewise-gold-labels",
        "DIAGNOSTIC: dialogue proxy with GOLD cue labels + ffsubsync piecewise",
        {"oracle": True, "default": False},
    ),
    "b1-va": (
        "targeted-asr-validation",
        "targeted-ASR semantic validation of a proposal arm",
        {"oracle": False, "default": False},
    ),
}
DEFAULT_CANDIDATE_IDS = [cid for cid, meta in CANDIDATES.items() if meta[2]["default"]]
ORACLE_DIAGNOSTIC_IDS = tuple(
    cid for cid, meta in CANDIDATES.items() if meta[2]["oracle"]
)
ORACLE_MARKER = (
    "oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; "
    "not a default candidate)"
)


@dataclass
class ToolConfig:
    ffsubsync: str | None = None
    alass: str | None = None
    command_overrides: dict[str, list[str]] = field(default_factory=dict)
    timeouts: dict[str, int] = field(default_factory=dict)

    @staticmethod
    def detect() -> ToolConfig:
        import shutil

        cfg = ToolConfig()
        cfg.ffsubsync = shutil.which("ffsubsync")
        if not cfg.ffsubsync:
            candidate = Path(sys.executable).parent / "Scripts" / "ffsubsync.exe"
            if candidate.exists():
                cfg.ffsubsync = str(candidate)
        cfg.alass = shutil.which("alass")
        return cfg


def probe_version(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(
            [*cmd, "-v"], capture_output=True, text=True, timeout=60, check=False
        )
        out = (proc.stdout + proc.stderr).strip()
        return out.splitlines()[0] if out else "unknown"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unprobeable: {exc}"


def probe_split_penalty(cmd: list[str]) -> bool:
    try:
        proc = subprocess.run(
            [*cmd, "--help"], capture_output=True, text=True, timeout=60, check=False
        )
        return "--split-penalty" in proc.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


def _run(
    cmd: list[str], timeout: int, log_dir: Path | None
) -> tuple[int, str, str, float]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        return -1, "", f"timeout after {timeout}s: {exc}", time.monotonic() - started
    return proc.returncode, proc.stdout, proc.stderr, time.monotonic() - started


def _load_ssa(path: Path, fmt: str):
    return pysubs2.SSAFile.load(path, format=fmt, keep_privates=True)


def _load_events_with_text(path: Path, fmt: str) -> list[tuple[int, int, str]]:
    return [
        (ev.start * 1000, ev.end * 1000, ev.text) for ev in _load_ssa(path, fmt).events
    ]


def _proposal_for_indices(
    case: CaseManifest,
    out_events: list[tuple[int, int, str]],
    mapping: ProxyMapping | None,
    corrupted_times: dict[str, tuple[int, int]],
    tol_us: int,
    notes: str,
    full_track_ids: list[str] | None = None,
    input_events: list[tuple[int, int, str]] | None = None,
) -> ProposalRecord:
    """Map tool output back to cue IDs.

    Identity requires BOTH conditions:
    1. exact event-count equality (positional mapping is only defined then);
    2. cue correspondence by TEXT: at every mapped position, the output
       event's normalized text must equal the input event's normalized text
       (tools may change timings only; reordering, merged/rewritten text, or
       any other rewrite is an ambiguous correspondence, refused — never
       guessed).
    """
    if mapping is not None:
        ids = mapping.proxy_index_to_cue
    else:
        ids = list(full_track_ids or [])
    if len(out_events) != len(ids):
        return ProposalRecord(
            case_id=case.case_id,
            candidate_id="",
            mapping_status="mapping_failure_count_mismatch",
            regions=[],
            proposed_times_us={},
            unmapped_cue_ids=list(corrupted_times.keys()),
            notes=f"tool output has {len(out_events)} entries vs {len(ids)} inputs; refusing to guess correspondence",
        )
    input_events = list(input_events or [])
    out_texts = [t for _, _, t in out_events]
    if len(input_events) != len(out_texts):
        return ProposalRecord(
            case_id=case.case_id,
            candidate_id="",
            mapping_status="mapping_failure_ambiguous_text",
            regions=[],
            proposed_times_us={},
            unmapped_cue_ids=list(corrupted_times.keys()),
            notes=(
                f"cannot verify cue correspondence: {len(input_events)} input texts "
                f"vs {len(out_texts)} output texts; refusing to guess correspondence"
            ),
        )
    for pos, (cid, tin, tout) in enumerate(zip(ids, input_events, out_texts)):
        if normalize_text(tin[2]) != normalize_text(tout):
            return ProposalRecord(
                case_id=case.case_id,
                candidate_id="",
                mapping_status="mapping_failure_ambiguous_text",
                regions=[],
                proposed_times_us={},
                unmapped_cue_ids=list(corrupted_times.keys()),
                notes=(
                    f"tool rewrote events: normalized text mismatch at position "
                    f"{pos} (cue {cid}): input {tin[2]!r} vs output {tout!r}; "
                    f"{len(out_events)} outputs vs {len(ids)} inputs; refusing to "
                    "guess correspondence"
                ),
            )
    proposed: dict[str, tuple[int, int]] = {}
    deltas: list[tuple[int, int]] = []
    for cue_id, (start_us, end_us, _text) in zip(ids, out_events):
        c_start, _c_end = corrupted_times[cue_id]
        proposed[cue_id] = (start_us, end_us)
        deltas.append((c_start, start_us - c_start))
    regions = fit_regions(deltas, case.grid_us, tol_us)
    unmapped = [cid for cid in corrupted_times if cid not in proposed]
    return ProposalRecord(
        case_id=case.case_id,
        candidate_id="",
        mapping_status="1:1-order-preserving",
        regions=regions,
        proposed_times_us=proposed,
        unmapped_cue_ids=unmapped,
        notes=notes,
    )


def run_candidate(
    candidate_id: str,
    case: CaseManifest,
    corrupted_times: dict[str, tuple[int, int]],
    corrupted_path: Path,
    reference_media: Path,
    scratch_dir: Path,
    tools: ToolConfig,
    tol_us: int,
    gold_classification_path: Path | None = None,
) -> tuple[ProposalRecord, dict]:
    """Run one candidate arm.

    GOLD-LEAKAGE BOUNDARY: the gold cue-classification path is reference
    evaluation data. It is consumed ONLY by the oracle-assisted diagnostic
    arms (`b1-pxo-*`). For every default candidate — including the default
    proxy arms `b1-px-fg`/`b1-px-fp` — the gold path is ignored here, so
    anchor selection uses only the conservative heuristics; callers cannot
    leak gold labels into default arms by passing the path.
    """
    meta: dict = {
        "candidate_id": candidate_id,
        "tool_versions": {},
        "preprocessing_seconds": 0.0,
        "candidate_seconds": 0.0,
    }
    # Defensive identity validation: refuse unsafe ids BEFORE any filesystem
    # effect (scratch_dir.mkdir below), so traversal attempts create nothing.
    require_safe_id(candidate_id, "candidate id")
    require_safe_id(case.case_id, "case id")
    scratch_dir.mkdir(parents=True, exist_ok=True)
    timeout = tools.timeouts.get(candidate_id, 900)
    is_oracle = candidate_id in ORACLE_DIAGNOSTIC_IDS

    if candidate_id == "b1-n":
        regions = [
            {
                "start_us": 0,
                "end_us": None,
                "offset_us": 0,
                "kind": "global",
                "confidence": "noop",
            }
        ]
        rec = ProposalRecord(
            case.case_id,
            "b1-n",
            "noop",
            regions,
            dict(corrupted_times),
            [],
            "no changes proposed",
        )
        return rec, meta

    if candidate_id in ("b1-fg", "b1-fp"):
        use_proxy = False
    elif candidate_id in ("b1-px-fg", "b1-px-fp", "b1-pxo-fg", "b1-pxo-fp"):
        use_proxy = True
    elif candidate_id == "b1-al":
        use_proxy = False
    else:
        raise ValueError(f"unhandled candidate {candidate_id}")

    mode = candidate_id.split("-")[-1]

    if candidate_id.startswith("b1-px") or candidate_id in ("b1-fg", "b1-fp"):
        exe = tools.command_overrides.get(candidate_id)
        if exe is None:
            if not tools.ffsubsync:
                rec = ProposalRecord(
                    case.case_id,
                    candidate_id,
                    "not_run",
                    [],
                    {},
                    list(corrupted_times),
                    "ffsubsync executable not available",
                )
                return rec, meta
            exe = [tools.ffsubsync]
        meta["tool_versions"]["ffsubsync"] = probe_version(exe)
        if mode == "fp" and not probe_split_penalty(exe):
            rec = ProposalRecord(
                case.case_id,
                candidate_id,
                "unsupported",
                [],
                {},
                list(corrupted_times),
                "installed ffsubsync lacks --split-penalty",
            )
            return rec, meta

        mapping: ProxyMapping | None = None
        full_ids: list[str] = []
        if use_proxy:
            t0 = time.monotonic()
            proxy_srt = scratch_dir / "proxy.srt"
            mapping = build_proxy(
                _reload_track(corrupted_path, case.fmt),
                proxy_srt,
                scratch_dir / "proxy_mapping.json",
                gold_classification_path if is_oracle else None,
            )
            meta["preprocessing_seconds"] += time.monotonic() - t0
            if not mapping.proxy_index_to_cue:
                rec = ProposalRecord(
                    case.case_id,
                    candidate_id,
                    "abstain_no_speech_anchors",
                    [],
                    {},
                    list(corrupted_times),
                    "no speech-like cues in track; signs-only/anchorless tracks stay unmapped",
                )
                return rec, meta
            in_srt = proxy_srt
            out_srt = scratch_dir / "proxy.synced.srt"
            ensure_scratch_path(out_srt)
            out_fmt = "srt"
        else:
            in_srt = scratch_dir / "full.srt"
            full_track = _reload_track(corrupted_path, case.fmt)
            full_ids = [
                c.cue_id for c in sorted(full_track.cues, key=lambda c: c.order)
            ]
            doc = pysubs2.SSAFile.load(
                corrupted_path, format=case.fmt, keep_privates=True
            )
            ensure_scratch_path(in_srt)
            doc.save(in_srt, format="srt")
            out_srt = scratch_dir / "full.synced.srt"
            ensure_scratch_path(out_srt)
            out_fmt = "srt"

        cmd = [
            *exe,
            str(reference_media),
            "-i",
            str(in_srt),
            "-o",
            str(out_srt),
            "--log-dir-path",
            str(scratch_dir),
        ]
        if mode == "fp":
            cmd += ["--split-penalty", "5"]
        code, out, err, secs = _run(cmd, timeout, scratch_dir)
        meta["candidate_seconds"] += secs
        if code == -1:
            rec = ProposalRecord(
                case.case_id,
                candidate_id,
                "timeout",
                [],
                {},
                list(corrupted_times),
                err,
            )
            return rec, meta
        if code != 0:
            rec = ProposalRecord(
                case.case_id,
                candidate_id,
                "failed",
                [],
                {},
                list(corrupted_times),
                (err or out)[-800:],
            )
            return rec, meta
        if not out_srt.exists():
            rec = ProposalRecord(
                case.case_id,
                candidate_id,
                "invalid_output",
                [],
                {},
                list(corrupted_times),
                "tool produced no output file",
            )
            return rec, meta

        times = _load_events_with_text(out_srt, out_fmt)
        notes = (
            f"ffsubsync {mode}; full-track flattened timing proposals only "
            "(formatting never applied to originals)"
        )
        if is_oracle:
            notes = f"{notes}; {ORACLE_MARKER}"
        rec = _proposal_for_indices(
            case,
            times,
            mapping,
            corrupted_times,
            tol_us,
            notes=notes,
            full_track_ids=full_ids,
            input_events=_load_events_with_text(in_srt, "srt"),
        )
        rec.candidate_id = candidate_id
        return rec, meta

    if candidate_id == "b1-al":
        exe = tools.command_overrides.get(candidate_id)
        if exe is None:
            if not tools.alass:
                rec = ProposalRecord(
                    case.case_id,
                    "b1-al",
                    "unsupported",
                    [],
                    {},
                    list(corrupted_times),
                    "alass executable not available",
                )
                return rec, meta
            exe = [tools.alass]
        meta["tool_versions"]["alass"] = probe_version(exe)
        in_ass = scratch_dir / "in.ass"
        full_track = _reload_track(corrupted_path, case.fmt)
        full_ids = [c.cue_id for c in sorted(full_track.cues, key=lambda c: c.order)]
        doc = pysubs2.SSAFile.load(corrupted_path, format=case.fmt, keep_privates=True)
        ensure_scratch_path(in_ass)
        doc.save(in_ass, format="ass")
        out_ass = scratch_dir / "out.ass"
        ensure_scratch_path(out_ass)
        cmd = [*exe, str(reference_media), str(in_ass), str(out_ass)]
        code, out, err, secs = _run(cmd, timeout, None)
        meta["candidate_seconds"] += secs
        if code == -1:
            rec = ProposalRecord(
                case.case_id, "b1-al", "timeout", [], {}, list(corrupted_times), err
            )
            return rec, meta
        if code != 0:
            rec = ProposalRecord(
                case.case_id,
                "b1-al",
                "failed",
                [],
                {},
                list(corrupted_times),
                (err or out)[-800:],
            )
            return rec, meta
        times = _load_events_with_text(out_ass, "ass")
        rec = _proposal_for_indices(
            case,
            times,
            None,
            corrupted_times,
            tol_us,
            "alass 1:1 event order",
            full_track_ids=full_ids,
            input_events=_load_events_with_text(in_ass, "ass"),
        )
        rec.candidate_id = "b1-al"
        return rec, meta

    raise ValueError(f"unhandled candidate {candidate_id}")


def _reload_track(path: Path, fmt: str):
    from .subtitles import Track

    return Track.load(path, fmt)
