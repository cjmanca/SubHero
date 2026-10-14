import sys
from pathlib import Path

from bench.adapters import ToolConfig, run_candidate
from bench.corrupt import prepare_case
from bench.manifests import ProposalRecord
from bench.scoring import Tolerances, score_case
from bench.subtitles import Track

STUB = Path(__file__).resolve().parent / "stubs" / "stub_ffsubsync.py"

UNSORTED = (
    "[Script Info]\nScriptType: v4.00+\n\n[V4 Styles]\nFormat: Name, Fontname, Fontsize\nStyle: Dialog,Arial,28\n\n[Events]\n"
    "Dialogue: 0,0:00:10.00,0:00:12.00,Dialog,Third\n"
    "Dialogue: 0,0:00:01.00,0:00:03.00,Dialog,First\n"
    "Dialogue: 0,0:00:05.00,0:00:07.00,Dialog,Second\n"
)


def _tools(offset_ms: int) -> ToolConfig:
    tools = ToolConfig()
    prefix = [sys.executable, str(STUB), "--offset-ms", str(offset_ms)]
    tools.command_overrides = {"b1-fg": prefix, "b1-fp": prefix}
    return tools


def test_full_track_mapping_preserves_file_order_for_unsorted_events(tmp_path):
    src = tmp_path / "episode.ass"
    src.write_text(UNSORTED, encoding="utf-8")
    case = prepare_case("T", "ord", "S00", 1, src, tmp_path / "out.ass")
    corrupted = Track.load(case.generated_path, case.fmt)
    corrupted_times = corrupted.time_map()
    proposal, _meta = run_candidate(
        "b1-fg",
        case,
        corrupted_times,
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run",
        _tools(2000),
        50_000,
    )
    assert proposal.mapping_status == "1:1-order-preserving"
    assert len(proposal.proposed_times_us) == len(corrupted_times)
    for cid, (c_start, _c_end) in corrupted_times.items():
        p_start, _p_end = proposal.proposed_times_us[cid]
        assert p_start == c_start + 2_000_000, cid


def test_breakpoint_detection_lives_in_original_timeline(tmp_path):
    src = tmp_path / "episode.ass"
    src.write_text(
        "[Script Info]\nScriptType: v4.00+\n\n[V4 Styles]\nFormat: Name, Fontname, Fontsize\nStyle: Dialog,Arial,28\n\n[Events]\n"
        + "".join(
            f"Dialogue: 0,0:00:{1 + i * 10:02}.00,0:00:{3 + i * 10:02}.00,Dialog,Line {i}\n"
            for i in range(60)
        ),
        encoding="utf-8",
    )
    case = prepare_case("T", "bp", "S03", 5, src, tmp_path / "out.ass")
    corrupted = Track.load(case.generated_path, case.fmt)
    tol = Tolerances(good_us=50_000, severe_us=2_000_000, break_match_us=11_000_000)
    noop = ProposalRecord("bp", "b1-n", "noop", [], dict(corrupted.time_map()), [], "")
    score = score_case(case, noop, corrupted.time_map(), None, tol)
    breaks = score["discontinuities"]
    assert breaks["true_breakpoints"] == len(case.true_breakpoints_us)
    assert breaks["matched_true_breakpoints"] == breaks["true_breakpoints"]
    assert breaks["false_positive_breakpoints"] == 0


def test_noop_is_not_counted_as_abstention(tmp_path):
    src = tmp_path / "episode.ass"
    src.write_text(UNSORTED, encoding="utf-8")
    case = prepare_case("T", "ab", "S00", 1, src, tmp_path / "out.ass")
    corrupted = Track.load(case.generated_path, case.fmt)
    noop = ProposalRecord(
        "ab",
        "b1-n",
        "noop",
        [{"start_us": 0, "end_us": None, "offset_us": 0}],
        dict(corrupted.time_map()),
        [],
        "",
    )
    score = score_case(case, noop, corrupted.time_map(), None, Tolerances())
    assert score["counts"]["abstained_regions"] == 0
    assert score["counts"]["regions_total"] == 1


def test_end_errors_are_scored(tmp_path):
    src = tmp_path / "episode.ass"
    src.write_text(UNSORTED, encoding="utf-8")
    case = prepare_case("T", "end", "S04", 7, src, tmp_path / "out.ass")
    corrupted = Track.load(case.generated_path, case.fmt)
    noop = ProposalRecord("end", "b1-n", "noop", [], dict(corrupted.time_map()), [], "")
    score = score_case(
        case,
        noop,
        corrupted.time_map(),
        None,
        Tolerances(good_us=50_000, severe_us=10_000_000),
    )
    if any(d[1] != 0 for d in case.injected_cue_deltas.values()):
        assert score["timing_errors_final_end_us"]["count"] > 0
        worst = max(abs(v[1]) for v in case.injected_cue_deltas.values())
        assert score["timing_errors_final_end_us"]["max_abs_us"] == worst


def test_zero_injection_guard_rejects_undetected_drift(tmp_path, fixture_dir):
    src = fixture_dir / "episode.ass"
    rejected = 0
    for seed in range(40):
        try:
            case = prepare_case(
                "Fx00", f"z{seed}", "S02", seed, src, tmp_path / f"z{seed}.ass"
            )
        except ValueError as exc:
            if "no grid-detectable" in str(exc):
                rejected += 1
                continue
            raise
        assert any(ds != 0 or de != 0 for ds, de in case.injected_cue_deltas.values())
    assert rejected == 0
