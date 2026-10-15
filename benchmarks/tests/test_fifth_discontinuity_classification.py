"""Fifth-review Milestone 2: discontinuity classification around local adjustments.

Finding A (P1): a sustained offset region hidden behind short transient runs
kept ZERO detections under the old boundary rule (`transient[ra] or
transient[rb]`), because a neighbouring transient run automatically suppressed
the boundary ENTERING the sustained region. Boundary suppression is now owned
by the local correction excursions: a sustained region's boundary keeps its
release-discontinuity claim and its false-positive penalty.

Finding B (P2): a ONE-CUE isolated correction at a track boundary (first or
last cue) had no outer anchor, so it was classified sustained and a perfect
repair earned a false-release-discontinuity penalty. Edge 1-cue deviating runs
against the zero baseline are now EDGE-AMBIGUOUS: the sole boundary claim is
suppressed, cues are not auto-counted as local, the ambiguity is recorded
explicitly, and timing repair / harm are scored on the cue axis independently.
A genuine sustained offset beginning at the first cue keeps its claims.
"""

from __future__ import annotations

from bench.manifests import CaseManifest, ProposalRecord
from bench.scoring import Tolerances, score_case

SECOND = 1_000_000
TOL = Tolerances(good_us=50_000, severe_us=250_000, break_match_us=500_000)


