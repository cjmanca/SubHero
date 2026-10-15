"""Benchmark CLI: source registry, case preparation, candidate runs, scoring, reports.

Run `python -m bench [--help]` from the `benchmarks/` directory, or
`python benchmarks/run_bench.py --help` from the repository root.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import __version__
from .adapters import (
    CANDIDATES,
    DEFAULT_CANDIDATE_IDS,
    ORACLE_DIAGNOSTIC_IDS,
    ToolConfig,
    run_candidate,
)
from .asr import get_semantic_verifier, get_transcriber
from .corrupt import prepare_case
from .fingerprint import GOLD_FILE_MISSING, compute_input_fingerprint
from .manifests import CaseManifest, ProposalRecord, read_json, write_json
from .media import extract_audio, extract_subtitle_stream, ffprobe_streams, sha256_file
from .paths import add_source_root, configure, require_safe_id
from .reporting import build_report, write_report
from .scoring import Tolerances, score_case
from .subtitles import Track
from .validator import (
    MIN_MATCH_RATIO,
    PAD_US,
    TIMING_TOLERANCE_US,
    normalize_language,
    validate_proposal,
)

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = DEFAULT_ROOT.parent
SYNTHETIC_RIGHTS = "redistributable-synthetic-fixture"


def _paths(root: Path) -> dict[str, Path]:
    return {
        "root": root,
        "cases": root / "cases",
        "fixtures": root / "fixtures",
        "private": root / "private",
        "private_cases": root / "private" / "cases",
        "scratch": root / "_scratch",
        "results": root / "results",
        "sources": root / "cases" / "sources.json",
    }


def _load_sources(p: Path) -> dict:
    return read_json(p) if p.exists() else {"schema_version": 1, "sources": {}}


def _save_sources(p: Path, data: dict) -> None:
    write_json(p, data)


def _load_case(p: Path) -> CaseManifest:
    d = read_json(p)
    d.pop("schema_version", None)
    return CaseManifest(**d)


def _resolve_under_root(paths: dict[str, Path], raw: str | Path) -> Path:
    gp = Path(raw)
    return gp if gp.is_absolute() else (paths["root"] / gp).resolve()


def _resolve_generated(paths: dict[str, Path], case: CaseManifest) -> Path:
    return _resolve_under_root(paths, case.generated_path)


def _under_root(path: Path, root: Path) -> bool:
    resolved = Path(path).resolve()
    root = Path(root).resolve()
    return resolved == root or root in resolved.parents


def _root_refuse(resolved: Path, reason: str) -> int:
    print(
        f"REFUSED (--root): {resolved} {reason}. Use an out-of-repo --root, the "
        f"canonical benchmarks root {Path(DEFAULT_ROOT).resolve()}, or a --root "
        "inside a Git-ignored area (for example "
        f"{(Path(REPO_ROOT) / 'benchmarks' / 'private').resolve()}/<name>/, "
        f"{(Path(REPO_ROOT) / 'benchmarks' / '_scratch').resolve()}/, or "
        f"{(Path(REPO_ROOT) / 'benchmarks' / 'results').resolve()}/).",
        file=sys.stderr,
    )
    return 2


def _refuse_unsafe_root(root: Path, repo_root: Path, default_root: Path) -> int | None:
    """Refuse an in-repo ``--root`` whose generated layout is not proven Git-ignored.

    The harness writes ``<root>/cases/sources.json``, ``<root>/private/…``,
    ``<root>/_scratch/…`` and ``<root>/results/…``. The committed ``.gitignore``
    protects ONLY the canonical default root's locations, so a fresh in-repo root
    such as ``benchmarks/custom-root/`` would make private media, manifests,
    scratch, and results eligible for a normal ``git add -A`` tracked commit.

    Roots outside the repository are allowed (out-of-repo/read-only-mount flows).
    The canonical default root is explicitly allowed: its layout is covered by
    committed ignore rules. Any other in-repo root must be proven ignored via
    ``git check-ignore`` from the repository root; when git is unavailable the
    ignorability cannot be proven, so such roots are refused (fail-closed).
    """
    resolved = Path(root).resolve()
    if not _under_root(resolved, repo_root):
        return None
    if resolved == Path(default_root).resolve():
        return None
    git = shutil.which("git")
    if git is None:
        return _root_refuse(
            resolved,
            "is in-repo and git is unavailable, so Git-ignorability cannot be proven",
        )
    proc = subprocess.run(
        [
            git,
            "-C",
            str(Path(repo_root).resolve()),
            "check-ignore",
            "-q",
            "--",
            str(resolved),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return None
    return _root_refuse(
        resolved,
        "is in-repo but not Git-ignored (its manifests/scratch/results would become committable)",
    )


class StreamSelectionError(ValueError):
    """A stream spec could not be resolved to exactly one stream of its type."""


def _typed_streams(streams: list[dict], codec_type: str) -> list[dict]:
    return [s for s in streams if s.get("codec_type") == codec_type]


def _describe_typed_streams(typed: list[dict]) -> str:
    lines = []
    for sidx, s in enumerate(typed):
        lines.append(
            f"  sidx={sidx} index={s.get('index')} "
            f"language={(s.get('tags') or {}).get('language') or 'und'} "
            f"codec={s.get('codec_name')}"
        )
    return "\n".join(lines) if lines else "  (none)"


def _stream_identity(stream: dict, sidx: int) -> dict:
    return {
        "index": stream.get("index"),
        "sidx": sidx,
        "language": (stream.get("tags") or {}).get("language"),
        "codec_name": stream.get("codec_name"),
    }


def _resolve_stream_spec(spec: str, streams: list[dict], codec_type: str) -> dict:
    """Resolve index:<n>|sidx:<n>|lang:<code> to a normalized stream identity.

    ``index`` is the ffprobe global stream index (must exist and match
    ``codec_type``); ``sidx`` is the ffmpeg type-relative map index used in
    ``0:a:<n>``/``0:s:<n>``; ``lang`` must match exactly one stream's ffprobe
    language tag. Raises StreamSelectionError listing the candidate streams.
    """
    typed = _typed_streams(streams, codec_type)
    listing = f"available {codec_type} streams:\n{_describe_typed_streams(typed)}"
    kind, sep, value = spec.partition(":")
    if not sep or kind not in ("index", "sidx", "lang"):
        raise StreamSelectionError(
            f"stream spec {spec!r} must be index:<n> (ffprobe global index), "
            f"sidx:<n> (ffmpeg {codec_type}-relative map index), or lang:<code>; "
            f"{listing}"
        )
    if kind == "lang":
        matches = [
            (sidx, s)
            for sidx, s in enumerate(typed)
            if (s.get("tags") or {}).get("language") == value
        ]
        if len(matches) != 1:
            raise StreamSelectionError(
                f"lang:{value} matches {len(matches)} {codec_type} streams "
                f"(exactly one is required); {listing}"
            )
        sidx, stream = matches[0]
        return _stream_identity(stream, sidx)
    if not value.isdigit():
        raise StreamSelectionError(
            f"stream spec {spec!r} needs a non-negative integer after {kind}:; {listing}"
        )
    n = int(value)
    if kind == "sidx":
        if not 0 <= n < len(typed):
            raise StreamSelectionError(
                f"sidx:{n} is out of range for {len(typed)} {codec_type} "
                f"streams; {listing}"
            )
        return _stream_identity(typed[n], n)
    for sidx, s in enumerate(typed):
        if s.get("index") == n:
            return _stream_identity(s, sidx)
    raise StreamSelectionError(f"index:{n} is not a {codec_type} stream; {listing}")


def _resolve_audio_selection(spec: str | None, streams: list[dict]) -> dict | None:
    """Resolve the reference-audio track; refuse ambiguous multi-audio sources."""
    audio = _typed_streams(streams, "audio")
    if spec:
        return _resolve_stream_spec(spec, streams, "audio")
    if len(audio) > 1:
        raise StreamSelectionError(
            f"media has {len(audio)} audio streams; register with --audio "
            f"index:<n>|sidx:<n>|lang:<code> to pick the reference track; "
            f"{_describe_typed_streams(audio)}"
        )
    if len(audio) == 1:
        return _stream_identity(audio[0], 0)
    return None


def _resolve_user_path(raw: str) -> Path:
    """Canonical resolution for USER-GIVEN relative paths: from the current
    working directory. `cmd_source_add` resolves sidecar/gold input with this
    function **at registration time**, evaluates the private-data policy on the
    exact result, and persists that absolute path in the Git-ignored local
    registry (as it already does for ``media_path``), so later invocations from
    any other working directory open the same files. Harness-stored manifest
    paths are root-relative and resolved at run time by `_resolve_under_root`;
    they are internal and unaffected.
    """
    return Path(raw).resolve()


def _private_path_policy(
    candidate: Path, benchmarks_root: Path, repo_root: Path, rights: str
) -> str | None:
    """Return a refusal reason for in-repo paths outside the rights-appropriate homes.

    Paths outside the repository (e.g. read-only mounts) are allowed for every
    rights class. Inside the repo the permitted home is rights-aware:

    * ``--rights redistributable-synthetic-fixture`` may target the ``fixtures/``
      homes (the synthetic coherence check in ``cmd_source_add`` further pins
      these to the canonical committed fixtures home) and, permissively, the
      private homes.
    * Any non-synthetic rights claim (``private-local``, i.e. real reference
      episodes) may target ONLY the private homes — the canonical
      ``benchmarks/private/`` and the active root's ``private/`` — never the
      tracked ``benchmarks/fixtures/`` home, which is reserved for explicitly
      declared redistributable synthetic references. A private episode placed in
      the fixtures home is eligible for a normal tracked commit, so it is refused.

    The candidate must be the exact resolved path that registration stores and
    the consumers will open (CWD-joined for user-given relative paths).
    """
    resolved = Path(candidate).resolve()
    if not _under_root(resolved, repo_root):
        return None
    private_homes = [
        Path(repo_root) / "benchmarks" / "private",
        Path(benchmarks_root) / "private",
    ]
    homes = list(private_homes)
    if rights == SYNTHETIC_RIGHTS:
        homes += [
            Path(repo_root) / "benchmarks" / "fixtures",
            Path(benchmarks_root) / "fixtures",
        ]
    for home in homes:
        if _under_root(resolved, home):
            return None
    if rights == SYNTHETIC_RIGHTS:
        return (
            f"in-repo path {resolved} is outside benchmarks/private/ and "
            f"benchmarks/fixtures/; register synthetic references under "
            f"{(Path(repo_root) / 'benchmarks' / 'fixtures').resolve()} "
            "or outside the repository (read-only mounts are allowed)"
        )
    return (
        f"in-repo path {resolved} is outside benchmarks/private/; --rights {rights} "
        f"registrations must live under {(benchmarks_root / 'private').resolve()} "
        f"or the repository private home {(Path(repo_root) / 'benchmarks' / 'private').resolve()} "
        "or outside the repository (read-only mounts are allowed); "
        f"benchmarks/fixtures/ is reserved for --rights {SYNTHETIC_RIGHTS}"
    )


def _case_manifest_path(
    paths: dict[str, Path], case_id: str, rights_status: str
) -> Path:
    """Keep non-synthetic case manifests out of the committed cases directory."""
    if rights_status == SYNTHETIC_RIGHTS:
        return paths["cases"] / f"{case_id}.case.json"
    return paths["private_cases"] / f"{case_id}.case.json"


def _lookup_case_path(paths: dict[str, Path], case_id: str) -> Path | None:
    for d in (paths["cases"], paths["private_cases"]):
        p = d / f"{case_id}.case.json"
        if p.is_file():
            return p
    return None


def _iter_case_paths(paths: dict[str, Path]) -> list[Path]:
    found: dict[str, Path] = {}
    for d in (paths["cases"], paths["private_cases"]):
        for p in sorted(d.glob("*.case.json")):
            found.setdefault(p.name, p)
    return [found[name] for name in sorted(found)]


def _case_id_is_safe(case_id: str) -> bool:
    return (
        bool(case_id)
        and "/" not in case_id
        and "\\" not in case_id
        and ".." not in case_id
        and not case_id.startswith(".")
    )


def _refuse_unsafe_id(value: str, label: str) -> int | None:
    """Return exit code 2 with a message when an id is unsafe; None if safe."""
    try:
        require_safe_id(value, label)
    except ValueError as exc:
        print(f"{exc}", file=sys.stderr)
        return 2
    return None


def _verify_sources(
    paths: dict[str, Path],
    source_id: str,
    sources: dict,
    case: CaseManifest | None = None,
) -> list[str]:
    problems: list[str] = []
    s = sources["sources"].get(source_id)
    if s is None:
        return [f"source {source_id} no longer registered"]
    mp = s.get("media_path")
    if not isinstance(mp, str) or not mp:
        return [
            (
                f"source {source_id} registry record has no media_path; "
                "re-register the source"
            )
        ]
    media = Path(mp)
    if not media.is_file():
        problems.append("registered media file missing")
    else:
        recorded_media = s.get("media_sha256")
        if not isinstance(recorded_media, str) or not recorded_media:
            problems.append(
                f"source {source_id} registry record has no media_sha256; "
                "re-register the source"
            )
        elif sha256_file(media) != recorded_media:
            problems.append("SOURCE MUTATION DETECTED: media fingerprint changed")
    for track_id, spec in s.get("subtitle_specs", {}).items():
        recorded = s.get("subtitle_sha256", {}).get(track_id)
        if spec.startswith("sidecar:") and recorded:
            p = Path(spec.removeprefix("sidecar:"))
            if not p.is_file():
                problems.append(f"registered subtitle {track_id} missing")
            elif sha256_file(p) != recorded:
                problems.append(
                    f"SOURCE MUTATION DETECTED: subtitle {track_id} fingerprint changed"
                )
    if case is not None:
        generated = _resolve_generated(paths, case)
        if not generated.is_file():
            problems.append("generated corrupted file missing from scratch")
        elif sha256_file(generated) != case.generated_subtitle_sha256:
            problems.append("case input no longer matches case manifest fingerprint")
    return problems


def _gold_content_sha256(paths: dict[str, Path], case: CaseManifest) -> str | None:
    """Live content hash of the case's gold-classification file (F02 binding).

    ``None`` when the case declares no gold input; the literal
    ``GOLD_FILE_MISSING`` when the manifest names a gold file that cannot be
    read (treated as part of the case identity, so a deleted/added gold file
    is a fingerprint change, never a silent pass); otherwise the sha256 of the
    file bytes. Recomputed at run, score, b1-va base/acceptance binding, and
    report so edits to the oracle material invalidate dependent artifacts.
    """
    if not case.gold_classification_path:
        return None
    gold_path = _resolve_under_root(paths, case.gold_classification_path)
    if not gold_path.is_file():
        return GOLD_FILE_MISSING
    return sha256_file(gold_path)


def _provenance_problem(
    cand_dir: Path,
    candidate_id: str,
    case: CaseManifest,
    source: dict,
    gold_sha: str | None = None,
) -> str:
    """Return a refusal reason when persisted candidate artifacts are not bound
    to the current case generation; the empty string when they are.

    Versioned provenance (schema_version 2 ``run.json``) is the only basis for
    trusting a persisted proposal: the recorded ``input_fingerprint`` must equal
    the fingerprint recomputed from the *current* case manifest + registry
    source record + candidate id + recorded tool versions, and the
    ``proposal.json`` bytes on disk must match the recorded ``proposal_sha256``.
    Missing, legacy (schema 1), stale, or tampered artifacts are reported as
    ``UNVERIFIED:``/``STALE:`` and always require a fresh candidate run.
    """
    label = f"{case.case_id}/{candidate_id}"
    rerun = f"re-run it: run --case {case.case_id} --candidate {candidate_id}"
    run_path = cand_dir / "run.json"
    if not run_path.exists():
        return f"UNVERIFIED: {label} has proposal.json with no run.json provenance; {rerun}"
    try:
        run = read_json(run_path)
    except (OSError, ValueError) as exc:
        return f"UNVERIFIED: {label} run.json is unreadable ({exc}); {rerun}"
    if not isinstance(run, dict):
        return (
            f"UNVERIFIED: {label} run.json is not a JSON object "
            f"({type(run).__name__}); {rerun}"
        )
    recorded = run.get("input_fingerprint")
    if not recorded:
        return (
            f"UNVERIFIED: {label} run.json (schema_version "
            f"{run.get('schema_version', '?')}) predates versioned input "
            f"fingerprints and cannot be bound to this case generation; {rerun}"
        )
    current = compute_input_fingerprint(
        case, source, candidate_id, run.get("tool_versions", {}), gold_sha
    )
    if recorded != current:
        return (
            f"STALE: {label} was run against a different case generation "
            f"(run.json input_fingerprint {str(recorded)[:16]}… != current {str(current)[:16]}…; "
            f"case seed/inputs, ground-truth annotations, gold/oracle inputs, "
            f"subtitle input, selected audio, source fingerprint, or tool "
            f"identity changed); {rerun}"
        )
    recorded_proposal = run.get("proposal_sha256")
    prop_path = cand_dir / "proposal.json"
    if not recorded_proposal:
        return (
            f"UNVERIFIED: {label} run.json records no proposal_sha256; "
            f"proposal bytes are unbound; {rerun}"
        )
    if not prop_path.is_file():
        return (
            f"UNVERIFIED: {label} run.json claims a proposal but proposal.json "
            f"is missing; {rerun}"
        )
    actual = sha256_file(prop_path)
    if actual != recorded_proposal:
        return (
            f"STALE: {label} proposal.json bytes no longer match run.json "
            f"proposal_sha256 (recorded {str(recorded_proposal)[:16]}… vs actual "
            f"{str(actual)[:16]}…; tampered or replaced?); {rerun}"
        )
    return ""


REQUIRED_VALIDATION_CONFIG_KEYS = (
    "seed",
    "language",
    "subtitle_language",
    "asr_model",
    "verifier_model",
    "pad_us",
    "min_match_ratio",
    "timing_tolerance_us",
)


def _acceptance_binding_problem(
    cand_dir: Path,
    run: dict,
    case: CaseManifest,
    source: dict,
    paths: dict[str, Path],
    gold_sha: str | None = None,
) -> str:
    """Return a refusal reason when a b1-va ``acceptance.json`` is not bound to
    the verified ``run.json`` provenance AND to the CURRENT base arm; the empty
    string when it is.

    Binding contract (P1-1 + third-review F01). ``cmd_score`` loads an
    acceptance record ONLY for the ``b1-va`` arm, and only when ALL of the
    following hold:

    * ``run.json`` records ``acceptance_sha256`` equal to the actual
      ``acceptance.json`` bytes. ``cmd_run`` writes ``acceptance.json`` FIRST,
      hashes those exact bytes into ``run.json.acceptance_sha256``, and only
      then writes ``run.json``; the file, its hash, and the run provenance are
      therefore mutually consistent for a genuine run.
    * ``acceptance.case_id == case.case_id`` — a cross-case acceptance copy is
      refused (case_id is checked, not ignored).
    * ``acceptance.candidate_id == "b1-va"`` — the acceptance is attributed to
      the validating arm, not to a base/proposal-only arm.
    * ``acceptance.validated_candidate_id == run.validated_candidate_id`` —
      the base arm identity (name) is bound.
    * F01 base-run/proposal binding: the base arm's CURRENT artifacts must
      still match what the acceptance validated. The base arm must pass the
      full ``_provenance_problem`` gate against the current case generation
      (fingerprint + proposal bytes), the recorded ``base_input_fingerprint``
      must equal the base ``run.json``'s fingerprint, the recorded
      ``base_proposal_sha256`` must equal the CURRENT base ``proposal.json``
      bytes, and the recorded ``base_run_sha256`` must equal the CURRENT base
      ``run.json`` bytes. Re-running the base with different settings/results
      (new proposal bytes, new run record, new fingerprint from seed/audio/
      gold/ground-truth changes) therefore invalidates the downstream
      acceptance AT READ TIME (score and report) without rerunning the
      validator: the old acceptance can never be scored as if it validated
      the new proposal.
    * F01 validation-identity binding: ``run.json`` records a
      ``validation_config`` (sampling seed, resolved spoken/subtitle language
      identities, ASR and semantic-verifier model ids, validator constants;
      NO credentials) with every required key present. Artifacts predating
      this contract are unbound and must be re-validated; the config is
      embedded in the score row so a run made with a different seed/model/
      language can never be silently labeled as the same experiment.

    Missing, legacy (no recorded hash), unreadable, tampered, replaced, or
    planted acceptance artifacts return a non-empty reason so ``cmd_score``
    takes the rc-6 refusal path (message + delete any stale ``score.json``); a
    hand-written ``success``/original-times file can never drive final-timeline
    scoring, and the verified current fingerprint is embedded in a real score.
    """
    label = f"{case.case_id}/b1-va"
    rerun = f"re-run it: run --case {case.case_id} --candidate b1-va"
    from .manifests import AcceptanceRecord

    acc_path = cand_dir / "acceptance.json"
    if not acc_path.is_file():
        return (
            f"UNVERIFIED: {label} run.json validated a base arm but "
            f"acceptance.json is missing; {rerun}"
        )
    recorded = run.get("acceptance_sha256")
    if not recorded:
        return (
            f"UNVERIFIED: {label} run.json (schema_version "
            f"{run.get('schema_version', '?')}) records no acceptance_sha256; "
            f"acceptance bytes are unbound; {rerun}"
        )
    actual = sha256_file(acc_path)
    if actual != recorded:
        return (
            f"STALE: {label} acceptance.json bytes no longer match run.json "
            f"acceptance_sha256 (recorded {str(recorded)[:16]}… vs actual {str(actual)[:16]}…; "
            f"tampered, replaced, or planted?); {rerun}"
        )
    try:
        acceptance_data = read_json(acc_path)
        if not isinstance(acceptance_data, dict):
            raise TypeError(
                f"acceptance.json is a JSON {type(acceptance_data).__name__}, not an object"
            )
        acceptance = AcceptanceRecord(**acceptance_data)
    except (OSError, ValueError, TypeError) as exc:
        return f"UNVERIFIED: {label} acceptance.json is unreadable ({exc}); {rerun}"
    if acceptance.case_id != case.case_id:
        return (
            f"UNVERIFIED: {label} acceptance.json case_id "
            f"{acceptance.case_id!r} does not match this case {case.case_id!r} "
            f"(cross-case acceptance planted); {rerun}"
        )
    if (
        not isinstance(acceptance.accepted_times_us, dict)
        or not isinstance(acceptance.accepted_regions, list)
        or not isinstance(acceptance.rejected_regions, list)
        or not isinstance(acceptance.abstained_regions, list)
        or not isinstance(acceptance.sample_cue_ids, list)
        or not isinstance(acceptance.validated_candidate_id, str)
        or not isinstance(acceptance.status, str)
        or any(
            not isinstance(v, (list, tuple))
            or len(v) != 2
            or any(type(x) is not int for x in v)
            for v in acceptance.accepted_times_us.values()
        )
    ):
        return (
            f"UNVERIFIED: {label} acceptance.json field types are "
            f"incompatible (hostile/planted values); refusing to score; {rerun}"
        )
    if acceptance.candidate_id != "b1-va":
        return (
            f"UNVERIFIED: {label} acceptance.json candidate_id "
            f"{acceptance.candidate_id!r} is not b1-va; {rerun}"
        )
    validated = run.get("validated_candidate_id")
    if not validated:
        return (
            f"UNVERIFIED: {label} run.json records no validated_candidate_id; "
            f"the acceptance base arm is unbound; {rerun}"
        )
    if acceptance.validated_candidate_id != validated:
        return (
            f"UNVERIFIED: {label} acceptance.json validated_candidate_id "
            f"{acceptance.validated_candidate_id!r} != run.json "
            f"{validated!r}; {rerun}"
        )
    validation_config = run.get("validation_config")
    if not isinstance(validation_config, dict):
        return (
            f"UNVERIFIED: {label} run.json records no validation_config "
            f"(sampling seed / language identities / ASR+verifier models are "
            f"unbound; predates the F01 binding contract); {rerun}"
        )
    missing_keys = [
        k for k in REQUIRED_VALIDATION_CONFIG_KEYS if k not in validation_config
    ]
    if missing_keys:
        return (
            f"UNVERIFIED: {label} run.json validation_config is missing keys "
            f"{missing_keys}; the validation input identity is unbound; {rerun}"
        )
    base_rerun = f"re-run the base arm, then re-run b1-va (run --case {case.case_id} --candidate {validated} && run --case {case.case_id} --candidate b1-va --base-candidate {validated})"
    base_dir = paths["results"] / case.case_id / validated
    base_run_path = base_dir / "run.json"
    base_proposal_path = base_dir / "proposal.json"
    if not base_run_path.is_file():
        return (
            f"UNVERIFIED: {label} base arm {validated} has no run.json; the "
            f"validated base run is unbound; {base_rerun}"
        )
    try:
        base_run = read_json(base_run_path)
    except (OSError, ValueError) as exc:
        return (
            f"UNVERIFIED: {label} base arm {validated} run.json is unreadable "
            f"({exc}); {base_rerun}"
        )
    if not isinstance(base_run, dict):
        return (
            f"UNVERIFIED: {label} base arm {validated} run.json is not a JSON "
            f"object ({type(base_run).__name__}); {base_rerun}"
        )
    base_problem = _provenance_problem(base_dir, validated, case, source, gold_sha)
    if base_problem:
        return (
            f"STALE: {label} accepted a base proposal that is no longer the "
            f"current case generation — {base_problem}; the validator was run "
            f"against different base inputs; {base_rerun}"
        )
    recorded_base_fp = run.get("base_input_fingerprint")
    current_base_fp = base_run.get("input_fingerprint")
    if not recorded_base_fp or not current_base_fp:
        return (
            f"UNVERIFIED: {label} run.json records no base_input_fingerprint; "
            f"the validated base run generation is unbound; {base_rerun}"
        )
    if recorded_base_fp != current_base_fp:
        return (
            f"STALE: {label} validated base run fingerprint {str(recorded_base_fp)[:16]}… "
            f"!= current base {validated} fingerprint {str(current_base_fp)[:16]}…; "
            f"the base arm was re-run against a different case generation; "
            f"{base_rerun}"
        )
    recorded_base_proposal = run.get("base_proposal_sha256")
    if not recorded_base_proposal:
        return (
            f"UNVERIFIED: {label} run.json records no base_proposal_sha256; "
            f"the validated base proposal bytes are unbound; {base_rerun}"
        )
    current_base_proposal = sha256_file(base_proposal_path)
    if recorded_base_proposal != current_base_proposal:
        return (
            f"STALE: {label} validated base proposal bytes {str(recorded_base_proposal)[:16]}… "
            f"!= current base proposal.json bytes {str(current_base_proposal)[:16]}…; "
            f"the base arm produced a different proposal (settings/results "
            f"changed) and the acceptance was not re-validated; {base_rerun}"
        )
    recorded_base_run_sha = run.get("base_run_sha256")
    if not recorded_base_run_sha:
        return (
            f"UNVERIFIED: {label} run.json records no base_run_sha256; the "
            f"validated base run record is unbound; {base_rerun}"
        )
    current_base_run_sha = sha256_file(base_run_path)
    if recorded_base_run_sha != current_base_run_sha:
        return (
            f"STALE: {label} validated base run.json bytes {str(recorded_base_run_sha)[:16]}… "
            f"!= current base run.json bytes {str(current_base_run_sha)[:16]}…; the "
            f"base run record changed (re-run with new identity) and the "
            f"acceptance was not re-validated; {base_rerun}"
        )
    return ""


def _delete_stale_score(cand_dir: Path, label: str, reason: str) -> None:
    """Delete a candidate's ``score.json`` when it is skipped/refused (P1-2).

    Any number left on disk from an EARLIER case generation is untrustworthy:
    the report binding will drop it, and leaving it invites a stale row. Report
    the removal on stderr so a skip/refusal is never silent.
    """
    stale = cand_dir / "score.json"
    if stale.exists():
        stale.unlink()
        print(
            f"deleted stale score.json for {label} ({reason})",
            file=sys.stderr,
        )


def cmd_source_add(args, paths) -> int:
    refused = _refuse_unsafe_id(args.source_id, "source id")
    if refused is not None:
        return refused
    for spec in list(args.subtitle or []) + list(args.gold or []):
        track_id, _, _ = spec.partition("=")
        refused = _refuse_unsafe_id(track_id, "track id")
        if refused is not None:
            return refused
    media = Path(args.path).resolve()
    if not media.exists():
        print(f"NOT FOUND: {media}", file=sys.stderr)
        return 2
    policy_targets: list[Path] = [media]
    for spec in args.subtitle or []:
        _, _, target = spec.partition("=")
        if target.startswith("sidecar:"):
            # Same resolution registration persists (CWD-joined, then resolved).
            policy_targets.append(_resolve_user_path(target.removeprefix("sidecar:")))
    for gold_spec in args.gold or []:
        _, _, target = gold_spec.partition("=")
        policy_targets.append(_resolve_user_path(target))
    for target in policy_targets:
        reason = _private_path_policy(target, paths["root"], REPO_ROOT, args.rights)
        if reason is not None:
            print(f"REFUSED (private data policy): {reason}", file=sys.stderr)
            return 2
    # Rights-claim coherence: a redistributable-synthetic-fixture registration
    # must point at the committed fixtures home; real episodes declare private-local.
    if args.rights == SYNTHETIC_RIGHTS:
        fixtures_home = (REPO_ROOT / "benchmarks" / "fixtures").resolve()
        for target in policy_targets:
            if not _under_root(target, fixtures_home):
                print(
                    f"REFUSED (rights claim): --rights {SYNTHETIC_RIGHTS} requires "
                    f"the media and all sidecar/gold paths to live inside "
                    f"{fixtures_home}; register real episodes with --rights private-local",
                    file=sys.stderr,
                )
                return 2
    sources = _load_sources(paths["sources"])
    if args.source_id in sources["sources"]:
        print(f"source id already registered: {args.source_id}", file=sys.stderr)
        return 2
    streams = ffprobe_streams(media)
    raw_streams = streams.get("streams", [])
    try:
        audio_selected = _resolve_audio_selection(args.audio, raw_streams)
    except StreamSelectionError as exc:
        print(f"REFUSED (audio selection): {exc}", file=sys.stderr)
        return 2
    audio_spec = args.audio if args.audio else ("sidx:0" if audio_selected else None)
    subtitles: dict[str, str] = {}
    hashes: dict[str, str] = {}
    subtitle_selected: dict[str, dict] = {}
    for spec in args.subtitle or []:
        track_id, _, target = spec.partition("=")
        if target.startswith("sidecar:"):
            # F08: persist the canonical absolute path, i.e. the exact path the
            # private-data policy evaluated, so later CWDs cannot move the target.
            resolved_sidecar = _resolve_user_path(target.removeprefix("sidecar:"))
            subtitles[track_id] = f"sidecar:{resolved_sidecar}"
            hashes[track_id] = sha256_file(resolved_sidecar)
        elif target.startswith("mkv:"):
            remainder = target.removeprefix("mkv:")
            if remainder.isdigit():
                print(
                    f"REFUSED: legacy subtitle spec {target!r} is ambiguous: ffmpeg "
                    "-map 0:s:<n> counts only subtitle streams while 'source inspect' "
                    "lists ffprobe GLOBAL indices. Use mkv:sidx:<n> (ffmpeg "
                    "subtitle-relative index), mkv:index:<n> (ffprobe global index), "
                    "or mkv:lang:<code> (unique ffprobe language tag).",
                    file=sys.stderr,
                )
                return 2
            try:
                sel = _resolve_stream_spec(remainder, raw_streams, "subtitle")
            except StreamSelectionError as exc:
                print(f"REFUSED (subtitle selection): {exc}", file=sys.stderr)
                return 2
            subtitles[track_id] = f"mkv:sidx:{sel['sidx']}"
            subtitle_selected[track_id] = sel
        else:
            print(f"unsupported subtitle spec {target}", file=sys.stderr)
            return 2
    subtitle_languages: dict[str, str] = {}
    for spec in args.subtitle_language or []:
        track_id, sep, code = spec.partition("=")
        if not sep or not code.strip():
            print(
                f"REFUSED: --subtitle-language spec {spec!r} must be track_id=<lang>",
                file=sys.stderr,
            )
            return 2
        refused = _refuse_unsafe_id(track_id, "track id")
        if refused is not None:
            return refused
        subtitle_languages[track_id] = code.strip()
    # MKV subtitle tracks carry an embedded ffprobe language tag; capture it so
    # the run consumes a verified target identity. Sidecar tracks have no
    # embedded tag, so they rely on the explicit --subtitle-language hint above.
    for track_id, sel in subtitle_selected.items():
        if track_id not in subtitle_languages and sel.get("language"):
            subtitle_languages[track_id] = sel["language"]
    # A prepared case records a sidecar track by its file stem (corrupt.py sets
    # track_id = source_track_path.stem), so alias each sidecar hint by stem too
    # for the run to look the identity up by the case's persisted track_id. The
    # alias exists ONLY to bridge that stem-based track_id for the single-sidecar
    # case (the common, working flow). When TWO sidecar tracks share a stem
    # (e.g. `ep.ass` = eng and `stemB/ep.ass` = kor), the stem is ambiguous: a
    # stem-keyed language would leak one track's identity onto the other (P2-1),
    # so on a stem COLLISION the alias is NOT stored and the registry keeps only
    # the track-id keys. `cmd_run` resolves the target identity via
    # `subtitle_languages.get(case.track_id)`: for a collided stem that lookup
    # returns nothing, giving the identity-unknown abstain path (never a
    # wrong-identity lexical reject).
    from collections import Counter

    sidecar_stem_counts = Counter(
        Path(target.removeprefix("sidecar:")).stem
        for target in subtitles.values()
        if target.startswith("sidecar:")
    )
    for track_id, target in subtitles.items():
        if target.startswith("sidecar:") and track_id in subtitle_languages:
            stem = Path(target.removeprefix("sidecar:")).stem
            if sidecar_stem_counts[stem] == 1:
                subtitle_languages.setdefault(stem, subtitle_languages[track_id])
    duration = None
    fmt = streams.get("format", {})
    if fmt.get("duration"):
        duration = int(float(fmt["duration"]) * 1_000_000)
    # F08: gold classification targets are stored as the same canonical absolute
    # paths the policy evaluated, parsed exactly like the policy loop above.
    gold_targets = {
        track_id: str(_resolve_user_path(target))
        for track_id, _, target in (g.partition("=") for g in args.gold or [])
    }
    sources["sources"][args.source_id] = {
        "source_id": args.source_id,
        "media_path": str(media),
        "media_sha256": sha256_file(media),
        "duration_us": duration,
        "streams": [
            {
                "index": s.get("index"),
                "codec_type": s.get("codec_type"),
                "language": (s.get("tags") or {}).get("language"),
                "codec_name": s.get("codec_name"),
            }
            for s in streams.get("streams", [])
        ],
        "subtitle_specs": subtitles,
        "subtitle_sha256": hashes,
        "audio_selected": audio_selected,
        "audio_spec": audio_spec,
        "subtitle_selected": subtitle_selected,
        "subtitle_languages": subtitle_languages,
        "gold_classification": gold_targets,
        "rights_status": args.rights,
        "notes": args.notes,
    }
    _save_sources(paths["sources"], sources)
    add_source_root(media.parent)
    audio_note = f" (audio 0:a:{audio_selected['sidx']})" if audio_selected else ""
    print(f"registered source {args.source_id} @ {media}{audio_note}")
    return 0


def cmd_source_list(args, paths) -> int:
    sources = _load_sources(paths["sources"])
    for sid, s in sorted(sources["sources"].items()):
        print(
            f"{sid}\tmedia={s.get('media_path', 'MISSING')}\tsha256={str(s.get('media_sha256', ''))[:16]}…\ttracks={list(s.get('subtitle_specs', {}))}"
        )
    return 0


def cmd_source_inspect(args, paths) -> int:
    refused = _refuse_unsafe_id(args.source_id, "source id")
    if refused is not None:
        return refused
    sources = _load_sources(paths["sources"])
    s = sources["sources"].get(args.source_id)
    if not s:
        print(f"unknown source {args.source_id}", file=sys.stderr)
        return 2
    import json

    print(json.dumps(s, indent=2, ensure_ascii=False))
    return 0


def cmd_case_prepare(args, paths) -> int:
    # Validate ALL user-controlled ids up front, before any mkdir/write.
    for value, label in (
        (args.source_id, "source id"),
        (args.track_id, "track id"),
    ):
        refused = _refuse_unsafe_id(value, label)
        if refused is not None:
            return refused
    if args.case_id is not None:
        refused = _refuse_unsafe_id(args.case_id, "case id")
        if refused is not None:
            return refused
    sources = _load_sources(paths["sources"])
    s = sources["sources"].get(args.source_id)
    if not s:
        print(f"unknown source {args.source_id}", file=sys.stderr)
        return 2
    specs = s.get("subtitle_specs")
    if not isinstance(specs, dict):
        print(
            f"REFUSED: source {args.source_id} registry record has no "
            "subtitle_specs; re-register the source",
            file=sys.stderr,
        )
        return 2
    spec = specs.get(args.track_id)
    if spec is None:
        print(
            f"track {args.track_id} not registered for source {args.source_id}",
            file=sys.stderr,
        )
        return 2
    case_id = (
        args.case_id or f"{args.source_id}-{args.track_id}-{args.scenario}-{args.seed}"
    )
    if not _case_id_is_safe(case_id):
        print(
            f"REFUSED: case id {case_id!r} contains path separators; refusing to route manifest",
            file=sys.stderr,
        )
        return 2
    refused = _refuse_unsafe_id(case_id, "case id")
    if refused is not None:
        return refused
    scratch_case = paths["scratch"] / case_id
    scratch_case.mkdir(parents=True, exist_ok=True)
    if spec.startswith("sidecar:"):
        src_ass = Path(spec.removeprefix("sidecar:"))
    elif spec.startswith("mkv:"):
        remainder = spec.removeprefix("mkv:")
        kind, _sep, value = remainder.partition(":")
        if kind != "sidx" or not value.isdigit():
            print(
                f"REFUSED: subtitle spec {spec!r} is not a normalized "
                "mkv:sidx:<n> registration; re-register the source using "
                "mkv:sidx:<n>, mkv:index:<n>, or mkv:lang:<code>",
                file=sys.stderr,
            )
            return 2
        src_ass = scratch_case / f"{args.track_id}.ass"
        mp = s.get("media_path")
        if not isinstance(mp, str) or not mp:
            print(
                f"REFUSED: source {args.source_id} registry record has no "
                "media_path; re-register the source",
                file=sys.stderr,
            )
            return 2
        extract_subtitle_stream(Path(mp), int(value), src_ass)
    else:
        print(f"unsupported subtitle spec {spec}", file=sys.stderr)
        return 2
    problems = _verify_sources(paths, args.source_id, sources)
    if problems:
        for p in problems:
            print(f"SOURCE CHECK FAILED: {p}", file=sys.stderr)
        return 3
    out = (
        scratch_case / "corrupted.ass"
        if src_ass.suffix.lower() in (".ass", ".ssa")
        else scratch_case / "corrupted.srt"
    )
    gold = s.get("gold_classification", {}).get(args.track_id)
    case = prepare_case(
        source_id=args.source_id,
        case_id=case_id,
        scenario=args.scenario,
        seed=args.seed,
        source_track_path=src_ass,
        out_path=out,
        gold_classification_path=Path(gold) if gold else None,
        notes=args.notes,
    )
    try:
        rel = Path(case.generated_path).resolve().relative_to(paths["root"].resolve())
        case.generated_path = rel.as_posix()
    except ValueError:
        pass
    if case.gold_classification_path:
        try:
            relg = (
                Path(case.gold_classification_path)
                .resolve()
                .relative_to(paths["root"].resolve())
            )
            case.gold_classification_path = relg.as_posix()
        except ValueError:
            pass
    case_path = _case_manifest_path(paths, case_id, s.get("rights_status", ""))
    write_json(case_path, case.to_json())
    print(f"prepared case {case_id} -> {out} (manifest {case_path})")
    return 0


def cmd_case_list(args, paths) -> int:
    for p in _iter_case_paths(paths):
        d = read_json(p)
        print(
            f"{d['case_id']}\t{d['scenario']}\tseed={d['seed']}\tsource={d['source_id']}/{d['track_id']}"
        )
    return 0


def _get_reference_audio(
    paths: dict[str, Path], case: CaseManifest, sources: dict
) -> tuple[Path, str | None]:
    """Return (reference wav, ffmpeg audio map string) for the case's source.

    Uses the persisted registration selection; legacy single-audio records
    without one fall back to 0:a:0; multi-audio records without a persisted
    selection fail closed. A cached ``reference.wav`` is reused only when
    ``preprocess.json`` records the current audio map string and source media
    fingerprint **and** its recorded ``reference_sha256`` equals the actual
    sha256 of the WAV bytes on disk; stale, missing, corrupt (tampered,
    replaced, stubbed), or byte-hash-less metadata forces re-extraction, so a
    re-registration with a different ``--audio`` never reuses old audio and a
    swapped WAV is never trusted on JSON metadata alone.
    """
    s = sources["sources"].get(case.source_id)
    if s is None:
        raise StreamSelectionError(
            f"source {case.source_id} no longer registered; re-register before running"
        )
    mp = s.get("media_path")
    if not isinstance(mp, str) or not mp:
        raise StreamSelectionError(
            f"source {case.source_id} registry record has no media_path; "
            "re-register the source"
        )
    media = Path(mp)
    sel = s.get("audio_selected")
    if sel is not None:
        audio_stream = f"0:a:{sel['sidx']}"
    else:
        n_audio = len(_typed_streams(s.get("streams", []), "audio"))
        if n_audio > 1:
            raise StreamSelectionError(
                f"source {case.source_id} has {n_audio} audio streams but no "
                "persisted audio_selected; re-register with --audio so the "
                "intended track is decoded"
            )
        if n_audio == 0:
            raise StreamSelectionError(
                f"source {case.source_id} media has no audio stream; register "
                "audio-bearing reference media"
            )
        audio_stream = None
    scratch_case = paths["scratch"] / case.case_id
    ref_wav = scratch_case / "reference.wav"
    preprocess_path = scratch_case / "preprocess.json"
    media_sha256 = sha256_file(media)
    if ref_wav.exists():
        try:
            cached = read_json(preprocess_path)
        except (OSError, ValueError):
            cached = None
        if (
            cached is not None
            and cached.get("audio_stream") == audio_stream
            and cached.get("media_sha256") == media_sha256
            and cached.get("reference_sha256") == sha256_file(ref_wav)
        ):
            return ref_wav, audio_stream
    t0 = time.monotonic()
    extract_audio(media, ref_wav, audio_stream=audio_stream)
    write_json(
        preprocess_path,
        {
            "audio_extraction_seconds": time.monotonic() - t0,
            "audio_stream": audio_stream,
            "media_sha256": media_sha256,
            "case_id": case.case_id,
            "reference_sha256": sha256_file(ref_wav),
        },
    )
    return ref_wav, audio_stream


def _all_candidate_ids() -> list[str]:
    """Candidates executed by `--all`: default arms only.

    Oracle-assisted diagnostic arms (b1-pxo-*) are excluded from `--all` and
    must be selected explicitly with `--candidate`; b1-va keeps its special
    base-proposal handling.
    """
    return [cid for cid in CANDIDATES if cid in DEFAULT_CANDIDATE_IDS]


def cmd_run(args, paths) -> int:
    sources = _load_sources(paths["sources"])
    for case_id in args.case:
        refused = _refuse_unsafe_id(case_id, "case id")
        if refused is not None:
            return refused
    candidates = _all_candidate_ids() if args.all else args.candidate
    tools = ToolConfig.detect()
    rc = 0
    for case_id in args.case:
        case_path = _lookup_case_path(paths, case_id)
        if case_path is None:
            print(f"case not prepared: {case_id}", file=sys.stderr)
            rc = 2
            continue
        case = _load_case(case_path)
        problems = _verify_sources(paths, case.source_id, sources, case)
        if problems:
            for p in problems:
                print(f"SOURCE CHECK FAILED ({case_id}): {p}", file=sys.stderr)
            return 3
        source = sources["sources"][case.source_id]
        gold_sha = _gold_content_sha256(paths, case)
        corrupted_path = _resolve_generated(paths, case)
        corrupted = Track.load(corrupted_path, case.fmt)
        corrupted_times = corrupted.time_map()
        cue_text = {c.cue_id: c.text for c in corrupted.cues}
        ref_wav = None
        audio_stream = None
        try:
            ref_wav, audio_stream = _get_reference_audio(paths, case, sources)
        except StreamSelectionError as exc:
            print(f"REFUSED ({case_id}): {exc}", file=sys.stderr)
            return 4
        for cand in candidates:
            if cand == "b1-va":
                continue
            scratch_dir = paths["results"] / case_id / cand
            # GOLD-LEAKAGE BOUNDARY: gold cue labels are reference evaluation
            # data; only oracle-assisted diagnostic arms receive the path.
            # Default candidates (including b1-px-fg/b1-px-fp) get None here
            # and adapters.py independently refuses it for default ids.
            cand_gold_path = None
            if cand in ORACLE_DIAGNOSTIC_IDS and case.gold_classification_path:
                cand_gold_path = _resolve_under_root(
                    paths, case.gold_classification_path
                )
            try:
                proposal, meta = run_candidate(
                    cand,
                    case,
                    corrupted_times,
                    corrupted_path,
                    ref_wav,
                    scratch_dir,
                    tools,
                    tol_us=args.tol_good_us,
                    gold_classification_path=cand_gold_path,
                )
            except ValueError as exc:
                print(f"REFUSED ({case_id}/{cand}): {exc}", file=sys.stderr)
                return 2
            proposal_path = scratch_dir / "proposal.json"
            write_json(proposal_path, proposal.to_json())
            proposal_sha256 = sha256_file(proposal_path)
            write_json(
                scratch_dir / "run.json",
                {
                    "schema_version": 2,
                    "run_id": f"{case_id}-{cand}-{int(time.time())}",
                    "case_id": case_id,
                    "candidate_id": cand,
                    "status": proposal.mapping_status,
                    "reason": proposal.notes,
                    "input_sha256": case.generated_subtitle_sha256,
                    # Versioned identity of everything this run consumed: case
                    # generation (incl. ground truth + gold/oracle material) +
                    # selected source audio + subtitle input + rights +
                    # candidate + tool probes. score/b1-va recompute and
                    # require equality.
                    "input_fingerprint": compute_input_fingerprint(
                        case, source, cand, meta.get("tool_versions", {}), gold_sha
                    ),
                    "proposal_sha256": proposal_sha256,
                    "tool_versions": meta.get("tool_versions", {}),
                    "preprocessing_seconds": meta.get("preprocessing_seconds", 0.0),
                    "candidate_seconds": meta.get("candidate_seconds", 0.0),
                },
            )
            print(f"run {case_id}/{cand}: {proposal.mapping_status}")
        if "b1-va" in candidates or args.all:
            base = args.base_candidate
            base_dir = paths["results"] / case_id / base
            base_proposal_path = base_dir / "proposal.json"
            if not base_proposal_path.exists():
                print(
                    f"b1-va needs base proposal {base} first (run it)", file=sys.stderr
                )
                rc = 2
                continue
            base_problem = _provenance_problem(base_dir, base, case, source, gold_sha)
            if base_problem:
                print(
                    f"REFUSED ({case_id}/b1-va): base proposal unusable — {base_problem}",
                    file=sys.stderr,
                )
                rc = 6
                continue
            base_run_path = base_dir / "run.json"
            base_run = read_json(base_run_path)
            base_proposal = ProposalRecord(**read_json(base_proposal_path))
            # Transcription (BENCH_ASR_*) and semantic verification
            # (BENCH_SEM_VERIFY_*) are independently configured boundaries;
            # only production getters are wired here, never test mocks.
            transcriber = get_transcriber()
            verifier = get_semantic_verifier()
            # Resolve the two identities the validator routes on: the spoken
            # audio language (CLI hint, falling back to the persisted
            # audio_selected ffprobe tag) and the target subtitle language (CLI
            # hint, falling back to the registry-captured per-track language).
            audio_hint = args.language
            if normalize_language(audio_hint) is None:
                persisted_audio = (source.get("audio_selected") or {}).get("language")
                if persisted_audio:
                    audio_hint = persisted_audio
            subtitle_hint = args.subtitle_language
            if normalize_language(subtitle_hint) is None:
                persisted_subtitle = (source.get("subtitle_languages") or {}).get(
                    case.track_id
                )
                if persisted_subtitle:
                    subtitle_hint = persisted_subtitle
            acc = validate_proposal(
                case,
                base_proposal,
                base,
                corrupted_times,
                cue_text,
                ref_wav,
                paths["results"] / case_id / "b1-va",
                transcriber,
                audio_hint,
                args.seed,
                verifier=verifier,
                subtitle_language=subtitle_hint,
            )
            va_dir = paths["results"] / case_id / "b1-va"
            write_json(va_dir / "acceptance.json", acc.to_json())
            # P1-1: bind acceptance.json to this run. The acceptance file is
            # written FIRST, then its hash is recorded here so cmd_score can
            # require the on-disk acceptance bytes to match run.json
            # (acceptance_sha256) and to validate its identity fields; a
            # hand-written/planted acceptance can no longer drive scoring.
            acceptance_sha256 = sha256_file(va_dir / "acceptance.json")
            va_proposal_path = va_dir / "proposal.json"
            write_json(va_proposal_path, base_proposal.to_json())
            mp = source.get("media_path")
            if not isinstance(mp, str) or not mp:
                print(
                    f"REFUSED: source {case.source_id} registry record has no "
                    "media_path; re-register the source",
                    file=sys.stderr,
                )
                return 2
            source_media = Path(mp)
            write_json(
                va_dir / "run.json",
                {
                    "schema_version": 2,
                    "run_id": f"{case_id}-b1-va-{int(time.time())}",
                    "case_id": case_id,
                    "candidate_id": "b1-va",
                    "status": acc.status,
                    "reason": acc.notes,
                    "asr_seconds": acc.asr_seconds,
                    "asr_calls": acc.asr_calls,
                    # F07: transcription and semantic verification are separate
                    # cost boundaries; asr_seconds never includes verifier time.
                    "semantic_seconds": acc.semantic_seconds,
                    "verifier_calls": acc.verifier_calls,
                    "inference_seconds_total": acc.asr_seconds + acc.semantic_seconds,
                    "input_sha256": case.generated_subtitle_sha256,
                    # b1-va commits to the same case-generation identity as its
                    # base arm (base validity is verified before validating).
                    "input_fingerprint": compute_input_fingerprint(
                        case, source, "b1-va", {}, gold_sha
                    ),
                    "proposal_sha256": sha256_file(va_proposal_path),
                    "acceptance_sha256": acceptance_sha256,
                    "validated_candidate_id": base,
                    "base_proposal_sha256": sha256_file(base_proposal_path),
                    # F01: bind the acceptance to the EXACT validated base run
                    # (id + record bytes + generation fingerprint), not just the
                    # base arm name, and to the validation input configuration
                    # (seed, resolved identities, ASR/verifier models; no
                    # credentials). score/report re-verify these at read time,
                    # so a base re-run with new settings/results invalidates
                    # the downstream acceptance even without rerunning the
                    # validator.
                    "base_run_id": base_run.get("run_id"),
                    "base_run_sha256": sha256_file(base_run_path),
                    "base_input_fingerprint": base_run.get("input_fingerprint"),
                    "validation_config": {
                        "seed": args.seed,
                        "language": audio_hint,
                        "subtitle_language": subtitle_hint,
                        "asr_model": getattr(transcriber, "model", None)
                        if transcriber
                        else None,
                        "verifier_model": getattr(verifier, "model", None)
                        if verifier
                        else None,
                        "pad_us": PAD_US,
                        "min_match_ratio": MIN_MATCH_RATIO,
                        "timing_tolerance_us": TIMING_TOLERANCE_US,
                    },
                    # Provenance: which source audio stream the decoded
                    # reference.wav (validated windows' sole input) came from.
                    "audio_stream": audio_stream,
                    "media_sha256": sha256_file(source_media),
                },
            )
            print(f"run {case_id}/b1-va: {acc.status} (base {base})")
    return rc


def cmd_score(args, paths) -> int:
    tol = Tolerances(
        good_us=args.tol_good_us,
        severe_us=args.tol_severe_us,
        break_match_us=args.tol_break_us,
    )
    for case_id in args.case:
        refused = _refuse_unsafe_id(case_id, "case id")
        if refused is not None:
            return refused
    rc = 0
    for case_id in args.case:
        case_path = _lookup_case_path(paths, case_id)
        if case_path is None:
            print(f"case not prepared: {case_id}", file=sys.stderr)
            return 2
        case = _load_case(case_path)
        sources = _load_sources(paths["sources"])
        problems = _verify_sources(paths, case.source_id, sources, case)
        if problems:
            for p in problems:
                print(f"SOURCE CHECK FAILED ({case_id}): {p}", file=sys.stderr)
            return 3
        source = sources["sources"][case.source_id]
        gold_sha = _gold_content_sha256(paths, case)
        corrupted = Track.load(_resolve_generated(paths, case), case.fmt)
        corrupted_times = corrupted.time_map()
        candidates = list(CANDIDATES) if args.all else args.candidate
        for cand in candidates:
            d = paths["results"] / case_id / cand
            prop_path = d / "proposal.json"
            if not prop_path.exists():
                # A proposal.json that has been deleted/moved away must never
                # leave a prior generation's score.json behind (the report
                # binding is a backstop, not the fix). Delete it and treat the
                # arm as a provenance refusal (rc 6) ONLY when a score.json
                # existed to delete: a plain never-run arm (no proposal, no
                # score) keeps skipping silently so a normal ``--all`` over an
                # untouched matrix stays rc 0.
                if (d / "score.json").exists():
                    _delete_stale_score(d, f"{case_id}/{cand}", "proposal.json missing")
                    rc = 6
                continue
            # Provenance gate: a persisted proposal is scoreable only when its
            # run.json binds it to THIS case generation (fingerprint) and its
            # bytes still match the recorded proposal_sha256. Legacy/unverified,
            # stale, and tampered artifacts are refused with rc 6 and any
            # pre-existing score.json for that candidate is deleted so a stale
            # number cannot leak into reports.
            provenance = _provenance_problem(d, cand, case, source, gold_sha)
            if provenance:
                print(f"REFUSED ({case_id}/{cand}): {provenance}", file=sys.stderr)
                _delete_stale_score(
                    d, f"{case_id}/{cand}", "not recomputed from verified data"
                )
                rc = 6
                continue
            # The provenance gate just verified run.json binds to THIS case
            # generation, so recompute the verified current fingerprint (the same
            # tool_versions run.json recorded) and embed it in the score row so
            # the report can bind the number back to a matching run (P1-2).
            run = read_json(d / "run.json")
            current_fp = compute_input_fingerprint(
                case, source, cand, run.get("tool_versions", {}), gold_sha
            )
            proposal = ProposalRecord(**read_json(prop_path))
            proposal.candidate_id = cand
            acceptance = None
            if cand == "b1-va":
                # P1-1: acceptance is trusted ONLY for b1-va, and only when it
                # is bound to the verified run.json (recorded hash + identity).
                from .manifests import AcceptanceRecord

                acc_problem = _acceptance_binding_problem(
                    d, run, case, source, paths, gold_sha
                )
                if acc_problem:
                    print(
                        f"REFUSED ({case_id}/{cand}): {acc_problem}",
                        file=sys.stderr,
                    )
                    _delete_stale_score(
                        d, f"{case_id}/{cand}", "acceptance.json not bound to run.json"
                    )
                    rc = 6
                    continue
                acceptance = AcceptanceRecord(**read_json(d / "acceptance.json"))
            # Non-b1-va arms never accept: any acceptance.json present in their
            # directory is ignored (treated as absent), so a planted file cannot
            # steer proposal-only final-timeline scoring (P1-1).
            if (
                proposal.mapping_status not in ("noop", "1:1-order-preserving")
                and cand != "b1-va"
            ):
                # P1-2: a non-scoreable arm must not leave a prior generation's
                # score.json behind; delete it so the skip is never silent.
                _delete_stale_score(
                    d,
                    f"{case_id}/{cand}",
                    f"non-scoreable mapping_status {proposal.mapping_status}",
                )
                continue
            score = score_case(case, proposal, corrupted_times, acceptance, tol)
            score["candidate_id"] = cand
            score["input_fingerprint"] = current_fp
            # The score row also binds the exact proposal bytes it was computed
            # from (verified against run.json), so a relabeled proposal cannot
            # keep an old score row rendering in reports.
            score["proposal_sha256"] = run.get("proposal_sha256")
            if cand == "b1-va":
                # F01: the score row records the EXACT base run/proposal the
                # acceptance validated and the validation input configuration,
                # so it can never be mislabeled as the same experiment under a
                # different base, seed, language pair, or model.
                score["validated_base"] = {
                    "candidate_id": run.get("validated_candidate_id"),
                    "run_id": run.get("base_run_id"),
                    "input_fingerprint": run.get("base_input_fingerprint"),
                    "proposal_sha256": run.get("base_proposal_sha256"),
                    "run_sha256": run.get("base_run_sha256"),
                }
                score["validation_config"] = run.get("validation_config")
            write_json(d / "score.json", score)
            print(
                f"scored {case_id}/{cand}: median final onset err {score['timing_errors_final_us']['median_abs_us']} us"
            )
    return rc


def _case_evidence_missing(paths: dict[str, Path], case_id: str) -> bool:
    """True when present-day case manifest + registered source cannot be established."""
    case_path = _lookup_case_path(paths, case_id)
    if case_path is None:
        return True
    try:
        case = _load_case(case_path)
    except (OSError, ValueError):
        return True
    sources = _load_sources(paths["sources"])
    return sources["sources"].get(case.source_id) is None


def cmd_report(args, paths) -> int:
    for case_id in args.case:
        refused = _refuse_unsafe_id(case_id, "case id")
        if refused is not None:
            return refused
    case_ids = args.case or sorted(
        p.name.split(".")[0] for p in _iter_case_paths(paths)
    )
    sources = _load_sources(paths["sources"])
    current_fingerprints: dict[tuple, str] = {}
    acceptance_stale: list[tuple[str, str]] = []
    proposal_stale: list[tuple[str, str]] = []
    artifact_problems: list[tuple[str, str]] = []
    admitted_pairs: set[tuple] = set()
    runs, scores, versions = [], [], {}
    for case_id in case_ids:
        # Generation binding: recompute each arm's CURRENT fingerprint from the
        # live case manifest + registry source + the run's recorded tool_versions
        # + the live gold-classification content so a self-consistent run/score
        # pair from an OLDER case generation (its fingerprint is internally
        # consistent but predates a re-prepare, a ground-truth edit, or a gold
        # file change) can be dropped, not just an unbound one. When the
        # case/source cannot be loaded, current evidence is MISSING (F05): the
        # case's rows are rendered ONLY in the labeled unverified-historical
        # section, never in the comparative table.
        case_path = _lookup_case_path(paths, case_id)
        case = None
        if case_path is not None:
            try:
                case = _load_case(case_path)
            except (OSError, ValueError):
                case = None
        source = sources["sources"].get(case.source_id) if case is not None else None
        gold_sha = _gold_content_sha256(paths, case) if case is not None else None
        evidence_missing = case is None or source is None
        for d in (
            (paths["results"] / case_id).iterdir()
            if (paths["results"] / case_id).exists()
            else []
        ):
            # Per-directory admission: a run/score pair is admitted ONLY when
            # every read-time integrity check passes. Any exclusion skips the
            # directory's score.json too, so no obsolete number can render
            # comparably while its run record is refused (D1/D2 closures).
            excluded = False
            admitted_pair = None
            if (d / "run.json").exists():
                try:
                    run = read_json(d / "run.json")
                except (OSError, ValueError) as exc:
                    artifact_problems.append(
                        (case_id, f"run.json in {d.name} is unreadable ({exc})")
                    )
                    excluded = True
                    run = None
                if run is not None and not isinstance(run, dict):
                    artifact_problems.append(
                        (
                            case_id,
                            (
                                f"run.json in {d.name} is a JSON "
                                f"{type(run).__name__}, not an object"
                            ),
                        )
                    )
                    excluded = True
                    run = None
                if run is not None:
                    cand = run.get("candidate_id")
                    # F01 read-time binding at report: a b1-va run is bound
                    # UNCONDITIONALLY when current evidence exists — including
                    # "acceptance.json missing", which is itself a refusal.
                    if cand == "b1-va" and not evidence_missing:
                        acc_problem = _acceptance_binding_problem(
                            d, run, case, source, paths, gold_sha
                        )
                        if acc_problem:
                            acceptance_stale.append((case_id, acc_problem))
                            excluded = True
                    # Report-time proposal byte check (mirrors _provenance_problem
                    # at score): run.proposal_sha256 must match proposal.json
                    # bytes on disk, so a relabeled proposal cannot keep its old
                    # score row rendering as a current comparative number. A
                    # schema-3 run that records NO proposal hash is itself an
                    # integrity failure (round-2 P1: dropping the key must not
                    # skip the byte check).
                    if not excluded:
                        recorded_proposal = run.get("proposal_sha256")
                        if not recorded_proposal:
                            proposal_stale.append(
                                (
                                    case_id,
                                    (
                                        f"{cand}: run.json records no "
                                        "proposal_sha256; proposal bytes are "
                                        "unbound (schema-3 runs must record it)"
                                    ),
                                )
                            )
                            excluded = True
                        elif not (d / "proposal.json").is_file():
                            proposal_stale.append(
                                (
                                    case_id,
                                    (
                                        f"{cand}: run.json claims a proposal "
                                        "but proposal.json is missing"
                                    ),
                                )
                            )
                            excluded = True
                        else:
                            actual_proposal = sha256_file(d / "proposal.json")
                            if actual_proposal != recorded_proposal:
                                proposal_stale.append(
                                    (
                                        case_id,
                                        (
                                            f"{cand}: proposal.json bytes "
                                            f"{str(actual_proposal)[:16]}… != run.json "
                                            f"proposal_sha256 "
                                            f"{str(recorded_proposal)[:16]}… "
                                            "(tampered or replaced after scoring)"
                                        ),
                                    )
                                )
                                excluded = True
                    if not excluded:
                        pair_key = (run.get("case_id"), cand)
                        if pair_key in admitted_pairs:
                            # Round-3 R3-P1: only ONE admitted run/score pair
                            # per case+candidate. A whole copied triple (run +
                            # proposal + score) in a second directory must not
                            # duplicate the comparative row.
                            artifact_problems.append(
                                (
                                    case_id,
                                    (
                                        f"{cand}: duplicate candidate directory "
                                        f"{d.name} (case+candidate pair already "
                                        "admitted from another directory)"
                                    ),
                                )
                            )
                            excluded = True
                    if not excluded:
                        admitted_pairs.add(pair_key)
                        runs.append(run)
                        admitted_pair = (
                            run.get("case_id"),
                            cand,
                            run.get("input_fingerprint"),
                            run.get("proposal_sha256"),
                        )
                        versions.update(run.get("tool_versions", {}))
                        if case is not None and source is not None and cand:
                            current_fingerprints[(run.get("case_id"), cand)] = (
                                compute_input_fingerprint(
                                    case,
                                    source,
                                    cand,
                                    run.get("tool_versions", {}),
                                    gold_sha,
                                )
                            )
            if not excluded and (d / "score.json").exists():
                try:
                    sc = read_json(d / "score.json")
                except (OSError, ValueError) as exc:
                    artifact_problems.append(
                        (case_id, f"score.json in {d.name} is unreadable ({exc})")
                    )
                    sc = None
                if sc is not None and not isinstance(sc, dict):
                    artifact_problems.append(
                        (
                            case_id,
                            (
                                f"score.json in {d.name} is a JSON "
                                f"{type(sc).__name__}, not an object"
                            ),
                        )
                    )
                    sc = None
                if sc is not None:
                    # Round-3 R3-P1: a score.json only renders through the
                    # directory that produced it. A copied/planted score.json in
                    # a directory with no admitted run.json — or whose identity
                    # fields (case, candidate, fingerprint, proposal hash)
                    # differ from the directory's own run record — is refused,
                    # so a genuine pair cannot be piggybacked into an extra
                    # comparative row.
                    score_pair = (
                        sc.get("case_id"),
                        sc.get("candidate_id"),
                        sc.get("input_fingerprint"),
                        sc.get("proposal_sha256"),
                    )
                    if admitted_pair is None:
                        artifact_problems.append(
                            (
                                case_id,
                                (
                                    f"score.json in {d.name} has no admitted "
                                    "run.json pairing in the same directory"
                                ),
                            )
                        )
                    elif score_pair != admitted_pair:
                        proposal_stale.append(
                            (
                                case_id,
                                (
                                    f"{sc.get('candidate_id')}: score.json "
                                    "fields do not pair with the directory's "
                                    "run.json (identity/fingerprint/proposal "
                                    "hash differ)"
                                ),
                            )
                        )
                    else:
                        scores.append(sc)
    unverified_cases = [cid for cid in case_ids if _case_evidence_missing(paths, cid)]
    text = build_report(
        list(case_ids),
        runs,
        scores,
        versions,
        current_fingerprints,
        acceptance_stale,
        unverified_cases,
        proposal_stale,
        artifact_problems,
    )
    out = Path(args.out) if args.out else paths["results"] / "report.md"
    try:
        write_report(out, text)
    except RuntimeError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 5
    print(f"report written: {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bench",
        description=f"SubHero benchmark harness v{__version__} (B0+B1, offline, read-only sources)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help=(
            "benchmarks root directory; must be outside the repository, the "
            "canonical benchmarks root, or inside a Git-ignored area (a fresh "
            "in-repo root is refused so private manifests/scratch/results never "
            "become committable)"
        ),
    )
    parser.add_argument(
        "--forbidden-root",
        type=Path,
        action="append",
        default=[],
        help="path trees never used as scratch (e.g. Plex-watched libraries)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("source", help="reference media registry")
    ssub = p.add_subparsers(dest="subcommand", required=True)
    pa = ssub.add_parser("add")
    pa.add_argument("--path", required=True)
    pa.add_argument("--source-id", required=True)
    pa.add_argument(
        "--subtitle",
        action="append",
        help="track_id=sidecar:<file> or track_id=mkv:sidx:<n>|mkv:index:<n>|mkv:lang:<code> "
        "(sidx = ffmpeg 0:s:n subtitle-relative index; index = ffprobe global index; "
        "lang = exact unique ffprobe language tag; normalized to mkv:sidx:<n> at registration)",
    )
    pa.add_argument(
        "--subtitle-language",
        action="append",
        default=[],
        help="track_id=<lang> target subtitle language hint recorded for the run's "
        "identity routing (MKV subtitle tracks auto-capture their ffprobe language "
        "tag; sidecar tracks have no embedded tag, so declare the hint here)",
    )
    pa.add_argument(
        "--audio",
        help="audio stream spec: index:<n> (ffprobe global index), sidx:<n> "
        "(ffmpeg 0:a:n map index), or lang:<code> (exact unique ffprobe language "
        "tag); required when the media has more than one audio stream",
    )
    pa.add_argument(
        "--gold",
        action="append",
        help="track_id=path to gold classification JSON (cue_id -> speech_like|non_speech)",
    )
    pa.add_argument(
        "--rights",
        default="private-local",
        choices=("private-local", SYNTHETIC_RIGHTS),
        help="rights claim: private-local (real episodes) or "
        f"{SYNTHETIC_RIGHTS} (must point inside benchmarks/fixtures/)",
    )
    pa.add_argument("--notes", default="")
    pa.set_defaults(func=cmd_source_add)
    pl = ssub.add_parser("list")
    pl.set_defaults(func=cmd_source_list)
    pi = ssub.add_parser("inspect")
    pi.add_argument("--source-id", required=True)
    pi.set_defaults(func=cmd_source_inspect)

    p = sub.add_parser("case", help="benchmark cases")
    ssub = p.add_subparsers(dest="subcommand", required=True)
    pc = ssub.add_parser("prepare")
    pc.add_argument("--source-id", required=True)
    pc.add_argument("--track-id", required=True)
    pc.add_argument(
        "--scenario", required=True, choices=("S00", "S01", "S02", "S03", "S04", "S06")
    )
    pc.add_argument("--seed", type=int, required=True)
    pc.add_argument("--case-id")
    pc.add_argument("--notes", default="")
    pc.set_defaults(func=cmd_case_prepare)
    pl = ssub.add_parser("list")
    pl.set_defaults(func=cmd_case_list)

    p = sub.add_parser(
        "run",
        help=(
            "run candidate adapters (exit 0 ok, 2 unsafe id/missing case, 3 source "
            "mutation, 4 audio-selection refusal, 6 stale base proposal for b1-va: "
            "re-run the base candidate)"
        ),
    )
    p.add_argument("--case", action="append", required=True)
    p.add_argument("--candidate", action="append", default=[], choices=list(CANDIDATES))
    p.add_argument("--all", action="store_true")
    p.add_argument("--base-candidate", default="b1-px-fg")
    p.add_argument("--language", default="und")
    p.add_argument(
        "--subtitle-language",
        default="und",
        help="target subtitle language hint for the run's identity routing; when it "
        "is 'und' the registry-captured per-track language (MKV ffprobe tag / "
        "sidecar --subtitle-language hint) is used. A verified same-language pair "
        "is required for lexical reject evidence",
    )
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--tol-good-us", type=int, default=50_000)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser(
        "score",
        help=(
            "score proposals vs injected ground truth (exit 0 ok, 2 unsafe id/"
            "missing case, 3 source mutation, 6 STALE/UNVERIFIED candidate "
            "results: run.json provenance missing, legacy, bound to a different "
            "case generation/selected audio, or proposal.json bytes tampered — "
            "the candidate must be re-run; its stale score.json is deleted)"
        ),
    )
    p.add_argument("--case", action="append", required=True)
    p.add_argument("--candidate", action="append", default=[], choices=list(CANDIDATES))
    p.add_argument("--all", action="store_true")
    p.add_argument("--tol-good-us", type=int, default=50_000)
    p.add_argument("--tol-severe-us", type=int, default=250_000)
    p.add_argument("--tol-break-us", type=int, default=500_000)
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("report", help="human-readable comparison report")
    p.add_argument("--case", action="append", default=[])
    p.add_argument("--out")
    p.set_defaults(func=cmd_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    refused_root = _refuse_unsafe_root(root, REPO_ROOT, DEFAULT_ROOT)
    if refused_root is not None:
        return refused_root
    paths = _paths(root)
    scratch_roots = [
        paths["scratch"],
        paths["results"],
        paths["cases"],
        paths["private_cases"],
    ]
    sources = _load_sources(paths["sources"])
    source_roots = [
        Path(s["media_path"]).resolve().parent
        for s in sources["sources"].values()
        if isinstance(s.get("media_path"), str) and s.get("media_path")
    ]
    for extra in args.forbidden_root:
        from .paths import add_forbidden_root

        add_forbidden_root(Path(extra))
    configure(scratch_roots, source_roots, args.forbidden_root)
    for p in (
        paths["cases"],
        paths["private_cases"],
        paths["scratch"],
        paths["results"],
    ):
        p.mkdir(parents=True, exist_ok=True)
    return args.func(args, paths)


if __name__ == "__main__":
    raise SystemExit(main())
