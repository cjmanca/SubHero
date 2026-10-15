"""Sixth-review Milestone 1 (P1): whole-cue end-boundary safety metrics.

The schema-3 scorer recorded onset AND end errors but drove every aggregate
safety counter (altered/unaltered, repaired, worsened, harmful, severe) from
the ONSET error alone, so end-only defects were invisible in the primary
safety metrics. Schema 4 defines cue-boundary safety on BOTH boundaries:

* altered: either original boundary corrupted beyond the declared tolerance;
* fully repaired: both boundaries restored within tolerance;
* worsened: a previously-correct boundary becomes incorrect beyond tolerance;
* harmful: the proposed/accepted result makes either boundary materially
  worse than its corrupted baseline;
* severe: either boundary exceeds the declared severe tolerance.

Onset-only and end-only detail measurements stay preserved (per-cue
``onset_err_*``/``end_err_*`` values, boundary-level flags, and the
``timing_errors_*_end_us`` distributions) so both axes stay analyzable.
The release-discontinuity detector stays onset-anchored: display-duration
changes are NOT release-jump evidence (brief: cue-boundary safety and
release-offset classification are separate measurements).
"""

from __future__ import annotations

from bench.corrupt import prepare_case
from bench.manifests import CaseManifest, ProposalRecord
from bench.scoring import Tolerances, score_case

SECOND = 1_000_000
TOL = Tolerances(good_us=50_000, severe_us=250_000, break_match_us=500_000)


def _three_cue_original() -> dict[str, tuple[int, int]]:
    return {
        "e0000": (10 * SECOND, 12 * SECOND),
        "e0001": (20 * SECOND, 22 * SECOND),
        "e0002": (30 * SECOND, 32 * SECOND),
    }


def _case(case_id: str, original: dict, scenario: str, injected: dict) -> CaseManifest:
    return CaseManifest(
        case_id=case_id,
        source_id="R6",
        scenario=scenario,
        seed=1,
        track_id="ep",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": scenario},
        transform={},
        expected_inverse={},
        injected_cue_deltas={cid: injected.get(cid, (0, 0)) for cid in original},
        original_times_us=dict(original),
        true_breakpoints_us=[],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )


def _score(
    case: CaseManifest,
    corrupted: dict,
    proposed: dict,
    regions: list[dict] | None = None,
):
    return score_case(
        case,
        ProposalRecord(
            case.case_id,
            "b1-r6",
            "1:1-order-preserving",
            regions if regions is not None else [],
            dict(proposed),
            [],
            "",
        ),
        corrupted,
        None,
        TOL,
    )


def _corrupted_one(case_id: str, cue: tuple[int, int]):
    """Three-cue track whose e0000 is `cue`; the rest stay at their originals."""
    original = _three_cue_original()
    corrupted = dict(original)
    corrupted["e0000"] = cue
    injected = {"e0000": (cue[0] - original["e0000"][0], cue[1] - original["e0000"][1])}
    case = _case(case_id, original, "S04", injected)
    return case, corrupted, injected


# ---------------------------------------------------------------------------
# Test A — clean subtitle, damaged end (end-only proposal harm on a control)
# ---------------------------------------------------------------------------


