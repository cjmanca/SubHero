"""Shared scoring for B1: synthetic ground truth vs injected errors.

Tolerances are declared evaluation parameters reported with every result;
they are NOT calibrated production thresholds. Proposed corrections and
automatically accepted corrections are scored separately. Clean controls and
unaffected cues act as negative controls. Denominators are always reported.

Final-timeline semantics (schema_version 3, third-review F06): each score row
carries ``final_semantics``. For an arm WITH an AcceptanceRecord (b1-va) the
final timeline is the ACTUAL accepted output and counts use the accepted
names (``accepted_nonzero``, ``harmful_accepted``, ``severe_final``,
``repaired``, ``worsened_unaltered``). For an arm WITHOUT any validator
(tool-only arms) the "final" is the raw proposal; scoring it is a useful
counterfactual, but calling it "accepted" implied a safety gate that never
ran: schema 3 labels those measurements ``*_if_blindly_applied``
(``if_blindly_applied_nonzero``, ``harmful_if_blindly_applied``,
``severe_if_blindly_applied``, ``repaired_if_blindly_applied``,
``worsened_unaltered_if_blindly_applied``). ``*_proposed`` keys remain the
proposal-domain comparison in both cases. Schema 2 rows (where unguarded
proposals were counted as "accepted") are legacy: reports label them and
never mix them into schema-3 comparisons silently.

Discontinuity semantics (schema_version 3):
- Candidate-implied breakpoints come from the candidate's PROPOSED corrections
  only: per-cue applied correction d(cid) = proposed_onset - corrupted_onset
  (no proposal entry -> d = 0); a breakpoint is implied at the ORIGINAL onset
  of cue b when d steps between consecutive cues (in original onset order) by
  more than jump_threshold_us = max(2 * good_us, BREAK_JUMP_FLOOR_US = 250 ms).
  An unchanged/no-op candidate therefore implies zero breakpoints and gets no
  detection credit (residual steps are NOT detection).
- Local corrections vs offset regions (third-review F04, corrected by M3):
  group the applied-correction sequence into maximal runs of equal value. A run
  flanked on BOTH sides by runs of the SAME value is REVERSIBLE (an A->B->A
  offset sequence), and reversibility ALONE is not sufficient to call it local.
  Such a run is classified transient (a short, isolated local-cue adjustment)
  only when it is short in CUE COUNT (<= LOCAL_MAX_CUES = 5, the most isolated
  shifts an S04 scenario injects), short in TEMPORAL DURATION (its original-onset
  span <= LOCAL_MAX_SPAN_US), and supported by neighboring anchors (each flanking
  run contributes at least LOCAL_MIN_ANCHOR_CUES cues; a run with no flanking run
  is not sandwiched at all). Its deviating cues count additively as
  ``local_cue_adjustments`` (with their cue ids).
  Boundary SUPPRESSION is owned by the excursions (fifth-review Finding A): a
  step is suppressed as a release-discontinuity claim ONLY when both adjacent
  runs are transient/edge-ambiguous, or when exactly one adjacent run is
  transient/edge-ambiguous, that run DEVIATES (nonzero applied correction),
  and the other side is the unmodified (zero) baseline — the entering/exiting
  of a local correction excursion returning to the original timing. A
  zero-value transient neighbour next to a sustained non-zero offset does NOT
  suppress that sustained region's boundary: a sustained block hidden behind
  short transient runs keeps its release-discontinuity claim and false-
  positive accounting.
  A reversible run that exceeds LOCAL_MAX_CUES but stays within the declared
  borderline band (<= LOCAL_AMBIGUOUS_MAX_CUES = 2 * LOCAL_MAX_CUES) with a short
  temporal span - or a short run with missing outer anchors - is an AMBIGUOUS
  offset region: it is represented CONSERVATIVELY and explicitly in
  ``ambiguous_offset_regions`` (with per-region descriptors: cue count/ids,
  applied and flanking correction, onset span); its cues are NOT auto-counted as
  local adjustments and its breakpoint claims are NEVER suppressed.
  A reversible run beyond that band, or temporally long (its onset span exceeds
  LOCAL_MAX_SPAN_US), is a SUSTAINED REVERSIBLE OFFSET REGION: a region-wide
  release-specific offset block (e.g. cues 031-230 at -2 s between 0-offset
  blocks) whose entering AND exiting steps keep their implied-breakpoint claims,
  so a perfectly repaired long region keeps detection credit for BOTH genuine
  discontinuities even though its offset eventually returns to the original
  value; its cues are region corrections, not local adjustments. A sustained step
  (the value persists to a sequence edge, or the two sides differ) likewise stays
  a change-point claim, so real regional discontinuities keep their false-positive
  penalty and a perfect inverse of an isolated S04 cue shift no longer scores as
  two false release breaks. The track-boundary exception (fifth-review Finding
  B): a ONE-CUE deviating run at a sequence edge whose only neighbour is the
  zero baseline is classified EDGE-AMBIGUOUS — an isolated edge correction is
  inherently ambiguous (isolated timing error vs release-specific boundary
  offset), so it is never auto-declared a false release discontinuity solely
  for lacking an outer anchor: its boundary claim is KEPT for localization (a
  genuine release offset at the track boundary keeps bracketing credit when a
  true breakpoint lies in its bracket), its cues are not auto-counted as
  local adjustments, and an UNMATCHED edge claim is recorded explicitly as
  ``unmatched_edge_ambiguous_claims`` with the ambiguity described in
  ``edge_ambiguous_regions`` / ``edge_ambiguity_descriptors``, while the
  actual timing repair and any harm to previously-correct cues are scored on
  the cue axis independently. A deviating edge run above the
  one-cue band (e.g. a genuine sustained offset beginning at the first cue)
  stays SUSTAINED and keeps its claims.
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
  unresolved (conservative) and reported separately. This timing-recovery
  measurement is INDEPENDENT of the transient / ambiguous / sustained
  classification above: it reads only the final-timeline residuals, never the
  run classification.
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
SCORE_SCHEMA_VERSION = 3

# M3 local-correction vs offset-region bounds. These are declared evaluation
# parameters reported with every result (like Tolerances); they are NOT
# calibrated production thresholds.
# S04 (corrupt.py) injects at most 5 isolated cue shifts per case
# (n = rng.integers(1, min(6, len(cues)))), so 5 cues is the largest block an
# isolated-cue corruption scenario produces: a sandwiched run of at most this
# many cues can be a local isolated correction.
LOCAL_MAX_CUES = 5
# A local isolated correction must also be temporally short. An S04 shift is
# bounded by ±5 s per cue, and 5 adjacent cues at typical subtitle density
# (about one cue every few seconds) span well under 30 s, while a genuine
# release-offset region (e.g. the plan's 200-cue middle section) spans minutes.
# 30 s is the declared duration bound for transient eligibility.
LOCAL_MAX_SPAN_US = 30_000_000
# An entering/exiting step is supported by neighboring anchors only when each
# flanking run contributes at least this many cues (the anchors that bracket the
# run from the outer sides). Runs at a sequence edge have no flanking run and are
# never sandwiched/transient.
LOCAL_MIN_ANCHOR_CUES = 1
# Reversible runs above LOCAL_MAX_CUES up to this bound with a short temporal
# span (and short runs with missing outer anchors) are inherently ambiguous:
# classified conservatively as AMBIGUOUS offset regions — claims kept, cues never
# auto-counted as local adjustments, reported explicitly — rather than being
# silently swallowed as local adjustments.
LOCAL_AMBIGUOUS_MAX_CUES = 2 * LOCAL_MAX_CUES

# Internal run classifications (scoring-internal labels, reported via counts/
# descriptors; kept as constants so the classification sites cannot drift).
RUN_TRANSIENT = "transient"
RUN_AMBIGUOUS = "ambiguous"
RUN_SUSTAINED = "sustained"
# Fifth-review Finding B: a ONE-CUE deviating run at a sequence (track) edge
# against the unmodified baseline. It has no flanking anchor on its outer
# side, so it is inherently ambiguous — an isolated timing error OR a
# release-specific offset affecting the track boundary. Its boundary claim is
# KEPT for localization (a genuine release offset at the boundary keeps
# bracketing credit), but an UNMATCHED edge claim is recorded explicitly as
# ``unmatched_edge_ambiguous_claims`` instead of being auto-declared a false
# release discontinuity solely for lacking an anchor; its cues are NOT
# auto-counted as local adjustments, and the ambiguity is described in
# ``edge_ambiguous_regions``. A deviating edge run above the one-cue edge band
# stays SUSTAINED: a genuine sustained offset beginning at the first cue keeps
# its change-point claims.
RUN_EDGE_AMBIGUOUS = "edge_ambiguous"


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

    # F06: "accepted" labels are reserved for an arm with a real AcceptanceRecord.
    # Tool-only arms have NO validator: their raw proposal scored as the final
    # timeline is a counterfactual (what would happen if it were blindly
    # applied), and schema 3 names every final-derived measurement that way.
    has_acceptance = acceptance is not None
    blind = "" if has_acceptance else "_if_blindly_applied"
    final_semantics = (
        "accepted_output" if has_acceptance else "unguarded_proposal_if_blindly_applied"
    )
    accepted_label = "accepted" if has_acceptance else "if_blindly_applied"
    final_label = "final" if has_acceptance else "if_blindly_applied"

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
                    rec[f"repaired{blind}"] = True
                if abs(onset_err_proposed) <= tol.good_us:
                    rec["repaired_proposed"] = True
            else:
                unaltered.append(cid)
                if abs(onset_err_final) > tol.good_us:
                    rec[f"worsened{blind}"] = True
                if abs(onset_err_proposed) > tol.good_us:
                    rec["worsened_proposed"] = True
            if (
                p is not None
                and abs(onset_err_proposed) > abs(onset_err_corrupted) + tol.good_us
            ):
                rec["harmful_proposed"] = True
            if abs(onset_err_final) > abs(onset_err_corrupted) + tol.good_us:
                rec[f"harmful_{accepted_label}"] = True
            if abs(onset_err_final) > tol.severe_us:
                rec[f"severe_{final_label}"] = True
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

    # F04 + M3: stable-support classification of applied corrections. Group the
    # sequence (in original onset order) into maximal runs of equal applied
    # correction. A run flanked on BOTH sides by runs of the SAME value is
    # REVERSIBLE (A->B->A), which alone does NOT make it local: a long middle
    # section at a release-specific offset also returns to the surrounding value
    # and contains two genuine discontinuities. A reversible run is classified
    # transient (short isolated local-cue adjustment) only when it is short in
    # cue count, short in temporal duration, and supported by outer anchors; it
    # is classified AMBIGUOUS when it sits in the declared borderline band
    # (claims kept, cues not auto-counted, reported explicitly); otherwise it is
    # a SUSTAINED REVERSIBLE OFFSET REGION whose entering/exiting steps keep
    # their implied-breakpoint claims. A step that is not reversible (the value
    # persists to a sequence edge, or the two sides differ) stays a claim.
    run_ids: list[int] = []
    runs: list[dict] = []
    for cid in break_order:
        v = applied_correction(cid)
        if runs and runs[-1]["value"] == v:
            runs[-1]["cue_ids"].append(cid)
            run_ids.append(len(runs) - 1)
        else:
            runs.append({"value": v, "cue_ids": [cid]})
            run_ids.append(len(runs) - 1)

    def onset_of(cid: str) -> int:
        return int(per_cue[cid]["original_us"][0])

    classifications: list[str] = []
    for i, run in enumerate(runs):
        reversible = (
            0 < i < len(runs) - 1 and runs[i - 1]["value"] == runs[i + 1]["value"]
        )
        if not reversible:
            # Fifth-review Finding B: a one-cue deviating run pressed against a
            # sequence edge with the unmodified (zero) baseline as its only
            # neighbor is a track-boundary local correction — inherently
            # ambiguous, never auto-declared a release discontinuity solely
            # because its outer anchor is missing. Longer deviating edge runs
            # (and edge runs adjacent to non-baseline values) stay sustained,
            # so a genuine sustained offset starting at the first cue keeps its
            # change-point claim. INTERIOR runs are never edge-ambiguous: the
            # edge-index guard is required, and an interior 1-cue deviating
            # spike keeps sustained-region accounting (adversarial review F1).
            if (
                len(runs) > 1
                and (i == 0 or i == len(runs) - 1)
                and run["value"] != 0
                and len(run["cue_ids"]) == 1
            ):
                neighbor = runs[1] if i == 0 else runs[-2]
                if neighbor["value"] == 0:
                    classifications.append(RUN_EDGE_AMBIGUOUS)
                    continue
            classifications.append(RUN_SUSTAINED)
            continue
        cue_count = len(run["cue_ids"])
        span_us = onset_of(run["cue_ids"][-1]) - onset_of(run["cue_ids"][0])
        # At LOCAL_MIN_ANCHOR_CUES = 1 this guard is always True: runs are
        # maximal and non-empty, and `reversible` already requires both flanking
        # runs to exist. It is a declared, tunable support requirement — raising
        # it above 1 activates the short-run-with-weak-anchors ambiguous band.
        anchors = (
            len(runs[i - 1]["cue_ids"]) >= LOCAL_MIN_ANCHOR_CUES
            and len(runs[i + 1]["cue_ids"]) >= LOCAL_MIN_ANCHOR_CUES
        )
        temporally_short = span_us <= LOCAL_MAX_SPAN_US
        if anchors and cue_count <= LOCAL_MAX_CUES and temporally_short:
            classifications.append(RUN_TRANSIENT)
        elif cue_count <= LOCAL_AMBIGUOUS_MAX_CUES and temporally_short:
            # Borderline short region: conservative and explicit, never silent.
            classifications.append(RUN_AMBIGUOUS)
        else:
            classifications.append(RUN_SUSTAINED)
    # Fifth-review Finding A: a boundary is suppressible as a local-cue
    # excursion ONLY by the transient / edge-ambiguous runs that OWN the
    # entering and exiting steps of their excursion; the classification list
    # marks which runs may own a suppression.
    suppressible = [
        c == RUN_TRANSIENT or c == RUN_EDGE_AMBIGUOUS for c in classifications
    ]
    # Only cues whose applied correction deviates from the flanking value are
    # local adjustments; a zero run sandwiched between two equal transient
    # shift blocks (oscillation) has its boundaries suppressed by the
    # deviating neighbours' excursions, and its untouched cues are not
    # counted. Sustained, ambiguous, and edge-ambiguous region cues are never
    # counted as local adjustments.
    local_cue_ids = sorted(
        cid
        for i, run in enumerate(runs)
        if classifications[i] == RUN_TRANSIENT and run["value"] != 0
        for cid in run["cue_ids"]
    )
    ambiguous_regions = [
        {
            "cue_count": len(run["cue_ids"]),
            "cue_ids": list(run["cue_ids"]),
            "applied_correction_us": int(run["value"]),
            "flanking_correction_us": int(runs[i - 1]["value"]),
            "first_onset_us": onset_of(run["cue_ids"][0]),
            "last_onset_us": onset_of(run["cue_ids"][-1]),
            "onset_span_us": onset_of(run["cue_ids"][-1]) - onset_of(run["cue_ids"][0]),
        }
        for i, run in enumerate(runs)
        if classifications[i] == RUN_AMBIGUOUS
    ]
    # Fifth-review Finding B: track-boundary 1-cue corrections are recorded
    # explicitly as inherent local-vs-release ambiguities: their boundary claim
    # is kept for localization (matching a true breakpoint in the bracket
    # earns normal bracketing credit), an UNMATCHED edge claim is counted as
    # ``unmatched_edge_ambiguous_claims`` instead of a false-positive release
    # discontinuity, their cues are NOT auto-counted as local adjustments, and
    # the timing repair / harm to previously-correct cues is scored on the cue
    # axis independently.
    edge_ambiguous_regions = [
        {
            "cue_count": len(run["cue_ids"]),
            "cue_ids": list(run["cue_ids"]),
            "edge": "first" if i == 0 else "last",
            "applied_correction_us": int(run["value"]),
            "neighbour_correction_us": int((runs[1] if i == 0 else runs[-2])["value"]),
            "first_onset_us": onset_of(run["cue_ids"][0]),
            "last_onset_us": onset_of(run["cue_ids"][-1]),
        }
        for i, run in enumerate(runs)
        if classifications[i] == RUN_EDGE_AMBIGUOUS
    ]

    # A step in applied correction between consecutive cue anchors (a, b]
    # implies a break; the gap is bounded by onset(a), onset(b) and sub-divided
    # by proposed_edges strictly inside it. implied_breakpoint_times_us keeps
    # the cue-anchor b onset (legacy report coordinate); claims are the
    # per-boundary sub-brackets used for one-to-one detection credit.
    implied_breaks: list[int] = []
    claims: list[tuple[int, int, int]] = []
    for k, (a, b) in enumerate(itertools.pairwise(break_order)):
        if abs(applied_correction(b) - applied_correction(a)) > jump_threshold_us:
            ra, rb = run_ids[k], run_ids[k + 1]
            sa, sb = suppressible[ra], suppressible[rb]
            edge_claim = False
            if sa and sb:
                if RUN_EDGE_AMBIGUOUS in (classifications[ra], classifications[rb]):
                    edge_claim = True
                else:
                    # Both sides belong to transient local-cue excursions: this
                    # step is fully explained by local-cue corrections.
                    continue
            elif sa != sb:
                t, o = (ra, rb) if sa else (rb, ra)
                if classifications[t] == RUN_EDGE_AMBIGUOUS:
                    # Fifth-review Finding B: the sole boundary step of a
                    # one-cue track-boundary correction keeps its localization
                    # claim (a genuine release offset AT the boundary — e.g. a
                    # sparse tail offset — must keep bracketing credit), but it
                    # is tagged as an EDGE AMBIGUITY: an isolated edge
                    # correction and a boundary release offset are
                    # indistinguishable from the candidate side, so an
                    # unmatched edge claim must not be auto-declared a false
                    # release discontinuity.
                    edge_claim = True
                elif runs[t]["value"] != 0 and runs[o]["value"] == 0:
                    # The deviating transient run's OWN excursion step
                    # entering from (or returning to) the unmodified baseline:
                    # a local cue adjustment, not a release change-point.
                    continue
                # Fifth-review Finding A: the suppressible neighbour is a
                # zero-value run (an untouched gap, not a correction) next to
                # a sustained offset — this is the sustained region's boundary
                # and its claim survives. A neighbouring transient run must
                # not automatically suppress the boundary of a sustained
                # offset region; AMBIGUOUS borderline regions keep their
                # claims, and a sustained-vs-sustained step keeps its claim.
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
                    claims.append((bounds[i - 1], bounds[i], hi, edge_claim))
            else:
                claims.append((lo, hi, hi, edge_claim))

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
    unmatched_edge_claims = 0
    for bracket_start, bracket_end, anchor, edge_claim in claims:
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
            if edge_claim:
                # Fifth-review Finding B: an unmatched track-boundary
                # one-cue correction claim is recorded as an EXPLICIT edge
                # ambiguity (isolated edge timing error vs release-specific
                # boundary offset cannot be separated from the candidate
                # side), never auto-declared a false release discontinuity.
                unmatched_edge_claims += 1
            else:
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
        "final_semantics": final_semantics,
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
            f"repaired{blind}": sum(
                1 for r in per_cue.values() if r.get(f"repaired{blind}")
            ),
            "repaired_proposed": sum(
                1 for r in per_cue.values() if r.get("repaired_proposed")
            ),
            f"worsened_unaltered{blind}": sum(
                1 for r in per_cue.values() if r.get(f"worsened{blind}")
            ),
            "worsened_unaltered_proposed": sum(
                1 for r in per_cue.values() if r.get("worsened_proposed")
            ),
            "harmful_proposed": sum(
                1 for r in per_cue.values() if r.get("harmful_proposed")
            ),
            f"harmful_{accepted_label}": sum(
                1 for r in per_cue.values() if r.get(f"harmful_{accepted_label}")
            ),
            f"severe_{final_label}": sum(
                1 for r in per_cue.values() if r.get(f"severe_{final_label}")
            ),
            "proposals_nonzero": nonzero_proposals,
            (
                "accepted_nonzero" if has_acceptance else "if_blindly_applied_nonzero"
            ): nonzero_accepted,
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
            "local_cue_adjustments": len(local_cue_ids),
            "local_cue_adjusted_cue_ids": local_cue_ids,
            "ambiguous_offset_regions": len(ambiguous_regions),
            "ambiguous_offset_region_descriptors": ambiguous_regions,
            "edge_ambiguous_regions": len(edge_ambiguous_regions),
            "edge_ambiguity_descriptors": edge_ambiguous_regions,
            "unmatched_edge_ambiguous_claims": unmatched_edge_claims,
            "transient_rule": (
                "a maximal run of equal applied corrections flanked on BOTH "
                "sides by runs of the SAME value is reversible (A->B->A); "
                "reversibility alone is NOT enough: it is transient (a local "
                "cue adjustment, its deviating cues counted as "
                "local_cue_adjustments) only when it is short in cue count "
                f"(<= {LOCAL_MAX_CUES} cues, the maximum isolated shifts an "
                "S04 scenario injects), short in temporal duration (its "
                f"original-onset span <= {LOCAL_MAX_SPAN_US} us) and supported "
                f"by outer anchors (each flanking run has >= "
                f"{LOCAL_MIN_ANCHOR_CUES} cue); a reversible run above that "
                f"bound within the borderline band (<= "
                f"{LOCAL_AMBIGUOUS_MAX_CUES} cues) with a short temporal span, "
                "or a short run with missing outer anchors, is an AMBIGUOUS "
                "offset region: its claims are kept, its cues are NOT counted "
                "as local adjustments, and it is reported explicitly in "
                "ambiguous_offset_regions with descriptors; any other "
                "reversible run is a SUSTAINED REVERSIBLE OFFSET REGION "
                "(release-specific offset block, e.g. cues 031-230 at -2s "
                "between 0-offset blocks): its entering AND exiting steps keep "
                "their implied-breakpoint claims, so a perfectly repaired long "
                "region keeps detection credit for both discontinuities even "
                "though its offset eventually returns to the original value, "
                "and its cues are region corrections, not local adjustments; a "
                "sustained step (value persists to a sequence edge, or the two "
                "sides differ) keeps its claim. Boundary suppression is OWNED "
                "by the excursions (fifth-review Finding A): a step is "
                "suppressed as a release-discontinuity claim only when BOTH "
                "adjacent runs are transient/edge-ambiguous, or when exactly "
                "ONE adjacent run is transient/edge-ambiguous, that run "
                "DEVIATES (nonzero applied correction), and the other side is "
                "the unmodified (zero) baseline — i.e. the step is the "
                "entering/exiting of a local correction excursion returning to "
                "the original timing; a zero-value transient neighbour next to "
                "a sustained non-zero offset does NOT suppress that sustained "
                "region's boundary. A one-cue deviating run at a sequence "
                "edge against the zero baseline is an EDGE-AMBIGUOUS track-"
                "boundary correction (fifth-review Finding B): inherently "
                "ambiguous between an isolated timing error and a release-"
                "specific boundary offset, so its boundary claim is KEPT for "
                "localization (a genuine release offset at the track boundary "
                "keeps bracketing credit when a true breakpoint lies in its "
                "bracket), its cues are NOT auto-counted as local adjustments, "
                "and an UNMATCHED edge claim is recorded explicitly as "
                "unmatched_edge_ambiguous_claims instead of being "
                "auto-declared a false release discontinuity solely because "
                "its outer anchor is missing; the ambiguity is described in "
                "edge_ambiguous_regions/edge_ambiguity_descriptors; the actual "
                "timing repair and any harm to previously-correct cues are "
                "scored on the cue axis independently"
            ),
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
                "no straddling pair counts unresolved conservatively; this "
                "timing-recovery measurement is independent of the transient/"
                "ambiguous/sustained classification of the candidate's claims"
            ),
        },
        "offset_recovery": offset_recovery,
        "per_cue": per_cue,
    }
