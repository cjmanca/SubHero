"""Fifth-review Milestone 1: report generation verifies the ACTUAL input files.

Report generation must enforce the same source-integrity checks `run` and
`score` enforce — registered media exists and matches its recorded fingerprint,
registered sidecars still match their fingerprints, and the generated case
input matches the case manifest — BEFORE a case's run/score pair is rendered
as a current comparative result. A verified-failed case falls to the labeled
unverified-historical section (fail-closed), its reason is stated there, and
restoring the original files restores comparative eligibility without rerunning
any candidate. Verification is read-only: it never modifies source files, and
one report generation hashes a shared source's full episode at most once.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from bench import cli

FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg required")


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
        "-i",
        str(a440),
        "-map",
        "0:a:0",
        "-c:a",
        "pcm_s16le",
        "-metadata:s:a:0",
        "language=eng",
        str(out),
    )
    return out


def _setup(tmp_path: Path, fixture_dir: Path) -> tuple[Path, Path, Path]:
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    sidecar = tmp_path / "episode.ass"
    shutil.copy2(fixture_dir / "episode.ass", sidecar)
    assert (
        cli.main(
            [
                "--root",
                str(root),
                "source",
                "add",
                "--path",
                str(media),
                "--source-id",
                "RI",
                "--rights",
                "private-local",
                "--audio",
                "lang:eng",
                "--subtitle",
                f"main=sidecar:{sidecar}",
            ]
        )
        == 0
    )
    return root, media, sidecar


def _prepare(root: Path, case_id: str, scenario: str = "S01", seed: int = 1) -> int:
    return cli.main(
        [
            "--root",
            str(root),
            "case",
            "prepare",
            "--source-id",
            "RI",
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


def _run_score(root: Path, case_id: str) -> None:
    assert (
        cli.main(["--root", str(root), "run", "--case", case_id, "--candidate", "b1-n"])
        == 0
    )
    assert (
        cli.main(
            ["--root", str(root), "score", "--case", case_id, "--candidate", "b1-n"]
        )
        == 0
    )


def _report(root: Path, *case_ids: str) -> tuple[int, str]:
    argv = ["--root", str(root), "report"]
    for cid in case_ids:
        argv += ["--case", cid]
    rc = cli.main(argv)
    return rc, (root / "results" / "report.md").read_text(encoding="utf-8")


def _generated(root: Path, case_id: str) -> Path:
    paths = cli._paths(root)
    case = cli._load_case(cli._lookup_case_path(paths, case_id))
    return cli._resolve_generated(paths, case)


def _comparative_has_row(report: str, cand: str = "| b1-n |") -> bool:
    marker = "## Unverified historical results (NOT COMPARABLE)"
    lines = report.splitlines()
    if marker not in lines:
        return any(ln.startswith(cand) for ln in lines)
    idx = lines.index(marker)
    return any(ln.startswith(cand) for ln in lines[:idx])


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_unchanged_case_reports_comparatively(tmp_path, fixture_dir):
    root, _media, _sidecar = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "RI1") == 0
    _run_score(root, "RI1")
    rc, report = _report(root, "RI1")
    assert rc == 0
    assert _comparative_has_row(report)
    assert "Unverified historical results" not in report


def test_modified_generated_case_input_invalidates_current_results(
    tmp_path, fixture_dir
):
    root, _media, _sidecar = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "RI2") == 0
    _run_score(root, "RI2")
    rc, report = _report(root, "RI2")
    assert rc == 0 and _comparative_has_row(report)

    gen = _generated(root, "RI2")
    original_bytes = gen.read_bytes()
    gen.write_bytes(original_bytes + b"; tampered input\n")
    rc, report = _report(root, "RI2")
    assert rc == 0
    assert not _comparative_has_row(report), (
        "tampered generated input must not render comparably"
    )
    marker = "## Unverified historical results (NOT COMPARABLE)"
    lines = report.splitlines()
    idx = lines.index(marker)
    assert any("RI2" in ln and "b1-n" in ln for ln in lines[idx:])
    assert "case input no longer matches case manifest fingerprint" in report


def test_restoring_original_files_restores_eligibility_without_reruns(
    tmp_path, fixture_dir
):
    root, media, sidecar = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "RI3") == 0
    _run_score(root, "RI3")
    gen = _generated(root, "RI3")
    gen_bytes = gen.read_bytes()
    sidecar_bytes = sidecar.read_bytes()
    media_bytes = media.read_bytes()

    gen.write_bytes(b"Dialogue: 0,0:01:00,0:01:05,Default,,0,0,0,,tampered\n")
    sidecar.write_bytes(sidecar_bytes + b"; tampered\n")
    media.write_bytes(media_bytes + b"\x00tampered")
    rc, report = _report(root, "RI3")
    assert rc == 0
    assert not _comparative_has_row(report)
    assert "Unverified historical results (NOT COMPARABLE)" in report

    gen.write_bytes(gen_bytes)
    sidecar.write_bytes(sidecar_bytes)
    media.write_bytes(media_bytes)
    # No candidate re-run and no re-score between breakage and restoration.
    rc, report = _report(root, "RI3")
    assert rc == 0
    assert _comparative_has_row(report), "restored inputs must restore eligibility"
    assert "Unverified historical results" not in report


def test_missing_source_media_invalidates_current_results(tmp_path, fixture_dir):
    root, media, _sidecar = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "RI4") == 0
    _run_score(root, "RI4")
    media.unlink()
    rc, report = _report(root, "RI4")
    assert rc == 0
    assert not _comparative_has_row(report)
    assert "registered media file missing" in report


def test_modified_source_media_invalidates_current_results(tmp_path, fixture_dir):
    root, media, _sidecar = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "RI5") == 0
    _run_score(root, "RI5")
    media.write_bytes(media.read_bytes() + b"\x00mutated")
    rc, report = _report(root, "RI5")
    assert rc == 0
    assert not _comparative_has_row(report)
    assert "SOURCE MUTATION DETECTED: media fingerprint changed" in report


def test_modified_sidecar_invalidates_current_results(tmp_path, fixture_dir):
    root, _media, sidecar = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "RI6") == 0
    _run_score(root, "RI6")
    sidecar.write_bytes(sidecar.read_bytes() + b"; mutated sidecar\n")
    rc, report = _report(root, "RI6")
    assert rc == 0
    assert not _comparative_has_row(report)
    assert "SOURCE MUTATION DETECTED: subtitle main fingerprint changed" in report


def test_verification_never_modifies_source_files(tmp_path, fixture_dir):
    from bench.media import sha256_file

    root, media, sidecar = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "RI7") == 0
    _run_score(root, "RI7")
    before = {
        "media": sha256_file(media),
        "sidecar": sha256_file(sidecar),
        "generated": sha256_file(_generated(root, "RI7")),
    }
    # Break the generated input, report (verification reads every source), restore.
    gen = _generated(root, "RI7")
    gen_bytes = gen.read_bytes()
    gen.write_bytes(gen_bytes + b"; read-only probe\n")
    rc, _report_text = _report(root, "RI7")
    assert rc == 0
    gen.write_bytes(gen_bytes)
    after = {
        "media": sha256_file(media),
        "sidecar": sha256_file(sidecar),
        "generated": sha256_file(_generated(root, "RI7")),
    }
    assert after == before


def test_case_evidence_missing_enforces_file_integrity_for_library_callers(
    tmp_path, fixture_dir
):
    root, media, sidecar = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "RI10") == 0
    _run_score(root, "RI10")
    paths = cli._paths(root)
    sources = cli._load_sources(paths["sources"])
    cache: dict[str, str] = {}
    assert cli._case_evidence_missing(paths, "RI10", sources, cache) is False

    gen = _generated(root, "RI10")
    gen_bytes = gen.read_bytes()
    gen.write_bytes(gen_bytes + b"; mutated\n")
    cache2: dict[str, str] = {}
    assert cli._case_evidence_missing(paths, "RI10", sources, cache2) is True
    gen.write_bytes(gen_bytes)
    assert cli._case_evidence_missing(paths, "RI10", sources, {}) is False

    sidecar_bytes = sidecar.read_bytes()
    sidecar.write_bytes(sidecar_bytes + b"; mutated\n")
    assert cli._case_evidence_missing(paths, "RI10", sources, {}) is True
    sidecar.write_bytes(sidecar_bytes)
    assert cli._case_evidence_missing(paths, "RI10", sources, {}) is False

    media_bytes = media.read_bytes()
    media.unlink()
    assert cli._case_evidence_missing(paths, "RI10", sources, {}) is True
    media.write_bytes(media_bytes)
    assert cli._case_evidence_missing(paths, "RI10", sources, {}) is False


def test_report_hashes_shared_source_media_once_per_generation(
    tmp_path, fixture_dir, monkeypatch
):
    root, media, _sidecar = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "RI8", seed=1) == 0
    assert _prepare(root, "RI9", seed=2) == 0
    _run_score(root, "RI8")
    _run_score(root, "RI9")

    media_key = str(media.resolve())
    calls: list[str] = []
    real = cli.sha256_file

    def counting_sha256_file(p: Path) -> str:
        calls.append(str(Path(p).resolve()))
        return real(p)

    monkeypatch.setattr(cli, "sha256_file", counting_sha256_file)
    rc, report = _report(root, "RI8", "RI9")
    assert rc == 0
    assert _comparative_has_row(report)
    assert calls.count(media_key) == 1, (
        f"full media file hashed {calls.count(media_key)} times in one report "
        f"generation: {calls}"
    )