def test_clean_cue_end_only_proposal_is_harmful_worsened_and_severe():
    original = _three_cue_original()
    corrupted = dict(original)  # clean S00 control: nothing injected
    case = _case("r6-a", original, "S00", {})
    proposed = dict(original)
    proposed["e0000"] = (10 * SECOND, 15 * SECOND)  # 10-12 -> 10-15: end +3 s
    score = _score(case, corrupted, proposed)
    rec = score["per_cue"]["e0000"]
    counts = score["counts"]
    denom = score["denominators"]
    # Onset axis stays clean; end axis carries the 3 s defect.
    assert rec["onset_err_proposed_us"] == 0
    assert rec["end_err_proposed_us"] == 3 * SECOND
    assert score["timing_errors_proposed_us"]["max_abs_us"] == 0
    assert score["timing_errors_final_us"]["max_abs_us"] == 0
    assert score["timing_errors_proposed_end_us"]["max_abs_us"] == 3 * SECOND
    assert score["timing_errors_final_end_us"]["max_abs_us"] == 3 * SECOND
    # The previously-correct cue is worsened and the proposal is harmful —
    # on BOTH the proposed axis and the blind-application axis.
    assert counts["harmful_proposed"] == 1
    assert counts["harmful_if_blindly_applied"] == 1
    assert counts["worsened_unaltered_proposed"] == 1
    assert counts["worsened_unaltered_if_blindly_applied"] == 1
    assert denom["altered_cues"] == 0
    assert denom["unaltered_cues"] == 3
    # Severe accounting recognizes the damaged end boundary.
    assert counts["severe_if_blindly_applied"] == 1
    assert counts["repaired_if_blindly_applied"] == 0
    # Boundary-level detail: the harm/worsening/severity is end-attributed,
    # never onset-attributed.
    assert rec["harmful_end_proposed"] is True
    assert not rec.get("harmful_onset_proposed")
    assert rec["harmful_end_if_blindly_applied"] is True
    assert not rec.get("harmful_onset_if_blindly_applied")
    assert rec["worsened_end_if_blindly_applied"] is True
    assert not rec.get("worsened_onset_if_blindly_applied")
    assert rec["severe_end_if_blindly_applied"] is True
    assert not rec.get("severe_onset_if_blindly_applied")
    assert counts["harmful_end_proposed"] == 1
    assert counts["harmful_onset_proposed"] == 0
    assert counts["worsened_unaltered_end_if_blindly_applied"] == 1
    assert counts["worsened_unaltered_onset_if_blindly_applied"] == 0
    assert counts["severe_end_if_blindly_applied"] == 1
    assert counts["severe_onset_if_blindly_applied"] == 0


# ---------------------------------------------------------------------------
# Test B — end-only corruption repaired
# ---------------------------------------------------------------------------


def test_end_only_corruption_counts_altered_and_fully_repaired():
    case, corrupted, injected = _corrupted_one(
        "r6-b", (10 * SECOND, 15 * SECOND)
    )  # 10-12 -> 10-15: onset intact, end +3 s
    assert injected["e0000"] == (0, 3 * SECOND)
    proposed = dict(corrupted)
    proposed["e0000"] = (10 * SECOND, 12 * SECOND)  # 10-15 -> 10-12: exact inverse
    score = _score(case, corrupted, proposed)
    rec = score["per_cue"]["e0000"]
    counts = score["counts"]
    # Altered on the WHOLE-CUE definition: the end boundary was corrupted.
    assert score["denominators"]["altered_cues"] == 1
    assert score["denominators"]["unaltered_cues"] == 2
    # Fully repaired: BOTH boundaries within tolerance.
    assert counts["repaired_if_blindly_applied"] == 1
    assert counts["repaired_proposed"] == 1
    assert rec["repaired_if_blindly_applied"] is True
    assert rec["repaired_proposed"] is True
    assert rec["repaired_onset_if_blindly_applied"] is True
    assert rec["repaired_end_if_blindly_applied"] is True
    assert counts["repaired_end_if_blindly_applied"] == 1
    # No harmful correction.
    assert counts["harmful_proposed"] == 0
    assert counts["harmful_if_blindly_applied"] == 0
    assert not rec.get("harmful_proposed")
    assert not rec.get("harmful_if_blindly_applied")
    # The repaired cue is not counted as worsened.
    assert counts["worsened_unaltered_if_blindly_applied"] == 0


# ---------------------------------------------------------------------------
# Test C — partial repair (onset repaired, end stays wrong)
# ---------------------------------------------------------------------------


