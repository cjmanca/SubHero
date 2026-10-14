"""Schema-v2 scoring: candidate-implied breakpoints, unresolved true breakpoints,
offset-recovery sign convention, and report rendering."""

from __future__ import annotations

import json
from pathlib import Path

from bench.manifests import AcceptanceRecord, CaseManifest, ProposalRecord
from bench.reporting import build_report
from bench.scoring import Tolerances, score_case

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"
GOOD = 50_000
SEVERE = 250_000
BREAK_MATCH = 500_000
TOL = Tolerances(good_us=GOOD, severe_us=SEVERE, break_match_us=BREAK_MATCH)


def _load_committed_case(case_id: str) -> CaseManifest:
    d = json.loads((CASES_DIR / f"{case_id}.case.json").read_text(encoding="utf-8"))
    d.pop("schema_version", None)
    return CaseManifest(**d)


def _corrupted_from_manifest(case: CaseManifest) -> dict[str, tuple[int, int]]:
    return {
        cid: (int(times[0]) + int(delta[0]), int(times[1]) + int(delta[1]))
        for cid, times in case.original_times_us.items()
        for delta in [case.injected_cue_deltas[cid]]
    }


def _hand_s03_case() -> CaseManifest:
    """Two true breakpoints exactly at cue onsets 10 s and 30 s (original time).

    Region offsets injected: 0 for t<10s, +3 s for 10s..30s, +6 s for t>=30s.
    """
    original = {
        f"e{i:04d}": (start, start + 1_000_000)
        for i, start in enumerate(
            [1_000_000, 5_000_000, 10_000_000, 20_000_000, 30_000_000, 40_000_000]
        )
    }
    region_offset = {
        "e0000": 0,
        "e0001": 0,
        "e0002": 3_000_000,
        "e0003": 3_000_000,
        "e0004": 6_000_000,
        "e0005": 6_000_000,
    }
    injected = {cid: (off, off) for cid, off in region_offset.items()}
    return CaseManifest(
        case_id="hand-s03",
        source_id="HAND",
        scenario="S03",
        seed=0,
        track_id="episode",
        fmt="ass",
        grid_us=10_000,
        params={
            "scenario": "S03",
            "boundaries_us": [10_000_000, 30_000_000],
            "jump_offsets_us": [3_000_000, 3_000_000],
        },
        transform={},
        expected_inverse={},
        injected_cue_deltas=injected,
        original_times_us=original,
        true_breakpoints_us=[10_000_000, 30_000_000],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )


def _piecewise_regions(offsets: dict[str, int]) -> list[dict]:
    """Regions from a per-cue applied-shift map, keyed in cue order."""
    regions: list[dict] = []
    prev: int | None = None
    for cid in sorted(offsets):
        off = offsets[cid]
        if prev is None or abs(off - prev) > 2 * GOOD:
            regions.append(
                {
                    "start_us": None,
                    "end_us": None,
                    "offset_us": off,
                    "kind": "piecewise",
                    "confidence": "test",
                }
            )
        prev = off
    return regions


def _gap_s03_case() -> CaseManifest:
    """S03 with two discontinuities in subtitle-free gaps (between cue onsets).

    Cue onsets at 1/10/12/30/32/50 s. True breakpoints at 8 s and 28 s, i.e.
    strictly inside the (1,10] and (12,30] gaps. Region offsets injected: 0 for
    t<8s, +3s for 8s..28s, +6s for t>=28s.
    """
    original = {
        f"e{i:04d}": (start, start + 1_000_000)
        for i, start in enumerate(
            [1_000_000, 10_000_000, 12_000_000, 30_000_000, 32_000_000, 50_000_000]
        )
    }
    region_offset = {
        "e0000": 0,
        "e0001": 3_000_000,
        "e0002": 3_000_000,
        "e0003": 6_000_000,
        "e0004": 6_000_000,
        "e0005": 6_000_000,
    }
    injected = {cid: (off, off) for cid, off in region_offset.items()}
    return CaseManifest(
        case_id="gap-s03",
        source_id="GAP",
        scenario="S03",
        seed=0,
        track_id="episode",
        fmt="ass",
        grid_us=10_000,
        params={
            "scenario": "S03",
            "boundaries_us": [8_000_000, 28_000_000],
            "jump_offsets_us": [3_000_000, 3_000_000],
        },
        transform={},
        expected_inverse={},
        injected_cue_deltas=injected,
        original_times_us=original,
        true_breakpoints_us=[8_000_000, 28_000_000],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )


