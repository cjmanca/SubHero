"""Output-mapping safety: cue correspondence by text (never guess), strict
id validation before any filesystem effect, report path guard, abstention
scoring for ambiguous mappings."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest
from bench import cli
from bench.adapters import ToolConfig, run_candidate
from bench.corrupt import prepare_case
from bench.manifests import CaseManifest, ProposalRecord
from bench.scoring import Tolerances, score_case
from bench.subtitles import Track
from bench.validator import normalize_text

STUB_DIR = Path(__file__).resolve().parent / "stubs"

BASE_ASS = (
    "[Script Info]\nScriptType: v4.00+\n\n[V4+ Styles]\n"
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
    "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
    "MarginR, MarginV, Encoding\n"
    "Style: Dialog,Arial,28,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,"
    "0,0,100,100,0,0,1,2,2,2,10,10,10,1\n\n[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    "Dialogue: 0,0:00:01.00,0:00:03.00,Dialog,,0,0,0,,First line alpha\n"
    "Dialogue: 0,0:00:11.00,0:00:13.00,Dialog,,0,0,0,,Second line beta\n"
    "Dialogue: 0,0:00:21.00,0:00:23.00,Dialog,,0,0,0,,Third line gamma\n"
)

REORDER_STUB = (
    "import argparse, pysubs2\n"
    "p = argparse.ArgumentParser(prog='stub-reorder')\n"
    "p.add_argument('reference', nargs='?', default=None)\n"
    "p.add_argument('-i', '--srtin'); p.add_argument('-o', '--srtout')\n"
    "p.add_argument('--log-dir-path', default=None)\n"
    "p.add_argument('--split-penalty', type=float, default=None)\n"
    "a = p.parse_args()\n"
    "d = pysubs2.SSAFile.load(a.srtin, format='srt')\n"
    "out = pysubs2.SSAFile()\n"
    "for ev in reversed(list(d.events)):\n"
    "    out.events.append(ev)\n"
    "out.save(a.srtout, format='srt')\n"
)

REWRITE_STUB = (
    "import argparse, pysubs2\n"
    "p = argparse.ArgumentParser(prog='stub-rewrite')\n"
    "p.add_argument('reference', nargs='?', default=None)\n"
    "p.add_argument('-i', '--srtin'); p.add_argument('-o', '--srtout')\n"
    "p.add_argument('--log-dir-path', default=None)\n"
    "p.add_argument('--split-penalty', type=float, default=None)\n"
    "a = p.parse_args()\n"
    "d = pysubs2.SSAFile.load(a.srtin, format='srt')\n"
    "out = pysubs2.SSAFile()\n"
    "for ev in d.events:\n"
    "    out.events.append(pysubs2.SSAEvent(start=ev.start + 2000, end=ev.end + 2000,"
    " text=ev.text.replace('line', 'VERSES')))\n"
    "out.save(a.srtout, format='srt')\n"
)

ALASS_REORDER_STUB = (
    "import sys, pysubs2\n"
    "if len(sys.argv) == 2 and sys.argv[1] == '-v':\n"
    "    print('stub-alass 0.0')\n"
    "    sys.exit(0)\n"
    "_, ref, i, o = sys.argv[:4]\n"
    "d = pysubs2.SSAFile.load(i, format='ass')\n"
    "out = pysubs2.SSAFile()\n"
    "for ev in reversed(list(d.events)):\n"
    "    out.events.append(ev)\n"
    "out.save(o, format='ass')\n"
)


def _write_stub(tmp_path, name, source) -> Path:
    stub = tmp_path / name
    stub.write_text(source, encoding="utf-8")
    return stub


def _tools(cand: str, script: Path) -> ToolConfig:
    tools = ToolConfig()
    tools.command_overrides = {cand: [sys.executable, str(script)]}
    return tools


def _tools_offset(cand: str, offset_ms: int) -> ToolConfig:
    tools = ToolConfig()
    tools.command_overrides = {
        cand: [
            sys.executable,
            str(STUB_DIR / "stub_ffsubsync.py"),
            "--offset-ms",
            str(offset_ms),
        ]
    }
    return tools


def _s00_case(tmp_path, fixture_track: str = "episode.ass", fixture_dir=None):
    src = fixture_dir / fixture_track if fixture_dir else None
    if src is None:
        src = tmp_path / "episode.ass"
        src.write_text(BASE_ASS, encoding="utf-8")
    case = prepare_case(
        "SAF", "safe-case", "S00", 1, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path), case.fmt)
    return case, corrupted


# --- A: cue correspondence by text -------------------------------------------


def test_reordered_output_is_ambiguous_not_guessed(tmp_path):
    case, corrupted = _s00_case(tmp_path)
    stub = _write_stub(tmp_path, "reorder.py", REORDER_STUB)
    proposal, _meta = run_candidate(
        "b1-fg",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run-reorder",
        _tools("b1-fg", stub),
        50_000,
    )
    assert proposal.mapping_status == "mapping_failure_ambiguous_text"
    assert proposal.proposed_times_us == {}
    assert set(proposal.unmapped_cue_ids) == set(corrupted.time_map())
    assert "position" in proposal.notes
    assert "refusing to guess" in proposal.notes


def test_text_rewriting_output_is_ambiguous_not_guessed(tmp_path):
    case, corrupted = _s00_case(tmp_path)
    stub = _write_stub(tmp_path, "rewrite.py", REWRITE_STUB)
    proposal, _meta = run_candidate(
        "b1-fg",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run-rewrite",
        _tools("b1-fg", stub),
        50_000,
    )
    assert proposal.mapping_status == "mapping_failure_ambiguous_text"
    assert proposal.proposed_times_us == {}
    assert "VERSES" in proposal.notes  # first mismatch is reported


def test_timing_only_output_maps_normally(tmp_path):
    case, corrupted = _s00_case(tmp_path)
    proposal, _meta = run_candidate(
        "b1-fg",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run-good",
        _tools_offset("b1-fg", 2000),
        50_000,
    )
    assert proposal.mapping_status == "1:1-order-preserving"
    ct = corrupted.time_map()
    assert all(
        proposal.proposed_times_us[cid][0] == ct[cid][0] + 2_000_000 for cid in ct
    )


def test_proxy_arm_reordered_output_ambiguous_and_timing_ok(tmp_path, fixture_dir):
    src = fixture_dir / "episode.ass"
    case = prepare_case(
        "SAF", "safe-px", "S00", 1, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path), case.fmt)
    stub = _write_stub(tmp_path, "reorder.py", REORDER_STUB)
    proposal, _meta = run_candidate(
        "b1-px-fg",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run-px-bad",
        _tools("b1-px-fg", stub),
        50_000,
        gold_classification_path=fixture_dir / "gold_episode.json",
    )
    assert proposal.mapping_status == "mapping_failure_ambiguous_text"
    assert proposal.proposed_times_us == {}
    proposal_ok, _meta = run_candidate(
        "b1-px-fg",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run-px-good",
        _tools_offset("b1-px-fg", 2000),
        50_000,
        gold_classification_path=fixture_dir / "gold_episode.json",
    )
    assert proposal_ok.mapping_status == "1:1-order-preserving"
    assert 0 < len(proposal_ok.proposed_times_us) < len(corrupted.time_map())


def test_alass_arm_reordered_output_ambiguous(tmp_path):
    case, corrupted = _s00_case(tmp_path)
    stub = _write_stub(tmp_path, "alass_reorder.py", ALASS_REORDER_STUB)
    proposal, _meta = run_candidate(
        "b1-al",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run-al",
        _tools("b1-al", stub),
        50_000,
    )
    assert proposal.mapping_status == "mapping_failure_ambiguous_text"
    assert proposal.proposed_times_us == {}


# --- B: strict id validation before filesystem effects ------------------------


def _setup_root(tmp_path):
    root = tmp_path / "benchroot"
    fx = root / "fx"
    fx.mkdir(parents=True)
    src_dir = Path(__file__).resolve().parent.parent / "fixtures" / "Fx00"
    for name in ("reference.wav", "episode.ass", "gold_episode.json"):
        shutil.copy2(src_dir / name, fx / name)
    return root, fx


UNSAFE_IDS = [
    "../evil",
    "..\\evil",
    "a/b",
    "a\\b",
    "",
    ".hidden",
    "..",
    ".",
    "x" * 200,
    "nul\x00id",
    "evil;rm -rf",
    "spaced id",
]


def test_source_add_refuses_unsafe_source_ids(tmp_path, capsys):
    root, fx = _setup_root(tmp_path)
    for bad in UNSAFE_IDS:
        rc = cli.main(
            [
                "--root",
                str(root),
                "source",
                "add",
                "--path",
                str(fx / "reference.wav"),
                "--source-id",
                bad,
                "--rights",
                "private-local",
            ]
        )
        assert rc == 2, bad
    captured = capsys.readouterr()
    assert "not a safe id" in captured.err
    registry = root / "cases" / "sources.json"
    assert not registry.exists()
    assert not (tmp_path / "evil").exists()
    # only the expected scratch layout exists under the root
    assert {p.name for p in root.iterdir()} <= {
        "cases",
        "private",
        "_scratch",
        "results",
        "fx",
    }


def test_case_prepare_refuses_unsafe_ids_before_mkdir(tmp_path, capsys):
    root, fx = _setup_root(tmp_path)
    assert (
        cli.main(
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
                "--rights",
                "private-local",
            ]
        )
        == 0
    )
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
            "..\\..\\x",
            "--scenario",
            "S00",
            "--seed",
            "1",
        ]
    )
    assert rc == 2
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
            "a/b",
        ]
    )
    assert rc == 2
    captured = capsys.readouterr()
    assert "not a safe id" in captured.err
    scratch = root / "_scratch"
    created = {p.name for p in scratch.iterdir()} if scratch.exists() else set()
    assert created == set()  # nothing was created by the refused commands
    assert not (root / "private" / "cases" / "a").exists()
    # positive control: composed case id from validated parts works
    assert (
        cli.main(
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
            ]
        )
        == 0
    )


def test_run_score_report_refuse_unsafe_case_ids(tmp_path, capsys):
    root, _fx = _setup_root(tmp_path)
    for cmd in (
        ["run", "--case", "../escape"],
        ["score", "--case", "a/b"],
        ["report", "--case", "..\\x"],
    ):
        rc = cli.main(["--root", str(root)] + cmd)
        assert rc == 2, cmd
    captured = capsys.readouterr()
    assert "not a safe id" in captured.err
    assert not (root / "results" / "escape").exists()
    assert not (root / "results" / "a").exists()


def test_run_candidate_rejects_unsafe_ids_before_mkdir(tmp_path):
    src = tmp_path / "episode.ass"
    src.write_text(BASE_ASS, encoding="utf-8")
    case = prepare_case(
        "SAF", "safe-id", "S00", 1, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path))
    scratch = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="candidate id"):
        run_candidate(
            "bad id/../x",
            case,
            corrupted.time_map(),
            Path(case.generated_path),
            tmp_path / "ref.wav",
            scratch,
            ToolConfig(),
            50_000,
        )
    assert not scratch.exists()
    escaped = CaseManifest(**{**case.to_json(), "case_id": "../escape"})
    escaped.schema_version = 1
    with pytest.raises(ValueError, match="case id"):
        run_candidate(
            "b1-fg",
            escaped,
            corrupted.time_map(),
            Path(case.generated_path),
            tmp_path / "ref.wav",
            scratch,
            ToolConfig(),
            50_000,
        )
    assert not scratch.exists()


def test_report_out_traversal_refused_and_inside_results_ok(tmp_path, capsys):
    root, _fx = _setup_root(tmp_path)
    rc = cli.main(["--root", str(root), "report", "--out", str(tmp_path / "escape.md")])
    captured = capsys.readouterr()
    assert rc == 5
    assert "REFUSED" in captured.err
    assert not (tmp_path / "escape.md").exists()
    rc = cli.main(
        ["--root", str(root), "report", "--out", str(root / "results" / "ok.md")]
    )
    assert rc == 0
    assert (root / "results" / "ok.md").is_file()


# --- C: scoring counts ambiguous mapping as abstention -----------------------


def test_ambiguous_text_status_counts_as_abstention_no_repaired_credit():
    cue_ids = ["e0000", "e0001", "e0002"]
    original = {
        cid: (1_000_000 + i * 10_000_000, 2_000_000 + i * 10_000_000)
        for i, cid in enumerate(cue_ids)
    }
    corrupted = {
        cid: (s + 5_000_000, e + 5_000_000) for cid, (s, e) in original.items()
    }
    case = CaseManifest(
        case_id="amb",
        source_id="S",
        scenario="S01",
        seed=1,
        track_id="episode",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": "S01", "offset_us": 5_000_000},
        transform={},
        expected_inverse={},
        injected_cue_deltas={cid: (5_000_000, 5_000_000) for cid in cue_ids},
        original_times_us=original,
        true_breakpoints_us=[],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )
    ambiguous = ProposalRecord(
        "amb",
        "b1-al",
        "mapping_failure_ambiguous_text",
        [{"start_us": 0, "end_us": None, "offset_us": 0}],
        {},
        list(cue_ids),
        "refusing to guess correspondence",
    )
    tol = Tolerances(good_us=50_000, severe_us=250_000, break_match_us=500_000)
    score = score_case(case, ambiguous, corrupted, None, tol)
    assert score["counts"]["abstained_regions"] == 1
    assert score["counts"]["repaired_if_blindly_applied"] == 0
    assert score["counts"]["repaired_proposed"] == 0
    assert score["counts"]["proposals_nonzero"] == 0
    assert score["counts"]["worsened_unaltered_if_blindly_applied"] == 0
    assert score["mapping_status"] == "mapping_failure_ambiguous_text"


def test_normalize_text_preserves_line_break_semantics():
    from bench.validator import normalize_text

    assert normalize_text(r"First\NSecond") == normalize_text("First Second")
    assert normalize_text(r"{\k100}Sing{\k100}ing") == "singing"
    assert normalize_text("UPPER  {\b1}text\\N") == "upper text"


# --- D: duplicate-normalized-text identity (F06) ------------------------------

ASS_TWO_DUP = (
    "[Script Info]\nScriptType: v4.00+\n\n[V4+ Styles]\n"
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
    "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
    "MarginR, MarginV, Encoding\n"
    "Style: Dialog,Arial,28,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,"
    "0,0,100,100,0,0,1,2,2,2,10,10,10,1\n\n[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    "Dialogue: 0,0:00:01.00,0:00:03.00,Dialog,,0,0,0,,Unique intro one\n"
    "Dialogue: 0,0:00:10.00,0:00:11.00,Dialog,,0,0,0,,Same line here.\n"
    "Dialogue: 0,0:00:20.00,0:00:21.00,Dialog,,0,0,0,,Same line here.\n"
    "Dialogue: 0,0:00:30.00,0:00:32.00,Dialog,,0,0,0,,Unique outro three\n"
)

ASS_THREE_DUP = (
    "[Script Info]\nScriptType: v4.00+\n\n[V4+ Styles]\n"
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
    "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
    "MarginR, MarginV, Encoding\n"
    "Style: Dialog,Arial,28,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,"
    "0,0,100,100,0,0,1,2,2,2,10,10,10,1\n\n[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    "Dialogue: 0,0:00:01.00,0:00:03.00,Dialog,,0,0,0,,Unique intro one\n"
    "Dialogue: 0,0:00:10.00,0:00:11.00,Dialog,,0,0,0,,Refrain line.\n"
    "Dialogue: 0,0:00:20.00,0:00:21.00,Dialog,,0,0,0,,Refrain line.\n"
    "Dialogue: 0,0:00:30.00,0:00:31.00,Dialog,,0,0,0,,Refrain line.\n"
    "Dialogue: 0,0:00:40.00,0:00:42.00,Dialog,,0,0,0,,Unique outro five\n"
)

SWAP2_STUB = (
    "import argparse, pysubs2\n"
    "p = argparse.ArgumentParser(prog='stub-swap2')\n"
    "p.add_argument('reference', nargs='?', default=None)\n"
    "p.add_argument('-i', '--srtin'); p.add_argument('-o', '--srtout')\n"
    "p.add_argument('--log-dir-path', default=None)\n"
    "p.add_argument('--offset-ms', type=int, default=0)\n"
    "p.add_argument('--split-penalty', type=float, default=None)\n"
    "a = p.parse_args()\n"
    "d = pysubs2.SSAFile.load(a.srtin, format='srt')\n"
    "ev = list(d.events)\n"
    "for e in ev:\n"
    "    e.start += a.offset_ms; e.end += a.offset_ms\n"
    "ev[1].start, ev[2].start = ev[2].start, ev[1].start\n"
    "ev[1].end, ev[2].end = ev[2].end, ev[1].end\n"
    "out = pysubs2.SSAFile()\n"
    "for e in ev:\n"
    "    out.events.append(pysubs2.SSAEvent(start=e.start, end=e.end, text=e.text))\n"
    "out.save(a.srtout, format='srt')\n"
)

NONMONO3_STUB = (
    "import argparse, pysubs2\n"
    "p = argparse.ArgumentParser(prog='stub-nonmono3')\n"
    "p.add_argument('reference', nargs='?', default=None)\n"
    "p.add_argument('-i', '--srtin'); p.add_argument('-o', '--srtout')\n"
    "p.add_argument('--log-dir-path', default=None)\n"
    "p.add_argument('--offset-ms', type=int, default=0)\n"
    "p.add_argument('--split-penalty', type=float, default=None)\n"
    "a = p.parse_args()\n"
    "d = pysubs2.SSAFile.load(a.srtin, format='srt')\n"
    "ev = list(d.events)\n"
    "for e in ev:\n"
    "    e.start += a.offset_ms; e.end += a.offset_ms\n"
    "s1, s2, s3 = ev[1].start, ev[2].start, ev[3].start\n"
    "e1, e2, e3 = ev[1].end, ev[2].end, ev[3].end\n"
    "ev[1].start, ev[2].start, ev[3].start = s2, s3, s1\n"
    "ev[1].end, ev[2].end, ev[3].end = e2, e3, e1\n"
    "out = pysubs2.SSAFile()\n"
    "for e in ev:\n"
    "    out.events.append(pysubs2.SSAEvent(start=e.start, end=e.end, text=e.text))\n"
    "out.save(a.srtout, format='srt')\n"
)

MULTI_REWRITE_STUB = (
    "import argparse, pysubs2\n"
    "p = argparse.ArgumentParser(prog='stub-mwriter')\n"
    "p.add_argument('reference', nargs='?', default=None)\n"
    "p.add_argument('-i', '--srtin'); p.add_argument('-o', '--srtout')\n"
    "p.add_argument('--log-dir-path', default=None)\n"
    "p.add_argument('--offset-ms', type=int, default=0)\n"
    "p.add_argument('--split-penalty', type=float, default=None)\n"
    "a = p.parse_args()\n"
    "d = pysubs2.SSAFile.load(a.srtin, format='srt')\n"
    "ev = list(d.events)\n"
    "for e in ev:\n"
    "    e.start += a.offset_ms; e.end += a.offset_ms\n"
    "ev[-1].text = ev[1].text\n"
    "out = pysubs2.SSAFile()\n"
    "for e in ev:\n"
    "    out.events.append(pysubs2.SSAEvent(start=e.start, end=e.end, text=e.text))\n"
    "out.save(a.srtout, format='srt')\n"
)


def _build_case(tmp_path, ass_text, scenario="S01", seed=8):
    src = tmp_path / "dup.ass"
    src.write_text(ass_text, encoding="utf-8")
    case = prepare_case(
        "DUP", "dup-case", scenario, seed, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path), case.fmt)
    return case, corrupted


def _dup_cue_ids(corrupted, text):
    want = normalize_text(text)
    return [c.cue_id for c in corrupted.cues if normalize_text(c.text) == want]


def _run_shifted(case, corrupted, stub, offset_ms, scratch, cand="b1-fg"):
    tools = ToolConfig()
    tools.command_overrides = {
        cand: [sys.executable, str(stub), "--offset-ms", str(offset_ms)]
    }
    proposal, _meta = run_candidate(
        cand,
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        scratch / "ref.wav",
        scratch / "run",
        tools,
        50_000,
    )
    return proposal


def test_duplicate_text_swap_is_unmapped_not_guessed(tmp_path):
    case, corrupted = _build_case(tmp_path, ASS_TWO_DUP, "S01", 8)
    stub = _write_stub(tmp_path, "swap2.py", SWAP2_STUB)
    off_ms = -(case.params["offset_us"] // 1000)
    proposal = _run_shifted(case, corrupted, stub, off_ms, tmp_path / "swap")
    dups = _dup_cue_ids(corrupted, "Same line here.")
    assert len(dups) == 2
    assert proposal.mapping_status == "1:1-order-preserving"
    for cid in dups:
        assert cid in proposal.unmapped_cue_ids
        assert cid not in proposal.proposed_times_us
    for cue in corrupted.cues:
        if cue.cue_id not in dups:
            assert cue.cue_id in proposal.proposed_times_us
    assert "Same line here." in proposal.notes
    assert "positions" in proposal.notes
    for cid in dups:
        assert cid in proposal.notes


def test_duplicate_text_uniform_shift_maps_fully(tmp_path):
    case, corrupted = _build_case(tmp_path, ASS_TWO_DUP, "S01", 8)
    off_ms = -(case.params["offset_us"] // 1000)
    proposal = _tools_run_offset(case, corrupted, off_ms, tmp_path / "ok")
    assert proposal.mapping_status == "1:1-order-preserving"
    assert proposal.unmapped_cue_ids == []
    assert set(proposal.proposed_times_us) == set(corrupted.time_map())
    for cid, t in proposal.proposed_times_us.items():
        assert tuple(t) == tuple(case.original_times_us[cid])


def _tools_run_offset(case, corrupted, offset_ms, scratch):
    tools = ToolConfig()
    tools.command_overrides = {
        "b1-fg": [
            sys.executable,
            str(STUB_DIR / "stub_ffsubsync.py"),
            "--offset-ms",
            str(offset_ms),
        ]
    }
    proposal, _meta = run_candidate(
        "b1-fg",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        scratch / "ref.wav",
        scratch / "run",
        tools,
        50_000,
    )
    return proposal


def test_triple_duplicate_permutation_unmapped(tmp_path):
    case, corrupted = _build_case(tmp_path, ASS_THREE_DUP, "S01", 8)
    stub = _write_stub(tmp_path, "perm.py", NONMONO3_STUB)
    off_ms = -(case.params["offset_us"] // 1000)
    proposal = _run_shifted(case, corrupted, stub, off_ms, tmp_path / "perm")
    dups = _dup_cue_ids(corrupted, "Refrain line.")
    assert len(dups) == 3
    assert proposal.mapping_status == "1:1-order-preserving"
    for cid in dups:
        assert cid in proposal.unmapped_cue_ids
        assert cid not in proposal.proposed_times_us
    for cue in corrupted.cues:
        if cue.cue_id not in dups:
            assert cue.cue_id in proposal.proposed_times_us


def test_triple_duplicate_identity_shift_maps(tmp_path):
    case, corrupted = _build_case(tmp_path, ASS_THREE_DUP, "S01", 8)
    off_ms = -(case.params["offset_us"] // 1000)
    proposal = _tools_run_offset(case, corrupted, off_ms, tmp_path / "perm-ok")
    assert proposal.mapping_status == "1:1-order-preserving"
    assert proposal.unmapped_cue_ids == []
    assert set(proposal.proposed_times_us) == set(corrupted.time_map())


def test_multiset_rewrite_of_duplicates_is_ambiguous(tmp_path):
    case, corrupted = _build_case(tmp_path, ASS_TWO_DUP, "S01", 8)
    stub = _write_stub(tmp_path, "mwriter.py", MULTI_REWRITE_STUB)
    off_ms = -(case.params["offset_us"] // 1000)
    proposal = _run_shifted(case, corrupted, stub, off_ms, tmp_path / "mwriter")
    assert proposal.mapping_status == "mapping_failure_ambiguous_text"
    assert proposal.proposed_times_us == {}
    assert set(proposal.unmapped_cue_ids) == set(corrupted.time_map())


def test_partial_unmapped_scores_as_abstention_without_crash(tmp_path):
    case, corrupted = _build_case(tmp_path, ASS_TWO_DUP, "S01", 8)
    stub = _write_stub(tmp_path, "swap2.py", SWAP2_STUB)
    off_ms = -(case.params["offset_us"] // 1000)
    proposal = _run_shifted(case, corrupted, stub, off_ms, tmp_path / "swap-score")
    score = score_case(case, proposal, corrupted.time_map(), None, Tolerances())
    dups = _dup_cue_ids(corrupted, "Same line here.")
    assert score["mapping_status"] == "1:1-order-preserving"
    assert score["denominators"]["unmapped_cues"] == 2
    assert score["denominators"]["mapped_cues"] == 2
    for cid in dups:
        assert not score["per_cue"][cid].get("repaired_if_blindly_applied")
        assert not score["per_cue"][cid].get("repaired_proposed")
    for cue in corrupted.cues:
        if cue.cue_id not in dups:
            assert score["per_cue"][cue.cue_id].get("repaired_proposed")
