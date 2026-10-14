"""Shared scoring for B1: synthetic ground truth vs injected errors.

Tolerances are declared evaluation parameters reported with every result;
they are NOT calibrated production thresholds. Proposed corrections and
automatically accepted corrections are scored separately. Clean controls and
unaffected cues act as negative controls. Denominators are always reported.

Discontinuity semantics (schema_version 2):
- Candidate-implied breakpoints come from the candidate's PROPOSED corrections
  only: per-cue applied correction d(cid) = proposed_onset - corrupted_onset
  (no proposal entry -> d = 0); a breakpoint is implied at the ORIGINAL onset
  of cue b when d steps between consecutive cues (in original onset order) by
  more than jump_threshold_us = max(2 * good_us, BREAK_JUMP_FLOOR_US = 250 ms).
  An unchanged/no-op candidate therefore implies zero breakpoints and gets no
  detection credit (residual steps are NOT detection).
- Detection credit uses BRACKETING intervals, not a spurious sub-tolerance time
  estimate: an implied break from the a->b cue-anchor step certifies the
  DISCONTINUITY LOCATION, i.e. that the repair boundary falls between adjacent
  cue anchors, in the interval (onset(a), onset(b)]. A candidate-proposed
  region boundary (a region start_us whose applied offset changes) that lies
  strictly inside that gap is a finer localization claim and sub-divides the
  gap into per-boundary sub-brackets. Each bracket (sub-bracket) is matched
  one-to-one to true breakpoints: exactly one true breakpoint inside -> that
  break is credited (matched); zero inside -> the implied break is a false
  positive; two or more inside -> AMBIGUOUS, no automatic credit for any of
  them, reported via explicit ambiguous counts (never silent). Because the
  brackets are sub-intervals of a left-open/right-closed partition of the
  monotone cue-anchor onset sequence, every true breakpoint lies in at most one
  bracket, so one-to-one matching (one implied break credits at most one true
  breakpoint; one true breakpoint is credited by at most one implied break)
  holds structurally and deterministically. Localization is reported per matched
  pair as the bracketing anchors and interval width (bracket_start_us /
  bracket_end_us / bracket_width_us); the onset-anchored value is a precise
  estimate only when it lands within break_match_us of the true breakpoint
  (precise_within_tol), which coexists with (does not gate) bracket credit.
- Unresolved true breakpoints answer the separate question "does the FINAL
  (accepted, else proposed) timeline still step at each true breakpoint": for
  the cue pair straddling true breakpoint t in original onset order, it is
  resolved when the final onset residuals on both sides are equalized within
  jump_threshold_us (same applied offset), unresolved when they still step
  beyond it. A true breakpoint with no straddling cue pair is counted
  unresolved (conservative) and reported separately.
- Offset recovery (S01): Segment.apply in timeline.py shows corruption is
  corrupted = original + params.offset_us (verified against committed
  Fx00-S01.case.json: injected deltas equal +offset_us). fit_regions region
  offset_us is the applied shift (proposed - corrupted). exact recovery means
  applied_shift == -true_offset; residual_us = |-applied_shift - true_offset|.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from .manifests import AcceptanceRecord, CaseManifest, ProposalRecord

BREAK_JUMP_FLOOR_US = 250_000
OFFSET_RECOVERY_STATUSES = ("1:1-order-preserving", "noop")
SCORE_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class Tolerances:
    good_us: int = 50_000
    severe_us: int = 250_000
    break_match_us: int = 500_000

    def to_dict(self) -> dict:
        return {
            "good_us": self.good_us,
            "severe_us": self.severe_us,
            "break_match_us": self.break_match_us,
            "meaning": "declared evaluation tolerance for this run only; not a production threshold",
        }


def percentile(values: list[int], q: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    import math

    idx = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return ordered[idx]


def _stats(errors: list[int]) -> dict:
    if not errors:
        return {
            "count": 0,
            "median_abs_us": None,
            "p90_abs_us": None,
            "p95_abs_us": None,
            "max_abs_us": None,
        }
    import statistics

    abs_e = [abs(e) for e in errors]
    return {
        "count": len(abs_e),
        "median_abs_us": int(statistics.median(abs_e)),
        "p90_abs_us": percentile(abs_e, 0.90),
        "p95_abs_us": percentile(abs_e, 0.95),
        "max_abs_us": max(abs_e),
    }


def score_case(
    case: CaseManifest,
    proposal: ProposalRecord,
    corrupted_times: dict[str, tuple[int, int]],
    acceptance: AcceptanceRecord | None = None,
    tol: Tolerances | None = None,
) -> dict:
    tol = tol if tol is not None else Tolerances()
    original = {cid: (int(s), int(e)) for cid, (s, e) in case.original_times_us.items()}
    cues = sorted(set(original) | set(corrupted_times))

    proposed_times = proposal.proposed_times_us
    if acceptance:
        final_times = acceptance.accepted_times_us
    else:
        final_times = {
            cid: proposed_times.get(cid, corrupted_times.get(cid, (0, 0)))
            for cid in cues
        }

    per_cue: dict[str, dict] = {}
    onset_errors_final: list[int] = []
    onset_errors_proposed: list[int] = []
    end_errors_proposed: list[int] = []
    end_errors_final: list[int] = []
    altered, unaltered = [], []

    for cid in cues:
        o = original.get(cid)
        c = corrupted_times.get(cid)
        if o is None:
            continue
        injected = (c[0] - o[0], c[1] - o[1]) if c else (0, 0)
        p = proposed_times.get(cid, c)
        f = final_times.get(cid, c)
        rec = {
            "original_us": list(o),
            "corrupted_us": list(c) if c else None,
            "injected_us": list(injected),
            "proposed_us": list(p) if p else None,
            "final_us": list(f) if f else None,
        }
        if c is not None:
            onset_err_corrupted = c[0] - o[0]
            onset_err_proposed = (p[0] - o[0]) if p else onset_err_corrupted
            onset_err_final = f[0] - o[0]
            end_err_proposed = (p[1] - o[1]) if p else c[1] - o[1]
            end_err_final = f[1] - o[1]
            rec["onset_err_proposed_us"] = onset_err_proposed
            rec["onset_err_final_us"] = onset_err_final
            rec["end_err_proposed_us"] = end_err_proposed
            rec["end_err_final_us"] = end_err_final
            onset_errors_proposed.append(onset_err_proposed)
            onset_errors_final.append(onset_err_final)
            end_errors_proposed.append(end_err_proposed)
            end_errors_final.append(end_err_final)
            if abs(injected[0]) > tol.good_us:
                altered.append(cid)
                if abs(onset_err_final) <= tol.good_us:
                    rec["repaired"] = True
                if abs(onset_err_proposed) <= tol.good_us:
                    rec["repaired_proposed"] = True
            else:
                unaltered.append(cid)
                if abs(onset_err_final) > tol.good_us:
                    rec["worsened"] = True
                if abs(onset_err_proposed) > tol.good_us:
                    rec["worsened_proposed"] = True
            if (
                p is not None
                and abs(onset_err_proposed) > abs(onset_err_corrupted) + tol.good_us
            ):
                rec["harmful_proposed"] = True
            if abs(onset_err_final) > abs(onset_err_corrupted) + tol.good_us:
                rec["harmful_accepted"] = True
            if abs(onset_err_final) > tol.severe_us:
                rec["severe_final"] = True
        per_cue[cid] = rec

    nonzero_proposals = sum(
        1
        for cid, t in proposed_times.items()
        if cid in corrupted_times
        and (t[0] != corrupted_times[cid][0] or t[1] != corrupted_times[cid][1])
    )
    nonzero_accepted = sum(
        1
        for cid, t in final_times.items()
        if cid in corrupted_times
        and (t[0] != corrupted_times[cid][0] or t[1] != corrupted_times[cid][1])
    )

    # Candidate-implied breakpoints: derived from the candidate's own applied
    # corrections (proposed - corrupted), never from residual timing errors.
    regions = proposal.regions
    break_order = sorted(
        (cid for cid in per_cue if "onset_err_final_us" in per_cue[cid]),
        key=lambda cid: (int(per_cue[cid]["original_us"][0]), cid),
    )
    jump_threshold_us = max(2 * tol.good_us, BREAK_JUMP_FLOOR_US)

    def applied_correction(cid: str) -> int:
        c = corrupted_times.get(cid)
        p = proposed_times.get(cid)
        if c is None or p is None:
            return 0
        return int(p[0]) - int(c[0])

    def _region_start(region: dict) -> int | None:
        s = region.get("start_us")
        return None if s is None else int(s)

    # Candidate-proposed boundaries: region start times where the applied
    # offset changes. These are the candidate's own localization claims and can
    # be finer than the cue anchors when it proposes several steps inside one
    # cue gap (used below to sub-divide a bracketing interval).
    proposed_edges: list[int] = []
    prev_offset: int | None = None
    for region in sorted(
        regions,
        key=lambda r: (_region_start(r) is None, _region_start(r) or 0),
    ):
        offset = int(region.get("offset_us", 0))
        start = _region_start(region)
        if start is not None and prev_offset is not None and offset != prev_offset:
            proposed_edges.append(start)
        prev_offset = offset
    proposed_edges = sorted(set(proposed_edges))

    # A step in applied correction between consecutive cue anchors (a, b]
    # implies a break; the gap is bounded by onset(a), onset(b) and sub-divided
    # by proposed_edges strictly inside it. implied_breakpoint_times_us keeps
    # the cue-anchor b onset (legacy report coordinate); claims are the
    # per-boundary sub-brackets used for one-to-one detection credit.
    implied_breaks: list[int] = []
    claims: list[tuple[int, int, int]] = []
    for a, b in itertools.pairwise(break_order):
        if abs(applied_correction(b) - applied_correction(a)) > jump_threshold_us:
            lo = int(per_cue[a]["original_us"][0])
            hi = int(per_cue[b]["original_us"][0])
            implied_breaks.append(hi)
            interior = [e for e in proposed_edges if lo < e < hi]
            if interior:
                # The candidate explains the a->b step with proposed boundaries
                # strictly inside the gap; each boundary is a per-boundary
                # localization claim. No trailing claim is emitted at the cue
                # anchor: the candidate makes no break claim past its last
                # proposed boundary.
                bounds = [lo, *interior]
                for i in range(1, len(bounds)):
                    claims.append((bounds[i - 1], bounds[i], hi))
            else:
                claims.append((lo, hi, hi))

    true_breaks = sorted(int(t) for t in case.true_breakpoints_us)
    # Bracketing-interval, one-to-one matching (see module docstring). Brackets
    # are disjoint sub-intervals of a left-open/right-closed partition of the
    # cue-anchor onsets, so each true breakpoint sits in at most one bracket and
    # each bracket credits at most one true breakpoint: 1 inside -> matched,
    # 0 inside -> false positive, >=2 inside -> ambiguous (no auto-credit).
    matched_breaks: list[dict] = []
    false_breaks = 0
    ambiguous_breaks = 0
    ambiguous_true_breakpoints = 0
    for bracket_start, bracket_end, anchor in claims:
        inside = [tb for tb in true_breaks if bracket_start < tb <= bracket_end]
        if len(inside) == 1:
            tb = inside[0]
            residual = abs(anchor - tb)
            matched_breaks.append(
                {
                    "true_breakpoint_us": tb,
                    "bracket_start_us": bracket_start,
                    "bracket_end_us": bracket_end,
                    "bracket_width_us": bracket_end - bracket_start,
                    "implied_break_us": anchor,
                    "precise_residual_us": residual,
                    "precise_within_tol": residual <= tol.break_match_us,
                }
            )
        elif len(inside) == 0:
            false_breaks += 1
        else:
            ambiguous_breaks += 1
            ambiguous_true_breakpoints += len(inside)

    matched_true = len(matched_breaks)

    # Separate question: does the FINAL timeline (accepted, else proposed)
    # still step at each true breakpoint? For the consecutive cue pair whose
    # ORIGINAL onsets straddle t, resolved means the final onset residuals on
    # both sides are equalized within jump_threshold_us (same applied offset);
    # unresolved means they still step beyond it. No straddling pair ->
    # conservative unresolved, counted separately.
    final_order = [
        (int(per_cue[cid]["original_us"][0]), int(per_cue[cid]["onset_err_final_us"]))
        for cid in break_order
    ]
    resolved_true = 0
    unresolved_true = 0
    no_straddle_pair = 0
    for t in case.true_breakpoints_us:
        pair = None
        for i in range(len(final_order) - 1):
            if final_order[i][0] <= t <= final_order[i + 1][0]:
                pair = i
                break
        if pair is None:
            no_straddle_pair += 1
            unresolved_true += 1
        elif abs(final_order[pair + 1][1] - final_order[pair][1]) > jump_threshold_us:
            unresolved_true += 1
        else:
            resolved_true += 1

    offset_recovery = None
    if case.scenario == "S01" and "offset_us" in case.params:
        true_offset = int(case.params["offset_us"])
        if proposal.mapping_status in OFFSET_RECOVERY_STATUSES and regions:
            applied_shift = int(
                sum(r.get("offset_us", 0) for r in regions) / len(regions)
            )
            recovered_offset = -applied_shift
            offset_recovery = {
                "true_offset_us": true_offset,
                "applied_shift_us": applied_shift,
                "recovered_offset_us": recovered_offset,
                "residual_us": abs(recovered_offset - true_offset),
                "convention": (
                    "applied shift is what the candidate moved the subtitles "
                    "(proposed - corrupted); exact recovery means "
                    "applied_shift == -true_offset"
                ),
            }

    return {
        "schema_version": SCORE_SCHEMA_VERSION,
        "case_id": case.case_id,
        "scenario": case.scenario,
        "candidate_id": proposal.candidate_id,
        "mapping_status": proposal.mapping_status,
        "tolerances": tol.to_dict(),
        "denominators": {
            "total_cues": len(cues),
            "altered_cues": len(altered),
            "unaltered_cues": len(unaltered),
            "mapped_cues": len(proposed_times),
            "unmapped_cues": len(proposal.unmapped_cue_ids),
            "independent_source_episodes": 1,
            "note": "synthetic variants of one fixture are correlated, not independent episodes",
        },
        "timing_errors_proposed_us": _stats([abs(e) for e in onset_errors_proposed]),
        "timing_errors_final_us": _stats([abs(e) for e in onset_errors_final]),
        "timing_errors_proposed_end_us": _stats([abs(e) for e in end_errors_proposed]),
        "timing_errors_final_end_us": _stats([abs(e) for e in end_errors_final]),
        "counts": {
            "repaired": sum(1 for r in per_cue.values() if r.get("repaired")),
            "repaired_proposed": sum(
                1 for r in per_cue.values() if r.get("repaired_proposed")
            ),
            "worsened_unaltered": sum(1 for r in per_cue.values() if r.get("worsened")),
            "worsened_unaltered_proposed": sum(
                1 for r in per_cue.values() if r.get("worsened_proposed")
            ),
            "harmful_proposed": sum(
                1 for r in per_cue.values() if r.get("harmful_proposed")
            ),
            "harmful_accepted": sum(
                1 for r in per_cue.values() if r.get("harmful_accepted")
            ),
            "severe_final": sum(1 for r in per_cue.values() if r.get("severe_final")),
            "proposals_nonzero": nonzero_proposals,
            "accepted_nonzero": nonzero_accepted,
            "abstained_regions": len(regions)
            if proposal.mapping_status
            in (
                "abstain_no_speech_anchors",
                "not_run",
                "unsupported",
                "timeout",
                "failed",
                "invalid_output",
                "mapping_failure_count_mismatch",
                "mapping_failure_ambiguous_text",
            )
            else 0,
            "regions_total": len(regions),
            "accepted_regions": len(acceptance.accepted_regions)
            if acceptance
            else len(regions),
            "rejected_regions": len(acceptance.rejected_regions) if acceptance else 0,
            "abstention_regions": len(acceptance.abstained_regions)
            if acceptance
            else 0,
        },
        "discontinuities": {
            "true_breakpoints": len(case.true_breakpoints_us),
            "jump_threshold_us": jump_threshold_us,
            "detected_breakpoints": len(implied_breaks),
            "implied_breakpoint_times_us": implied_breaks,
            "matched_true_breakpoints": matched_true,
            "false_positive_breakpoints": false_breaks,
            "ambiguous_breakpoints": ambiguous_breaks,
            "ambiguous_true_breakpoints": ambiguous_true_breakpoints,
            "matched_breaks": matched_breaks,
            "unresolved_true_breakpoints": unresolved_true,
            "resolved_true_breakpoints": resolved_true,
            "true_breakpoints_without_straddle_pair": no_straddle_pair,
            "matching_rule": (
                "an implied break from the a->b cue-anchor step is credited to "
                "the true breakpoints in the bracketing interval "
                "(onset(a), onset(b)], sub-divided by candidate-proposed region "
                "boundaries strictly inside the gap; exactly one true "
                "breakpoint in a bracket -> matched (localization = bracketing "
                "anchors and width), zero -> false positive, two or more -> "
                "ambiguous with no automatic credit; brackets are disjoint so "
                "matching is one-to-one; detection credit comes from the "
                "bracket, not from the break_match_us time tolerance"
            ),
            "unresolved_rule": (
                "a true breakpoint is unresolved when the final onset residuals "
                "of the straddling cue pair (original onset order) still step "
                "beyond jump_threshold_us; equalized within it means resolved; "
                "no straddling pair counts unresolved conservatively"
            ),
        },
        "offset_recovery": offset_recovery,
        "per_cue": per_cue,
    }