def _perfect_inverse(case: CaseManifest, candidate_id: str = "b1-ideal"):
    """A candidate applying the exact per-cue inverse of the injection."""
    corrupted = _corrupted_from_manifest(case)
    original = {cid: (int(s), int(e)) for cid, (s, e) in case.original_times_us.items()}
    applied = {cid: original[cid][0] - corrupted[cid][0] for cid in corrupted}
    proposed = {
        cid: (corrupted[cid][0] + applied[cid], corrupted[cid][1] + applied[cid])
        for cid in corrupted
    }
    assert proposed == original
    return (
        corrupted,
        ProposalRecord(
            case.case_id,
            candidate_id,
            "1:1-order-preserving",
            _piecewise_regions(applied),
            proposed,
            [],
            "",
        ),
    )


# --- A1: an unchanged candidate implies NO breakpoints and gets no credit ---


def test_noop_gets_zero_breakpoint_credit_on_hand_s03():
    case = _hand_s03_case()
    corrupted = _corrupted_from_manifest(case)
    noop = ProposalRecord(
        "hand-s03", "b1-n", "noop", [], dict(corrupted), [], "no changes proposed"
    )
    score = score_case(case, noop, corrupted, None, TOL)
    dis = score["discontinuities"]
    assert score["schema_version"] == 2
    assert dis["jump_threshold_us"] == max(2 * GOOD, 250_000)
    assert dis["true_breakpoints"] == 2
    assert dis["detected_breakpoints"] == 0
    assert dis["implied_breakpoint_times_us"] == []
    assert dis["matched_true_breakpoints"] == 0
    assert dis["false_positive_breakpoints"] == 0


def test_noop_gets_zero_breakpoint_credit_on_committed_s04():
    case = _load_committed_case("Fx00-S04")
    corrupted = _corrupted_from_manifest(case)
    noop = ProposalRecord(
        case.case_id, "b1-n", "noop", [], dict(corrupted), [], "no changes proposed"
    )
    score = score_case(case, noop, corrupted, None, TOL)
    dis = score["discontinuities"]
    # S04's isolated per-cue steps leave big residual jumps; a no-op must not
    # be credited for discontinuities it did nothing about.
    assert dis["detected_breakpoints"] == 0
    assert dis["matched_true_breakpoints"] == 0
    assert dis["false_positive_breakpoints"] == 0


# --- A2: perfect piecewise repair implies breakpoints exactly at true ones ---


def test_perfect_piecewise_repair_matches_all_true_breakpoints():
    case = _hand_s03_case()
    corrupted = _corrupted_from_manifest(case)
    original = {cid: (int(s), int(e)) for cid, (s, e) in case.original_times_us.items()}
    applied = {
        "e0000": 0,
        "e0001": 0,
        "e0002": -3_000_000,
        "e0003": -3_000_000,
        "e0004": -6_000_000,
        "e0005": -6_000_000,
    }
    proposed = {
        cid: (corrupted[cid][0] + applied[cid], corrupted[cid][1] + applied[cid])
        for cid in corrupted
    }
    assert proposed == original
    perfect = ProposalRecord(
        case.case_id,
        "b1-test",
        "1:1-order-preserving",
        _piecewise_regions(applied),
        proposed,
        [],
        "",
    )
    score = score_case(case, perfect, corrupted, None, TOL)
    dis = score["discontinuities"]
    assert dis["detected_breakpoints"] == 2
    assert sorted(dis["implied_breakpoint_times_us"]) == [10_000_000, 30_000_000]
    assert dis["matched_true_breakpoints"] == len(case.true_breakpoints_us)
    assert dis["false_positive_breakpoints"] == 0
    assert score["counts"]["repaired"] == score["denominators"]["altered_cues"] == 4
    assert dis["resolved_true_breakpoints"] == 2
    assert dis["unresolved_true_breakpoints"] == 0


# --- A3: extra correction step with no true discontinuity = exactly one FP ---