def test_partial_repair_repairs_onset_only_and_is_not_fully_repaired():
    case, corrupted, _ = _corrupted_one(
        "r6-c", (11 * SECOND, 15 * SECOND)
    )  # 10-12 -> 11-15: both boundaries corrupted
    proposed = dict(corrupted)
    proposed["e0000"] = (10 * SECOND, 15 * SECOND)  # onset fixed, end stays +3 s
    score = _score(case, corrupted, proposed)
    rec = score["per_cue"]["e0000"]
    counts = score["counts"]
    assert score["denominators"]["altered_cues"] == 1
    # Onset repaired within tolerance...
    assert rec["onset_err_proposed_us"] == 0
    assert rec["onset_err_final_us"] == 0
    assert rec["repaired_onset_if_blindly_applied"] is True
    assert rec["repaired_onset_proposed"] is True
    assert counts["repaired_onset_if_blindly_applied"] == 1
    # ...the end remains incorrect beyond tolerance.
    assert rec["end_err_proposed_us"] == 3 * SECOND
    assert rec["end_err_final_us"] == 3 * SECOND
    assert not rec.get("repaired_end_if_blindly_applied")
    assert not rec.get("repaired_end_proposed")
    assert counts["repaired_end_if_blindly_applied"] == 0
    # The cue is NOT fully repaired.
    assert counts["repaired_if_blindly_applied"] == 0
    assert counts["repaired_proposed"] == 0
    assert not rec.get("repaired_if_blindly_applied")
    assert not rec.get("repaired_proposed")
    # No harmful/worsened accounting for the repaired onset side.
    assert counts["harmful_proposed"] == 0
    assert counts["worsened_unaltered_if_blindly_applied"] == 0
    # Severe accounting sees the still-damaged end on the final timeline.
    assert counts["severe_if_blindly_applied"] == 1
    assert counts["severe_end_if_blindly_applied"] == 1
    assert counts["severe_onset_if_blindly_applied"] == 0


# ---------------------------------------------------------------------------
# Test D — existing behavior retained (schema-4 view of the schema-3 cases)
# ---------------------------------------------------------------------------


def test_global_offset_recovery_keeps_full_repair_measurements(tmp_path):
    src = tmp_path / "episode.ass"
    src.write_text(
        "[Script Info]\nScriptType: v4.00+\n\n[V4 Styles]\nFormat: Name, Fontname, Fontsize\nStyle: Dialog,Arial,28\n\n[Events]\nFormat: Layer, Start, End, Style, Text\nDialogue: 0,0:00:01.00,0:00:03.00,Dialog,Hello\nDialogue: 0,0:00:11.00,0:00:13.00,Dialog,World\nDialogue: 0,0:00:21.00,0:00:23.00,Dialog,Again\n",
        encoding="utf-8",
    )
    case = prepare_case(
        "T", "r6-d1", "S01", 3, src, tmp_path / "out.ass", track_id="episode"
    )
    from bench.subtitles import Track

    corrupted = Track.load(case.generated_path, case.fmt).time_map()
    exact = ProposalRecord(
        case.case_id,
        "b1-r6d",
        "1:1-order-preserving",
        [
            {
                "start_us": 0,
                "end_us": None,
                "offset_us": -int(case.params["offset_us"]),
                "kind": "global",
            }
        ],
        dict(case.original_times_us),
        [],
        "",
    )
    score = score_case(case, exact, corrupted, None, TOL)
    counts = score["counts"]
    # Global offsets move BOTH boundaries; the exact inverse restores both, so
    # the ordinary global-offset recovery keeps its intended full-repair
    # measurement under whole-cue semantics.
    assert counts["repaired_if_blindly_applied"] == 3
    assert score["denominators"]["altered_cues"] == 3
    assert counts["worsened_unaltered_if_blindly_applied"] == 0
    assert counts["harmful_if_blindly_applied"] == 0
    assert counts["severe_if_blindly_applied"] == 0
    assert score["offset_recovery"]["residual_us"] == 0
    assert score["timing_errors_final_end_us"]["max_abs_us"] == 0


def test_clean_control_noop_stays_all_zero(tmp_path):
    src = tmp_path / "episode.ass"
    src.write_text(
        "[Script Info]\nScriptType: v4.00+\n\n[V4 Styles]\nFormat: Name, Fontname, Fontsize\nStyle: Dialog,Arial,28\n\n[Events]\nFormat: Layer, Start, End, Style, Text\nDialogue: 0,0:00:01.00,0:00:03.00,Dialog,Hello\nDialogue: 0,0:00:11.00,0:00:13.00,Dialog,World\nDialogue: 0,0:00:21.00,0:00:23.00,Dialog,Again\n",
        encoding="utf-8",
    )
    case = prepare_case(
        "T", "r6-d2", "S00", 5, src, tmp_path / "out.ass", track_id="episode"
    )
    from bench.subtitles import Track

    corrupted = Track.load(case.generated_path, case.fmt).time_map()
    noop = ProposalRecord(
        case.case_id, "b1-n", "noop", [], dict(corrupted), [], "no changes proposed"
    )
    score = score_case(case, noop, corrupted, None, TOL)
    counts = score["counts"]
    denom = score["denominators"]
    # Unchanged S00 controls: no alterations, no repairs, no harm, no severity,
    # and the noop keeps its zero release-discontinuity claims.
    assert denom["altered_cues"] == 0
    assert denom["unaltered_cues"] == 3
    assert counts["repaired_if_blindly_applied"] == 0
    assert counts["worsened_unaltered_if_blindly_applied"] == 0
    assert counts["harmful_proposed"] == 0
    assert counts["harmful_if_blindly_applied"] == 0
    assert counts["severe_if_blindly_applied"] == 0
    assert score["discontinuities"]["detected_breakpoints"] == 0
    assert score["discontinuities"]["false_positive_breakpoints"] == 0


