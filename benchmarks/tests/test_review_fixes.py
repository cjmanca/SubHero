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
    corrupted_times = corrupted.time_map()
    original_times = {
        cid: (int(s), int(e)) for cid, (s, e) in case.original_times_us.items()
    }
    tol = Tolerances(good_us=50_000, severe_us=2_000_000, break_match_us=11_000_000)
    boundaries = case.params["boundaries_us"]
    jumps = case.params["jump_offsets_us"]
    regions = []
    cumulative = 0
    edges = [0] + list(boundaries) + [None]
    for i, jump in enumerate(jumps + [0]):
        regions.append(
            {
                "start_us": edges[i],
                "end_us": edges[i + 1],
                "offset_us": -cumulative,
                "kind": "piecewise",
                "confidence": "run-median",
            }
        )
        cumulative += jump
    perfect = ProposalRecord(
        "bp",
        "b1-test",
        "1:1-order-preserving",
        regions,
        dict(original_times),
        [],
        "",
    )
    noop = ProposalRecord("bp", "b1-n", "noop", [], dict(corrupted_times), [], "")

    noop_score = score_case(case, noop, corrupted_times, None, tol)
    breaks = noop_score["discontinuities"]
    # A no-op proposes no corrections, so it implies NO breakpoints and gets no
    # detection credit (the old residual-domain behavior granted it free credit).
    assert breaks["true_breakpoints"] == len(case.true_breakpoints_us) > 0
    assert breaks["detected_breakpoints"] == 0
    assert breaks["implied_breakpoint_times_us"] == []
    assert breaks["matched_true_breakpoints"] == 0
    assert breaks["false_positive_breakpoints"] == 0
    # Residual steps in the final (unchanged) timeline are the separate
    # unresolved-discontinuity measure, not candidate detection.
    assert breaks["unresolved_true_breakpoints"] == len(case.true_breakpoints_us)

    perfect_score = score_case(case, perfect, corrupted_times, None, tol)
    breaks = perfect_score["discontinuities"]
    # Implied breakpoints are recorded in ORIGINAL-time coordinates: each is the
    # original onset of a cue.
    original_onsets = {s for s, _ in original_times.values()}
    assert breaks["implied_breakpoint_times_us"]
    assert all(t in original_onsets for t in breaks["implied_breakpoint_times_us"])
    # All true breakpoints matched, zero false positives; two adjacent true
    # breakpoints inside one 10 s cue gap collapse into one implied breakpoint.
    assert breaks["true_breakpoints_without_straddle_pair"] == 0
    assert breaks["matched_true_breakpoints"] == breaks["true_breakpoints"]
    assert breaks["false_positive_breakpoints"] == 0
    assert breaks["unresolved_true_breakpoints"] == 0
    assert breaks["resolved_true_breakpoints"] == breaks["true_breakpoints"]
    assert (
        perfect_score["counts"]["repaired_if_blindly_applied"]
        == perfect_score["denominators"]["altered_cues"]
    )
    assert perfect_score["counts"]["worsened_unaltered_if_blindly_applied"] == 0


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
