"""Benchmark CLI: source registry, case preparation, candidate runs, scoring, reports.

Run `python -m bench [--help]` from the `benchmarks/` directory, or
`python benchmarks/run_bench.py --help` from the repository root.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import __version__
from .adapters import CANDIDATES, ToolConfig, run_candidate
from .asr import get_transcriber
from .corrupt import prepare_case
from .manifests import CaseManifest, ProposalRecord, read_json, write_json
from .media import extract_audio, extract_subtitle_stream, ffprobe_streams, sha256_file
from .paths import add_source_root, configure
from .reporting import build_report, write_report
from .scoring import Tolerances, score_case
from .subtitles import Track
from .validator import validate_proposal

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


def _private_path_policy(
    candidate: Path, benchmarks_root: Path, repo_root: Path
) -> str | None:
    """Return a refusal reason for in-repo paths outside the private/fixtures homes.

    Paths outside the repository (e.g. read-only mounts) are allowed. Inside the repo,
    registered media, sidecar subtitles, and gold annotations must live under
    ``benchmarks/private/`` (real reference episodes) or ``benchmarks/fixtures/``
    (redistributable synthetic fixtures).
    """
    resolved = Path(candidate).resolve()
    if not _under_root(resolved, repo_root):
        return None
    for home in (benchmarks_root / "private", benchmarks_root / "fixtures"):
        if _under_root(resolved, home):
            return None
    return (
        f"in-repo path {resolved} is outside benchmarks/private/ and benchmarks/fixtures/; "
        f"register private data under {(benchmarks_root / 'private').resolve()} "
        "or outside the repository (read-only mounts are allowed)"
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
    media = Path(s["media_path"])
    if not media.is_file():
        problems.append("registered media file missing")
    elif sha256_file(media) != s["media_sha256"]:
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


def cmd_source_add(args, paths) -> int:
    media = Path(args.path).resolve()
    if not media.exists():
        print(f"NOT FOUND: {media}", file=sys.stderr)
        return 2
    policy_targets: list[Path] = [media]
    for spec in args.subtitle or []:
        _, _, target = spec.partition("=")
        if target.startswith("sidecar:"):
            policy_targets.append(
                _resolve_under_root(paths, target.removeprefix("sidecar:"))
            )
    for gold_spec in args.gold or []:
        _, _, target = gold_spec.partition("=")
        policy_targets.append(_resolve_under_root(paths, target))
    for target in policy_targets:
        reason = _private_path_policy(target, paths["root"], REPO_ROOT)
        if reason is not None:
            print(f"REFUSED (private data policy): {reason}", file=sys.stderr)
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
            subtitles[track_id] = target
            hashes[track_id] = sha256_file(Path(target.removeprefix("sidecar:")))
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
    duration = None
    fmt = streams.get("format", {})
    if fmt.get("duration"):
        duration = int(float(fmt["duration"]) * 1_000_000)
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
        "gold_classification": dict(g.split("=", 1) for g in args.gold)
        if args.gold
        else {},
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
            f"{sid}\tmedia={s['media_path']}\tsha256={s['media_sha256'][:16]}…\ttracks={list(s['subtitle_specs'])}"
        )
    return 0


def cmd_source_inspect(args, paths) -> int:
    sources = _load_sources(paths["sources"])
    s = sources["sources"].get(args.source_id)
    if not s:
        print(f"unknown source {args.source_id}", file=sys.stderr)
        return 2
    import json

    print(json.dumps(s, indent=2, ensure_ascii=False))
    return 0


def cmd_case_prepare(args, paths) -> int:
    sources = _load_sources(paths["sources"])
    s = sources["sources"].get(args.source_id)
    if not s:
        print(f"unknown source {args.source_id}", file=sys.stderr)
        return 2
    spec = s["subtitle_specs"].get(args.track_id)
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
        extract_subtitle_stream(Path(s["media_path"]), int(value), src_ass)
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
    fingerprint; stale, missing, or corrupt metadata forces re-extraction, so
    a re-registration with a different ``--audio`` never reuses old audio.
    """
    s = sources["sources"][case.source_id]
    media = Path(s["media_path"])
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
        },
    )
    return ref_wav, audio_stream


