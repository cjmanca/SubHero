import shutil
from pathlib import Path

from bench import cli


def _setup_cli_root(tmp_path):
    root = tmp_path / "benchroot"
    (root / "cases").mkdir(parents=True)
    (root / "_scratch").mkdir()
    (root / "results").mkdir()
    fx = root / "fx"
    fx.mkdir()
    src_dir = Path(__file__).resolve().parent.parent / "fixtures" / "Fx00"
    for name in ("reference.wav", "episode.ass", "signs.ass", "gold_episode.json"):
        shutil.copy2(src_dir / name, fx / name)
    return root, fx


def test_cli_matrix_fingerprint_verification_blocks_tampered_source(tmp_path, capsys):
    root, fx = _setup_cli_root(tmp_path)
    # M7 rights coherence: tmp copies are not in the committed fixtures home, so
    # they must register as private-local (synthetic rights are refused for
    # out-of-fixtures paths); private case manifests route to private/cases/.
    argv_add = [
        "--root",
        str(root),
        "source",
        "add",
        "--path",
        str(fx / "reference.wav"),
        "--source-id",
        "FXC",
        "--subtitle",
        f"main=sidecar:{fx / 'episode.ass'}",
        "--gold",
        f"main={fx / 'gold_episode.json'}",
        "--rights",
        "private-local",
    ]
    assert cli.main(argv_add) == 0
    assert (
        cli.main(
            [
                "--root",
                str(root),
                "case",
                "prepare",
                "--source-id",
                "FXC",
                "--track-id",
                "main",
                "--scenario",
                "S00",
                "--seed",
                "1",
                "--case-id",
                "C1",
            ]
        )
        == 0
    )
    manifest = (root / "private" / "cases" / "C1.case.json").read_text(encoding="utf-8")
    assert str(root) not in manifest
    (fx / "episode.ass").write_text(
        (fx / "episode.ass").read_text(encoding="utf-8")
        + "Dialogue: 0,0:00:01.00,0:00:02.00,Dialog,tampered\n",
        encoding="utf-8",
    )
    rc = cli.main(["--root", str(root), "run", "--case", "C1", "--candidate", "b1-n"])
    assert rc == 3
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "SOURCE CHECK FAILED" in out or "MUTATION" in out
    rc = cli.main(["--root", str(root), "score", "--case", "C1", "--candidate", "b1-n"])
    assert rc == 3


def test_cli_report_refuses_write_outside_scratch_roots(tmp_path):
    root, _fx = _setup_cli_root(tmp_path)
    ev = tmp_path / "elsewhere"
    ev.mkdir()
    rc = cli.main(
        [
            "--root",
            str(root),
            "report",
            "--out",
            str(ev / "leak.md"),
        ]
    )
    assert rc != 0
    assert not (ev / "leak.md").exists()
