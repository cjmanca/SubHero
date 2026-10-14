"""F04: versioned input fingerprint binds run/score/b1-va/reference-cache artifacts.

Stale candidate results from a previous case generation (new seed), a changed
selected audio, tampered reference.wav bytes, tampered proposal.json bytes, and
legacy/unverifiable artifacts must all be refused explicitly — never silently
rescored against the current case.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from bench import cli
from bench.fingerprint import compute_input_fingerprint, fingerprint_payload
from bench.manifests import ProposalRecord, write_json
from bench.media import sha256_file
from bench.subtitles import Track

FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg required")

RC_STALE = 6
STALE_ASR_ENV = (
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


def _decode(media: Path, stream: str, out: Path) -> str:
    _ffmpeg(
        "-i",
        str(media),
        "-map",
        stream,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(out),
    )
    return sha256_file(out)


def _build_mkv(tmp_path: Path, name: str = "episode.mkv") -> Path:
    """Two sine audio streams (440 Hz jpn / 880 Hz eng) + one tagged ASS track."""
    media_dir = tmp_path / "media"
    media_dir.mkdir(exist_ok=True)
    out = media_dir / name
    a440 = tmp_path / f"{name}-440.wav"
    a880 = tmp_path / f"{name}-880.wav"
    s_jpn = tmp_path / f"{name}-jpn.srt"
    s_eng = tmp_path / f"{name}-eng.srt"
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
    s_jpn.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nJPNMARKER4471\n", encoding="utf-8"
    )
    s_eng.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nENGMARKER9135\n", encoding="utf-8"
    )
    _ffmpeg(
        "-i",
        str(a440),
        "-i",
        str(a880),
        "-i",
        str(s_jpn),
        "-i",
        str(s_eng),
        "-map",
        "0:a:0",
        "-map",
        "1:a:0",
        "-map",
        "2:s:0",
        "-map",
        "3:s:0",
        "-c:a",
        "pcm_s16le",
        "-c:s",
        "ass",
        "-metadata:s:a:0",
        "language=jpn",
        "-metadata:s:a:1",
        "language=eng",
        "-metadata:s:s:0",
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


def _record(root: Path, source_id: str) -> dict:
    data = json.loads((root / "cases" / "sources.json").read_text(encoding="utf-8"))
    return data["sources"][source_id]


def _setup(tmp_path: Path, fixture_dir: Path) -> tuple[Path, Path]:
    """Register a 2-audio source with an Fx00 sidecar subtitle (private-local)."""
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


def _run(root: Path, case_id: str, *extra: str) -> int:
    return cli.main(
        ["--root", str(root), "run", "--case", case_id, "--candidate", "b1-n", *extra]
    )


def _score(root: Path, case_id: str, cand: str = "b1-n") -> int:
    return cli.main(
        ["--root", str(root), "score", "--case", case_id, "--candidate", cand]
    )


def _run_va(root: Path, case_id: str, base: str = "b1-n") -> int:
    """Run b1-va alone: the base arm is NOT re-run in the same invocation."""
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


def _generated_sha(root: Path, case_id: str) -> str:
    manifest = cli._lookup_case_path(cli._paths(root), case_id)
    assert manifest is not None
    return json.loads(manifest.read_text(encoding="utf-8"))["generated_subtitle_sha256"]


def _mock_va(monkeypatch, cue_text: dict[str, str]):
    from bench.asr import MockTranscriber

    for var in STALE_ASR_ENV:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(cli, "get_transcriber", lambda: MockTranscriber(dict(cue_text)))
    monkeypatch.setattr(cli, "get_semantic_verifier", lambda: None)


def _cue_text(root: Path, case_id: str) -> dict[str, str]:
    paths = cli._paths(root)
    case = cli._load_case(cli._lookup_case_path(paths, case_id))
    track = Track.load(cli._resolve_generated(paths, case), case.fmt)
    return {c.cue_id: c.text for c in track.cues}


# --- fingerprint helper contract -------------------------------------------------


def test_fingerprint_is_deterministic_and_bound_to_fields(fixture_dir, tmp_path):
    media = _build_mkv(tmp_path)
    source = {
        "media_sha256": sha256_file(media),
        "audio_selected": {
            "index": 1,
            "sidx": 1,
            "language": "eng",
            "codec_name": "pcm_s16le",
        },
        "audio_spec": "lang:eng",
        "rights_status": "private-local",
    }
    assert media.is_file()
    from bench.corrupt import prepare_case

    case = prepare_case(
        "MS", "fp-case", "S01", 3, fixture_dir / "episode.ass", tmp_path / "fp.ass"
    )
    fp = compute_input_fingerprint(case, source, "b1-n")
    assert fp == compute_input_fingerprint(case, source, "b1-n")
    assert fp != compute_input_fingerprint(case, source, "b1-al")
    assert fp != compute_input_fingerprint(case, source, "b1-n", {"ffsubsync": "v1"})
    assert (
        fingerprint_payload(case, source, "b1-n")["audio"]["media_sha256"]
        == source["media_sha256"]
    )
    # Seed is bound even when the generated artifact is byte-identical (S00 control).
    control = prepare_case(
        "MS", "fp-ctrl", "S00", 1, fixture_dir / "episode.ass", tmp_path / "fp00.ass"
    )
    control2 = prepare_case(
        "MS", "fp-ctrl", "S00", 2, fixture_dir / "episode.ass", tmp_path / "fp00b.ass"
    )
    assert control.generated_subtitle_sha256 == control2.generated_subtitle_sha256
    assert compute_input_fingerprint(
        control, source, "b1-n"
    ) != compute_input_fingerprint(control2, source, "b1-n")
    # Selected audio identity is bound.
    other_audio = dict(
        source,
        audio_selected={
            "index": 0,
            "sidx": 0,
            "language": "jpn",
            "codec_name": "pcm_s16le",
        },
    )
    assert compute_input_fingerprint(
        control, source, "b1-n"
    ) != compute_input_fingerprint(control, other_audio, "b1-n")


# --- 1. seed change --------------------------------------------------------------


def test_seed_change_makes_prior_results_stale_until_rerun(
    tmp_path, fixture_dir, monkeypatch, capsys
):
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "SEEDX", "S01", 1) == 0
    sha_a = _generated_sha(root, "SEEDX")
    assert _run(root, "SEEDX") == 0
    assert _score(root, "SEEDX") == 0
    results = root / "results" / "SEEDX" / "b1-n"
    assert (results / "score.json").is_file()
    run_meta = json.loads((results / "run.json").read_text(encoding="utf-8"))
    assert run_meta["schema_version"] == 2
    assert len(run_meta["input_fingerprint"]) == 64
    assert len(run_meta["proposal_sha256"]) == 64

    _mock_va(monkeypatch, _cue_text(root, "SEEDX"))
    assert _run_va(root, "SEEDX") == 0
    va_acc = root / "results" / "SEEDX" / "b1-va" / "acceptance.json"
    assert va_acc.is_file()
    acc_before = va_acc.read_bytes()

    # Re-prepare the SAME case id with a different seed overwrites the timeline.
    assert _prepare(root, "SEEDX", "S01", 2) == 0
    sha_b = _generated_sha(root, "SEEDX")
    assert sha_b != sha_a

    capsys.readouterr()
    assert _score(root, "SEEDX") == RC_STALE
    captured = capsys.readouterr()
    assert "STALE" in captured.err
    assert "re-run" in captured.err
    assert not (results / "score.json").exists()
    assert _score(root, "SEEDX", "b1-va") == RC_STALE
    assert not (root / "results" / "SEEDX" / "b1-va" / "score.json").exists()

    # b1-va refuses the stale base and writes no acceptance from stale data.
    capsys.readouterr()
    assert _run_va(root, "SEEDX") == RC_STALE
    captured = capsys.readouterr()
    assert "STALE" in captured.err and "b1-va" in captured.err
    assert va_acc.read_bytes() == acc_before

    # Re-running the candidate restores scoring.
    assert _run(root, "SEEDX") == 0
    assert _score(root, "SEEDX") == 0
    assert (results / "score.json").is_file()
    assert _run_va(root, "SEEDX") == 0
    assert _score(root, "SEEDX", "b1-va") == 0
    assert (root / "results" / "SEEDX" / "b1-va" / "score.json").is_file()


def test_seed_change_stale_even_for_identical_control_output(tmp_path, fixture_dir):
    """S00 control: re-preparing with another seed leaves bytes identical; the
    fingerprint must still bind the seed and refuse stale scoring."""
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "CTRLX", "S00", 1) == 0
    sha_a = _generated_sha(root, "CTRLX")
    assert _run(root, "CTRLX") == 0
    assert _score(root, "CTRLX") == 0
    assert _prepare(root, "CTRLX", "S00", 2) == 0
    assert _generated_sha(root, "CTRLX") == sha_a
    assert _score(root, "CTRLX") == RC_STALE
    assert not (root / "results" / "CTRLX" / "b1-n" / "score.json").exists()
    assert _run(root, "CTRLX") == 0
    assert _score(root, "CTRLX") == 0


# --- 2. audio-selection change ---------------------------------------------------


def test_audio_selection_change_makes_prior_results_stale(
    tmp_path, fixture_dir, monkeypatch
):
    root, media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "AUDX", "S01", 1) == 0
    generated_sha_before = _generated_sha(root, "AUDX")
    assert _run(root, "AUDX") == 0
    assert _score(root, "AUDX") == 0

    _mock_va(monkeypatch, _cue_text(root, "AUDX"))
    assert _run_va(root, "AUDX") == 0

    # Re-register the same source id with the OTHER audio stream (index:0 = jpn).
    registry_path = root / "cases" / "sources.json"
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    del data["sources"]["MS"]
    registry_path.write_text(json.dumps(data), encoding="utf-8")
    sidecar = tmp_path / "episode.ass"
    assert (
        _cli_add(
            root,
            media,
            ("--audio", "lang:jpn", "--subtitle", f"main=sidecar:{sidecar}"),
        )
        == 0
    )
    assert _record(root, "MS")["audio_selected"]["sidx"] == 0
    # The corrupted case artifact is byte-identical: only the audio identity moved.
    assert _generated_sha(root, "AUDX") == generated_sha_before

    assert _score(root, "AUDX") == RC_STALE
    assert not (root / "results" / "AUDX" / "b1-n" / "score.json").exists()
    assert _run_va(root, "AUDX") == RC_STALE

    assert _run(root, "AUDX") == 0
    assert _score(root, "AUDX") == 0
    assert _run_va(root, "AUDX") == 0


# --- 3. tampered reference.wav ---------------------------------------------------


def test_tampered_reference_wav_is_reextracted(tmp_path, fixture_dir):
    root, media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "TAMX", "S01", 1) == 0
    assert _run(root, "TAMX") == 0
    paths = cli._paths(root)
    ref_wav = root / "_scratch" / "TAMX" / "reference.wav"
    preprocess = root / "_scratch" / "TAMX" / "preprocess.json"
    meta = json.loads(preprocess.read_text(encoding="utf-8"))
    good_sha = meta["reference_sha256"]
    assert good_sha == sha256_file(ref_wav)
    assert meta["case_id"] == "TAMX"
    assert meta["audio_stream"] == "0:a:1"

    # Corrupt the WAV payload bytes (flip one sample byte in the middle).
    raw = bytearray(ref_wav.read_bytes())
    mid = len(raw) // 2
    raw[mid] ^= 0xFF
    ref_wav.write_bytes(bytes(raw))
    tampered_sha = sha256_file(ref_wav)
    assert tampered_sha != good_sha

    case = cli._load_case(cli._lookup_case_path(paths, "TAMX"))
    sources = cli._load_sources(paths["sources"])
    reused, audio_stream = cli._get_reference_audio(paths, case, sources)
    assert reused == ref_wav
    assert audio_stream == "0:a:1"
    fresh_decode = _decode(media, "0:a:1", tmp_path / "direct880.wav")
    assert sha256_file(ref_wav) == fresh_decode
    assert sha256_file(ref_wav) != tampered_sha
    meta = json.loads(preprocess.read_text(encoding="utf-8"))
    assert meta["reference_sha256"] == sha256_file(ref_wav)


# --- 4. proposal.json tamper -----------------------------------------------------


def test_proposal_tamper_is_refused_not_scored(tmp_path, fixture_dir):
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "PROPX", "S01", 1) == 0
    assert _run(root, "PROPX") == 0
    assert _score(root, "PROPX") == 0
    results = root / "results" / "PROPX" / "b1-n"
    assert (results / "score.json").is_file()

    prop = results / "proposal.json"
    tampered = prop.read_bytes().replace(
        b'"no changes proposed"', b'"no changes proposesd"'
    )
    assert tampered != prop.read_bytes()
    prop.write_bytes(tampered)

    captured_before = (results / "score.json").read_bytes()
    assert _score(root, "PROPX") == RC_STALE
    assert not (results / "score.json").exists()
    assert captured_before  # the refusal deletes, never overwrites with a new number


# --- 5. legacy / unverifiable artifacts ------------------------------------------


def test_hand_written_artifacts_without_run_provenance_are_refused(
    tmp_path, fixture_dir
):
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "LEGF", "S01", 1) == 0
    paths = cli._paths(root)
    case = cli._load_case(cli._lookup_case_path(paths, "LEGF"))
    times = Track.load(cli._resolve_generated(paths, case), case.fmt).time_map()
    d = root / "results" / "LEGF" / "b1-n"
    d.mkdir(parents=True)
    write_json(
        d / "proposal.json",
        ProposalRecord(
            case_id="LEGF",
            candidate_id="b1-n",
            mapping_status="noop",
            regions=[{"start_us": 0, "end_us": None, "offset_us": 0, "kind": "global"}],
            proposed_times_us=dict(times),
            unmapped_cue_ids=[],
            notes="hand-written legacy proposal",
        ).to_json(),
    )
    write_json(
        d / "score.json",
        {
            "schema_version": 2,
            "case_id": "LEGF",
            "candidate_id": "b1-n",
            "sentinel": "999999999-UNVERIFIED-NUMBER",
        },
    )
    assert _score(root, "LEGF") == RC_STALE
    assert not (d / "score.json").exists()
    rc = cli.main(["--root", str(root), "report", "--case", "LEGF"])
    assert rc == 0
    report = (root / "results" / "report.md").read_text(encoding="utf-8")
    assert "999999999-UNVERIFIED-NUMBER" not in report


def test_schema1_run_without_fingerprint_is_unverified(tmp_path, fixture_dir):
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "LEGL", "S01", 1) == 0
    assert _run(root, "LEGL") == 0
    assert _score(root, "LEGL") == 0
    d = root / "results" / "LEGL" / "b1-n"
    assert (d / "score.json").is_file()
    # Simulate a pre-F04 (schema 1) run.json: no fingerprint, no proposal hash.
    run = json.loads((d / "run.json").read_text(encoding="utf-8"))
    run.pop("input_fingerprint", None)
    run.pop("proposal_sha256", None)
    run["schema_version"] = 1
    write_json(d / "run.json", run)
    assert _score(root, "LEGL") == RC_STALE
    assert not (d / "score.json").exists()


# --- 6. negative control: fresh end-to-end pipeline ------------------------------


def test_fresh_pipeline_scores_and_reports(tmp_path, fixture_dir):
    root, _media = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "GOODX", "S01", 1) == 0
    assert _run(root, "GOODX") == 0
    assert _score(root, "GOODX") == 0
    run_meta = json.loads(
        (root / "results" / "GOODX" / "b1-n" / "run.json").read_text(encoding="utf-8")
    )
    assert run_meta["schema_version"] == 2
    score = json.loads(
        (root / "results" / "GOODX" / "b1-n" / "score.json").read_text(encoding="utf-8")
    )
    assert score["schema_version"] == 2
    assert "timing_errors_final_us" in score
    assert cli.main(["--root", str(root), "report", "--case", "GOODX"]) == 0
    report = (root / "results" / "report.md").read_text(encoding="utf-8")
    assert "GOODX" in report and "b1-n" in report
    assert f"input {run_meta['input_fingerprint'][:16]}" in report