def test_extra_correction_step_counts_false_positive():
    case = _hand_s03_case()
    corrupted = _corrupted_from_manifest(case)
    applied = {
        "e0000": 0,
        "e0001": 0,
        "e0002": -3_000_000,
        "e0003": -9_000_000,  # extra -3 s step at 20 s, where there is no discontinuity
        "e0004": -6_000_000,
        "e0005": -6_000_000,
    }
    proposed = {
        cid: (corrupted[cid][0] + applied[cid], corrupted[cid][1] + applied[cid])
        for cid in corrupted
    }
    extra = ProposalRecord(
        case.case_id,
        "b1-test",
        "1:1-order-preserving",
        _piecewise_regions(applied),
        proposed,
        [],
        "",
    )
    score = score_case(case, extra, corrupted, None, TOL)
    dis = score["discontinuities"]
    assert sorted(dis["implied_breakpoint_times_us"]) == [
        10_000_000,
        20_000_000,
        30_000_000,
    ]
    assert dis["matched_true_breakpoints"] == 2
    assert dis["false_positive_breakpoints"] == 1
    assert dis["detected_breakpoints"] == 3


# --- A4: unaltered-region protection and no credit for unproposed regions ---


def test_proposal_touching_synchronized_cues_counts_worsened_and_harmful():
    case = _hand_s03_case()
    corrupted = _corrupted_from_manifest(case)
    applied = {
        "e0000": 5_000_000,  # shifts a synchronized cue: harm, no detection credit
        "e0001": 5_000_000,
        "e0002": -3_000_000,
        "e0003": -3_000_000,
        "e0004": -6_000_000,
        "e0005": -6_000_000,
    }
    proposed = {
        cid: (corrupted[cid][0] + applied[cid], corrupted[cid][1] + applied[cid])
        for cid in corrupted
    }
    rec = ProposalRecord(
        case.case_id,
        "b1-test",
        "1:1-order-preserving",
        _piecewise_regions(applied),
        proposed,
        [],
        "",
    )
    score = score_case(case, rec, corrupted, None, TOL)
    counts = score["counts"]
    assert counts["worsened_unaltered"] == 2
    assert counts["worsened_unaltered_proposed"] == 2
    assert counts["harmful_proposed"] == 2
    assert counts["harmful_accepted"] == 2
    assert counts["severe_final"] >= 2
    assert counts["repaired"] == 4
    # Implied breakpoints stay at the two true locations only (the +5 s pair
    # steps at the 10 s boundary, which is a true breakpoint; at 5 s/40 s the
    # corrections are flat, so no extra credit).
    dis = score["discontinuities"]
    assert sorted(dis["implied_breakpoint_times_us"]) == [10_000_000, 30_000_000]
    assert dis["false_positive_breakpoints"] == 0


def test_unresolved_field_uses_final_accepted_state_separate_from_detection():
    case = _hand_s03_case()
    corrupted = _corrupted_from_manifest(case)
    original = {cid: (int(s), int(e)) for cid, (s, e) in case.original_times_us.items()}
    noop = ProposalRecord(
        "hand-s03", "b1-n", "noop", [], dict(corrupted), [], "no changes proposed"
    )
    acceptance = AcceptanceRecord(
        case_id="hand-s03",
        candidate_id="b1-va",
        validated_candidate_id="b1-n",
        status="success",
        accepted_regions=[],
        rejected_regions=[],
        abstained_regions=[],
        accepted_times_us=dict(original),
        sample_cue_ids=[],
        asr_seconds=0.0,
        asr_calls=0,
        notes="test acceptance applying original times",
    )
    score = score_case(case, noop, corrupted, acceptance, TOL)
    dis = score["discontinuities"]
    # The no-op candidate proposed nothing: zero detection credit...
    assert dis["detected_breakpoints"] == 0
    assert dis["matched_true_breakpoints"] == 0
    # ...while the accepted FINAL timeline is continuous: the separate
    # unresolved measure reports 0 of 2.
    assert dis["unresolved_true_breakpoints"] == 0
    assert dis["resolved_true_breakpoints"] == 2
    score_no_acc = score_case(case, noop, corrupted, None, TOL)
    assert score_no_acc["discontinuities"]["unresolved_true_breakpoints"] == 2
    assert score_no_acc["discontinuities"]["resolved_true_breakpoints"] == 0


# --- B: bracketing-interval detection credit (F02 gap cases) ---


