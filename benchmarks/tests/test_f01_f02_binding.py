"""Third-review F01 + F02 focused regressions (validity/provenance binding).

F01: a B1-VA acceptance is invalidated AT READ TIME when its validated base
arm's proposal/run record/fingerprint no longer match what the validator
consumed, and the validation input identity (seed, language identities,
ASR/verifier models) is recorded and embedded in the score row.

F02: the version-2 input fingerprint binds the canonical ground-truth
annotations and the oracle/gold material by live content, so edited gold
timing, changed injected deltas, and rewritten gold-classification files
invalidate cached proposals/scores even when the corrupted subtitle bytes are
byte-identical.

Each reproducible failure mode carries a positive control (unchanged base
keeps scoring; a genuine unchanged case stays cacheable; legitimate current
results are never deleted by a stale-score removal).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
from bench import cli
from bench.fingerprint import (
    FINGERPRINT_SCHEMA_VERSION,
    compute_input_fingerprint,
    fingerprint_payload,
)
from bench.manifests import ProposalRecord, read_json, write_json
from bench.media import sha256_file
from bench.subtitles import Track

FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg required")

RC_STALE = 6
STUB = Path(__file__).resolve().parent / "stubs" / "stub_ffsubsync.py"
ASR_ENV = (
    "BENCH_ASR_BASE_URL",
    "BENCH_ASR_MODEL",
    "BENCH_ASR_API_KEY",
    "BENCH_SEM_VERIFY_BASE_URL",
    "BENCH_SEM_VERIFY_MODEL",
    "BENCH_SEM_VERIFY_API_KEY",
)


def _ffmpeg(*args: str) -> None:
    import subprocess

    subprocess.run(
        [FFMPEG, "-y", "-v", "error", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _build_mkv(tmp_path: Path) -> Path:
    media_dir = tmp_path / "media"
    media_dir.mkdir(exist_ok=True)
    out = media_dir / "episode.mkv"
    a440 = tmp_path / "e-440.wav"
    a880 = tmp_path / "e-880.wav"
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


def _setup(tmp_path: Path, fixture_dir: Path, gold: Path | None = None) -> Path:
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    sidecar = tmp_path / "episode.ass"
    shutil.copy2(fixture_dir / "episode.ass", sidecar)
    extra = [
        "--audio",
        "lang:eng",
        "--subtitle",
        f"main=sidecar:{sidecar}",
        "--subtitle-language",
        "main=eng",
    ]
    if gold is not None:
        extra += ["--gold", f"main={gold}"]
    assert _cli_add(root, media, tuple(extra)) == 0
    return root


def _prepare(root: Path, case_id: str, scenario: str, seed: int) -> int:
    return cli.main(
        [
            "--root",
            str(root),
            "case",
            "prepare",
            "--source-id",
            "MS",
            "--track-id",
            "main",
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


def _run_va(root: Path, case_id: str, extra: tuple[str, ...] = ()) -> int:
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
            "b1-n",
            *extra,
        ]
    )


def _score(root: Path, case_id: str, cand: str) -> int:
    return cli.main(
        ["--root", str(root), "score", "--case", case_id, "--candidate", cand]
    )


def _report(root: Path, case_id: str) -> tuple[int, str]:
    rc = cli.main(["--root", str(root), "report", "--case", case_id])
    return rc, (root / "results" / "report.md").read_text(encoding="utf-8")


def _cand_dir(root: Path, case_id: str, cand: str) -> Path:
    return root / "results" / case_id / cand


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _stub_oracle_tools(monkeypatch):
    from bench.adapters import ToolConfig

    def _fake_detect(cls):
        tools = ToolConfig()
        tools.command_overrides = {
            "b1-pxo-fg": [sys.executable, str(STUB), "--offset-ms", "2000"],
        }
        return tools

    monkeypatch.setattr(ToolConfig, "detect", classmethod(_fake_detect))
    for var in ASR_ENV:
        monkeypatch.delenv(var, raising=False)


def _case_manifest_path(root: Path, case_id: str) -> Path:
    p = cli._lookup_case_path(cli._paths(root), case_id)
    assert p is not None
    return p


def _relabel_base_proposal(root: Path, case_id: str, shift_us: int) -> str:
    """Simulate a base re-run that keeps the case identity but produces a
    different proposal: new proposal bytes, base run.json re-hashed to match."""
    d = _cand_dir(root, case_id, "b1-n")
    prop = ProposalRecord(**read_json(d / "proposal.json"))
    shifted = {
        cid: (s + shift_us, e + shift_us)
        for cid, (s, e) in prop.proposed_times_us.items()
    }
    new = ProposalRecord(
        case_id=prop.case_id,
        candidate_id="b1-n",
        mapping_status="1:1-order-preserving",
        regions=[
            {"start_us": 0, "end_us": None, "offset_us": shift_us, "kind": "global"}
        ],
        proposed_times_us=shifted,
        unmapped_cue_ids=[],
        notes="simulated base re-run result",
    )
    write_json(d / "proposal.json", new.to_json())
    run = _load(d / "run.json")
    run["proposal_sha256"] = sha256_file(d / "proposal.json")
    run["status"] = "1:1-order-preserving"
    write_json(d / "run.json", run)
    return run["proposal_sha256"]


# ---------------------------------------------------------------------------
# F01 — acceptance invalidated when the validated base proposal changes
# ---------------------------------------------------------------------------


def test_base_rerun_with_new_proposal_invalidates_b1va_acceptance(
    tmp_path, fixture_dir, monkeypatch, capsys
):
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "BASER", "S01", 1) == 0
    assert _run(root, "BASER") == 0
    _mock_va(monkeypatch, _cue_text(root, "BASER"))
    assert _run_va(root, "BASER") == 0
    va_dir = _cand_dir(root, "BASER", "b1-va")
    assert _score(root, "BASER", "b1-va") == 0  # before: the acceptance scores
    assert (va_dir / "score.json").is_file()

    _relabel_base_proposal(root, "BASER", 2_000_000)

    capsys.readouterr()
    assert _score(root, "BASER", "b1-va") == RC_STALE
    captured = capsys.readouterr()
    assert "STALE" in captured.err
    assert "validated base proposal bytes" in captured.err
    assert not (va_dir / "score.json").exists()
    # The refusal deletes ONLY the b1-va score; the base arm's current result
    # stays scoreable (a stale-score deletion never removes legitimate rows).
    assert _score(root, "BASER", "b1-n") == 0
    assert (_cand_dir(root, "BASER", "b1-n") / "score.json").is_file()

    rc, report = _report(root, "BASER")
    assert rc == 0
    assert "dropped obsolete-acceptance rows: 1" in report
    assert "| b1-va |" not in report
    assert "| b1-n |" in report

    # Re-validating against the current base restores scoring.
    assert _run_va(root, "BASER") == 0
    assert _score(root, "BASER", "b1-va") == 0


def test_base_run_record_bytes_are_bound(tmp_path, fixture_dir, monkeypatch, capsys):
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "BSER", "S01", 1) == 0
    assert _run(root, "BSER") == 0
    _mock_va(monkeypatch, _cue_text(root, "BSER"))
    assert _run_va(root, "BSER") == 0
    assert _score(root, "BSER", "b1-va") == 0
    base_run_path = _cand_dir(root, "BSER", "b1-n") / "run.json"
    run = _load(base_run_path)
    run["run_id"] = "rewritten-base-run"
    write_json(base_run_path, run)
    capsys.readouterr()
    assert _score(root, "BSER", "b1-va") == RC_STALE
    captured = capsys.readouterr()
    assert "base run.json bytes" in captured.err
    assert not (_cand_dir(root, "BSER", "b1-va") / "score.json").exists()


def test_validation_config_recorded_and_embedded(tmp_path, fixture_dir, monkeypatch):
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "VCFG", "S01", 1) == 0
    assert _run(root, "VCFG") == 0
    _mock_va(monkeypatch, _cue_text(root, "VCFG"))
    assert _run_va(root, "VCFG", ("--seed", "7", "--language", "jpn")) == 0
    va_run = _load(_cand_dir(root, "VCFG", "b1-va") / "run.json")
    vc = va_run["validation_config"]
    assert vc["seed"] == 7
    assert vc["language"] == "jpn"
    assert vc["subtitle_language"] == "eng"
    assert vc["asr_model"] == "mock"
    assert vc["verifier_model"] is None
    assert vc["pad_us"] == 1_500_000
    assert vc["min_match_ratio"] == pytest.approx(0.45)
    assert vc["timing_tolerance_us"] == 500_000
    base_run = _load(_cand_dir(root, "VCFG", "b1-n") / "run.json")
    assert va_run["base_input_fingerprint"] == base_run["input_fingerprint"]
    assert va_run["base_run_id"] == base_run["run_id"]
    assert va_run["base_run_sha256"] == sha256_file(
        _cand_dir(root, "VCFG", "b1-n") / "run.json"
    )
    assert va_run["base_proposal_sha256"] == sha256_file(
        _cand_dir(root, "VCFG", "b1-n") / "proposal.json"
    )
    assert _score(root, "VCFG", "b1-va") == 0
    score = _load(_cand_dir(root, "VCFG", "b1-va") / "score.json")
    assert score["validated_base"]["candidate_id"] == "b1-n"
    assert score["validated_base"]["input_fingerprint"] == base_run["input_fingerprint"]
    assert score["validated_base"]["proposal_sha256"] == va_run["base_proposal_sha256"]
    assert score["validation_config"]["seed"] == 7
    rc, report = _report(root, "VCFG")
    assert rc == 0
    assert "validated base b1-n @ run" in report
    assert "validation seed 7" in report
    # Re-running with a DIFFERENT seed records the new identity (never
    # mislabelable as the same experiment as seed 7).
    assert _run_va(root, "VCFG", ("--seed", "9", "--language", "jpn")) == 0
    assert (
        _load(_cand_dir(root, "VCFG", "b1-va") / "run.json")["validation_config"][
            "seed"
        ]
        == 9
    )
    assert _score(root, "VCFG", "b1-va") == 0
    assert (
        _load(_cand_dir(root, "VCFG", "b1-va") / "score.json")["validation_config"][
            "seed"
        ]
        == 9
    )


def test_legacy_acceptance_without_config_is_unbound(
    tmp_path, fixture_dir, monkeypatch, capsys
):
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "LVAC", "S01", 1) == 0
    assert _run(root, "LVAC") == 0
    _mock_va(monkeypatch, _cue_text(root, "LVAC"))
    assert _run_va(root, "LVAC") == 0
    assert _score(root, "LVAC", "b1-va") == 0
    va_dir = _cand_dir(root, "LVAC", "b1-va")
    run = _load(va_dir / "run.json")
    run.pop("validation_config")
    run.pop("base_input_fingerprint")
    write_json(va_dir / "run.json", run)
    capsys.readouterr()
    assert _score(root, "LVAC", "b1-va") == RC_STALE
    captured = capsys.readouterr()
    assert "validation_config" in captured.err
    assert not (va_dir / "score.json").exists()


# ---------------------------------------------------------------------------
# F02 — fingerprint binds ground truth and oracle material
# ---------------------------------------------------------------------------


def test_fingerprint_v2_binds_ground_truth_gold_and_subtitle_input(
    fixture_dir, tmp_path
):
    from bench.corrupt import prepare_case

    assert FINGERPRINT_SCHEMA_VERSION == 2
    source = {
        "media_sha256": "a" * 64,
        "audio_selected": {
            "index": 1,
            "sidx": 1,
            "language": "eng",
            "codec_name": "pcm_s16le",
        },
        "audio_spec": "lang:eng",
        "rights_status": "private-local",
        "subtitle_specs": {"episode": "sidecar:C:/x/episode.ass"},
        "subtitle_sha256": {"episode": "b" * 64},
    }
    case = prepare_case(
        "MS",
        "fp2",
        "S04",
        4,
        fixture_dir / "episode.ass",
        tmp_path / "fp2.ass",
        track_id="episode",
    )
    base = compute_input_fingerprint(case, source, "b1-n", {}, "g" * 64)
    payload = fingerprint_payload(case, source, "b1-n", {}, "g" * 64)
    assert payload["fingerprint_schema_version"] == 2
    assert payload["case"]["grid_us"] == case.grid_us
    assert payload["case"]["fmt"] == case.fmt
    assert payload["case"]["transform"] == case.transform
    assert payload["case"]["expected_inverse"] == case.expected_inverse
    assert payload["gold_classification_sha256"] == "g" * 64
    assert payload["subtitle_input"]["sha256"] == "b" * 64
    # Editing the ground-truth annotation (same seed/params/subtitle bytes)
    # changes the fingerprint.
    edited_times = dict(case.original_times_us)
    first = min(edited_times)
    s, e = edited_times[first]
    edited_times[first] = (s + 1_000_000, e)
    case2 = prepare_case(
        "MS",
        "fp2",
        "S04",
        4,
        fixture_dir / "episode.ass",
        tmp_path / "fp2b.ass",
        track_id="episode",
    )
    case2.original_times_us = edited_times
    assert compute_input_fingerprint(case2, source, "b1-n", {}, "g" * 64) != base
    edited_deltas = dict(case.injected_cue_deltas)
    edited_deltas[first] = (edited_deltas[first][0] + 10_000, edited_deltas[first][1])
    case3 = prepare_case(
        "MS",
        "fp2",
        "S04",
        4,
        fixture_dir / "episode.ass",
        tmp_path / "fp2c.ass",
        track_id="episode",
    )
    case3.injected_cue_deltas = edited_deltas
    assert compute_input_fingerprint(case3, source, "b1-n", {}, "g" * 64) != base
    # Gold content change (same case) changes the fingerprint.
    assert compute_input_fingerprint(case, source, "b1-n", {}, "h" * 64) != base
    # Selected subtitle input identity is bound.
    other_sub = dict(source, subtitle_sha256={"episode": "c" * 64})
    assert compute_input_fingerprint(case, other_sub, "b1-n", {}, "g" * 64) != base
    assert base == compute_input_fingerprint(case, source, "b1-n", {}, "g" * 64)


def test_ground_truth_edit_in_manifest_makes_scores_stale(
    tmp_path, fixture_dir, capsys
):
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "GTIM", "S01", 1) == 0
    assert _run(root, "GTIM") == 0
    assert _score(root, "GTIM", "b1-n") == 0
    generated_sha = _load(_case_manifest_path(root, "GTIM"))[
        "generated_subtitle_sha256"
    ]

    manifest_path = _case_manifest_path(root, "GTIM")
    manifest = _load(manifest_path)
    first = min(manifest["original_times_us"])
    s, e = manifest["original_times_us"][first]
    manifest["original_times_us"][first] = [s + 1_000_000, e]
    write_json(manifest_path, manifest)
    assert (
        _load(_case_manifest_path(root, "GTIM"))["generated_subtitle_sha256"]
        == generated_sha
    )

    capsys.readouterr()
    assert _score(root, "GTIM", "b1-n") == RC_STALE
    captured = capsys.readouterr()
    assert "STALE" in captured.err
    assert "ground-truth" in captured.err
    assert not (_cand_dir(root, "GTIM", "b1-n") / "score.json").exists()
    rc, report = _report(root, "GTIM")
    assert rc == 0
    assert "| b1-n |" not in report  # the old pair never renders under the edited case
    # Re-running against the edited ground truth restores cacheable scoring.
    assert _run(root, "GTIM") == 0
    assert _score(root, "GTIM", "b1-n") == 0
    assert _score(root, "GTIM", "b1-n") == 0  # unchanged case stays cacheable


def _write_gold(path: Path, cues: list[str], flip: str | None = None) -> None:
    payload = {cid: ("non_speech" if cid == flip else "speech_like") for cid in cues}
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_gold_classification_change_forces_oracle_arm_rerun(
    tmp_path, fixture_dir, monkeypatch, capsys
):
    gold = tmp_path / "gold.json"
    _write_gold(gold, ["1"])
    root = _setup(tmp_path, fixture_dir, gold=gold)
    assert _prepare(root, "GLDC", "S01", 1) == 0
    _stub_oracle_tools(monkeypatch)
    assert _run(root, "GLDC", "b1-pxo-fg") == 0
    assert _score(root, "GLDC", "b1-pxo-fg") == 0  # before: bound and scored

    manifest = _load(_case_manifest_path(root, "GLDC"))
    cue_ids = sorted(manifest["original_times_us"])
    _write_gold(gold, cue_ids, flip=cue_ids[0])  # rewrite the oracle content
    capsys.readouterr()
    assert _score(root, "GLDC", "b1-pxo-fg") == RC_STALE
    captured = capsys.readouterr()
    assert "STALE" in captured.err
    assert "gold/oracle" in captured.err
    assert not (_cand_dir(root, "GLDC", "b1-pxo-fg") / "score.json").exists()
    rc, report = _report(root, "GLDC")
    assert rc == 0
    assert "| b1-pxo-fg |" not in report
    # The dependent arm must rerun; a genuine unchanged gold stays cacheable.
    assert _run(root, "GLDC", "b1-pxo-fg") == 0
    assert _score(root, "GLDC", "b1-pxo-fg") == 0
    assert _score(root, "GLDC", "b1-pxo-fg") == 0


def test_gold_file_removal_and_restoration_changes_fingerprint(
    tmp_path, fixture_dir, monkeypatch, capsys
):
    gold = tmp_path / "gold.json"
    _write_gold(gold, ["1"])
    root = _setup(tmp_path, fixture_dir, gold=gold)
    assert _prepare(root, "GLMR", "S01", 1) == 0
    _stub_oracle_tools(monkeypatch)
    assert _run(root, "GLMR", "b1-pxo-fg") == 0
    assert _score(root, "GLMR", "b1-pxo-fg") == 0
    good_bytes = gold.read_bytes()

    gold.unlink()
    capsys.readouterr()
    assert _score(root, "GLMR", "b1-pxo-fg") == RC_STALE
    assert not (_cand_dir(root, "GLMR", "b1-pxo-fg") / "score.json").exists()
    gold.write_bytes(good_bytes)
    assert _score(root, "GLMR", "b1-pxo-fg") == 0


# ---------------------------------------------------------------------------
# Adversarial review round 1 closures: report-path bypasses D1 / D2
# ---------------------------------------------------------------------------


def test_report_excludes_b1va_when_acceptance_json_deleted(
    tmp_path, fixture_dir, monkeypatch
):
    """Review D1: deleting the binding's own verification input must exclude
    the b1-va row at report read time, never render it as comparable."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "ADEN", "S01", 1) == 0
    assert _run(root, "ADEN") == 0
    _mock_va(monkeypatch, _cue_text(root, "ADEN"))
    assert _run_va(root, "ADEN") == 0
    assert _score(root, "ADEN", "b1-n") == 0
    assert _score(root, "ADEN", "b1-va") == 0
    rc, report = _report(root, "ADEN")
    assert rc == 0 and "| b1-va |" in report
    (_cand_dir(root, "ADEN", "b1-va") / "acceptance.json").unlink()
    rc, report = _report(root, "ADEN")
    assert rc == 0
    assert "dropped obsolete-acceptance rows: 1" in report
    assert "| b1-va |" not in report
    assert "acceptance.json is missing" in report
    # The base arm's current row is unaffected by the b1-va exclusion.
    assert "| b1-n |" in report


