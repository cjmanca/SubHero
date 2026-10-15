"""Milestone 3: local repairs vs reversible release offset regions.

The F04 transient rule was length/duration blind: ANY sandwiched A->B->A run was
classified as a local cue adjustment, so a long middle section with a genuine
release-specific offset (A for cues 1-30, -2 s for cues 31-230, A for cues
231-260) lost the detection credit for BOTH of its real discontinuities and its
200 cues were counted as local adjustments.

These regressions pin the corrected policy:

- Test A: a short isolated shift repaired perfectly stays a local cue adjustment
  with zero release-break claims (suppressed ONLY because it is short).
- Test B: a sustained reversible offset region keeps both entering/exiting
  breakpoint claims (2 matched true breakpoints, 0 false positives, 0 local
  adjustments), while the same geometry with a short middle run stays local.
- Test C: a candidate introducing a sustained A->B->A regional shift into
  previously correct subtitles is penalized (worsened/harmful/severe cues AND
  false-positive breakpoint claims; nothing is suppressed).
- Test D: the gap-aware sparse-dialogue behavior is preserved (the existing
  test_scoring_breakpoints.py / test_f04_scoring_local_cue.py suite stays green).
- Ambiguous short regions are represented conservatively and explicitly: claims
  are kept, cues are not auto-counted as local adjustments, and the region is
  reported in ``ambiguous_offset_regions`` with descriptors (never silent).
- Ground truth stays scorer-only, and the resolved/unresolved true-breakpoint
  measurement stays independent of the classification.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from bench import adapters, cli, proxy, scoring, validator
from bench.manifests import AcceptanceRecord, CaseManifest, ProposalRecord
from bench.scoring import Tolerances, score_case

SECOND = 1_000_000
TOL = Tolerances(good_us=50_000, severe_us=250_000, break_match_us=500_000)


def _dense_original(n_cues: int) -> dict[str, tuple[int, int]]:
    """Cue k (0-based) onsets at (k + 1) s with a 0.5 s display span."""
    return {
        f"e{i:04d}": ((i + 1) * SECOND, (i + 1) * SECOND + SECOND // 2)
        for i in range(n_cues)
    }


def _case(
    case_id: str,
    original: dict[str, tuple[int, int]],
    injected: dict[str, int],
    true_breaks: list[int],
    scenario: str,
) -> CaseManifest:
    return CaseManifest(
        case_id=case_id,
        source_id="M3",
        scenario=scenario,
        seed=1,
        track_id="ep",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": scenario},
        transform={},
        expected_inverse={},
        injected_cue_deltas={cid: (d, d) for cid, d in injected.items()},
        original_times_us=dict(original),
        true_breakpoints_us=list(true_breaks),
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )


def _corrupted(original: dict[str, tuple[int, int]], injected: dict[str, int]):
    return {
        cid: (s + injected.get(cid, 0), e + injected.get(cid, 0))
        for cid, (s, e) in original.items()
    }


def _proposal(case_id: str, corrupted: dict, applied: dict[str, int]):
    """A proposal whose applied per-cue offsets become piecewise candidate
    regions, each region starting at the corrupted onset of its first cue."""
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
        "b1-m3",
        "1:1-order-preserving",
        regions,
        proposed,
        [],
        "",
    )


# ---------------------------------------------------------------------------
# Test A — isolated error, perfectly repaired: stays a local adjustment
# ---------------------------------------------------------------------------


def test_A_isolated_single_cue_repair_stays_local_with_zero_claims():
    original = _dense_original(5)
    injected = {"e0001": 3 * SECOND // 2}  # S04-style isolated +1.5 s shift
    corrupted = _corrupted(original, injected)
    case = _case("m3-a", original, injected, [], "S04")
    perfect = _proposal(case.case_id, corrupted, {"e0001": -3 * SECOND // 2})
    dis = score_case(case, perfect, corrupted, None, TOL)["discontinuities"]
    # Claims are suppressed ONLY because the reversing run is short in cue count
    # and time (the A->B->A shape alone is no longer sufficient).
    assert dis["detected_breakpoints"] == 0
    assert dis["false_positive_breakpoints"] == 0
    assert dis["matched_true_breakpoints"] == 0
    assert dis["local_cue_adjustments"] == 1
    assert dis["local_cue_adjusted_cue_ids"] == ["e0001"]
    assert dis["ambiguous_offset_regions"] == 0
    assert dis["ambiguous_offset_region_descriptors"] == []
    score = score_case(case, perfect, corrupted, None, TOL)
    assert score["counts"]["repaired_if_blindly_applied"] == 1
    assert score["counts"]["worsened_unaltered_if_blindly_applied"] == 0


def test_A_short_reversing_run_without_true_breaks_counts_two_local():
    original = _dense_original(6)
    injected = {"e0002": 2 * SECOND, "e0003": 2 * SECOND}
    corrupted = _corrupted(original, injected)
    case = _case("m3-a2", original, injected, [], "S04")
    perfect = _proposal(
        case.case_id, corrupted, {"e0002": -2 * SECOND, "e0003": -2 * SECOND}
    )
    dis = score_case(case, perfect, corrupted, None, TOL)["discontinuities"]
    assert dis["detected_breakpoints"] == 0
    assert dis["false_positive_breakpoints"] == 0
    assert dis["local_cue_adjustments"] == 2
    assert dis["ambiguous_offset_regions"] == 0


# ---------------------------------------------------------------------------
# Test B — genuine reversible offset region keeps BOTH discontinuity claims
# ---------------------------------------------------------------------------


def _long_region_case(case_id: str, n_middle: int):
    """Plan example geometry: cues 1-30 offset 0, cues 31..(30+n_middle) offset
    -2 s, the remaining cues offset 0, with true breakpoints at the two region
    boundaries (the onset of the first cue of each new offset block)."""
    original = _dense_original(260)
    start = 30  # 0-based index of the first middle cue = 1-based cue 031
    middle = [f"e{i:04d}" for i in range(start, start + n_middle)]
    injected = {cid: -2 * SECOND for cid in middle}
    true_breaks = [
        (start + 1) * SECOND,  # entering boundary: inside (cue 030, cue 031]
        (start + n_middle + 1) * SECOND,  # exiting boundary
    ]
    case = _case(case_id, original, injected, true_breaks, "S03")
    corrupted = _corrupted(original, injected)
    applied = {cid: 2 * SECOND for cid in middle}
    return case, corrupted, applied


def test_B_perfect_repair_of_long_offset_region_keeps_both_discontinuity_claims():
    case, corrupted, applied = _long_region_case("m3-b", 200)
    perfect = _proposal(case.case_id, corrupted, applied)
    score = score_case(case, perfect, corrupted, None, TOL)
    dis = score["discontinuities"]
    # Acceptance: a perfectly repaired 200-cue release-specific region must NOT
    # lose discontinuity credit merely because its offset returns to 0.
    assert dis["detected_breakpoints"] == 2
    assert sorted(dis["implied_breakpoint_times_us"]) == [31 * SECOND, 231 * SECOND]
    assert dis["matched_true_breakpoints"] == 2
    assert dis["false_positive_breakpoints"] == 0
    assert dis["ambiguous_breakpoints"] == 0
    # These are region corrections, not local cue adjustments.
    assert dis["local_cue_adjustments"] == 0
    assert dis["local_cue_adjusted_cue_ids"] == []
    assert dis["ambiguous_offset_regions"] == 0
    credited = sorted(m["true_breakpoint_us"] for m in dis["matched_breaks"])
    assert credited == [31 * SECOND, 231 * SECOND]
    assert score["counts"]["repaired_if_blindly_applied"] == 200


def test_B_boundary_contrast_short_middle_run_stays_local():
    # Same geometry, 2-cue middle run: short in cue count AND time -> local
    # adjustment with zero claims (no true breakpoints declared).
    case, corrupted, applied = _long_region_case("m3-b2", 2)
    perfect = _proposal(case.case_id, corrupted, applied)
    dis = score_case(case, perfect, corrupted, None, TOL)["discontinuities"]
    assert dis["detected_breakpoints"] == 0
    assert dis["false_positive_breakpoints"] == 0
    assert dis["local_cue_adjustments"] == 2
    assert dis["ambiguous_offset_regions"] == 0


def test_B_sustained_region_with_long_span_and_few_cues_is_not_local():
    # Required change 3: a reversing run must not be classified local SOLELY
    # because the offset returns. Few cues (3) but spread over 40 s > the
    # declared local time bound -> sustained region, claims kept.
    original = {
        f"e{i:04d}": (onset, onset + SECOND // 2)
        for i, onset in enumerate(
            [1 * SECOND, 30 * SECOND, 50 * SECOND, 70 * SECOND, 90 * SECOND]
        )
    }
    injected = {"e0001": -2 * SECOND, "e0002": -2 * SECOND, "e0003": -2 * SECOND}
    corrupted = _corrupted(original, injected)
    case = _case("m3-b3", original, injected, [], "S03")
    repaired = _proposal(
        case.case_id,
        corrupted,
        {"e0001": 2 * SECOND, "e0002": 2 * SECOND, "e0003": 2 * SECOND},
    )
    dis = score_case(case, repaired, corrupted, None, TOL)["discontinuities"]
    assert dis["local_cue_adjustments"] == 0
    assert dis["ambiguous_offset_regions"] == 0
    assert dis["detected_breakpoints"] == 2
    # No true breakpoints exist in this synthetic control, so the claims are
    # honestly reported as false positives (never suppressed).
    assert dis["false_positive_breakpoints"] == 2


# ---------------------------------------------------------------------------
# Test C — spurious sustained regional shift is penalized, not suppressed
# ---------------------------------------------------------------------------


def test_C_spurious_sustained_regional_shift_keeps_harm_and_false_positives():
    # Clean control (no injected errors) + a candidate introducing a sustained
    # A->B->A shift over 30 cues at -2 s.
    original = _dense_original(260)
    injected: dict[str, int] = {}
    corrupted = _corrupted(original, injected)
    case = _case("m3-c", original, injected, [], "S00")
    shifted = [f"e{i:04d}" for i in range(30, 60)]
    applied = {cid: -2 * SECOND for cid in shifted}
    bad = _proposal(case.case_id, corrupted, applied)
    score = score_case(case, bad, corrupted, None, TOL)
    dis = score["discontinuities"]
    counts = score["counts"]
    # Harmful correction is penalized on the cue axis...
    assert counts["worsened_unaltered_if_blindly_applied"] == 30
    assert counts["harmful_proposed"] == 30
    assert counts["harmful_if_blindly_applied"] == 30
    assert counts["severe_if_blindly_applied"] == 30
    assert counts["repaired_if_blindly_applied"] == 0
    # ...and the entering/exiting steps keep their breakpoint claims, so with no
    # true breakpoints every claim is a counted false positive.
    assert dis["detected_breakpoints"] == 2
    assert dis["false_positive_breakpoints"] == 2
    assert dis["matched_true_breakpoints"] == 0
    assert dis["local_cue_adjustments"] == 0
    assert dis["ambiguous_offset_regions"] == 0


# ---------------------------------------------------------------------------
# Ambiguous short regions — conservative, explicit, never silent
# ---------------------------------------------------------------------------


def test_ambiguous_borderline_run_keeps_claims_and_is_reported_explicitly():
    # 8 cues (above the local cue bound, within the declared borderline band)
    # with a short temporal span over a clean control: claims kept, cues NOT
    # auto-counted as local, region reported in the explicit ambiguous field.
    original = _dense_original(260)
    injected: dict[str, int] = {}
    corrupted = _corrupted(original, injected)
    case = _case("m3-amb", original, injected, [], "S00")
    block = [f"e{i:04d}" for i in range(30, 38)]
    applied = {cid: -2 * SECOND for cid in block}
    score = score_case(
        case, _proposal(case.case_id, corrupted, applied), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    assert dis["detected_breakpoints"] == 2
    assert dis["false_positive_breakpoints"] == 2
    assert dis["local_cue_adjustments"] == 0
    assert dis["local_cue_adjusted_cue_ids"] == []
    assert dis["ambiguous_offset_regions"] == 1
    (descriptor,) = dis["ambiguous_offset_region_descriptors"]
    assert descriptor["cue_count"] == 8
    assert descriptor["cue_ids"] == block
    assert descriptor["applied_correction_us"] == -2 * SECOND
    assert descriptor["flanking_correction_us"] == 0
    assert descriptor["first_onset_us"] == 31 * SECOND
    assert descriptor["last_onset_us"] == 38 * SECOND
    assert descriptor["onset_span_us"] == 7 * SECOND
    # Harmful counts remain reported on the cue axis as well.
    assert score["counts"]["worsened_unaltered_if_blindly_applied"] == 8


def test_ambiguous_region_with_true_breakpoints_keeps_detection_credit():
    # Same borderline band where genuine discontinuities DO exist: the claims
    # are kept, so bracketing credit is preserved and nothing is auto-counted.
    case, corrupted, applied = _long_region_case("m3-amb2", 8)
    proposal = _proposal(case.case_id, corrupted, applied)
    dis = score_case(case, proposal, corrupted, None, TOL)["discontinuities"]
    assert dis["detected_breakpoints"] == 2
    assert dis["matched_true_breakpoints"] == 2
    assert dis["false_positive_breakpoints"] == 0
    assert dis["local_cue_adjustments"] == 0
    assert dis["ambiguous_offset_regions"] == 1


# ---------------------------------------------------------------------------
# Independence: final-timing recovery measured separately from classification
# ---------------------------------------------------------------------------


def test_resolution_measurement_is_independent_of_claim_classification():
    case, corrupted, applied = _long_region_case("m3-ind", 200)
    original = {cid: (int(s), int(e)) for cid, (s, e) in case.original_times_us.items()}
    # Arm 1: the claim-making candidate (2 bracketed matches, 0 local).
    claims_score = score_case(
        case, _proposal(case.case_id, corrupted, applied), corrupted, None, TOL
    )
    claims_dis = claims_score["discontinuities"]
    assert claims_dis["detected_breakpoints"] == 2
    assert claims_dis["matched_true_breakpoints"] == 2
    assert claims_dis["local_cue_adjustments"] == 0
    # Arm 2: a candidate that makes NO claims at all, whose accepted final
    # timeline is fully repaired. Timing recovery is credited from the final
    # residuals, independently of the breakpoint classification.
    noop = ProposalRecord(
        case.case_id, "b1-n", "noop", [], dict(corrupted), [], "no changes proposed"
    )
    acceptance = AcceptanceRecord(
        case_id=case.case_id,
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
        notes="M3 independence: accepted final timeline equals original",
    )
    final_score = score_case(case, noop, corrupted, acceptance, TOL)
    final_dis = final_score["discontinuities"]
    assert final_dis["detected_breakpoints"] == 0
    assert final_dis["matched_true_breakpoints"] == 0
    assert final_dis["local_cue_adjustments"] == 0
    assert final_dis["resolved_true_breakpoints"] == 2
    assert final_dis["unresolved_true_breakpoints"] == 0
    # And the claim-making arm's own final timeline recovers the same timing.
    assert claims_dis["resolved_true_breakpoints"] == 2
    assert claims_dis["unresolved_true_breakpoints"] == 0


# ---------------------------------------------------------------------------
# Ground-truth stays scorer-only
# ---------------------------------------------------------------------------


def test_ground_truth_never_enters_the_candidate_side_pipeline():
    # The scorer is the only candidate-facing consumer of true breakpoints; the
    # proposal-side modules must not read them (test_gold_leakage.py covers the
    # gold-label boundary at the adapter/CLI boundary, and asserts the score_case
    # signature exposes no ground-truth parameter).
    for module in (adapters, validator, proxy, cli):
        assert "true_breakpoints" not in inspect.getsource(module), module.__name__
    fields = {f for f in ProposalRecord.__dataclass_fields__}
    assert not any("true_breakpoint" in f or "gold" in f for f in fields)
    # The candidate-visible run/proposal artifacts carry no ground-truth keys, so
    # the new classification fields cannot leak them to a candidate.
    case, corrupted, applied = _long_region_case("m3-leak", 200)
    proposal = _proposal(case.case_id, corrupted, applied)
    assert not any("true_breakpoint" in k for k in proposal.to_json())


def test_module_and_rule_strings_document_the_classified_policy():
    doc = Path(scoring.__file__).read_text(encoding="utf-8")
    score = score_case(*_long_region_case_args())
    rule = score["discontinuities"]["transient_rule"]
    assert "sustained" in rule and "cue count" in rule and "duration" in rule
    assert "ambiguous_offset_regions" in doc


def _long_region_case_args():
    case, corrupted, applied = _long_region_case("m3-rule", 200)
    return (case, _proposal(case.case_id, corrupted, applied), corrupted, None, TOL)