def _dense_original(n_cues: int) -> dict[str, tuple[int, int]]:
    return {
        f"e{i:04d}": ((i + 1) * SECOND, (i + 1) * SECOND + SECOND // 2)
        for i in range(n_cues)
    }


def _case(case_id: str, original: dict, true_breaks: list[int], scenario: str):
    return CaseManifest(
        case_id=case_id,
        source_id="R5",
        scenario=scenario,
        seed=1,
        track_id="ep",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": scenario},
        transform={},
        expected_inverse={},
        injected_cue_deltas={cid: (0, 0) for cid in original},
        original_times_us=dict(original),
        true_breakpoints_us=list(true_breaks),
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )


def _proposal(case_id: str, corrupted: dict, applied: dict[str, int]):
    order = sorted(corrupted, key=lambda cid: (int(corrupted[cid][0]), cid))
    regions: list[dict] = []
    prev: int | None = None
    for cid in order:
        off = applied.get(cid, 0)
        if prev is None or off != prev:
            start = 0 if prev is None else int(corrupted[cid][0])
            if regions:
                regions[-1]["end_us"] = start
            regions.append({"start_us": start, "end_us": None, "offset_us": off})
        prev = off
    proposed = {
        cid: (
            corrupted[cid][0] + applied.get(cid, 0),
            corrupted[cid][1] + applied.get(cid, 0),
        )
        for cid in corrupted
    }
    return ProposalRecord(
        case_id,
        "b1-r5",
        "1:1-order-preserving",
        regions,
        proposed,
        [],
        "",
    )


# ---------------------------------------------------------------------------
# Finding A — sustained region hidden by adjacent transient runs
# ---------------------------------------------------------------------------


def test_sustained_block_behind_transient_runs_keeps_release_claim_and_penalty():
    # PLAN.md's exact correction sequence on a track that was ALREADY
    # correctly synchronized (clean S00 control, no true breakpoints):
    #   cues 001-010: 0 s, cue 011: -2 s, cue 012: 0 s, cues 013-037: -2 s
    # The old rule suppressed the boundary entering the 25-cue sustained -2 s
    # block (its preceding run — the untouched cue 012 gap — was transient),
    # yielding ZERO detections despite the substantial sustained correction.
    original = _dense_original(37)
    corrupted = dict(original)
    case = _case("r5-a", original, [], "S00")
    applied = {cid: 0 for cid in original}
    applied["e0010"] = -2 * SECOND  # cue 011: isolated local correction
    applied.update({f"e{i:04d}": -2 * SECOND for i in range(12, 37)})  # cues 013-037
    score = score_case(
        case, _proposal(case.case_id, corrupted, applied), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    # The sustained final block contributes a release-discontinuity claim.
    assert dis["detected_breakpoints"] == 1
    assert dis["implied_breakpoint_times_us"] == [13 * SECOND]
    # The reference was already synchronized: no true breakpoints, so the
    # sustained regional discontinuity is counted as a false-positive change.
    assert dis["false_positive_breakpoints"] == 1
    assert dis["matched_true_breakpoints"] == 0
    # The isolated local correction is detected as a local cue adjustment.
    assert dis["local_cue_adjustments"] == 1
    assert dis["local_cue_adjusted_cue_ids"] == ["e0010"]
    # The harmful timing changes are penalized on the cue axis.
    counts = score["counts"]
    assert counts["repaired_if_blindly_applied"] == 0
    assert counts["worsened_unaltered_if_blindly_applied"] == 26
    assert counts["harmful_if_blindly_applied"] == 26
    assert counts["severe_if_blindly_applied"] == 26


def test_oscillation_between_transient_shifts_stays_suppressed_with_zero_runs():
    # [0, -2, 0, -2, 0] (isolated shifts, zero baseline everywhere): every
    # boundary sits between two transient excursion runs, so suppression
    # remains correct — the M3 oscillation semantics are preserved.
    original = _dense_original(5)
    injected = {"e0001": 2 * SECOND, "e0003": 2 * SECOND}
    corrupted = {
        cid: (s + injected.get(cid, 0), e + injected.get(cid, 0))
        for cid, (s, e) in original.items()
    }
    case = CaseManifest(
        case_id="r5-a2",
        source_id="R5",
        scenario="S04",
        seed=1,
        track_id="ep",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": "S04"},
        transform={},
        expected_inverse={},
        injected_cue_deltas={cid: (d, d) for cid, d in injected.items()},
        original_times_us=dict(original),
        true_breakpoints_us=[],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )
    applied = {"e0001": -2 * SECOND, "e0003": -2 * SECOND}
    dis = score_case(
        case, _proposal(case.case_id, corrupted, applied), corrupted, None, TOL
    )["discontinuities"]
    assert dis["detected_breakpoints"] == 0
    assert dis["false_positive_breakpoints"] == 0
    assert dis["local_cue_adjustments"] == 2


def test_sustained_offset_with_zero_run_gap_keeps_both_region_boundaries():
    # [+2 (20 cues), 0 (1 untouched cue), +2 (20 cues)] on a clean control:
    # the zero gap run is transient, the shifted blocks are sustained — the
    # zero neighbour must NOT suppress the sustained region's boundaries.
    original = _dense_original(41)
    corrupted = dict(original)
    case = _case("r5-a3", original, [], "S00")
    applied = {f"e{i:04d}": 2 * SECOND for i in range(20)}
    applied.update({f"e{i:04d}": 2 * SECOND for i in range(21, 41)})
    score = score_case(
        case, _proposal(case.case_id, corrupted, applied), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    assert dis["detected_breakpoints"] == 2
    assert dis["false_positive_breakpoints"] == 2
    assert dis["local_cue_adjustments"] == 0
    assert dis["ambiguous_offset_regions"] == 0
    assert dis["edge_ambiguous_regions"] == 0
    assert score["counts"]["worsened_unaltered_if_blindly_applied"] == 40


# ---------------------------------------------------------------------------
# Finding B — isolated correction at a track boundary
# ---------------------------------------------------------------------------


def _s04_boundary_case(case_id: str, n_cues: int, target: str):
    """S04-style: ONE isolated +2 s shift on `target`; perfect repair inverse."""
    original = _dense_original(n_cues)
    injected = {target: 2 * SECOND}
    corrupted = {
        cid: (s + injected.get(cid, 0), e + injected.get(cid, 0))
        for cid, (s, e) in original.items()
    }
    case = CaseManifest(
        case_id=case_id,
        source_id="R5",
        scenario="S04",
        seed=1,
        track_id="ep",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": "S04"},
        transform={},
        expected_inverse={},
        injected_cue_deltas={cid: (d, d) for cid, d in injected.items()},
        original_times_us=dict(original),
        true_breakpoints_us=[],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )
    applied = {target: -2 * SECOND}
    return case, corrupted, applied


def test_first_cue_isolated_repair_gets_credit_without_false_release_penalty():
    case, corrupted, applied = _s04_boundary_case("r5-b1", 21, "e0000")
    score = score_case(
        case, _proposal(case.case_id, corrupted, applied), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    assert score["counts"]["repaired_if_blindly_applied"] == 1
    assert score["counts"]["worsened_unaltered_if_blindly_applied"] == 0
    assert score["counts"]["harmful_if_blindly_applied"] == 0
    # The localization claim survives (a genuine boundary release offset must
    # keep bracketing credit), but on this S04 control (no true breakpoints)
    # the perfect isolated repair receives NO false-release-discontinuity
    # penalty: the unmatched edge claim is recorded as an explicit ambiguity.
    assert dis["detected_breakpoints"] == 1
    assert dis["matched_true_breakpoints"] == 0
    assert dis["false_positive_breakpoints"] == 0
    assert dis["unmatched_edge_ambiguous_claims"] == 1
    # The edge ambiguity is recorded explicitly, not silently absorbed.
    assert dis["edge_ambiguous_regions"] == 1
    (descriptor,) = dis["edge_ambiguity_descriptors"]
    assert descriptor["edge"] == "first"
    assert descriptor["cue_ids"] == ["e0000"]
    assert descriptor["cue_count"] == 1
    assert descriptor["applied_correction_us"] == -2 * SECOND
    assert descriptor["neighbour_correction_us"] == 0
    assert dis["ambiguous_offset_regions"] == 0
    assert dis["local_cue_adjustments"] == 0


def test_last_cue_isolated_repair_gets_credit_without_false_release_penalty():
    case, corrupted, applied = _s04_boundary_case("r5-b2", 21, "e0020")
    score = score_case(
        case, _proposal(case.case_id, corrupted, applied), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    assert score["counts"]["repaired_if_blindly_applied"] == 1
    assert score["counts"]["worsened_unaltered_if_blindly_applied"] == 0
    assert dis["detected_breakpoints"] == 1
    assert dis["false_positive_breakpoints"] == 0
    assert dis["unmatched_edge_ambiguous_claims"] == 1
    assert dis["edge_ambiguous_regions"] == 1
    (descriptor,) = dis["edge_ambiguity_descriptors"]
    assert descriptor["edge"] == "last"
    assert descriptor["cue_ids"] == ["e0020"]
    assert dis["local_cue_adjustments"] == 0


def test_interior_cue_isolated_repair_unchanged_transient_local():
    case, corrupted, applied = _s04_boundary_case("r5-b3", 21, "e0010")
    score = score_case(
        case, _proposal(case.case_id, corrupted, applied), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    assert score["counts"]["repaired_if_blindly_applied"] == 1
    assert dis["detected_breakpoints"] == 0
    assert dis["false_positive_breakpoints"] == 0
    # Interior transient local adjustment: unchanged classification, and it is
    # NOT an edge-ambiguous region.
    assert dis["local_cue_adjustments"] == 1
    assert dis["local_cue_adjusted_cue_ids"] == ["e0010"]
    assert dis["edge_ambiguous_regions"] == 0


def test_sustained_offset_beginning_at_first_cue_keeps_its_claims():
    # Preserved plan requirement: a genuinely sustained erroneous offset
    # (10 cues at +2 s) introduced into previously correct subtitles is NOT a
    # one-cue edge adjustment; its change-point claim (and false-positive
    # penalty) survives at the track boundary.
    original = _dense_original(25)
    corrupted = dict(original)
    case = _case("r5-b4", original, [], "S00")
    applied = {f"e{i:04d}": 2 * SECOND for i in range(10)}
    score = score_case(
        case, _proposal(case.case_id, corrupted, applied), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    assert dis["detected_breakpoints"] == 1
    assert dis["implied_breakpoint_times_us"] == [11 * SECOND]
    assert dis["false_positive_breakpoints"] == 1
    assert dis["edge_ambiguous_regions"] == 0
    assert dis["local_cue_adjustments"] == 0
    assert score["counts"]["worsened_unaltered_if_blindly_applied"] == 10
    assert score["counts"]["harmful_if_blindly_applied"] == 10


def test_classification_never_reads_ground_truth_positions():
    # Ground truth is scorer-only: the classification must not consult
    # case.true_breakpoints_us when classifying runs / suppressing boundaries.
    import inspect

    from bench import scoring

    src = inspect.getsource(scoring.score_case)
    cls_start = src.index("# F04 + M3: stable-support classification")
    cls_end = src.index("true_breaks = sorted(")
    classification_block = src[cls_start:cls_end]
    assert "true_breakpoints" not in classification_block
