"""Review-batch hardening: report write order, reserved device ids, rights
coherence, zero-audio refusal posture."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from bench import cli
from bench.paths import is_safe_id
from bench.reporting import write_report

# --- F1: write_report validates BEFORE creating anything ---------------------


def test_write_report_creates_no_parents_when_refused(tmp_path):
    root = tmp_path / "benchroot"
    (root / "results").mkdir(parents=True)
    from bench import paths

    paths.configure([root / "results"], [], [])
    refused_parent = tmp_path / "evil"
    with pytest.raises(RuntimeError, match="not inside a scratch root"):
        write_report(refused_parent / "deep" / "escape.md", "x")
    assert not refused_parent.exists()  # no directory creation on refusal
    ok = root / "results" / "nested" / "deeper" / "report.md"
    write_report(ok, "content")
    assert ok.is_file()


def test_report_cli_refuses_without_parent_creation(tmp_path, capsys):
    root = tmp_path / "benchroot"
    out = tmp_path / "outside" / "deep" / "report.md"
    rc = cli.main(["--root", str(root), "report", "--out", str(out)])
    captured = capsys.readouterr()
    assert rc == 5
    assert "REFUSED" in captured.err
    assert not (tmp_path / "outside").exists()
    rc = cli.main(
        [
            "--root",
            str(root),
            "report",
            "--out",
            str(root / "results" / "sub" / "dir" / "report.md"),
        ]
    )
    assert rc == 0
    assert (root / "results" / "sub" / "dir" / "report.md").is_file()


# --- F4: Windows reserved device names / trailing punctuation ----------------


def test_reserved_device_names_and_trailing_dots_refused():
    for bad in (
        "CON",
        "con",
        "NUL",
        "nul.txt",
        "COM1",
        "com9",
        "LPT3",
        "PRN",
        "AUX",
        "aux.log",
        "CON.txt",
        "a.",
        "a.b.",
    ):
        assert not is_safe_id(bad), bad
    for good in (
        "Fx00",
        "main",
        "a.b_c-1",
        "FX00-S01",
        "signs.ass",
        "con3sole",
        "nightly",
    ):
        assert is_safe_id(good), good


def test_cli_source_add_refuses_reserved_device_ids(tmp_path, capsys):
    root = tmp_path / "benchroot"
    fx = root / "fx"
    fx.mkdir(parents=True)
    src = Path(__file__).resolve().parent.parent / "fixtures" / "Fx00"
    shutil.copy2(src / "reference.wav", fx / "reference.wav")
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            str(fx / "reference.wav"),
            "--source-id",
            "NUL",
            "--rights",
            "private-local",
        ]
    )
    assert rc == 2
    captured = capsys.readouterr()
    assert "not a safe id" in captured.err
    assert not (root / "cases" / "sources.json").exists()


# --- F5: rights enumeration + synthetic-home coherence -----------------------


def test_source_add_refuses_unknown_rights_values(tmp_path):
    root = tmp_path / "benchroot"
    fx = root / "fx"
    fx.mkdir(parents=True)
    src = Path(__file__).resolve().parent.parent / "fixtures" / "Fx00"
    shutil.copy2(src / "reference.wav", fx / "reference.wav")
    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            [
                "--root",
                str(root),
                "source",
                "add",
                "--path",
                str(fx / "reference.wav"),
                "--source-id",
                "R1",
                "--rights",
                "public-domain-miracle",
            ]
        )
    assert excinfo.value.code == 2
    assert not (root / "cases" / "sources.json").exists()


def test_synthetic_rights_require_fixtures_home(tmp_path, capsys):
    root = tmp_path / "benchroot"
    fx = root / "fx"
    fx.mkdir(parents=True)
    src_dir = Path(__file__).resolve().parent.parent / "fixtures" / "Fx00"
    shutil.copy2(src_dir / "reference.wav", fx / "reference.wav")
    shutil.copy2(src_dir / "episode.ass", fx / "episode.ass")
    # tmp copies are OUTSIDE the committed fixtures home -> synthetic claim refused
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            str(fx / "reference.wav"),
            "--source-id",
            "FAKEFX",
            "--subtitle",
            f"main=sidecar:{fx / 'episode.ass'}",
            "--rights",
            "redistributable-synthetic-fixture",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "REFUSED (rights claim)" in captured.err
    assert "private-local" in captured.err
    assert not (root / "cases" / "sources.json").exists()
    # same data as private-local: accepted (control)
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            str(fx / "reference.wav"),
            "--source-id",
            "PRIVFX",
            "--subtitle",
            f"main=sidecar:{fx / 'episode.ass'}",
            "--rights",
            "private-local",
        ]
    )
    assert rc == 0
    # committed fixtures + synthetic rights: accepted (canonical flow)
    repo_root = Path(__file__).resolve().parents[2]
    monkeycwd = Path.cwd()
    try:
        os.chdir(repo_root)
        rc = cli.main(
            [
                "--root",
                str(root),
                "source",
                "add",
                "--path",
                "benchmarks/fixtures/Fx00/reference.wav",
                "--source-id",
                "FXTRUE",
                "--subtitle",
                "main=sidecar:benchmarks/fixtures/Fx00/episode.ass",
                "--rights",
                "redistributable-synthetic-fixture",
            ]
        )
        assert rc == 0
    finally:
        os.chdir(monkeycwd)


# --- F8: zero-audio media refuses at run time (no traceback) -----------------


def test_zero_audio_media_fails_closed_without_ffmpeg(tmp_path):
    from bench.cli import StreamSelectionError
    from bench.manifests import CaseManifest

    paths_dict = cli._paths(tmp_path / "root")
    media = tmp_path / "subs-only.mkv"
    media.write_bytes(b"stub")
    case = CaseManifest(
        case_id="c1",
        source_id="Z",
        scenario="S00",
        seed=1,
        track_id="main",
        fmt="ass",
        grid_us=10_000,
        params={},
        transform={},
        expected_inverse={},
        injected_cue_deltas={},
        original_times_us={},
        true_breakpoints_us=[],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )
    sources = {
        "sources": {
            "Z": {
                "media_path": str(media),
                "streams": [{"index": 0, "codec_type": "subtitle"}],
            }
        }
    }
    with pytest.raises(StreamSelectionError, match="no audio stream"):
        cli._get_reference_audio(paths_dict, case, sources)