def test_perfect_s03_piecewise_repair_keeps_repair_and_break_credit():
    # Hand-built S03-style track: two true release boundaries at 20 s and
    # 40 s; the corruptions shift onset AND end of every cue in the affected
    # segments (a release offset moves the whole region).
    second = SECOND
    original = {
        "e0000": (5 * second, 8 * second),
        "e0001": (15 * second, 18 * second),
        "e0002": (25 * second, 28 * second),
        "e0003": (35 * second, 38 * second),
        "e0004": (45 * second, 48 * second),
        "e0005": (55 * second, 58 * second),
    }
    shifts = {
        "e0000": 0,
        "e0001": 0,
        "e0002": 3 * second,
        "e0003": 3 * second,
        "e0004": 6 * second,
        "e0005": 6 * second,
    }
    corrupted = {
        cid: (s + shifts[cid], e + shifts[cid]) for cid, (s, e) in original.items()
    }
    injected = {cid: (d, d) for cid, d in shifts.items() if d}
    case = CaseManifest(
        case_id="r6-d3",
        source_id="R6",
        scenario="S03",
        seed=1,
        track_id="ep",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": "S03"},
        transform={},
        expected_inverse={},
        injected_cue_deltas=injected,
        original_times_us=dict(original),
        true_breakpoints_us=[20 * second, 40 * second],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )
    # Perfect piecewise inverse: every region returns to its original timing.
    applied = {cid: -d for cid, d in shifts.items()}
    order = sorted(corrupted, key=lambda cid: (corrupted[cid][0], cid))
    regions: list[dict] = []
    prev = None
    for cid in order:
        off = applied[cid]
        if prev is None or off != prev:
            start = 0 if not regions else int(corrupted[cid][0])
            if regions:
                regions[-1]["end_us"] = start
            regions.append({"start_us": start, "end_us": None, "offset_us": off})
            prev = off
    proposed = {
        cid: (corrupted[cid][0] + applied[cid], corrupted[cid][1] + applied[cid])
        for cid in corrupted
    }
    score = score_case(
        case,
        ProposalRecord(
            case.case_id, "b1-r6d3", "1:1-order-preserving", regions, proposed, [], ""
        ),
        corrupted,
        None,
        TOL,
    )
    counts = score["counts"]
    dis = score["discontinuities"]
    # Correctly repaired S03 discontinuities keep their intended measurements:
    # every altered cue fully repaired, both true breakpoints matched, no
    # false positives, no worsening, no harm, no severe final error.
    assert counts["repaired_if_blindly_applied"] == 4
    assert score["denominators"]["altered_cues"] == 4
    assert dis["matched_true_breakpoints"] == 2
    assert dis["false_positive_breakpoints"] == 0
    assert dis["unresolved_true_breakpoints"] == 0
    assert counts["worsened_unaltered_if_blindly_applied"] == 0
    assert counts["harmful_proposed"] == 0
    assert counts["harmful_if_blindly_applied"] == 0
    assert counts["severe_if_blindly_applied"] == 0
    assert score["timing_errors_final_end_us"]["max_abs_us"] == 0


def test_schema_version_marks_the_whole_cue_semantics():
    # The aggregate counter semantics changed; rows must declare the new
    # version so old onset-only-scored rows can never mix into comparisons.
    original = _three_cue_original()
    corrupted = dict(original)
    case = _case("r6-v", original, "S00", {})
    score = _score(case, corrupted, dict(original))
    assert score["schema_version"] == 4