def test_committed_s03_gap_perfect_inverse_gets_full_credit():
    # Fx00-S03: true breakpoint 45,120,000 sits in the subtitle-free gap
    # between cue e0018 (onset 45,000,000) and cue e0019 (onset 48,000,000).
    # A perfect inverse records the break at the next cue onset (48 s), 2.88 s
    # from the true breakpoint; bracketing credit must NOT penalize the gap.
    case = _load_committed_case("Fx00-S03")
    corrupted, perfect = _perfect_inverse(case)
    score = score_case(case, perfect, corrupted, None, TOL)
    dis = score["discontinuities"]
    assert dis["detected_breakpoints"] == 1
    assert dis["matched_true_breakpoints"] == dis["true_breakpoints"] == 1
    assert dis["false_positive_breakpoints"] == 0
    assert dis["ambiguous_breakpoints"] == 0
    assert dis["ambiguous_true_breakpoints"] == 0
    (mb,) = dis["matched_breaks"]
    assert mb["true_breakpoint_us"] == 45_120_000
    assert mb["bracket_start_us"] == 45_000_000  # prior cue anchor e0018
    assert mb["bracket_end_us"] == 48_000_000  # next cue anchor e0019
    assert mb["bracket_width_us"] == 3_000_000  # localization uncertainty
    assert mb["implied_break_us"] == 48_000_000
    assert mb["precise_residual_us"] == 2_880_000
    assert mb["precise_within_tol"] is False  # 2.88 s > break_match_us
    assert dis["unresolved_true_breakpoints"] == 0
    assert dis["resolved_true_breakpoints"] == 1


def test_committed_s03_gap_noop_gets_zero_credit():
    case = _load_committed_case("Fx00-S03")
    corrupted = _corrupted_from_manifest(case)
    noop = ProposalRecord(
        case.case_id, "b1-n", "noop", [], dict(corrupted), [], "no changes proposed"
    )
    dis = score_case(case, noop, corrupted, None, TOL)["discontinuities"]
    assert dis["detected_breakpoints"] == 0
    assert dis["matched_true_breakpoints"] == 0
    assert dis["false_positive_breakpoints"] == 0
    assert dis["ambiguous_breakpoints"] == 0


def test_multiple_gap_jumps_repair_gets_full_credit_one_to_one():
    # Two discontinuities in gaps, both repaired perfectly -> full credit,
    # one-to-one, zero false positives.
    case = _gap_s03_case()
    corrupted, perfect = _perfect_inverse(case)
    dis = score_case(case, perfect, corrupted, None, TOL)["discontinuities"]
    assert dis["true_breakpoints"] == 2
    assert dis["detected_breakpoints"] == 2
    assert dis["matched_true_breakpoints"] == 2
    assert dis["false_positive_breakpoints"] == 0
    assert dis["ambiguous_breakpoints"] == 0
    credited = sorted(m["true_breakpoint_us"] for m in dis["matched_breaks"])
    assert credited == [8_000_000, 28_000_000]  # each credited exactly once
    brackets = {
        (m["bracket_start_us"], m["bracket_end_us"]) for m in dis["matched_breaks"]
    }
    assert brackets == {(1_000_000, 10_000_000), (12_000_000, 30_000_000)}


def test_sparse_dialogue_wide_bracket_credits_and_reports_uncertainty():
    # A jump whose bracketing interval is wide (only two cues, 39 s apart):
    # credited via the interval, localization uncertainty reflects the bracket.
    original = {
        "e0000": (1_000_000, 2_000_000),
        "e0001": (40_000_000, 41_000_000),
    }
    injected = {"e0000": (0, 0), "e0001": (5_000_000, 5_000_000)}
    case = CaseManifest(
        case_id="sparse-s03",
        source_id="SPARSE",
        scenario="S03",
        seed=0,
        track_id="episode",
        fmt="ass",
        grid_us=10_000,
        params={
            "scenario": "S03",
            "boundaries_us": [25_000_000],
            "jump_offsets_us": [5_000_000],
        },
        transform={},
        expected_inverse={},
        injected_cue_deltas=injected,
        original_times_us=original,
        true_breakpoints_us=[25_000_000],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )
    corrupted, perfect = _perfect_inverse(case)
    dis = score_case(case, perfect, corrupted, None, TOL)["discontinuities"]
    assert dis["detected_breakpoints"] == 1
    assert dis["matched_true_breakpoints"] == 1
    assert dis["false_positive_breakpoints"] == 0
    (mb,) = dis["matched_breaks"]
    assert mb["bracket_start_us"] == 1_000_000
    assert mb["bracket_end_us"] == 40_000_000
    assert mb["bracket_width_us"] == 39_000_000
    assert mb["precise_within_tol"] is False


