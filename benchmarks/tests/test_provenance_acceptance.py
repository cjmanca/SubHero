"""Provenance binding of b1-va acceptance + report fingerprint binding + sidecar stem alias.

Negative-control regressions reproducing the acceptance-blocking findings from the
adversarial review of the remediation range:

* P1-1 — ``acceptance.json`` was NOT provenance-bound: a hand-written
  ``success``/original-times file, a cross-case acceptance copy, and a file
  planted in a non-b1-va arm dir all influenced scoring. These now refuse (rc 6)
  or are ignored, and a genuine b1-va run's acceptance is bound to ``run.json``.
* P1-2 — a stale ``score.json`` survived a non-scoreable skip and ``score.json``
  bound nothing; reports rendered unbound rows. Score rows now embed the verified
  ``input_fingerprint`` and the report binds each row to a fingerprint-matching
  ``run.json``, dropping (and counting) unbound rows.
* P2-1 — the sidecar stem alias leaked identities across same-stem tracks; the
  alias is now stored only for a unique sidecar stem, and a collided stem yields
  the identity-unknown abstain path (never a wrong-identity lexical reject).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from bench import cli
from bench.manifests import AcceptanceRecord, ProposalRecord, read_json, write_json
from bench.media import sha256_file
from bench.subtitles import Track

FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg required")

RC_STALE = 6
ASR_ENV = (
    "BENCH_ASR_BASE_URL",
    "BENCH_ASR_MODEL",
    "BENCH_ASR_API_KEY",
    "BENCH_SEM_VERIFY_BASE_URL",
    "BENCH_SEM_VERIFY_MODEL",
    "BENCH_SEM_VERIFY_API_KEY",
)


def _ffmpeg(*args: str) -> None:
    subprocess.run(
        [FFMPEG, "-y", "-v", "error", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _build_mkv(tmp_path: Path, name: str = "episode.mkv") -> Path:
    """Two sine audio streams (440 Hz jpn / 880 Hz eng); sidecars carry subtitles."""
    media_dir = tmp_path / "media"
    media_dir.mkdir(exist_ok=True)
    out = media_dir / name
    a440 = tmp_path / f"{name}-440.wav"
    a880 = tmp_path / f"{name}-880.wav"
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2",
        "-c:a",
        "pcm_s16le",
        str(a440),
    )
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=880:duration=2",
        "-c:a",
        "pcm_s16le",
        str(a880),
    )
    _ffmpeg(
        "-i",
        str(a440),
        "-i",
        str(a880),
        "-map",
        "0:a:0",
        "-map",
        "1:a:0",
        "-c:a",
        "pcm_s16le",
        "-metadata:s:a:0",
        "language=jpn",
        "-metadata:s:a:1",
        "language=eng",
        str(out),
    )
    return out


def _cli_add(
    root: Path, media: Path, extra: tuple[str, ...], source_id: str = "MS"
) -> int:
    return cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            str(media),
            "--source-id",
            source_id,
            "--rights",
            "private-local",
            *extra,
        ]
    )


def _record(root: Path, source_id: str = "MS") -> dict:
    data = json.loads((root / "cases" / "sources.json").read_text(encoding="utf-8"))
    return data["sources"][source_id]


def _setup(tmp_path: Path, fixture_dir: Path) -> tuple[Path, Path]:
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    sidecar = tmp_path / "episode.ass"
    shutil.copy2(fixture_dir / "episode.ass", sidecar)
    assert (
        _cli_add(
            root,
            media,
            ("--audio", "lang:eng", "--subtitle", f"main=sidecar:{sidecar}"),
        )
        == 0
    )
    return root, media


def _prepare(
    root: Path, case_id: str, scenario: str, seed: int, track: str = "main"
) -> int:
    return cli.main(
        [
            "--root",
            str(root),
            "case",
            "prepare",
            "--source-id",
            "MS",
            "--track-id",
            track,
            "--scenario",
            scenario,
            "--seed",
            str(seed),
            "--case-id",
            case_id,
        ]
    )


def _run(root: Path, case_id: str, cand: str = "b1-n") -> int:
    return cli.main(
        ["--root", str(root), "run", "--case", case_id, "--candidate", cand]
    )


def _run_va(root: Path, case_id: str, base: str = "b1-n") -> int:
    return cli.main(
        [
            "--root",
            str(root),
            "run",
            "--case",
            case_id,
            "--candidate",
            "b1-va",
            "--base-candidate",
            base,
        ]
    )


def _score(root: Path, case_id: str, cand: str = "b1-n") -> int:
    return cli.main(
        ["--root", str(root), "score", "--case", case_id, "--candidate", cand]
    )


def _score_all(root: Path, case_id: str) -> int:
    return cli.main(["--root", str(root), "score", "--case", case_id, "--all"])


def _report(root: Path, case_id: str) -> int:
    return cli.main(["--root", str(root), "report", "--case", case_id])


def _report_text(root: Path) -> str:
    return (root / "results" / "report.md").read_text(encoding="utf-8")


def _cand_dir(root: Path, case_id: str, cand: str) -> Path:
    return root / "results" / case_id / cand


def _cue_text(root: Path, case_id: str) -> dict[str, str]:
    paths = cli._paths(root)
    case = cli._load_case(cli._lookup_case_path(paths, case_id))
    track = Track.load(cli._resolve_generated(paths, case), case.fmt)
    return {c.cue_id: c.text for c in track.cues}


def _mock_va(monkeypatch, cue_text: dict[str, str]):
    from bench.asr import MockTranscriber

    for var in ASR_ENV:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(cli, "get_transcriber", lambda: MockTranscriber(dict(cue_text)))
    monkeypatch.setattr(cli, "get_semantic_verifier", lambda: None)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# P1-1: b1-va acceptance is provenance-bound
# ---------------------------------------------------------------------------


def _genuine_b1va_abstain(tmp_path, fixture_dir, monkeypatch, case_id: str):
    """Prepare/run b1-n then run b1-va with a labeled mock transcriber.

    The mock forces abstain verdicts, so the genuine acceptance abstains (no
    accepts); the acceptance bytes are recorded in run.json.acceptance_sha256.
    """
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, case_id, "S01", 1) == 0
    assert _run(root, case_id) == 0
    _mock_va(monkeypatch, _cue_text(root, case_id))
    assert _run_va(root, case_id) == 0
    va_dir = _cand_dir(root, case_id, "b1-va")
    run = _load(va_dir / "run.json")
    assert run["acceptance_sha256"] == sha256_file(va_dir / "acceptance.json")
    acc = AcceptanceRecord(**read_json(va_dir / "acceptance.json"))
    assert acc.accepted_regions == []  # labeled mock never accepts
    return root


def test_genuine_b1va_flow_scores_with_bound_acceptance(
    tmp_path, fixture_dir, monkeypatch
):
    root = _genuine_b1va_abstain(tmp_path, fixture_dir, monkeypatch, "GVA")
    va_dir = _cand_dir(root, "GVA", "b1-va")
    assert _score(root, "GVA", "b1-va") == 0
    run = _load(va_dir / "run.json")
    score = _load(va_dir / "score.json")
    assert score["schema_version"] == 2
    assert score["input_fingerprint"] == run["input_fingerprint"]
    # Tampering the genuine acceptance bytes now refuses (rc 6), not rescores.
    tampered = va_dir / "acceptance.json"
    b = bytearray(tampered.read_bytes())
    b[10] ^= 0xFF
    tampered.write_bytes(bytes(b))
    assert _score(root, "GVA", "b1-va") == RC_STALE
    assert not (va_dir / "score.json").exists()


def test_hand_written_success_acceptance_over_abstain_run_is_refused(
    tmp_path, fixture_dir, monkeypatch, capsys
):
    root = _genuine_b1va_abstain(tmp_path, fixture_dir, monkeypatch, "HWVA")
    assert _score(root, "HWVA", "b1-va") == 0  # genuine abstain scores fine
    va_dir = _cand_dir(root, "HWVA", "b1-va")
    case = cli._load_case(cli._lookup_case_path(cli._paths(root), "HWVA"))
    # Reproduce the review probe: a hand-written success/original-times acceptance
    # over the genuine abstain run's b1-va directory.
    write_json(
        va_dir / "acceptance.json",
        AcceptanceRecord(
            case_id="HWVA",
            candidate_id="b1-va",
            validated_candidate_id="b1-n",
            status="success",
            accepted_regions=[{"start_us": 0, "end_us": None, "offset_us": 0}],
            rejected_regions=[],
            abstained_regions=[],
            accepted_times_us={
                cid: (int(s), int(e)) for cid, (s, e) in case.original_times_us.items()
            },
            sample_cue_ids=[],
            asr_seconds=0.0,
            asr_calls=0,
            notes="hand-written success",
        ).to_json(),
    )
    capsys.readouterr()
    assert _score(root, "HWVA", "b1-va") == RC_STALE
    captured = capsys.readouterr()
    assert "acceptance.json" in captured.err
    assert "acceptance_sha256" in captured.err
    assert not (
        va_dir / "score.json"
    ).exists()  # tampered data never numerically scored


def test_cross_case_acceptance_copy_is_refused_by_case_id_binding(
    tmp_path, fixture_dir, monkeypatch, capsys
):
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "ACCPA", "S01", 1) == 0
    assert _prepare(root, "ACCPB", "S01", 2) == 0
    assert _run(root, "ACCPA") == 0
    assert _run(root, "ACCPB") == 0
    _mock_va(monkeypatch, _cue_text(root, "ACCPA"))
    assert _run_va(root, "ACCPA") == 0
    _mock_va(monkeypatch, _cue_text(root, "ACCPB"))
    assert _run_va(root, "ACCPB") == 0
    assert _score(root, "ACCPB", "b1-va") == 0
    va_b = _cand_dir(root, "ACCPB", "b1-va")
    # Reproduce the probe: copy case A's genuine acceptance into case B's b1-va
    # dir. Re-bind B's recorded acceptance_sha256 to the copied bytes so ONLY the
    # identity binding (case_id) can catch it — the hash check alone would pass.
    shutil.copy2(
        _cand_dir(root, "ACCPA", "b1-va") / "acceptance.json", va_b / "acceptance.json"
    )
    run = _load(va_b / "run.json")
    run["acceptance_sha256"] = sha256_file(va_b / "acceptance.json")
    write_json(va_b / "run.json", run)
    capsys.readouterr()
    assert _score(root, "ACCPB", "b1-va") == RC_STALE
    captured = capsys.readouterr()
    assert "case_id" in captured.err
    assert not (va_b / "score.json").exists()


def test_acceptance_in_non_va_arm_dir_is_ignored(tmp_path, fixture_dir):
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "PLNT", "S01", 1) == 0
    assert _run(root, "PLNT") == 0
    assert _score(root, "PLNT", "b1-n") == 0
    b1n = _cand_dir(root, "PLNT", "b1-n")
    baseline = _load(b1n / "score.json")
    case = cli._load_case(cli._lookup_case_path(cli._paths(root), "PLNT"))
    # Plant a success/original-times acceptance into a proposal-only arm's dir.
    write_json(
        b1n / "acceptance.json",
        AcceptanceRecord(
            case_id="PLNT",
            candidate_id="b1-n",
            validated_candidate_id="b1-n",
            status="success",
            accepted_regions=[{"start_us": 0, "end_us": None, "offset_us": 0}],
            rejected_regions=[],
            abstained_regions=[],
            accepted_times_us={
                cid: (int(s), int(e)) for cid, (s, e) in case.original_times_us.items()
            },
            sample_cue_ids=[],
            asr_seconds=0.0,
            asr_calls=0,
            notes="planted",
        ).to_json(),
    )
    assert _score(root, "PLNT", "b1-n") == 0
    after = _load(b1n / "score.json")
    # Ignored: identical proposal-only result, nothing "accepted".
    assert after["counts"]["accepted_nonzero"] == 0
    assert after["timing_errors_final_us"] == baseline["timing_errors_final_us"]
    assert after["counts"]["repaired"] == baseline["counts"]["repaired"]


# ---------------------------------------------------------------------------
# P1-2: stale score.json deleted on skip; report binds fingerprints
# ---------------------------------------------------------------------------


def test_non_scoreable_skip_deletes_prior_score_json(tmp_path, fixture_dir, capsys):
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "SKIP", "S01", 1) == 0
    assert _run(root, "SKIP") == 0
    assert _score(root, "SKIP", "b1-n") == 0
    d = _cand_dir(root, "SKIP", "b1-n")
    assert (d / "score.json").is_file()
    # Re-prepare a new generation (gen-B) and rerun the same case id.
    assert _prepare(root, "SKIP", "S01", 2) == 0
    assert _run(root, "SKIP") == 0
    # Force the current proposal to a non-scoreable mapping_failure while keeping
    # run.json's provenance consistent (hash updated, fingerprint still valid),
    # reproducing the "score skips (bare continue), gen-A score.json survives" probe.
    paths = cli._paths(root)
    case = cli._load_case(cli._lookup_case_path(paths, "SKIP"))
    corrupted = Track.load(cli._resolve_generated(paths, case), case.fmt).time_map()
    write_json(
        d / "proposal.json",
        ProposalRecord(
            case_id="SKIP",
            candidate_id="b1-n",
            mapping_status="mapping_failure_count_mismatch",
            regions=[],
            proposed_times_us={},
            unmapped_cue_ids=list(corrupted.keys()),
            notes="forced mapping failure",
        ).to_json(),
    )
    run = _load(d / "run.json")
    run["proposal_sha256"] = sha256_file(d / "proposal.json")
    write_json(d / "run.json", run)
    capsys.readouterr()
    assert _score(root, "SKIP", "b1-n") == 0  # skip is not a provenance refusal
    captured = capsys.readouterr()
    assert not (
        d / "score.json"
    ).exists()  # the non-scoreable skip deletes the stale number
    assert "deleted stale score.json" in captured.err


def test_score_json_embeds_fingerprint_and_report_renders_bound_row(
    tmp_path, fixture_dir
):
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "EMBD", "S01", 1) == 0
    assert _run(root, "EMBD") == 0
    assert _score(root, "EMBD", "b1-n") == 0
    d = _cand_dir(root, "EMBD", "b1-n")
    run = _load(d / "run.json")
    score = _load(d / "score.json")
    assert score["input_fingerprint"] == run["input_fingerprint"]
    assert cli.main(["--root", str(root), "report", "--case", "EMBD"]) == 0
    report = (root / "results" / "report.md").read_text(encoding="utf-8")
    assert "b1-n" in report
    assert "dropped unbound score rows: 0" in report


def test_report_drops_planted_unbound_score_and_shows_note(tmp_path, fixture_dir):
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "UNBD", "S01", 1) == 0
    assert _run(root, "UNBD") == 0
    assert _score(root, "UNBD", "b1-n") == 0
    # Plant a schema-2 score.json with a fingerprint no run.json carries.
    planted = _cand_dir(root, "UNBD", "b1-al")
    write_json(
        planted / "score.json",
        {
            "schema_version": 2,
            "case_id": "UNBD",
            "candidate_id": "b1-al",
            "scenario": "S01",
            "input_fingerprint": "f" * 64,
            "counts": {
                "proposals_nonzero": 24,
                "accepted_nonzero": 24,
                "repaired": 24,
                "worsened_unaltered": 0,
                "harmful_proposed": 0,
                "harmful_accepted": 0,
            },
            "denominators": {"total_cues": 24, "altered_cues": 24, "unaltered_cues": 0},
            "discontinuities": {
                "true_breakpoints": 0,
                "detected_breakpoints": 0,
                "matched_true_breakpoints": 0,
                "false_positive_breakpoints": 0,
                "unresolved_true_breakpoints": 0,
                "jump_threshold_us": 500000,
                "true_breakpoints_without_straddle_pair": 0,
                "matched_breaks": [],
            },
            "timing_errors_final_us": {
                "median_abs_us": 0,
                "p90_abs_us": 0,
                "p95_abs_us": 0,
            },
            "tolerances": {
                "good_us": 50000,
                "severe_us": 250000,
                "break_match_us": 500000,
                "meaning": "x",
            },
        },
    )
    assert cli.main(["--root", str(root), "report", "--case", "UNBD"]) == 0
    report = (root / "results" / "report.md").read_text(encoding="utf-8")
    assert "dropped unbound score rows: 1" in report
    assert "| b1-al |" not in report  # the planted row is never rendered
    assert "| b1-n |" in report  # the genuinely bound row is rendered


def test_report_drops_score_with_no_run_json(tmp_path, fixture_dir):
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "NORUN", "S01", 1) == 0
    assert _run(root, "NORUN") == 0
    assert _score(root, "NORUN", "b1-n") == 0
    # Copy the bound score.json's payload to a candidate dir with NO run.json
    # provenance, relabeled to that candidate (the fingerprint is real but no
    # b1-al run.json carries it, so the row must be dropped as unbound).
    src = _cand_dir(root, "NORUN", "b1-n")
    dst = _cand_dir(root, "NORUN", "b1-al")
    dst.mkdir(parents=True, exist_ok=True)
    payload = _load(src / "score.json")
    payload["candidate_id"] = "b1-al"
    write_json(dst / "score.json", payload)
    assert cli.main(["--root", str(root), "report", "--case", "NORUN"]) == 0
    report = (root / "results" / "report.md").read_text(encoding="utf-8")
    assert "dropped unbound score rows: 1" in report
    assert "| b1-al |" not in report


# ---------------------------------------------------------------------------
# P2-1: sidecar stem alias uniqueness
# ---------------------------------------------------------------------------


def _register_two_same_stem(tmp_path: Path, fixture_dir: Path) -> Path:
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    a_side = tmp_path / "trackA" / "ep.ass"
    b_side = tmp_path / "trackB" / "ep.ass"
    a_side.parent.mkdir(parents=True, exist_ok=True)
    b_side.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(fixture_dir / "episode.ass", a_side)
    shutil.copy2(fixture_dir / "episode.ass", b_side)
    assert (
        _cli_add(
            root,
            media,
            (
                "--audio",
                "lang:eng",
                "--subtitle",
                f"a=sidecar:{a_side}",
                "--subtitle",
                f"b=sidecar:{b_side}",
                "--subtitle-language",
                "a=eng",
                "--subtitle-language",
                "b=kor",
            ),
        )
        == 0
    )
    return root


def test_same_stem_sidecar_tracks_have_no_stem_alias(tmp_path, fixture_dir):
    root = _register_two_same_stem(tmp_path, fixture_dir)
    langs = _record(root)["subtitle_languages"]
    assert langs.get("a") == "eng"
    assert langs.get("b") == "kor"
    assert "ep" not in langs  # collision => stem alias NOT stored


def test_collided_sidecar_run_is_identity_unknown_never_wrong_identity(
    tmp_path, fixture_dir, monkeypatch
):
    root = _register_two_same_stem(tmp_path, fixture_dir)
    # Prepare a case from track b (kor sidecar); corrupt.py records track_id = stem "ep".
    assert _prepare(root, "COLL", "S01", 1, track="b") == 0
    paths = cli._paths(root)
    case = cli._load_case(cli._lookup_case_path(paths, "COLL"))
    assert case.track_id == "ep"
    # No stem key exists, so registry resolution must NOT return a language.
    assert (case.track_id in (_record(root)["subtitle_languages"])) is False

    captured: dict = {}

    def _fake_validate(*args, **kwargs):
        captured["language"] = args[8]
        captured.update(kwargs)
        return AcceptanceRecord(
            case_id=case.case_id,
            candidate_id="b1-va",
            validated_candidate_id=args[2],
            status="abstain",
            accepted_regions=[],
            rejected_regions=[],
            abstained_regions=[
                {
                    "start_us": 0,
                    "end_us": None,
                    "offset_us": 0,
                    "reason": "identity unknown",
                }
            ],
            accepted_times_us=dict(args[3]),
            sample_cue_ids=[],
            asr_seconds=0.0,
            asr_calls=0,
        )

    monkeypatch.setattr(cli, "validate_proposal", _fake_validate)
    assert _run(root, "COLL") == 0
    assert _run_va(root, "COLL") == 0
    # Identity-unknown path: the target hint stays "und" (never the leaked eng/kor).
    assert captured["language"] == "eng"  # audio identity from the selected stream
    assert captured["subtitle_language"] == "und"  # collided stem resolves to nothing


def test_collided_sidecar_genuine_run_produces_zero_rejects(
    tmp_path, fixture_dir, monkeypatch
):
    root = _register_two_same_stem(tmp_path, fixture_dir)
    assert _prepare(root, "COLLQ", "S01", 1, track="b") == 0
    assert _run(root, "COLLQ") == 0
    _mock_va(monkeypatch, _cue_text(root, "COLLQ"))
    assert _run_va(root, "COLLQ") == 0
    acc = AcceptanceRecord(
        **read_json(_cand_dir(root, "COLLQ", "b1-va") / "acceptance.json")
    )
    # A verified same-language pair is required for a lexical reject; identity-
    # unknown must NEVER reject legitimate translations.
    assert acc.rejected_regions == []


def test_single_sidecar_stem_alias_still_resolves(tmp_path, fixture_dir, monkeypatch):
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    sidecar = tmp_path / "solo.ass"
    shutil.copy2(fixture_dir / "episode.ass", sidecar)
    assert (
        _cli_add(
            root,
            media,
            (
                "--audio",
                "lang:eng",
                "--subtitle",
                f"m=sidecar:{sidecar}",
                "--subtitle-language",
                "m=kor",
            ),
        )
        == 0
    )
    langs = _record(root)["subtitle_languages"]
    assert langs.get("m") == "kor"
    assert langs.get("solo") == "kor"  # unique stem keeps the working alias
    assert _prepare(root, "SOLO", "S01", 1, track="m") == 0
    case = cli._load_case(cli._lookup_case_path(cli._paths(root), "SOLO"))
    assert case.track_id == "solo"

    captured: dict = {}

    def _fake_validate(*args, **kwargs):
        captured.update(kwargs)
        captured["language"] = args[8]
        return AcceptanceRecord(
            case_id=case.case_id,
            candidate_id="b1-va",
            validated_candidate_id=args[2],
            status="not_run",
            accepted_regions=[],
            rejected_regions=[],
            abstained_regions=[],
            accepted_times_us=dict(args[3]),
            sample_cue_ids=[],
            asr_seconds=0.0,
            asr_calls=0,
        )

    monkeypatch.setattr(cli, "validate_proposal", _fake_validate)
    assert _run(root, "SOLO") == 0
    assert _run_va(root, "SOLO") == 0
    assert (
        captured["subtitle_language"] == "kor"
    )  # stem alias bridges the case track_id


# ---------------------------------------------------------------------------
# P2 residual: proposal-missing stale-score deletion + report generation binding
# ---------------------------------------------------------------------------


def test_proposal_removal_deletes_stale_score_refuses_and_report_has_no_row(
    tmp_path, fixture_dir, capsys
):
    """Reproduce the review probe: gen-A run+score, re-prepare as gen-B, run the
    arm (writes gen-B run.json + proposal.json), delete proposal.json, then
    ``score --all``. The bound gen-A score.json must NOT survive: it is deleted
    and the run refuses with rc 6, and the report renders no row for the arm."""
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "PROP", "S01", 1) == 0
    assert _run(root, "PROP") == 0
    assert _score(root, "PROP", "b1-n") == 0
    d = _cand_dir(root, "PROP", "b1-n")
    assert (d / "score.json").is_file()
    # Re-prepare the same case_id as a NEW generation, then re-run b1-n so the
    # directory holds a gen-B run.json/proposal.json and the surviving gen-A
    # score.json.
    assert _prepare(root, "PROP", "S02", 2) == 0
    assert _run(root, "PROP") == 0
    (d / "proposal.json").unlink()
    capsys.readouterr()
    assert _score_all(root, "PROP") == RC_STALE
    captured = capsys.readouterr()
    assert "proposal.json missing" in captured.err
    assert "deleted stale score.json" in captured.err
    assert not (d / "score.json").exists()
    assert _report(root, "PROP") == 0
    assert "| b1-n |" not in _report_text(root)  # no bound number left to render


def test_report_drops_stale_bound_pair_after_reprepare(tmp_path, fixture_dir):
    """A gen-A run.json + score.json form a self-consistent bound pair. After
    re-preparing the same case_id as gen-B WITHOUT re-running, the fingerprint
    match (score fp == run fp) alone would render it under gen-B's manifest. The
    generation binding recomputes the CURRENT fingerprint and drops the pair,
    counted as stale-generation (not unbound), with rc 0."""
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "STALE", "S01", 1) == 0
    assert _run(root, "STALE") == 0
    assert _score(root, "STALE", "b1-n") == 0
    d = _cand_dir(root, "STALE", "b1-n")
    run_fp = _load(d / "run.json")["input_fingerprint"]
    score_fp = _load(d / "score.json")["input_fingerprint"]
    assert run_fp == score_fp  # the pair the fingerprint-match binding alone trusts
    # Re-prepare as a new generation; do NOT touch results/.
    assert _prepare(root, "STALE", "S02", 2) == 0
    assert _load(d / "run.json")["input_fingerprint"] == run_fp  # pair unchanged
    assert _report(root, "STALE") == 0
    report = _report_text(root)
    assert "dropped stale-generation rows: 1" in report
    assert "dropped unbound score rows: 0" in report
    assert "| b1-n |" not in report


def test_fresh_full_pipeline_scores_and_reports_rows(tmp_path, fixture_dir):
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "FRESH", "S01", 1) == 0
    assert _run(root, "FRESH") == 0
    assert _score(root, "FRESH", "b1-n") == 0
    assert _report(root, "FRESH") == 0
    report = _report_text(root)
    assert "| b1-n |" in report
    assert "dropped unbound score rows: 0" in report
    assert "dropped stale-generation rows: 0" in report


def test_never_run_arm_keeps_score_all_rc_zero(tmp_path, fixture_dir, capsys):
    """A never-run arm (no proposal.json, no score.json) must keep ``--all`` at
    rc 0: the proposal-missing deletion/refusal fires only when a stale
    score.json exists to delete."""
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "NEVER", "S01", 1) == 0
    assert _run(root, "NEVER") == 0
    assert _score(root, "NEVER", "b1-n") == 0
    capsys.readouterr()
    assert _score_all(root, "NEVER") == 0
    captured = capsys.readouterr()
    assert "deleted stale score.json" not in captured.err
