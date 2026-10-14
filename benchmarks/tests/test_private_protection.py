"""Private benchmark data protection: path policy, manifest routing, gitignore coverage."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from bench import cli

BENCH_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BENCH_ROOT.parent


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


def _register_private_source(tmp_path) -> Path:
    root = tmp_path / "benchroot"
    fx = root / "fx"
    fx.mkdir(parents=True)
    src_dir = BENCH_ROOT / "fixtures" / "Fx00"
    for name in ("reference.wav", "episode.ass", "gold_episode.json"):
        shutil.copy2(src_dir / name, fx / name)
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            str(fx / "reference.wav"),
            "--source-id",
            "PVT",
            "--subtitle",
            f"main=sidecar:{fx / 'episode.ass'}",
            "--gold",
            f"main={fx / 'gold_episode.json'}",
            "--rights",
            "private-local",
        ]
    )
    assert rc == 0
    return root


def _registry_bytes(sources_path: Path) -> bytes:
    """Registry bytes for snapshot guards; b'' when absent (fresh clone)."""
    return sources_path.read_bytes() if sources_path.exists() else b""


def test_source_add_refuses_in_repo_media_outside_allowed(capsys):
    guard_dir = BENCH_ROOT / "_scratch" / "priv-guard-media"
    sources_path = BENCH_ROOT / "cases" / "sources.json"
    try:
        guard_dir.mkdir(parents=True, exist_ok=True)
        stub = guard_dir / "episode.mkv"
        stub.write_bytes(b"stub")
        before = _registry_bytes(sources_path)
        rc = cli.main(
            [
                "source",
                "add",
                "--path",
                str(stub),
                "--source-id",
                "PRIVGUARD-M",
                "--rights",
                "private-local",
            ]
        )
        after = _registry_bytes(sources_path)
    finally:
        shutil.rmtree(guard_dir, ignore_errors=True)
    captured = capsys.readouterr()
    assert rc == 2
    assert "REFUSED (private data policy)" in captured.err
    assert before == after
    assert "PRIVGUARD-M" not in _registry_bytes(sources_path).decode("utf-8", "replace")


def test_source_add_refuses_in_repo_sidecar_outside_allowed(tmp_path, capsys):
    media = tmp_path / "mnt" / "media" / "episode.mkv"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"stub")
    sources_path = BENCH_ROOT / "cases" / "sources.json"
    evil_sidecar = BENCH_ROOT / "cases" / "evil.ass"
    before = _registry_bytes(sources_path)
    rc = cli.main(
        [
            "source",
            "add",
            "--path",
            str(media),
            "--source-id",
            "PRIVGUARD-S",
            "--subtitle",
            f"main=sidecar:{evil_sidecar}",
            "--rights",
            "private-local",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "REFUSED (private data policy)" in captured.err
    assert not evil_sidecar.exists()
    assert _registry_bytes(sources_path) == before


def test_source_add_refuses_in_repo_gold_outside_allowed(tmp_path, capsys):
    media = tmp_path / "mnt" / "media" / "episode.mkv"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"stub")
    sources_path = BENCH_ROOT / "cases" / "sources.json"
    before = _registry_bytes(sources_path)
    rc = cli.main(
        [
            "source",
            "add",
            "--path",
            str(media),
            "--source-id",
            "PRIVGUARD-G",
            "--gold",
            f"main={BENCH_ROOT / 'transcripts' / 'x.json'}",
            "--rights",
            "private-local",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "REFUSED (private data policy)" in captured.err
    assert _registry_bytes(sources_path) == before
    assert not (BENCH_ROOT / "transcripts").exists()


def test_relative_sidecar_registration_from_repo_root_matches_documented_flow(
    tmp_path, monkeypatch, capsys
):
    """The README-documented relative registration command must work from repo root CWD."""
    root = tmp_path / "benchroot"
    real_registry = BENCH_ROOT / "cases" / "sources.json"
    before = real_registry.read_bytes() if real_registry.exists() else None
    monkeypatch.chdir(REPO_ROOT)
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            "benchmarks/fixtures/Fx00/reference.wav",
            "--source-id",
            "Fx00",
            "--subtitle",
            "episode=sidecar:benchmarks/fixtures/Fx00/episode.ass",
            "--subtitle",
            "signs=sidecar:benchmarks/fixtures/Fx00/signs.ass",
            "--gold",
            "episode=benchmarks/fixtures/Fx00/gold_episode.json",
            "--gold",
            "signs=benchmarks/fixtures/Fx00/gold_signs.json",
            "--rights",
            "redistributable-synthetic-fixture",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0, captured.out + captured.err
    registry = root / "cases" / "sources.json"
    assert registry.is_file()
    record = json.loads(registry.read_text(encoding="utf-8"))["sources"]["Fx00"]
    # specs stored exactly as given
    assert record["subtitle_specs"]["episode"] == (
        "sidecar:benchmarks/fixtures/Fx00/episode.ass"
    )
    assert record["subtitle_specs"]["signs"] == (
        "sidecar:benchmarks/fixtures/Fx00/signs.ass"
    )
    assert record["gold_classification"]["episode"] == (
        "benchmarks/fixtures/Fx00/gold_episode.json"
    )
    # media path resolved absolutely as before
    assert Path(record["media_path"]).is_absolute()
    # real committed registry untouched by this tmp-root flow
    after = real_registry.read_bytes() if real_registry.exists() else None
    assert before == after


def test_relative_sidecar_resolution_follows_cwd(tmp_path, monkeypatch, capsys):
    root = tmp_path / "benchroot2"
    monkeypatch.chdir(BENCH_ROOT)
    # relative from benchmarks CWD -> allowed fixtures home
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            "fixtures/Fx00/reference.wav",
            "--source-id",
            "FXREL",
            "--subtitle",
            "main=sidecar:fixtures/Fx00/episode.ass",
            "--rights",
            "private-local",
        ]
    )
    assert rc == 0
    assert (root / "cases" / "sources.json").is_file()
    capsys.readouterr()
    # relative escaping: ../evil.ass from benchmarks CWD = benchmarks/evil.ass -> refused
    rc = cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            "fixtures/Fx00/reference.wav",
            "--source-id",
            "FXEVIL",
            "--subtitle",
            "main=sidecar:../evil.ass",
            "--rights",
            "private-local",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "REFUSED (private data policy)" in captured.err
    registry = (root / "cases" / "sources.json").read_text(encoding="utf-8")
    assert "FXEVIL" not in registry
    assert not (BENCH_ROOT / "evil.ass").exists()


def test_private_path_policy(tmp_path):
    repo = tmp_path / "repo"
    bench = repo / "benchmarks"
    private_ep = bench / "private" / "E01" / "episode.mkv"
    private_ep.parent.mkdir(parents=True)
    private_ep.write_bytes(b"stub")
    fixture = bench / "fixtures" / "Fx00" / "episode.ass"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("stub", encoding="utf-8")
    outside = tmp_path / "mnt" / "media" / "episode.mkv"
    outside.parent.mkdir(parents=True)
    outside.write_bytes(b"stub")
    stray_media = bench / "media" / "episode.mkv"
    stray_media.parent.mkdir(parents=True)
    stray_media.write_bytes(b"stub")
    stray_cases = bench / "media" / "evil.wav"
    stray_cases.write_bytes(b"stub")

    assert cli._private_path_policy(private_ep, bench, repo) is None
    assert cli._private_path_policy(private_ep.parent, bench, repo) is None
    assert cli._private_path_policy(fixture, bench, repo) is None
    assert cli._private_path_policy(outside, bench, repo) is None
    assert cli._private_path_policy(stray_media, bench, repo) is not None
    assert cli._private_path_policy(stray_cases, bench, repo) is not None
    assert cli._private_path_policy(repo / "other" / "x.wav", bench, repo) is not None


def test_case_manifest_routing(tmp_path):
    paths = cli._paths(tmp_path / "bench")
    assert (
        cli._case_manifest_path(paths, "E01-S01", "private-local")
        == paths["private_cases"] / "E01-S01.case.json"
    )
    assert (
        cli._case_manifest_path(paths, "E01-S01", "")
        == paths["private_cases"] / "E01-S01.case.json"
    )
    assert (
        cli._case_manifest_path(paths, "Fx00-S01", cli.SYNTHETIC_RIGHTS)
        == paths["cases"] / "Fx00-S01.case.json"
    )


def test_case_lookup_and_iteration_cover_both_dirs(tmp_path):
    paths = cli._paths(tmp_path / "bench")
    paths["cases"].mkdir(parents=True)
    paths["private_cases"].mkdir(parents=True)
    (paths["cases"] / "A.case.json").write_text("{}", encoding="utf-8")
    (paths["private_cases"] / "B.case.json").write_text("{}", encoding="utf-8")
    assert cli._lookup_case_path(paths, "A") == paths["cases"] / "A.case.json"
    assert cli._lookup_case_path(paths, "B") == paths["private_cases"] / "B.case.json"
    assert cli._lookup_case_path(paths, "C") is None
    assert [p.name for p in cli._iter_case_paths(paths)] == [
        "A.case.json",
        "B.case.json",
    ]


def test_prepare_routes_private_manifest_for_non_synthetic_source(tmp_path, capsys):
    root = _register_private_source(tmp_path)
    capsys.readouterr()
    rc = cli.main(
        [
            "--root",
            str(root),
            "case",
            "prepare",
            "--source-id",
            "PVT",
            "--track-id",
            "main",
            "--scenario",
            "S00",
            "--seed",
            "1",
            "--case-id",
            "PVT-S00",
        ]
    )
    assert rc == 0
    assert (root / "private" / "cases" / "PVT-S00.case.json").is_file()
    assert not (root / "cases" / "PVT-S00.case.json").exists()
    rc = cli.main(
        [
            "--root",
            str(root),
            "run",
            "--case",
            "PVT-S00",
            "--candidate",
            "b1-n",
        ]
    )
    assert rc == 0
    rc = cli.main(["--root", str(root), "case", "list"])
    assert rc == 0
    assert "PVT-S00" in capsys.readouterr().out


def test_prepare_refuses_path_escaping_case_id(tmp_path, capsys):
    root = _register_private_source(tmp_path)
    capsys.readouterr()
    rc = cli.main(
        [
            "--root",
            str(root),
            "case",
            "prepare",
            "--source-id",
            "PVT",
            "--track-id",
            "main",
            "--scenario",
            "S00",
            "--seed",
            "1",
            "--case-id",
            "..\\escape",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "REFUSED" in captured.err
    assert not (root / "escape.case.json").exists()
    assert not (root / "private" / "escape.case.json").exists()
    assert not (root / "private" / "cases" / "..escape.case.json").exists()


PRIVATE_IGNORED = [
    "benchmarks/private/E01/episode.mkv",
    "benchmarks/private/E01/episode.ass",
    "benchmarks/private/E01/reference.wav",
    "benchmarks/private/transcripts/x.json",
    "benchmarks/private/cases/E01-S01.case.json",
]

COMMITTED_EXAMPLES = [
    "benchmarks/fixtures/Fx00/episode.ass",
    "benchmarks/cases/Fx00-S00.case.json",
    "benchmarks/bench/cli.py",
]


@pytest.mark.parametrize("rel", PRIVATE_IGNORED)
def test_private_paths_are_git_ignored(rel):
    git = _git()
    result = subprocess.run(
        [git, "check-ignore", "-q", "--", rel],
        check=False,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{rel} should be git-ignored: {result.stderr}"


def test_private_readme_is_not_git_ignored():
    git = _git()
    result = subprocess.run(
        [git, "check-ignore", "-q", "--", "benchmarks/private/README.md"],
        check=False,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, "benchmarks/private/README.md must be committable"


def test_private_tree_tracks_only_the_readme_stub():
    git = _git()
    listed = subprocess.run(
        [git, "ls-files", "--", "benchmarks/private"],
        check=False,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert listed.returncode == 0
    assert listed.stdout.split() == ["benchmarks/private/README.md"]


@pytest.mark.parametrize("rel", COMMITTED_EXAMPLES)
def test_representative_files_are_tracked(rel):
    git = _git()
    listed = subprocess.run(
        [git, "ls-files", "--", rel],
        check=False,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert rel in listed.stdout.split(), f"{rel} should be tracked by git"