def cmd_run(args, paths) -> int:
    sources = _load_sources(paths["sources"])
    candidates = list(CANDIDATES) if args.all else args.candidate
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
            proposal, meta = run_candidate(
                cand,
                case,
                corrupted_times,
                corrupted_path,
                ref_wav,
                scratch_dir,
                tools,
                tol_us=args.tol_good_us,
                gold_classification_path=(
                    _resolve_under_root(paths, case.gold_classification_path)
                    if case.gold_classification_path
                    else None
                ),
            )
            write_json(scratch_dir / "proposal.json", proposal.to_json())
            write_json(
                scratch_dir / "run.json",
                {
                    "schema_version": 1,
                    "run_id": f"{case_id}-{cand}-{int(time.time())}",
                    "case_id": case_id,
                    "candidate_id": cand,
                    "status": proposal.mapping_status,
                    "reason": proposal.notes,
                    "input_sha256": case.generated_subtitle_sha256,
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
            base_proposal = ProposalRecord(**read_json(base_proposal_path))
            transcriber = get_transcriber()
            acc = validate_proposal(
                case,
                base_proposal,
                base,
                corrupted_times,
                cue_text,
                ref_wav,
                paths["results"] / case_id / "b1-va",
                transcriber,
                args.language,
                args.seed,
                audio_stream=audio_stream,
            )
            va_dir = paths["results"] / case_id / "b1-va"
            write_json(va_dir / "acceptance.json", acc.to_json())
            write_json(va_dir / "proposal.json", base_proposal.to_json())
            write_json(
                va_dir / "run.json",
                {
                    "schema_version": 1,
                    "run_id": f"{case_id}-b1-va-{int(time.time())}",
                    "case_id": case_id,
                    "candidate_id": "b1-va",
                    "status": acc.status,
                    "reason": acc.notes,
                    "asr_seconds": acc.asr_seconds,
                    "asr_calls": acc.asr_calls,
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
        corrupted = Track.load(_resolve_generated(paths, case), case.fmt)
        corrupted_times = corrupted.time_map()
        candidates = list(CANDIDATES) if args.all else args.candidate
        for cand in candidates:
            d = paths["results"] / case_id / cand
            prop_path = d / "proposal.json"
            if not prop_path.exists():
                continue
            proposal = ProposalRecord(**read_json(prop_path))
            proposal.candidate_id = cand
            acceptance = None
            acc_path = d / "acceptance.json"
            if acc_path.exists():
                from .manifests import AcceptanceRecord

                acceptance = AcceptanceRecord(**read_json(acc_path))
            if (
                proposal.mapping_status not in ("noop", "1:1-order-preserving")
                and cand != "b1-va"
            ):
                continue
            score = score_case(case, proposal, corrupted_times, acceptance, tol)
            score["candidate_id"] = cand
            write_json(d / "score.json", score)
            print(
                f"scored {case_id}/{cand}: median final onset err {score['timing_errors_final_us']['median_abs_us']} us"
            )
    return 0


def cmd_report(args, paths) -> int:
    case_ids = args.case or sorted(
        p.name.split(".")[0] for p in _iter_case_paths(paths)
    )
    runs, scores, versions = [], [], {}
    for case_id in case_ids:
        for d in (
            (paths["results"] / case_id).iterdir()
            if (paths["results"] / case_id).exists()
            else []
        ):
            if (d / "run.json").exists():
                runs.append(read_json(d / "run.json"))
                versions.update(read_json(d / "run.json").get("tool_versions", {}))
            if (d / "score.json").exists():
                scores.append(read_json(d / "score.json"))
    text = build_report(list(case_ids), runs, scores, versions)
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
        "--root", type=Path, default=DEFAULT_ROOT, help="benchmarks root directory"
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
    pa.add_argument("--rights", default="private-local")
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

    p = sub.add_parser("run", help="run candidate adapters")
    p.add_argument("--case", action="append", required=True)
    p.add_argument("--candidate", action="append", default=[], choices=list(CANDIDATES))
    p.add_argument("--all", action="store_true")
    p.add_argument("--base-candidate", default="b1-px-fg")
    p.add_argument("--language", default="und")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--tol-good-us", type=int, default=50_000)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("score", help="score proposals vs injected ground truth")
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
    paths = _paths(Path(args.root).resolve())
    scratch_roots = [
        paths["scratch"],
        paths["results"],
        paths["cases"],
        paths["private_cases"],
    ]
    sources = _load_sources(paths["sources"])
    source_roots = [
        Path(s["media_path"]).resolve().parent for s in sources["sources"].values()
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