def test_report_excludes_arm_with_tampered_proposal_bytes(tmp_path, fixture_dir):
    """Review D2: proposal.json bytes rewritten after scoring (run.json left
    self-consistent) must not keep the old score row rendering comparably."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "ATAM", "S01", 1) == 0
    assert _run(root, "ATAM") == 0
    assert _score(root, "ATAM", "b1-n") == 0
    rc, report = _report(root, "ATAM")
    assert rc == 0 and "| b1-n |" in report
    d = _cand_dir(root, "ATAM", "b1-n")
    prop = _load(d / "proposal.json")
    shifted = {
        cid: [s + 3_000_000, e + 3_000_000]
        for cid, (s, e) in prop["proposed_times_us"].items()
    }
    prop["proposed_times_us"] = shifted
    prop["mapping_status"] = "1:1-order-preserving"
    (d / "proposal.json").write_text(
        json.dumps(prop, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    rc, report = _report(root, "ATAM")
    assert rc == 0
    assert "dropped tampered/removed proposal rows: 1" in report
    assert "| b1-n |" not in report
    assert "proposal.json bytes" in report


def test_report_and_score_close_key_removal_bypass(tmp_path, fixture_dir, capsys):
    """Round-2 P1: deleting run.proposal_sha256 must NOT skip the byte check.
    Score refuses (rc 6) and report excludes with the no-hash reason."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "AKRM", "S01", 1) == 0
    assert _run(root, "AKRM") == 0
    assert _score(root, "AKRM", "b1-n") == 0
    d = _cand_dir(root, "AKRM", "b1-n")
    prop = _load(d / "proposal.json")
    shifted = {
        cid: [s + 3_000_000, e + 3_000_000]
        for cid, (s, e) in prop["proposed_times_us"].items()
    }
    prop["proposed_times_us"] = shifted
    (d / "proposal.json").write_text(
        json.dumps(prop, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    run = _load(d / "run.json")
    run.pop("proposal_sha256")
    (d / "run.json").write_text(
        json.dumps(run, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    capsys.readouterr()
    assert _score(root, "AKRM", "b1-n") == RC_STALE
    captured = capsys.readouterr()
    assert "no proposal_sha256" in captured.err
    rc, report = _report(root, "AKRM")
    assert rc == 0
    assert "dropped tampered/removed proposal rows: 1" in report
    assert "no proposal_sha256" in report
    assert "| b1-n |" not in report


def test_report_survives_non_dict_run_json(tmp_path, fixture_dir):
    """Round-2 P2: a parseable non-object run.json is a diagnostic, not a
    traceback; the report still writes and the row never renders."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "ANDICT", "S01", 1) == 0
    assert _run(root, "ANDICT") == 0
    assert _score(root, "ANDICT", "b1-n") == 0
    d = _cand_dir(root, "ANDICT", "b1-n")
    (d / "run.json").write_text("[]\n", encoding="utf-8")
    rc, report = _report(root, "ANDICT")
    assert rc == 0
    assert "unreadable artifacts skipped: 1" in report
    assert "not an object" in report
    assert "| b1-n |" not in report


def test_report_refuses_incomplete_schema3_score(tmp_path, fixture_dir):
    """Round-2 P2: a schema-3 score.json missing a required measurement
    section is refused (dropped unbound), never rendered with defaults."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "AINC", "S01", 1) == 0
    assert _run(root, "AINC") == 0
    assert _score(root, "AINC", "b1-n") == 0
    d = _cand_dir(root, "AINC", "b1-n")
    score = _load(d / "score.json")
    score.pop("counts")
    (d / "score.json").write_text(
        json.dumps(score, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    rc, report = _report(root, "AINC")
    assert rc == 0
    assert "dropped unbound score rows: 1" in report
    assert "| b1-n |" not in report


def test_acceptance_with_incompatible_shape_is_unreadable(
    tmp_path, fixture_dir, monkeypatch, capsys
):
    """Round-2 P2: an acceptance.json that parses as a dict but not as an
    AcceptanceRecord must fail closed in the binding (rc 6), not crash."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "ASHA", "S01", 1) == 0
    assert _run(root, "ASHA") == 0
    _mock_va(monkeypatch, _cue_text(root, "ASHA"))
    assert _run_va(root, "ASHA") == 0
    assert _score(root, "ASHA", "b1-va") == 0
    va_dir = _cand_dir(root, "ASHA", "b1-va")
    write_json_bytes = json.dumps({"junk": "shape"}, sort_keys=True, indent=2) + "\n"
    (va_dir / "acceptance.json").write_text(write_json_bytes, encoding="utf-8")
    run = _load(va_dir / "run.json")
    run["acceptance_sha256"] = sha256_file(va_dir / "acceptance.json")
    (va_dir / "run.json").write_text(
        json.dumps(run, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    capsys.readouterr()
    assert _score(root, "ASHA", "b1-va") == RC_STALE
    captured = capsys.readouterr()
    assert "acceptance.json is unreadable" in captured.err
    assert not (va_dir / "score.json").exists()
    rc, report = _report(root, "ASHA")
    assert rc == 0
    assert "obsolete-acceptance" in report
    assert "| b1-va |" not in report


def test_copied_score_json_cannot_piggyback_a_directory(tmp_path, fixture_dir):
    """Round-3 R3-P1: a score.json copied into a directory with no admitted
    run.json renders no comparative row; the genuine row renders once."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "APIG", "S01", 1) == 0
    assert _run(root, "APIG") == 0
    assert _score(root, "APIG", "b1-n") == 0
    genuine = _cand_dir(root, "APIG", "b1-n")
    piggy = root / "results" / "APIG" / "piggy"
    piggy.mkdir(parents=True, exist_ok=True)
    shutil.copy(genuine / "score.json", piggy / "score.json")
    rc, report = _report(root, "APIG")
    assert rc == 0
    assert "no admitted run.json pairing" in report
    assert "unreadable artifacts skipped: 1" in report
    assert report.count("| b1-n |") == 1


def test_copied_run_triple_cannot_duplicate_a_candidate_row(tmp_path, fixture_dir):
    """Round-3 R3-P1: copying the whole run/proposal/score triple into a
    second directory must not duplicate (or enable tampered twins of) the row."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "ACOPY", "S01", 1) == 0
    assert _run(root, "ACOPY") == 0
    assert _score(root, "ACOPY", "b1-n") == 0
    genuine = _cand_dir(root, "ACOPY", "b1-n")
    copy_dir = root / "results" / "ACOPY" / "b1-n-twin"
    copy_dir.mkdir(parents=True, exist_ok=True)
    for name in ("run.json", "proposal.json", "score.json"):
        shutil.copy(genuine / name, copy_dir / name)
    twin_score = _load(copy_dir / "score.json")
    twin_score["counts"]["proposals_nonzero"] = 99999
    (copy_dir / "score.json").write_text(
        json.dumps(twin_score, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    rc, report = _report(root, "ACOPY")
    assert rc == 0
    assert "duplicate candidate directory" in report
    assert report.count("| b1-n |") == 1
    assert "99999" not in report


def test_score_fields_grafted_into_foreign_directory_are_refused(tmp_path, fixture_dir):
    """Round-3 R3-P1: a score.json whose fields do not pair with the
    directory's own admitted run.json is refused, never rendered."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "AGRF", "S01", 1) == 0
    assert _run(root, "AGRF") == 0
    assert _score(root, "AGRF", "b1-n") == 0
    assert _prepare(root, "AGRF2", "S01", 1) == 0
    assert _run(root, "AGRF2") == 0
    assert _score(root, "AGRF2", "b1-n") == 0
    a_dir = _cand_dir(root, "AGRF", "b1-n")
    b_dir = _cand_dir(root, "AGRF2", "b1-n")
    shutil.copy(a_dir / "score.json", b_dir / "score.json")
    rc, report = _report(root, "AGRF2")
    assert rc == 0
    assert "fields do not pair" in report
    assert report.count("| b1-n |") == 0


def test_bool_proposal_hash_fails_the_byte_check(tmp_path, fixture_dir, capsys):
    """Round-3 R3-P2: a non-string proposal_sha256 (bool true) must fail
    closed at score and report, never slice-crash."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "ABOOL", "S01", 1) == 0
    assert _run(root, "ABOOL") == 0
    assert _score(root, "ABOOL", "b1-n") == 0
    d = _cand_dir(root, "ABOOL", "b1-n")
    run = _load(d / "run.json")
    run["proposal_sha256"] = True
    (d / "run.json").write_text(
        json.dumps(run, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    capsys.readouterr()
    assert _score(root, "ABOOL", "b1-n") == RC_STALE
    captured = capsys.readouterr()
    assert "proposal.json bytes" in captured.err
    rc, report = _report(root, "ABOOL")
    assert rc == 0
    assert "proposal.json bytes" in report
    assert "| b1-n |" not in report


def test_type_tampered_score_numbers_render_as_refused_not_crash(tmp_path, fixture_dir):
    """Round-3 R3-P2: string counts, list schema_version, and offset-recovery
    junk are refused at binding; the report survives with counted drops."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "ATYPE", "S01", 1) == 0
    assert _run(root, "ATYPE") == 0
    assert _score(root, "ATYPE", "b1-n") == 0
    d = _cand_dir(root, "ATYPE", "b1-n")
    sc = _load(d / "score.json")
    sc["counts"] = "x"
    (d / "score.json").write_text(
        json.dumps(sc, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    rc, report = _report(root, "ATYPE")
    assert rc == 0
    assert "dropped unbound score rows: 1" in report
    assert "| b1-n |" not in report
    sc = _load(d / "score.json")
    sc["counts"] = {"proposals_nonzero": [[1, 2]]}
    sc["schema_version"] = []
    (d / "score.json").write_text(
        json.dumps(sc, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    rc, report = _report(root, "ATYPE")
    assert rc == 0
    assert "| b1-n |" not in report


def test_acceptance_with_hostile_field_values_is_incompatible(
    tmp_path, fixture_dir, monkeypatch, capsys
):
    """Round-3 R3-P2: acceptance.json with valid key names but hostile value
    types (accepted_times_us: string) must be refused, not crash scoring."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "AHOST", "S01", 1) == 0
    assert _run(root, "AHOST") == 0
    _mock_va(monkeypatch, _cue_text(root, "AHOST"))
    assert _run_va(root, "AHOST") == 0
    assert _score(root, "AHOST", "b1-va") == 0
    va_dir = _cand_dir(root, "AHOST", "b1-va")
    acc = _load(va_dir / "acceptance.json")
    acc["accepted_times_us"] = "x"
    (va_dir / "acceptance.json").write_text(
        json.dumps(acc, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    run = _load(va_dir / "run.json")
    run["acceptance_sha256"] = sha256_file(va_dir / "acceptance.json")
    (va_dir / "run.json").write_text(
        json.dumps(run, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    capsys.readouterr()
    assert _score(root, "AHOST", "b1-va") == RC_STALE
    captured = capsys.readouterr()
    assert "incompatible" in captured.err
    assert not (va_dir / "score.json").exists()
    rc, report = _report(root, "AHOST")
    assert rc == 0
    assert "| b1-va |" not in report