def test_ambiguous_interval_no_auto_credit_and_counted():
    # Two true breakpoints in one cue gap with NO proposed sub-boundary: the
    # single cue-anchor implied break cannot uniquely localize them -> no
    # automatic credit, reported as an explicit ambiguous abstention (0 matched,
    # 0 false positives, 2 true breakpoints abstained).
    original = {
        "e0000": (1_000_000, 2_000_000),
        "e0001": (40_000_000, 41_000_000),
        "e0002": (50_000_000, 51_000_000),
    }
    injected = {
        "e0000": (0, 0),
        "e0001": (5_000_000, 5_000_000),
        "e0002": (5_000_000, 5_000_000),
    }
    case = CaseManifest(
        case_id="ambiguous-s03",
        source_id="AMB",
        scenario="S03",
        seed=0,
        track_id="episode",
        fmt="ass",
        grid_us=10_000,
        params={
            "scenario": "S03",
            "boundaries_us": [10_000_000, 20_000_000],
            "jump_offsets_us": [5_000_000, 0],
        },
        transform={},
        expected_inverse={},
        injected_cue_deltas=injected,
        original_times_us=original,
        true_breakpoints_us=[10_000_000, 20_000_000],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )
    corrupted, perfect = _perfect_inverse(case)
    dis = score_case(case, perfect, corrupted, None, TOL)["discontinuities"]
    assert dis["true_breakpoints"] == 2
    assert dis["detected_breakpoints"] == 1
    assert dis["matched_true_breakpoints"] == 0  # no automatic credit
    assert dis["false_positive_breakpoints"] == 0  # not a spurious break
    assert dis["ambiguous_breakpoints"] == 1
    assert dis["ambiguous_true_breakpoints"] == 2
    assert dis["matched_breaks"] == []


# --- C: offset recovery sign convention, pinned on committed Fx00-S01 data ---


def _s01_offset_recovery(applied_region_offset: int | None, mapping_status: str):
    case = _load_committed_case("Fx00-S01")
    corrupted = _corrupted_from_manifest(case)
    true_offset = int(case.params["offset_us"])
    if mapping_status == "noop":
        proposed = dict(corrupted)
        regions = [{"start_us": 0, "end_us": None, "offset_us": 0, "kind": "global"}]
    else:
        proposed = {
            cid: (times[0] + applied_region_offset, times[1] + applied_region_offset)
            for cid, times in corrupted.items()
        }
        regions = [
            {
                "start_us": 0,
                "end_us": None,
                "offset_us": applied_region_offset,
                "kind": "global",
            }
        ]
    proposal = ProposalRecord(
        case.case_id, "b1-test", mapping_status, regions, proposed, [], ""
    )
    score = score_case(case, proposal, corrupted, None, TOL)
    return case, true_offset, score["offset_recovery"]


def test_s01_exact_inverse_residual_zero():
    # corrupt.py/timeline.py Segment.apply: corrupted = original + offset_us
    # (committed Fx00-S01 injected deltas are all +1_900_000 == params.offset_us).
    case, true_offset, recovery = _s01_offset_recovery(
        -1_900_000, "1:1-order-preserving"
    )
    assert true_offset == int(case.params["offset_us"]) == 1_900_000
    assert recovery is not None
    assert recovery["true_offset_us"] == 1_900_000
    assert recovery["applied_shift_us"] == -1_900_000
    assert recovery["recovered_offset_us"] == 1_900_000
    assert recovery["residual_us"] == 0
    assert "applied shift" in recovery["convention"]


def test_s01_noop_reports_zero_applied_shift_with_residual():
    _case, true_offset, recovery = _s01_offset_recovery(None, "noop")
    assert recovery is not None
    assert recovery["applied_shift_us"] == 0
    assert recovery["recovered_offset_us"] == 0
    assert recovery["residual_us"] == abs(true_offset)


