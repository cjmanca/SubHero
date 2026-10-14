"""F05 hardening: rights-aware home policy and Git-ignored custom-root safety.

Disposable git checkouts model running the harness from a fresh clone: the CLI's
``REPO_ROOT``/``DEFAULT_ROOT`` are monkeypatched onto the checkout so the real
in-repo policy/root code paths are exercised, and git ``check-ignore`` proves the
private-data escape routes (tracked fixtures, fresh in-repo roots) are refused
while the canonical default root, out-of-repo roots, ignored private sub-roots,
and synthetic fixture registrations keep working.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from bench import cli

BENCH_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BENCH_ROOT.parent
FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(
    FFMPEG is None, reason="ffmpeg required for MKV probing"
)


def _git() -> str:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not available")
    probe = subprocess.run(
        [git, "rev-parse", "--show-toplevel"],
        check=False,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        pytest.skip("not inside a git repository")
    return git


def _git_run(git: str, cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [git, "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _build_mkv(dest: Path) -> Path:
    """Tiny real MKV (one sine audio stream + one ASS subtitle) for ffprobe."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    wav = dest.parent / f"{dest.stem}-audio.wav"
    srt = dest.parent / f"{dest.stem}.srt"
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-c:a",
            "pcm_s16le",
            str(wav),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nF05MARKER\n", encoding="utf-8")
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-v",
            "error",
            "-i",
            str(wav),
            "-i",
            str(srt),
            "-map",
            "0:a:0",
            "-map",
            "1:s:0",
            "-c:a",
            "copy",
            "-c:s",
            "ass",
            "-metadata:s:s:0",
            "language=eng",
            str(dest),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return dest


def _make_checkout(tmp_path: Path) -> Path:
    """Disposable git checkout carrying the repo's .gitignore + fixtures layout."""
    git = _git()
    co = tmp_path / "checkout"
    co.mkdir()
    subprocess.run(
        [git, "-c", "init.defaultBranch=main", "init", "-q", str(co)],
        check=True,
        capture_output=True,
        text=True,
    )
    shutil.copy2(REPO_ROOT / ".gitignore", co / ".gitignore")
    src_fx = REPO_ROOT / "benchmarks" / "fixtures"
    dst_fx = co / "benchmarks" / "fixtures"
    shutil.copytree(src_fx / "Fx00", dst_fx / "Fx00")
    shutil.copy2(src_fx / "make_fixture.py", dst_fx / "make_fixture.py")
    priv = co / "benchmarks" / "private"
    priv.mkdir(parents=True)
    shutil.copy2(REPO_ROOT / "benchmarks" / "private" / "README.md", priv / "README.md")
    _git_run(git, co, "add", "-A")
    _git_run(
        git,
        co,
        "-c",
        "user.email=f05@example.com",
        "-c",
        "user.name=f05",
        "commit",
        "-q",
        "-m",
        "init fixtures",
    )
    return co


def _point_cli_at_checkout(monkeypatch, co: Path) -> Path:
    """Make the CLI treat the disposable checkout as its repository root."""
    monkeypatch.setattr(cli, "REPO_ROOT", co)
    default = co / "benchmarks"
    monkeypatch.setattr(cli, "DEFAULT_ROOT", default)
    return default


def _status_porcelain(git: str, co: Path) -> str:
    return _git_run(git, co, "status", "--porcelain").stdout


def _add_dry_run(git: str, co: Path) -> str:
    return _git_run(git, co, "add", "-A", "--dry-run").stdout


def _check_ignore(git: str, co: Path, rel: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [git, "-C", str(co), "check-ignore", "-v", "--", rel],
        check=False,
        capture_output=True,
        text=True,
    )


# --- Fixtures escape (acceptance 1): private-local in fixtures refused ----------


def test_private_local_registration_in_fixtures_home_is_refused(
    tmp_path, monkeypatch, capsys
):
    co = _make_checkout(tmp_path)
    _point_cli_at_checkout(monkeypatch, co)
    root = co / "benchmarks"
    fx = co / "benchmarks" / "fixtures" / "E01"
    media = _build_mkv(fx / "episode.mkv")
    sidecar = fx / "episode.ass"
    sidecar.write_text(
        "[Events]\nDialogue: 0,0:00:01.00,0:00:02.00,,0,0,0,,hi\n", encoding="utf-8"
    )
    gold = fx / "gold.json"
    gold.write_text(json.dumps({"1": "speech_like"}), encoding="utf-8")
    registry = root / "cases" / "sources.json"

    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            str(media),
            "--source-id",
            "PVT",
            "--subtitle",
            f"main=sidecar:{sidecar}",
            "--gold",
            f"main={gold}",
            "--rights",
            "private-local",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "REFUSED (private data policy)" in captured.err
    assert not registry.exists()

    # same files declared as redistributable synthetic fixtures: accepted
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            str(media),
            "--source-id",
            "SYN",
            "--subtitle",
            f"main=sidecar:{sidecar}",
            "--gold",
            f"main={gold}",
            "--rights",
            cli.SYNTHETIC_RIGHTS,
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0, captured.out + captured.err
    record = json.loads(registry.read_text(encoding="utf-8"))["sources"]["SYN"]
    assert record["rights_status"] == cli.SYNTHETIC_RIGHTS


