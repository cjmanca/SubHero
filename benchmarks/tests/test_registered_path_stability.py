"""F08: registered sidecar/gold paths are pinned to absolute paths at registration.

Relative user input is resolved against the CWD **at registration time** (the
exact path the private-data policy evaluated) and stored in the Git-ignored
local registry as a canonical absolute path, mirroring ``media_path``. Later
invocations from any other working directory must therefore resolve the same
files, while redistributable manifests keep only root-relative identifiers.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from bench import cli, paths
from bench.media import sha256_file

BENCH_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BENCH_ROOT.parent
GIT = shutil.which("git")
FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(
    GIT is None, reason="disposable git checkout required for path-stability tests"
)

SYNTH = cli.SYNTHETIC_RIGHTS


def _git_run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [GIT, "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _make_checkout(tmp_path: Path) -> Path:
    """Disposable checkout carrying the repo .gitignore + committed fixtures."""
    probe = subprocess.run(
        [GIT, "rev-parse", "--show-toplevel"],
        check=False,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        pytest.skip("not inside a git repository")
    co = tmp_path / "checkout"
    co.mkdir()
    subprocess.run(
        [GIT, "-c", "init.defaultBranch=main", "init", "-q", str(co)],
        check=True,
        capture_output=True,
        text=True,
    )
    shutil.copy2(REPO_ROOT / ".gitignore", co / ".gitignore")
    src_fx = REPO_ROOT / "benchmarks" / "fixtures"
    dst_fx = co / "benchmarks" / "fixtures"
    shutil.copytree(src_fx / "Fx00", dst_fx / "Fx00")
    priv = co / "benchmarks" / "private"
    priv.mkdir(parents=True)
    shutil.copy2(REPO_ROOT / "benchmarks" / "private" / "README.md", priv / "README.md")
    _git_run(co, "add", "-A")
    _git_run(
        co,
        "-c",
        "user.email=f08@example.com",
        "-c",
        "user.name=f08",
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
    paths.configure(
        [
            default / "cases",
            default / "_scratch",
            default / "results",
            default / "private",
        ],
        [default / "fixtures"],
        [],
    )
    return default


def _registry(root: Path, source_id: str) -> dict:
    data = json.loads((root / "cases" / "sources.json").read_text(encoding="utf-8"))
    return data["sources"][source_id]


def _register_synthetic_relative(root: Path, source_id: str) -> None:
    """Register Fx00 with README-style relative paths, CWD = checkout repo root."""
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            "benchmarks/fixtures/Fx00/reference.wav",
            "--source-id",
            source_id,
            "--subtitle",
            "episode=sidecar:benchmarks/fixtures/Fx00/episode.ass",
            "--gold",
            "episode=benchmarks/fixtures/Fx00/gold_episode.json",
            "--rights",
            SYNTH,
        ]
    )
    assert rc == 0


def test_registry_stores_resolved_absolute_sidecar_and_gold_paths(
    tmp_path, monkeypatch, capsys
):
    """Acceptance 1: registration pins relative sidecar/gold input to absolute paths."""
    co = _make_checkout(tmp_path)
    root = _point_cli_at_checkout(monkeypatch, co)
    monkeypatch.chdir(co)
    _register_synthetic_relative(root, "Fx00")
    capsys.readouterr()

    record = _registry(root, "Fx00")
    fx = (co / "benchmarks" / "fixtures" / "Fx00").resolve()
    assert record["subtitle_specs"]["episode"] == f"sidecar:{fx / 'episode.ass'}"
    assert Path(
        record["subtitle_specs"]["episode"].removeprefix("sidecar:")
    ).is_absolute()
    assert record["gold_classification"]["episode"] == str(fx / "gold_episode.json")
    assert Path(record["gold_classification"]["episode"]).is_absolute()
    # media_path behavior is unchanged: canonical absolute path of the registered media
    assert record["media_path"] == str(fx / "reference.wav")
    assert record["subtitle_sha256"]["episode"]


def test_stored_path_is_the_exact_policy_checked_path(tmp_path, monkeypatch, capsys):
    """Stored absolute paths are the resolved targets the private-data policy evaluated."""
    co = _make_checkout(tmp_path)
    root = _point_cli_at_checkout(monkeypatch, co)
    media = tmp_path / "mnt" / "media" / "reference.wav"
    media.parent.mkdir(parents=True)
    shutil.copy2(BENCH_ROOT / "fixtures" / "Fx00" / "reference.wav", media)
    priv_sidecar = root / "private" / "E01" / "episode.ass"
    priv_sidecar.parent.mkdir(parents=True)
    shutil.copy2(root / "fixtures" / "Fx00" / "episode.ass", priv_sidecar)
    priv_gold = root / "private" / "transcripts" / "gold.json"
    priv_gold.parent.mkdir(parents=True)
    shutil.copy2(root / "fixtures" / "Fx00" / "gold_episode.json", priv_gold)
    # CWD = benchmarks dir, so the relative input resolves into the private home,
    # which is the exact candidate `_private_path_policy` accepts for private-local.
    monkeypatch.chdir(root)
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            str(media),
            "--source-id",
            "PVTREL",
            "--subtitle",
            "main=sidecar:private/E01/episode.ass",
            "--gold",
            "main=private/transcripts/gold.json",
            "--rights",
            "private-local",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0, captured.out + captured.err
    record = _registry(root, "PVTREL")
    checked_sidecar = cli._resolve_user_path("private/E01/episode.ass")
    checked_gold = cli._resolve_user_path("private/transcripts/gold.json")
    assert cli._private_path_policy(checked_sidecar, root, co, "private-local") is None
    assert cli._private_path_policy(checked_gold, root, co, "private-local") is None
    assert record["subtitle_specs"]["main"] == f"sidecar:{checked_sidecar}"
    assert record["gold_classification"]["main"] == str(checked_gold)
    # the escaping relative form the policy refuses is never stored
    capsys.readouterr()
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            str(media),
            "--source-id",
            "PVTESCAPE",
            "--subtitle",
            "main=sidecar:private/../fixtures/Fx00/episode.ass",
            "--rights",
            "private-local",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "REFUSED (private data policy)" in captured.err
    registry_text = (root / "cases" / "sources.json").read_text(encoding="utf-8")
    assert "PVTESCAPE" not in registry_text


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg required for reference audio")
def test_case_prepare_run_score_stable_from_different_cwd(
    tmp_path, monkeypatch, capsys
):
    """Acceptance 2/3: registration from repo root works from any later CWD, with
    root-relative (redacted) manifest fields identical to a same-CWD run."""
    co = _make_checkout(tmp_path)
    root = _point_cli_at_checkout(monkeypatch, co)
    monkeypatch.chdir(co)
    _register_synthetic_relative(root, "Fx00")
    capsys.readouterr()

    def prepare(case_id: str) -> dict:
        rc = cli.main(
            [
                "--root",
                str(root),
                "case",
                "prepare",
                "--source-id",
                "Fx00",
                "--track-id",
                "episode",
                "--scenario",
                "S00",
                "--seed",
                "11",
                "--case-id",
                case_id,
            ]
        )
        assert rc == 0
        return json.loads((root / "cases" / f"{case_id}.case.json").read_text("utf-8"))

    # same-CWD (repo root) baseline
    same_cwd_manifest = prepare("SAME-CWD")
    capsys.readouterr()

    # later invocations from an unrelated working directory
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert not (elsewhere / "benchmarks" / "fixtures" / "Fx00" / "episode.ass").exists()
    assert not (elsewhere / "fixtures" / "Fx00" / "episode.ass").exists()
    other_manifest = prepare("OTHER-CWD")

    for key in ("case_id", "generated_path"):
        assert key in same_cwd_manifest and key in other_manifest
    stripped = {k: v for k, v in same_cwd_manifest.items() if k not in ("case_id",)}
    stripped_other = {k: v for k, v in other_manifest.items() if k not in ("case_id",)}
    same_gen = stripped.pop("generated_path")
    other_gen = stripped_other.pop("generated_path")
    assert stripped == stripped_other
    assert same_gen == "_scratch/SAME-CWD/corrupted.ass"
    assert other_gen == "_scratch/OTHER-CWD/corrupted.ass"
    # committed-manifest redaction: root-relative identifiers only, no absolute leak
    assert (
        other_manifest["gold_classification_path"] == "fixtures/Fx00/gold_episode.json"
    )
    manifest_text = (root / "cases" / "OTHER-CWD.case.json").read_text("utf-8")
    assert str(co) not in manifest_text
    assert str(root) not in manifest_text

    sources = json.loads((root / "cases" / "sources.json").read_text("utf-8"))
    assert cli._verify_sources(cli._paths(root), "Fx00", sources) == []

    rc = cli.main(
        ["--root", str(root), "run", "--case", "OTHER-CWD", "--candidate", "b1-n"]
    )
    assert rc == 0, capsys.readouterr().out + capsys.readouterr().err
    rc = cli.main(
        ["--root", str(root), "score", "--case", "OTHER-CWD", "--candidate", "b1-n"]
    )
    assert rc == 0
    run_root = (root / "results" / "OTHER-CWD" / "b1-n").resolve()
    same_root = (root / "results" / "SAME-CWD" / "b1-n").resolve()
    gen_sha = other_manifest["generated_subtitle_sha256"]
    assert (run_root / "proposal.json").is_file()
    # a case prepared at the repo-root CWD runs and scores from this other CWD too
    assert (
        cli.main(
            ["--root", str(root), "run", "--case", "SAME-CWD", "--candidate", "b1-n"]
        )
        == 0
    )
    assert (
        cli.main(
            ["--root", str(root), "score", "--case", "SAME-CWD", "--candidate", "b1-n"]
        )
        == 0
    )
    assert (same_root / "proposal.json").is_file()
    assert gen_sha == same_cwd_manifest["generated_subtitle_sha256"]
    assert sha256_file(root / "_scratch" / "OTHER-CWD" / "corrupted.ass") == gen_sha
    assert sha256_file(root / "_scratch" / "SAME-CWD" / "corrupted.ass") == gen_sha


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg required for reference audio")
def test_committed_fixture_case_manifest_is_byte_stable(tmp_path, monkeypatch, capsys):
    """`case prepare` from the repo root still writes the committed root-relative
    manifest fields (no absolute private paths enter a committed-path manifest)."""
    co = _make_checkout(tmp_path)
    root = _point_cli_at_checkout(monkeypatch, co)
    monkeypatch.chdir(co)
    _register_synthetic_relative(root, "Fx00")
    capsys.readouterr()
    rc = cli.main(
        [
            "--root",
            str(root),
            "case",
            "prepare",
            "--source-id",
            "Fx00",
            "--track-id",
            "episode",
            "--scenario",
            "S00",
            "--seed",
            "11",
            "--case-id",
            "Fx00-S00",
        ]
    )
    assert rc == 0
    generated = root / "cases" / "Fx00-S00.case.json"
    committed = BENCH_ROOT / "cases" / "Fx00-S00.case.json"
    manifest_text = generated.read_text("utf-8")
    assert manifest_text == committed.read_text("utf-8")
    manifest = json.loads(manifest_text)
    assert manifest["generated_path"] == "_scratch/Fx00-S00/corrupted.ass"
    assert manifest["gold_classification_path"] == "fixtures/Fx00/gold_episode.json"
    assert str(co) not in manifest_text
    assert str(REPO_ROOT) not in manifest_text


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg required for reference audio")
def test_missing_registered_sidecar_refuses_from_other_cwd(
    tmp_path, monkeypatch, capsys
):
    """Acceptance 4: a registered absolute sidecar that disappears is refused cleanly."""
    co = _make_checkout(tmp_path)
    root = _point_cli_at_checkout(monkeypatch, co)
    monkeypatch.chdir(co)
    _register_synthetic_relative(root, "Fx00")
    capsys.readouterr()
    assert (
        cli.main(
            [
                "--root",
                str(root),
                "case",
                "prepare",
                "--source-id",
                "Fx00",
                "--track-id",
                "episode",
                "--scenario",
                "S00",
                "--seed",
                "11",
                "--case-id",
                "GONE",
            ]
        )
        == 0
    )
    capsys.readouterr()

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    (root / "fixtures" / "Fx00" / "episode.ass").unlink()

    sources = json.loads((root / "cases" / "sources.json").read_text("utf-8"))
    problems = cli._verify_sources(cli._paths(root), "Fx00", sources)
    assert problems == ["registered subtitle episode missing"]

    rc = cli.main(["--root", str(root), "run", "--case", "GONE", "--candidate", "b1-n"])
    captured = capsys.readouterr()
    assert rc == 3
    assert "SOURCE CHECK FAILED" in captured.out + captured.err
    assert "registered subtitle episode missing" in captured.out + captured.err
    rc = cli.main(
        ["--root", str(root), "score", "--case", "GONE", "--candidate", "b1-n"]
    )
    captured = capsys.readouterr()
    assert rc == 3
    assert "registered subtitle episode missing" in captured.out + captured.err
