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


def _paths(root: Path) -> dict[str, Path]:
    return {
        "root": root,
        "cases": root / "cases",
        "fixtures": root / "fixtures",
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
    sources = _load_sources(paths["sources"])
    if args.source_id in sources["sources"]:
        print(f"source id already registered: {args.source_id}", file=sys.stderr)
        return 2
    streams = ffprobe_streams(media)
    subtitles: dict[str, str] = {}
    hashes: dict[str, str] = {}
    for spec in args.subtitle or []:
        track_id, _, target = spec.partition("=")
        subtitles[track_id] = target
        if target.startswith("sidecar:"):
            hashes[track_id] = sha256_file(Path(target.removeprefix("sidecar:")))
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
        "gold_classification": dict(g.split("=", 1) for g in args.gold)
        if args.gold
        else {},
        "rights_status": args.rights,
        "notes": args.notes,
    }
    _save_sources(paths["sources"], sources)
    add_source_root(media.parent)
    print(f"registered source {args.source_id} @ {media}")
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
    scratch_case = paths["scratch"] / case_id
    scratch_case.mkdir(parents=True, exist_ok=True)
    if spec.startswith("sidecar:"):
        src_ass = Path(spec.removeprefix("sidecar:"))
    elif spec.startswith("mkv:"):
        src_ass = scratch_case / f"{args.track_id}.ass"
        extract_subtitle_stream(
            Path(s["media_path"]), spec.removeprefix("mkv:"), src_ass
        )
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
    case_path = paths["cases"] / f"{case_id}.case.json"
    write_json(case_path, case.to_json())
    print(f"prepared case {case_id} -> {out} (manifest {case_path})")
    return 0


def cmd_case_list(args, paths) -> int:
    for p in sorted((paths["cases"]).glob("*.case.json")):
        d = read_json(p)
        print(
            f"{d['case_id']}\t{d['scenario']}\tseed={d['seed']}\tsource={d['source_id']}/{d['track_id']}"
        )
    return 0


def _get_reference_audio(paths: Path, case: CaseManifest, sources: dict) -> Path:
    s = sources["sources"][case.source_id]
    media = Path(s["media_path"])
    audio_stream = None
    scratch_case = paths["scratch"] / case.case_id
    ref_wav = scratch_case / "reference.wav"
    if not ref_wav.exists():
        t0 = time.monotonic()
        extract_audio(media, ref_wav, audio_stream=audio_stream)
        write_json(
            scratch_case / "preprocess.json",
            {"audio_extraction_seconds": time.monotonic() - t0},
        )
    return ref_wav


def cmd_run(args, paths) -> int:
    sources = _load_sources(paths["sources"])
    candidates = list(CANDIDATES) if args.all else args.candidate
    tools = ToolConfig.detect()
    rc = 0
    for case_id in args.case:
        case_path = paths["cases"] / f"{case_id}.case.json"
        if not case_path.exists():
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
        ref_wav = _get_reference_audio(paths, case, sources)
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
        case = _load_case(paths["cases"] / f"{case_id}.case.json")
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
        p.name.split(".")[0] for p in paths["cases"].glob("*.case.json")
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
        help="track_id=sidecar:<file> or track_id=mkv:<stream-index>",
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
    scratch_roots = [paths["scratch"], paths["results"], paths["cases"]]
    sources = _load_sources(paths["sources"])
    source_roots = [
        Path(s["media_path"]).resolve().parent for s in sources["sources"].values()
    ]
    for extra in args.forbidden_root:
        from .paths import add_forbidden_root

        add_forbidden_root(Path(extra))
    configure(scratch_roots, source_roots, args.forbidden_root)
    for p in (paths["cases"], paths["scratch"], paths["results"]):
        p.mkdir(parents=True, exist_ok=True)
    return args.func(args, paths)


if __name__ == "__main__":
    raise SystemExit(main())
