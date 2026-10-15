"""Sixth-review Milestone 2 (P2): acceptance-region accounting.

The schema-3 scorer filled ``counts.accepted_regions`` with ``len(regions)``
for tool-only arms — every proposed region was counted as "accepted" even
though NO validator ran. Schema 4 reserves acceptance terminology for
validated decisions:

* unvalidated (tool-only) arms report ``regions_total`` (proposed regions)
  and ``proposed_regions_nonzero`` (regions with proposed changes), and
  ``accepted_regions == 0` — validated acceptance never claims what did not
  happen;
* the b1-va arm reports the ACTUAL accepted / rejected / abstained region
  counts from its bound AcceptanceRecord.
"""

from __future__ import annotations

from bench.manifests import AcceptanceRecord, CaseManifest, ProposalRecord
from bench.scoring import Tolerances, score_case

SECOND = 1_000_000
TOL = Tolerances(good_us=50_000, severe_us=250_000, break_match_us=500_000)


def _case() -> CaseManifest:
    original = {
        "e0000": (10 * SECOND, 12 * SECOND),
        "e0001": (20 * SECOND, 22 * SECOND),
        "e0002": (30 * SECOND, 32 * SECOND),
    }
    return CaseManifest(
        case_id="r6-reg",
        source_id="R6",
        scenario="S00",
        seed=1,
        track_id="ep",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": "S00"},
        transform={},
        expected_inverse={},
        injected_cue_deltas={cid: (0, 0) for cid in original},
        original_times_us=dict(original),
        true_breakpoints_us=[],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )


def _proposal(times: dict, regions: list[dict]) -> ProposalRecord:
    return ProposalRecord(
        "r6-reg",
        "b1-r6",
        "1:1-order-preserving",
        regions,
        dict(times),
        [],
        "",
    )


# Two regions: the first applies a -1 s shift to cue e0000 (a proposed
# change), the second proposes nothing (offset 0).
_REGIONS = [
    {"start_us": 0, "end_us": 20 * SECOND, "offset_us": -1 * SECOND, "kind": "fit"},
    {"start_us": 20 * SECOND, "end_us": None, "offset_us": 0, "kind": "fit"},
]
_SHIFTED = {
    "e0000": (9 * SECOND, 11 * SECOND),
    "e0001": (20 * SECOND, 22 * SECOND),
    "e0002": (30 * SECOND, 32 * SECOND),
}


def test_tool_only_arm_never_claims_validated_acceptance():
    case = _case()
    corrupted = dict(case.original_times_us)
    score = score_case(case, _proposal(_SHIFTED, _REGIONS), corrupted, None, TOL)
    counts = score["counts"]
    # Proposal-side accounting stays visible...
    assert counts["regions_total"] == 2
    assert counts["proposed_regions_nonzero"] == 1
    # ...validated acceptance is explicitly ZERO: no AcceptanceRecord exists,
    # so proposing regions must never masquerade as accepted regions.
    assert counts["accepted_regions"] == 0
    assert counts["rejected_regions"] == 0
    assert counts["abstention_regions"] == 0
    assert score["final_semantics"] == "unguarded_proposal_if_blindly_applied"
    # The cue-level counterpart was already honest (F06); keep it that way.
    assert "accepted_nonzero" not in counts
    assert counts["if_blindly_applied_nonzero"] == 1


def test_validated_b1va_reports_actual_accepted_region_count():
    case = _case()
    corrupted = dict(case.original_times_us)
    acceptance = AcceptanceRecord(
        case_id="r6-reg",
        candidate_id="b1-va",
        validated_candidate_id="b1-r6",
        status="success",
        accepted_regions=[_REGIONS[0]],
        rejected_regions=[],
        abstained_regions=[],
        accepted_times_us=dict(_SHIFTED),
        sample_cue_ids=["e0000"],
        asr_seconds=0.1,
        asr_calls=1,
    )
    score = score_case(case, _proposal(_SHIFTED, _REGIONS), corrupted, acceptance, TOL)
    counts = score["counts"]
    # A genuinely validated acceptance reports the REAL accepted-region count.
    assert counts["accepted_regions"] == 1
    assert counts["rejected_regions"] == 0
    assert counts["abstention_regions"] == 0
    assert counts["regions_total"] == 2
    assert counts["proposed_regions_nonzero"] == 1
    assert counts["accepted_nonzero"] == 1
    assert score["final_semantics"] == "accepted_output"


def test_validated_b1va_rejected_and_abstained_report_no_false_acceptance():
    case = _case()
    corrupted = dict(case.original_times_us)
    acceptance = AcceptanceRecord(
        case_id="r6-reg",
        candidate_id="b1-va",
        validated_candidate_id="b1-r6",
        status="success",
        accepted_regions=[],
        rejected_regions=list(_REGIONS),
        abstained_regions=[
            {"start_us": 30 * SECOND, "end_us": None, "offset_us": 0, "kind": "fit"}
        ],
        # Nothing was applied: the accepted timeline keeps the base timings.
        accepted_times_us=dict(corrupted),
        sample_cue_ids=[],
        asr_seconds=0.1,
        asr_calls=1,
    )
    score = score_case(case, _proposal(_SHIFTED, _REGIONS), corrupted, acceptance, TOL)
    counts = score["counts"]
    # Rejected/abstained proposals claim ZERO accepted regions; the proposal
    # axis stays visible for analysis.
    assert counts["accepted_regions"] == 0
    assert counts["rejected_regions"] == 2
    assert counts["abstention_regions"] == 1
    assert counts["regions_total"] == 2
    assert counts["proposed_regions_nonzero"] == 1
    assert counts["accepted_nonzero"] == 0
    # The validated arm keeps the proposal-side harm visible on the proposal
    # axis while its ACCEPTED timeline (all rejected -> unchanged corrupted/
    # base times) stays harm-free.
    assert counts["harmful_proposed"] == 1
    assert counts["harmful_accepted"] == 0
