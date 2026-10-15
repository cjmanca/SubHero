"""Gold-leakage boundary: default candidates never receive gold cue labels;
oracle arms (b1-pxo-*) are explicit, labeled, and excluded from --all."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest
from bench import cli
from bench.adapters import (
    CANDIDATES,
    DEFAULT_CANDIDATE_IDS,
    ORACLE_DIAGNOSTIC_IDS,
    ORACLE_MARKER,
    ToolConfig,
    run_candidate,
)
from bench.corrupt import prepare_case
from bench.manifests import CaseManifest
from bench.scoring import score_case
from bench.subtitles import Track

STUB = Path(__file__).resolve().parent / "stubs" / "stub_ffsubsync.py"

# Every cue has the "Sign" style (heuristic NON_SPEECH match) plus bracketed
# descriptions; the gold file labels them ALL speech_like. Heuristic-only
# classification therefore finds NO anchors; gold-based classification maps all.
SIGN_ASS = (
    "[Script Info]\nScriptType: v4.00+\n\n[V4+ Styles]\n"
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
    "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
    "MarginR, MarginV, Encoding\n"
    "Style: Sign,Arial,26,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,"
    "0,100,100,0,0,1,2,2,2,10,10,10,1\n\n[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    "Dialogue: 1,0:00:05.00,0:00:08.00,Sign,,0,0,0,,[metallic creak] sign swings\n"
    "Dialogue: 1,0:00:15.00,0:00:18.00,Sign,,0,0,0,,[wind howling] shop window\n"
    "Dialogue: 1,0:00:25.00,0:00:28.00,Sign,,0,0,0,,[notes pinned] by the door\n"
)

FP_STUB = (
    "import argparse, pysubs2\n"
    "p = argparse.ArgumentParser(prog='stub-ffsubsync')\n"
    "p.add_argument('--offset-ms', type=int, required=True)\n"
    "p.add_argument('reference', nargs='?', default=None)\n"
    "p.add_argument('-i', '--srtin'); p.add_argument('-o', '--srtout')\n"
    "p.add_argument('--log-dir-path', default=None)\n"
    "p.add_argument('--split-penalty', type=float, default=None)\n"
    "a = p.parse_args()\n"
    "d = pysubs2.SSAFile.load(a.srtin, format='srt')\n"
    "out = pysubs2.SSAFile()\n"
    "for ev in d.events:\n"
    "    out.events.append(pysubs2.SSAEvent(start=ev.start + a.offset_ms,"
    " end=ev.end + a.offset_ms, text=ev.text))\n"
    "out.save(a.srtout, format='srt')\n"
)


def _discriminating_case(tmp_path):
    """S00-identity case whose heuristic and gold classifications disagree."""
    ass = tmp_path / "signs-only.ass"
    ass.write_text(SIGN_ASS, encoding="utf-8")
    track = Track.load(ass)
    ids = [c.cue_id for c in track.cues]
    assert len(ids) >= 3
    gold = tmp_path / "gold.json"
    gold.write_text(
        json.dumps({cid: "speech_like" for cid in ids}),
        encoding="utf-8",
    )
    times = track.time_map()
    case = CaseManifest(
        case_id="leak-s00",
        source_id="LEAK",
        scenario="S00",
        seed=1,
        track_id="signs-only",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": "S00", "control": True},
        transform={},
        expected_inverse={},
        injected_cue_deltas={cid: (0, 0) for cid in ids},
        original_times_us={cid: (s, e) for cid, (s, e) in times.items()},
        true_breakpoints_us=[],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path=str(ass),
        gold_classification_path=str(gold),
    )
    return case, ass, gold, times


def _tools(tmp_path, extra_fp_stub: bool) -> ToolConfig:
    tools = ToolConfig()
    prefix = [sys.executable, str(STUB), "--offset-ms", "2000"]
    tools.command_overrides = {
        "b1-px-fg": prefix,
        "b1-pxo-fg": prefix,
    }
    if extra_fp_stub:
        stub_fp = tmp_path / "stub_fp.py"
        stub_fp.write_text(FP_STUB, encoding="utf-8")
        fp_prefix = [sys.executable, str(stub_fp), "--offset-ms", "2000"]
        tools.command_overrides["b1-px-fp"] = fp_prefix
        tools.command_overrides["b1-pxo-fp"] = fp_prefix
    return tools


def test_default_proxy_arm_ignores_gold_path_at_adapter_boundary(tmp_path):
    case, ass, gold, times = _discriminating_case(tmp_path)
    tools = _tools(tmp_path, extra_fp_stub=True)
    # The gold path is AVAILABLE (simulating the pre-fix CLI handoff); the
    # adapter boundary must refuse it for the default proxy arm.
    proposal, _meta = run_candidate(
        "b1-px-fg",
        case,
        dict(times),
        ass,
        tmp_path / "ref.wav",
        tmp_path / "run-default",
        tools,
        50_000,
        gold_classification_path=gold,
    )
    assert proposal.mapping_status == "abstain_no_speech_anchors"
    assert proposal.proposed_times_us == {}
    assert "gold" not in proposal.notes.lower()

    proposal_fp, _meta = run_candidate(
        "b1-px-fp",
        case,
        dict(times),
        ass,
        tmp_path / "ref.wav",
        tmp_path / "run-default-fp",
        tools,
        50_000,
        gold_classification_path=gold,
    )
    assert proposal_fp.mapping_status == "abstain_no_speech_anchors"
    assert "gold" not in proposal_fp.notes.lower()


def test_oracle_proxy_arms_use_gold_and_are_labeled(tmp_path):
    case, ass, gold, times = _discriminating_case(tmp_path)
    tools = _tools(tmp_path, extra_fp_stub=True)
    ids = [c.cue_id for c in Track.load(ass).cues]
    for cand in ("b1-pxo-fg", "b1-pxo-fp"):
        proposal, _meta = run_candidate(
            cand,
            case,
            dict(times),
            ass,
            tmp_path / "ref.wav",
            tmp_path / f"run-{cand}",
            tools,
            50_000,
            gold_classification_path=gold,
        )
        assert proposal.mapping_status == "1:1-order-preserving", cand
        assert set(proposal.proposed_times_us) == set(ids)
        assert ORACLE_MARKER in proposal.notes
        assert "gold" in proposal.notes.lower()

    default = run_candidate(
        "b1-px-fg",
        case,
        dict(times),
        ass,
        tmp_path / "ref.wav",
        tmp_path / "run-default2",
        tools,
        50_000,
        gold_classification_path=gold,
    )[0]
    assert ORACLE_MARKER not in default.notes


def test_all_runs_default_ids_only_and_oracle_is_explicitly_selectable():
    assert set(ORACLE_DIAGNOSTIC_IDS) == {"b1-pxo-fg", "b1-pxo-fp"}
    assert set(DEFAULT_CANDIDATE_IDS) == {
        "b1-n",
        "b1-fg",
        "b1-fp",
        "b1-al",
        "b1-px-fg",
        "b1-px-fp",
    }
    defaults = cli._all_candidate_ids()
    assert defaults == DEFAULT_CANDIDATE_IDS
    assert not any(cid.startswith("b1-pxo") for cid in defaults)
    assert "b1-va" not in defaults  # keeps its dedicated --all/base handling
    parser = cli.build_parser()
    args = parser.parse_args(["run", "--case", "X", "--candidate", "b1-pxo-fg"])
    assert args.candidate == ["b1-pxo-fg"]
    args = parser.parse_args(["run", "--case", "X", "--candidate", "b1-pxo-fp"])
    assert args.candidate == ["b1-pxo-fp"]
    assert "b1-pxo-fg" in CANDIDATES and "b1-pxo-fp" in CANDIDATES
    assert CANDIDATES["b1-pxo-fg"][2]["oracle"] is True
    assert CANDIDATES["b1-px-fg"][2]["oracle"] is False
    assert CANDIDATES["b1-px-fg"][2]["default"] is True


def test_cmd_run_passes_gold_only_to_oracle_arms(tmp_path, fixture_dir, monkeypatch):
    """CLI-boundary pin: record which arms receive a non-None gold path."""
    import shutil

    root = tmp_path / "benchroot"
    fx = root / "fx"
    fx.mkdir(parents=True)
    for name in ("reference.wav", "episode.ass", "gold_episode.json"):
        shutil.copy2(fixture_dir / name, fx / name)
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
                "LKR",
                "--subtitle",
                f"main=sidecar:{fx / 'episode.ass'}",
                "--gold",
                f"main={fx / 'gold_episode.json'}",
                "--rights",
                "private-local",
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "--root",
                str(root),
                "case",
                "prepare",
                "--source-id",
                "LKR",
                "--track-id",
                "main",
                "--scenario",
                "S00",
                "--seed",
                "1",
                "--case-id",
                "LKR-S00",
            ]
        )
        == 0
    )
    seen: dict[str, object] = {}
    real = cli.run_candidate

    def _spy(candidate_id, *args, **kwargs):
        seen[candidate_id] = kwargs.get("gold_classification_path")
        return real(candidate_id, *args, **kwargs)

    def _fake_detect(cls):
        tools = ToolConfig()
        tools.command_overrides = {
            "b1-px-fg": [sys.executable, str(STUB), "--offset-ms", "0"],
            "b1-pxo-fg": [sys.executable, str(STUB), "--offset-ms", "0"],
        }
        return tools

    monkeypatch.setattr(cli.ToolConfig, "detect", classmethod(_fake_detect))
    monkeypatch.setattr(cli, "run_candidate", _spy)
    rc = cli.main(
        [
            "--root",
            str(root),
            "run",
            "--case",
            "LKR-S00",
            "--candidate",
            "b1-px-fg",
            "--candidate",
            "b1-pxo-fg",
        ]
    )
    assert rc == 0
    assert seen["b1-px-fg"] is None
    assert seen["b1-pxo-fg"] is not None
    assert Path(seen["b1-pxo-fg"]).name == "gold_episode.json"
    pxo_run = json.loads(
        (root / "results" / "LKR-S00" / "b1-pxo-fg" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert ORACLE_MARKER in pxo_run["reason"]
    px_run = json.loads(
        (root / "results" / "LKR-S00" / "b1-px-fg" / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert ORACLE_MARKER not in px_run["reason"]


def test_manifests_keep_gold_path_for_evaluation():
    params = list(inspect.signature(score_case).parameters)
    assert params == ["case", "proposal", "corrupted_times", "acceptance", "tol"]
    assert not any("gold" in p.lower() for p in params)
    assert "gold" not in inspect.getsource(score_case).lower()


def test_prepare_case_stores_gold_classification_path(tmp_path, fixture_dir):
    case = prepare_case(
        "Fx00",
        "leak-prep",
        "S00",
        1,
        fixture_dir / "episode.ass",
        tmp_path / "out.ass",
        gold_classification_path=fixture_dir / "gold_episode.json",
        track_id="episode",
    )
    assert case.gold_classification_path == str(fixture_dir / "gold_episode.json")
    payload = json.loads(json.dumps(case.to_json()))
    assert payload["gold_classification_path"] == str(fixture_dir / "gold_episode.json")


@pytest.mark.parametrize("cand", ["b1-pxo-fg", "b1-pxo-fp"])
def test_oracle_marker_constant_wording(cand):
    assert ORACLE_MARKER == (
        "oracle-assisted diagnostic arm (uses gold cue labels; excluded from "
        "--all; not a default candidate)"
    )
    assert CANDIDATES[cand][2]["oracle"] is True
    assert cand not in DEFAULT_CANDIDATE_IDS