def test_s01_wrong_sign_proposal_residual_is_double_offset():
    _case, true_offset, recovery = _s01_offset_recovery(
        1_900_000, "1:1-order-preserving"
    )
    assert recovery is not None
    assert recovery["applied_shift_us"] == 1_900_000
    assert recovery["recovered_offset_us"] == -1_900_000
    assert recovery["residual_us"] == 2 * abs(true_offset)


def test_s01_gate_keeps_empty_regions_and_other_statuses_out():
    case = _load_committed_case("Fx00-S01")
    corrupted = _corrupted_from_manifest(case)
    noop_empty_regions = ProposalRecord(
        case.case_id, "b1-n", "noop", [], dict(corrupted), [], ""
    )
    score = score_case(case, noop_empty_regions, corrupted, None, TOL)
    assert score["offset_recovery"] is None
    abstain = ProposalRecord(
        case.case_id,
        "b1-al",
        "abstain_no_speech_anchors",
        [{"start_us": 0, "end_us": None, "offset_us": 0}],
        {},
        list(corrupted),
        "",
    )
    score = score_case(case, abstain, corrupted, None, TOL)
    assert score["offset_recovery"] is None
    assert score["counts"]["abstained_regions"] == 1


# --- D: reporting renders v2 fields and ignores v1 rows ---


def test_report_renders_v2_fields_and_skips_v1_scores():
    case = _hand_s03_case()
    corrupted = _corrupted_from_manifest(case)
    applied = {
        "e0000": 0,
        "e0001": 0,
        "e0002": -3_000_000,
        "e0003": -3_000_000,
        "e0004": -6_000_000,
        "e0005": -6_000_000,
    }
    proposed = {
        cid: (corrupted[cid][0] + applied[cid], corrupted[cid][1] + applied[cid])
        for cid in corrupted
    }
    perfect = ProposalRecord(
        case.case_id,
        "b1-ideal",
        "1:1-order-preserving",
        _piecewise_regions(applied),
        proposed,
        [],
        "",
    )
    v2 = score_case(case, perfect, corrupted, None, TOL)
    v1 = {
        "schema_version": 1,
        "case_id": "legacy-case",
        "scenario": "S01",
        "candidate_id": "b1-legacy",
        "counts": {
            "proposals_nonzero": 0,
            "accepted_nonzero": 0,
            "repaired": 0,
            "worsened_unaltered": 0,
            "harmful_proposed": 0,
            "harmful_accepted": 0,
        },
        "denominators": {
            "total_cues": 1,
            "altered_cues": 1,
            "unaltered_cues": 0,
        },
        "discontinuities": {
            "true_breakpoints": 1,
            "detected_breakpoints": 1,
            "matched_true_breakpoints": 1,
            "false_positive_breakpoints": 0,
        },
        "timing_errors_final_us": {
            "median_abs_us": 0,
            "p90_abs_us": 0,
            "p95_abs_us": 0,
        },
        "tolerances": {
            "good_us": 50_000,
            "severe_us": 250_000,
            "break_match_us": 500_000,
            "meaning": "test",
        },
        "offset_recovery": None,
    }
    text = build_report(["hand-s03", "legacy-case"], [], [v2, v1], {})
    assert "b1-ideal" in text
    assert "unresolved" in text
    assert (
        "candidate-implied breakpoints 2 (matched 2 of 2 true, false-positive 0" in text
    )
    assert "legacy-case" not in text
    assert "b1-legacy" not in text

    s01_case = _load_committed_case("Fx00-S01")
    s01_corrupted = _corrupted_from_manifest(s01_case)
    _c, _t, recovery = _s01_offset_recovery(-1_900_000, "1:1-order-preserving")
    v2_s01 = score_case(
        s01_case,
        ProposalRecord(
            s01_case.case_id,
            "b1-px-fg",
            "1:1-order-preserving",
            [
                {
                    "start_us": 0,
                    "end_us": None,
                    "offset_us": -1_900_000,
                    "kind": "global",
                }
            ],
            {
                cid: (times[0] - 1_900_000, times[1] - 1_900_000)
                for cid, times in s01_corrupted.items()
            },
            [],
            "",
        ),
        s01_corrupted,
        None,
        TOL,
    )
    text = build_report([s01_case.case_id], [], [v2_s01], {})
    assert "applied shift -1900 ms" in text
    assert "recovered 1900 ms" in text
    assert "residual 0 ms" in text
    assert recovery is not None and recovery["residual_us"] == 0
