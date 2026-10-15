"""Milestone 1: prepared case manifests preserve the REGISTERED track id.

Regression coverage for the track-identity corrective benchmark:

* ``prepare_case`` takes an explicit ``track_id`` (the registered identifier);
  the manifest never derives the track identity from a sidecar file stem.
* Two sidecar tracks with the SAME filename in DIFFERENT directories under
  DIFFERENT registered ids keep distinct identities end to end: manifests,
  subtitle-language resolution (no cross-leakage), and fingerprint subtitle
  bindings are per-track.
* ``subtitle_languages`` is keyed ONLY by registered track ids (no stem
  aliases).
* Pre-fix stem-based manifests on disk fail closed at run/score with an
  actionable re-prepare message (never silently reinterpreted), and never
  render as comparative report rows.
* Re-registering the subtitle source at the same track id with a changed
  subtitle file (same media and audio) invalidates previously generated
  candidate results through the fingerprint, at score time, end to end.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from bench import cli
from bench.corrupt import prepare_case
from bench.fingerprint import fingerprint_payload
from bench.manifests import AcceptanceRecord, read_json, write_json

FFMPEG = shutil.which("ffmpeg")
# Applied per-test: the two pure prepare_case identity tests run without ffmpeg;
# only the CLI/media tests need it.
requires_ffmpeg = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg required")

RC_STALE = 6
RC_IDENTITY = 2
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


def _build_mkv(tmp_path: Path) -> Path:
    """Two sine audio streams (440 Hz jpn / 880 Hz eng); audio selection is stable."""
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


def _record(root: Path, source_id: str = "MS") -> dict:
    data = json.loads((root / "cases" / "sources.json").read_text(encoding="utf-8"))
    return data["sources"][source_id]


def _prepare(
    root: Path, case_id: str, track: str, scenario: str = "S01", seed: int = 1
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


def _report(root: Path, case_id: str) -> tuple[int, str]:
    rc = cli.main(["--root", str(root), "report", "--case", case_id])
    return rc, (root / "results" / "report.md").read_text(encoding="utf-8")


def _case_manifest(root: Path, case_id: str) -> dict:
    p = cli._lookup_case_path(cli._paths(root), case_id)
    assert p is not None
    return read_json(p)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _cand_dir(root: Path, case_id: str, cand: str) -> Path:
    return root / "results" / case_id / cand


def _capture_validate(monkeypatch):
    """Replace cli.validate_proposal with a recorder (no ASR/model access)."""
    captured: dict = {}

    def _fake_validate(*args, **kwargs):
        captured["args"] = args
        captured.update(kwargs)
        return AcceptanceRecord(
            case_id=args[0].case_id,
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
    for var in ASR_ENV:
        monkeypatch.delenv(var, raising=False)
    return captured


def _register_two_same_name(tmp_path: Path, fixture_dir: Path) -> Path:
    """Two sidecar tracks, SAME filename in DIFFERENT dirs, ids mainA/mainB."""
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    a_side = tmp_path / "dirA" / "episode.ass"
    b_side = tmp_path / "dirB" / "episode.ass"
    a_side.parent.mkdir(parents=True)
    b_side.parent.mkdir(parents=True)
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
                f"mainA=sidecar:{a_side}",
                "--subtitle",
                f"mainB=sidecar:{b_side}",
                "--subtitle-language",
                "mainA=eng",
                "--subtitle-language",
                "mainB=kor",
            ),
        )
        == 0
    )
    return root


# ---------------------------------------------------------------------------
# 1. prepare_case identity is the registered id, explicitly passed
# ---------------------------------------------------------------------------


def test_prepare_case_requires_explicit_track_id(fixture_dir, tmp_path):
    """No path-derived identity: prepare_case refuses without an explicit track_id."""
    with pytest.raises(TypeError):
        prepare_case(
            "Fx00", "m1-req", "S00", 1, fixture_dir / "episode.ass", tmp_path / "a.ass"
        )


def test_prepare_case_track_id_is_not_the_file_stem(fixture_dir, tmp_path):
    case = prepare_case(
        "Fx00",
        "m1-id",
        "S00",
        1,
        fixture_dir / "episode.ass",
        tmp_path / "a.ass",
        track_id="registered-main",
    )
    assert case.track_id == "registered-main"
    assert case.track_id != (fixture_dir / "episode.ass").stem  # not path-derived
    assert case.to_json()["track_id"] == "registered-main"


@requires_ffmpeg
def test_registered_sidecar_manifest_preserves_registered_id(tmp_path, fixture_dir):
    root = tmp_path / "benchroot"
    media = _build_mkv(tmp_path)
    sidecar = tmp_path / "episode.ass"
    shutil.copy2(fixture_dir / "episode.ass", sidecar)
    assert (
        _cli_add(
            root,
            media,
            (
                "--audio",
                "lang:eng",
                "--subtitle",
                f"main=sidecar:{sidecar}",
                "--subtitle-language",
                "main=kor",
            ),
        )
        == 0
    )
    assert _prepare(root, "M1ONE", "main") == 0
    manifest = _case_manifest(root, "M1ONE")
    assert manifest["track_id"] == "main"
    # stem-alias bridge is gone: languages keyed ONLY by registered track ids
    assert _record(root)["subtitle_languages"] == {"main": "kor"}


# ---------------------------------------------------------------------------
# 2. two same-named sidecar tracks keep distinct identities
# ---------------------------------------------------------------------------


@requires_ffmpeg
def test_two_same_name_sidecar_tracks_preserve_distinct_ids(
    tmp_path, fixture_dir, capsys
):
    root = _register_two_same_name(tmp_path, fixture_dir)
    capsys.readouterr()
    assert _prepare(root, "M1A", "mainA") == 0
    assert _prepare(root, "M1B", "mainB") == 0
    capsys.readouterr()

    ma = _case_manifest(root, "M1A")
    mb = _case_manifest(root, "M1B")
    assert ma["track_id"] == "mainA"
    assert mb["track_id"] == "mainB"

    record = _record(root)
    # No basename aliases exist: the registry keys are exactly the registered ids.
    assert set(record["subtitle_languages"]) == {"mainA", "mainB"}
    assert "episode" not in record["subtitle_languages"]

    # Fingerprint subtitle bindings are per-track, distinct, and bound to the
    # real registered spec + sha (never None for a registered track).
    pa = fingerprint_payload(ma_case := _load_case(root, "M1A"), record, "b1-n")
    pb = fingerprint_payload(mb_case := _load_case(root, "M1B"), record, "b1-n")
    assert pa["case"]["track_id"] == "mainA"
    assert pb["case"]["track_id"] == "mainB"
    assert pa["subtitle_input"]["spec"] == record["subtitle_specs"]["mainA"]
    assert pb["subtitle_input"]["spec"] == record["subtitle_specs"]["mainB"]
    assert pa["subtitle_input"]["sha256"] == record["subtitle_sha256"]["mainA"]
    assert pb["subtitle_input"]["sha256"] == record["subtitle_sha256"]["mainB"]
    assert pa["subtitle_input"]["spec"] != pb["subtitle_input"]["spec"]
    assert pa["subtitle_input"]["sha256"] == pb["subtitle_input"]["sha256"]
    # Same content, different identity: the bound spec path keeps the fingerprints distinct.
    from bench.fingerprint import compute_input_fingerprint

    assert compute_input_fingerprint(
        ma_case, record, "b1-n"
    ) != compute_input_fingerprint(mb_case, record, "b1-n")


def _load_case(root: Path, case_id: str):
    paths = cli._paths(root)
    return cli._load_case(cli._lookup_case_path(paths, case_id))


@requires_ffmpeg
def test_two_same_name_sidecar_language_resolution_no_cross_leakage(
    tmp_path, fixture_dir, monkeypatch, capsys
):
    root = _register_two_same_name(tmp_path, fixture_dir)
    capsys.readouterr()
    assert _prepare(root, "M1LA", "mainA") == 0
    assert _prepare(root, "M1LB", "mainB") == 0
    assert _run(root, "M1LA") == 0
    assert _run(root, "M1LB") == 0
    capsys.readouterr()

    captured_a = _capture_validate(monkeypatch)
    assert _run_va(root, "M1LA") == 0
    assert captured_a["subtitle_language"] == "eng"  # mainA's own hint
    assert captured_a["args"][8] == "eng"  # audio identity, unchanged routing

    captured_b = _capture_validate(monkeypatch)
    assert _run_va(root, "M1LB") == 0
    assert captured_b["subtitle_language"] == "kor"  # mainB's own hint, never a leak
    assert captured_b["args"][8] == "eng"


# ---------------------------------------------------------------------------
# 3. existing (pre-fix, stem-based) manifests fail closed, never reinterpreted
# ---------------------------------------------------------------------------


def _stem_rewrite_manifest(root: Path, case_id: str) -> Path:
    """Simulate an on-disk pre-fix manifest: track_id persisted as the file stem."""
    manifest_path = cli._lookup_case_path(cli._paths(root), case_id)
    assert manifest_path is not None
    manifest = read_json(manifest_path)
    manifest["track_id"] = "episode"  # the pre-fix stem value for sidecar episode.ass
    write_json(manifest_path, manifest)
    return manifest_path


@requires_ffmpeg
def test_legacy_stem_manifest_fails_closed_at_run_and_score(
    tmp_path, fixture_dir, capsys
):
    root = tmp_path / "benchroot"
    media = _build_mkv(tmp_path)
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
    assert _prepare(root, "M1STEM", "main") == 0
    _stem_rewrite_manifest(root, "M1STEM")
    capsys.readouterr()

    rc = _run(root, "M1STEM")
    captured = capsys.readouterr()
    assert rc == RC_IDENTITY
    assert "episode" in captured.err
    assert "not registered" in captured.err
    assert "prepare the case" in captured.err.lower()
    # fail closed BEFORE any fingerprint/candidate work: no run artifacts, no audio decode
    assert not (root / "_scratch" / "M1STEM" / "reference.wav").exists()
    assert not (root / "results" / "M1STEM" / "b1-n").exists()

    rc = _score(root, "M1STEM")
    captured = capsys.readouterr()
    assert rc == RC_IDENTITY
    assert "not registered" in captured.err
    assert "prepare the case" in captured.err.lower()


@requires_ffmpeg
def test_legacy_stem_manifest_report_is_never_comparative(
    tmp_path, fixture_dir, capsys
):
    root = tmp_path / "benchroot"
    media = _build_mkv(tmp_path)
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
    assert _prepare(root, "M1RPT", "main") == 0
    assert _run(root, "M1RPT") == 0
    assert _score(root, "M1RPT") == 0
    capsys.readouterr()
    rc, report = _report(root, "M1RPT")
    assert rc == 0
    assert (
        "## Case `M1RPT`" in report
    )  # positive control: valid manifest renders comparably
    assert "Unverified historical" not in report

    _stem_rewrite_manifest(root, "M1RPT")
    capsys.readouterr()
    rc, report = _report(root, "M1RPT")
    assert rc == 0
    # deliberate, labeled fail-closed: never a comparative row for the unregistered identity
    assert "## Case `M1RPT`" not in report
    assert "Unverified historical" in report


# ---------------------------------------------------------------------------
# 4. re-registering a changed subtitle source invalidates candidate results
# ---------------------------------------------------------------------------


@requires_ffmpeg
def test_changed_registered_subtitle_invalidates_prior_candidate_results(
    tmp_path, fixture_dir, capsys
):
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    sidecar_a = tmp_path / "dirA" / "episode.ass"
    sidecar_a.parent.mkdir(parents=True)
    shutil.copy2(fixture_dir / "episode.ass", sidecar_a)
    assert (
        _cli_add(
            root,
            media,
            (
                "--audio",
                "lang:eng",
                "--subtitle",
                f"main=sidecar:{sidecar_a}",
                "--subtitle-language",
                "main=eng",
            ),
        )
        == 0
    )
    assert _prepare(root, "M1SUB", "main") == 0
    assert _run(root, "M1SUB") == 0
    assert _score(root, "M1SUB") == 0
    d = _cand_dir(root, "M1SUB", "b1-n")
    assert (d / "score.json").is_file()
    capsys.readouterr()

    # Re-register the SAME track id with a CHANGED subtitle file (same media, same audio).
    sidecar_b = tmp_path / "dirB" / "episode.ass"
    sidecar_b.parent.mkdir(parents=True)
    sidecar_b.write_text(
        sidecar_a.read_text(encoding="utf-8") + "M1-SUBTITLE-CHANGE-MARKER\n",
        encoding="utf-8",
    )
    registry_path = root / "cases" / "sources.json"
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    del data["sources"]["MS"]
    registry_path.write_text(json.dumps(data), encoding="utf-8")
    assert (
        _cli_add(
            root,
            media,
            (
                "--audio",
                "lang:eng",
                "--subtitle",
                f"main=sidecar:{sidecar_b}",
                "--subtitle-language",
                "main=eng",
            ),
        )
        == 0
    )

    # The prior generation's score must be refused (STALE), not silently reused.
    rc = _score(root, "M1SUB")
    captured = capsys.readouterr()
    assert rc == RC_STALE
    assert "STALE" in captured.err
    assert not (d / "score.json").exists()

    rc, report = _report(root, "M1SUB")
    assert rc == 0
    assert "| b1-n |" not in report  # the obsolete number never renders comparably

    # Re-running the candidate against the current subtitle binding restores scoring.
    assert _run(root, "M1SUB") == 0
    assert _score(root, "M1SUB") == 0
    assert (d / "score.json").is_file()
    rc, report = _report(root, "M1SUB")
    assert rc == 0
    assert "| b1-n |" in report