# --- Custom-root escape (acceptance 2) -----------------------------------------


def test_custom_in_repo_root_is_refused(tmp_path, monkeypatch, capsys):
    co = _make_checkout(tmp_path)
    _point_cli_at_checkout(monkeypatch, co)
    capsys.readouterr()
    rc = cli.main(["--root", str(co / "benchmarks" / "custom-root"), "case", "list"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "REFUSED (--root)" in captured.err
    assert not (co / "benchmarks" / "custom-root").exists()


def test_default_and_out_of_repo_roots_are_accepted(tmp_path, monkeypatch, capsys):
    co = _make_checkout(tmp_path)
    _point_cli_at_checkout(monkeypatch, co)
    capsys.readouterr()
    # canonical default root (the checkout's benchmarks dir)
    assert cli.main(["--root", str(co / "benchmarks"), "case", "list"]) == 0
    # out-of-repo root
    out = tmp_path / "mnt" / "benchroot"
    assert cli.main(["--root", str(out), "case", "list"]) == 0


def test_git_ignored_in_repo_root_exception_is_accepted(tmp_path, monkeypatch, capsys):
    co = _make_checkout(tmp_path)
    git = _git()
    _point_cli_at_checkout(monkeypatch, co)
    capsys.readouterr()
    root = co / "benchmarks" / "private" / "nested-root"
    media = _build_mkv(tmp_path / "mnt" / "media" / "episode.mkv")
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            str(media),
            "--source-id",
            "NEST",
            "--rights",
            "private-local",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0, captured.out + captured.err

    generated = [
        "benchmarks/private/nested-root/cases/sources.json",
        "benchmarks/private/nested-root/_scratch",
        "benchmarks/private/nested-root/results",
        "benchmarks/private/nested-root/private",
    ]
    assert (root / "cases" / "sources.json").is_file()
    for rel in generated:
        assert _check_ignore(git, co, rel).returncode == 0, f"{rel} must be git-ignored"

    status = _status_porcelain(git, co)
    dry = _add_dry_run(git, co)
    for rel in generated:
        assert rel not in status
        assert rel not in dry
    assert "nested-root" not in status
    assert "nested-root" not in dry


# --- Canonical private registration (acceptance 3) -----------------------------


def test_canonical_private_registration_works_and_is_ignored(
    tmp_path, monkeypatch, capsys
):
    co = _make_checkout(tmp_path)
    git = _git()
    _point_cli_at_checkout(monkeypatch, co)
    capsys.readouterr()
    root = co / "benchmarks"
    priv = co / "benchmarks" / "private" / "E01"
    media = _build_mkv(priv / "episode.mkv")
    sidecar = priv / "episode.ass"
    sidecar.write_text(
        "[Events]\nDialogue: 0,0:00:01.00,0:00:02.00,,0,0,0,,hi\n", encoding="utf-8"
    )
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            str(media),
            "--source-id",
            "PVT",
            "--subtitle",
            f"main=sidecar:{sidecar}",
            "--rights",
            "private-local",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0, captured.out + captured.err
    assert (root / "cases" / "sources.json").is_file()
    assert _check_ignore(git, co, "benchmarks/private/E01/episode.mkv").returncode == 0


# --- Unit coverage for the root rule (real repository globals) -----------------


def test_refuse_unsafe_root_real_repo_rules():
    _git()
    # canonical default root: allowed
    assert (
        cli._refuse_unsafe_root(cli.DEFAULT_ROOT, cli.REPO_ROOT, cli.DEFAULT_ROOT)
        is None
    )
    # out-of-repo root: allowed
    assert (
        cli._refuse_unsafe_root(
            Path("Z:/mnt/read-only/bench"), cli.REPO_ROOT, cli.DEFAULT_ROOT
        )
        is None
    )
    # ignored private sub-root: allowed
    nested = cli.REPO_ROOT / "benchmarks" / "private" / "nested-root"
    assert cli._refuse_unsafe_root(nested, cli.REPO_ROOT, cli.DEFAULT_ROOT) is None
    # ignored canonical dirs: allowed
    assert (
        cli._refuse_unsafe_root(
            cli.REPO_ROOT / "benchmarks" / "_scratch", cli.REPO_ROOT, cli.DEFAULT_ROOT
        )
        is None
    )
    assert (
        cli._refuse_unsafe_root(
            cli.REPO_ROOT / "benchmarks" / "results", cli.REPO_ROOT, cli.DEFAULT_ROOT
        )
        is None
    )


def test_refuse_unsafe_root_custom_in_repo_is_refused(tmp_path, capsys):
    _git()
    capsys.readouterr()
    custom = cli.REPO_ROOT / "benchmarks" / "custom-root"
    rc = cli._refuse_unsafe_root(custom, cli.REPO_ROOT, cli.DEFAULT_ROOT)
    captured = capsys.readouterr()
    assert rc == 2
    assert "REFUSED (--root)" in captured.err
    assert "not Git-ignored" in captured.err
