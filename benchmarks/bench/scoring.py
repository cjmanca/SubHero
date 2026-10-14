"""Shared scoring for B1: synthetic ground truth vs injected errors.

Tolerances are declared evaluation parameters reported with every result;
they are NOT calibrated production thresholds. Proposed corrections and
automatically accepted corrections are scored separately. Clean controls and
unaffected cues act as negative controls. Denominators are always reported.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from .manifests import AcceptanceRecord, CaseManifest, ProposalRecord


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
            rec["onset_err_proposed_us"] = onset_err_proposed
            rec["onset_err_final_us"] = onset_err_final
            onset_errors_proposed.append(onset_err_proposed)
            onset_errors_final.append(onset_err_final)
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

    detected_breaks: list[int] = []
    regions = proposal.regions
    for a, b in itertools.pairwise(regions):
        if a.get("offset_us") != b.get("offset_us"):
            gap_mid = (
                (a["end_us"] if a.get("end_us") is not None else b["start_us"])
                + b["start_us"]
            ) // 2
            detected_breaks.append(int(gap_mid))

    matched_true = 0
    for tb in case.true_breakpoints_us:
        if any(abs(db - tb) <= tol.break_match_us for db in detected_breaks):
            matched_true += 1
    false_breaks = sum(
        1
        for db in detected_breaks
        if all(abs(db - tb) > tol.break_match_us for tb in case.true_breakpoints_us)
    )

    offset_recovery = None
    if case.scenario == "S01" and "offset_us" in case.params:
        true_offset = int(case.params["offset_us"])
        if proposal.mapping_status == "1:1-order-preserving" and regions:
            est = int(sum(r.get("offset_us", 0) for r in regions) / len(regions))
            offset_recovery = {
                "true_offset_us": true_offset,
                "estimated_correction_us": -est,
                "convention": "correction is the applied shift; exact recovery means est == -true_offset",
                "residual_us": abs(est + true_offset),
            }

    return {
        "schema_version": 1,
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
            if proposal.mapping_status.startswith(
                ("abstain", "not_run", "unsupported", "no")
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
            "detected_breakpoints": len(detected_breaks),
            "matched_true_breakpoints": matched_true,
            "false_positive_breakpoints": false_breaks,
        },
        "offset_recovery": offset_recovery,
        "per_cue": per_cue,
    }
