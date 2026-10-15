"""Human-readable comparison reports over machine-readable results."""

from __future__ import annotations

from pathlib import Path


def _numeric(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _fmt_us(value) -> str:
    if value is None:
        return "-"
    if not _numeric(value):
        return "—"
    return f"{value / 1000:.0f} ms"


def _schema_of(row: dict) -> int:
    v = row.get("schema_version", 0)
    return v if _numeric(v) and int(v) == v else 0


# Round-3 R3-P2: comparative rendering dereferences numeric measurement
# fields; a schema-3 row is bound only when every section it reads is a dict
# whose dereferenced keys exist and are numeric, so type-tampered artifacts
# refuse binding (and are counted unbound) instead of crashing the report.
# Keys outside this set (lists like matched_breaks, labels) are validated at
# render time where they are used.
_REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "counts": ("proposals_nonzero", "harmful_proposed"),
    "denominators": ("total_cues", "altered_cues", "unaltered_cues"),
    "discontinuities": (
        "detected_breakpoints",
        "matched_true_breakpoints",
        "false_positive_breakpoints",
        "unresolved_true_breakpoints",
        "true_breakpoints",
        "true_breakpoints_without_straddle_pair",
        "jump_threshold_us",
    ),
    "timing_errors_final_us": ("median_abs_us", "p90_abs_us", "p95_abs_us"),
}


def _sections_valid(row: dict) -> bool:
    for section, keys in _REQUIRED_SECTIONS.items():
        data = row.get(section)
        if not isinstance(data, dict):
            return False
        if any(not _numeric(data.get(k)) for k in keys):
            return False
    return True


def build_report(
    case_ids: list[str],
    runs: list[dict],
    scores: list[dict],
    tool_versions: dict[str, str],
    current_fingerprints: dict[tuple, str] | None = None,
    acceptance_stale: list[tuple[str, str]] | None = None,
    unverified_cases: list[str] | None = None,
    proposal_stale: list[tuple[str, str]] | None = None,
    artifact_problems: list[tuple[str, str]] | None = None,
    unverified_reasons: dict[str, str] | None = None,
) -> str:
    """Render schema_version-3 scores; schema_version 2 rows are labeled legacy
    (rendered in a separate non-comparative section); v1 rows are ignored.

    Schema (third-review F04/F06): current measurements are schema_version 3 —
    counterfactuals for arms WITHOUT any validator are labeled
    ``*_if_blindly_applied`` (no safety gate ran), accepted names apply only to
    arms with an AcceptanceRecord (``final_semantics`` says which), and transient
    local-cue corrections are reported separately from release discontinuities
    (``local_cue_adjustments``). schema_version 2 rows (where an unguarded
    proposal was counted as "accepted") are legacy: never mixed into the
    comparative tables, only rendered in a labeled legacy section.

    P1-2 binding: every score row must be bound to a verified run.json in the
    SAME case/candidate whose recorded ``input_fingerprint`` EQUALS the
    fingerprint embedded in the score. A schema-2 score with no matching
    fingerprint run (no run.json, a legacy run.json without a fingerprint, a
    fingerprint from a different case generation, or a hand-planted number) is
    DROPPED and counted in ``dropped unbound score rows: N`` so the report never
    renders an unbound number. Legacy rows/runs are still never silently
    trusted, and legacy entries must not crash rendering.

    Generation binding (P2 residual): when ``current_fingerprints`` maps each
    ``(case_id, candidate_id)`` to the CURRENT fingerprint recomputed from the
    live case manifest + registry source (+ the arm's recorded tool_versions), a
    run/score pair whose recorded fingerprint is self-consistent but differs
    from that CURRENT value belongs to an OLDER case generation (a re-prepare
    with a new seed/scenario, a re-registered audio selection, a mutated source,
    an edited ground truth, a changed gold file) and is DROPPED (both the run
    and the score) and counted in ``dropped stale-generation rows: M``. This
    catches the run/score pair the fingerprint-match binding alone cannot (that
    binding only proves the score matches its own run, not that the pair matches
    the current case). Passing ``current_fingerprints=None`` (the default, e.g.
    direct library callers) keeps the pre-existing fingerprint-match behavior
    exactly.

    F01 acceptance binding (third review): ``acceptance_stale`` lists
    ``(case_id, reason)`` for b1-va rows the CLI excluded because the validated
    base run/proposal no longer matches the current artifacts; the count and
    per-case reasons are rendered so an obsolete acceptance never appears as a
    current result.

    F05 fail-closed rendering (third review): ``unverified_cases`` lists cases
    whose current case manifest / registered source evidence cannot be
    established. Their self-consistent run/score rows are NOT rendered in the
    comparative tables (a fail-open path that let stale numbers present
    themselves as current is exactly this finding); they appear ONLY in the
    separate, explicitly labeled *Unverified historical results* section,
    marked as not comparable.

    Fifth-review M1: report generation runs the same source-integrity
    verification as ``run``/``score`` (registered media and sidecars exist and
    match their recorded fingerprints; the generated case input matches the
    manifest hash). A case whose live input files no longer verify is added to
    ``unverified_cases`` like any other missing current evidence, and
    ``unverified_reasons`` (case_id -> reason) states WHY under the labeled
    section.

    Report-path integrity closures (adversarial review round 1):
    ``proposal_stale`` lists ``(case_id, reason)`` for arms whose
    ``run.json.proposal_sha256`` no longer matches ``proposal.json`` bytes at
    report read time (tampered/removed after scoring); those run/score pairs
    are excluded from comparative rows. ``artifact_problems`` lists unreadable
    run/score artifacts: they are counted and shown, never rendered as
    numbers, and never abort the rest of the report. Legacy schema-2 rows bind
    with the schema-appropriate fingerprint-only rule and render ONLY in the
    labeled legacy section.
    """
    cur = [s for s in scores if isinstance(s, dict) and _schema_of(s) == 3]
    legacy2 = [s for s in scores if isinstance(s, dict) and _schema_of(s) == 2]
    scores = cur
    runs = [r for r in runs if isinstance(r, dict)]
    acceptance_stale = list(acceptance_stale or [])
    proposal_stale = list(proposal_stale or [])
    artifact_problems = list(artifact_problems or [])
    unverified = set(unverified_cases or [])
    run_fingerprints: dict[tuple, set] = {}
    run_fingerprint_names: dict[tuple, set] = {}
    for r in runs:
        fp = r.get("input_fingerprint")
        if fp:
            key = (r.get("case_id"), r.get("candidate_id"))
            run_fingerprints.setdefault(key, set()).add((fp, r.get("proposal_sha256")))
            run_fingerprint_names.setdefault(key, set()).add(fp)
    dropped_stale_generation = 0
    if current_fingerprints is not None:

        def _stale_row(row: dict) -> bool:
            key = (row.get("case_id"), row.get("candidate_id"))
            current = current_fingerprints.get(key)
            fp = row.get("input_fingerprint")
            return bool(fp) and current is not None and fp != current

        runs = [r for r in runs if not _stale_row(r)]
        kept_scores: list[dict] = []
        for s in scores:
            if _stale_row(s):
                dropped_stale_generation += 1
            else:
                kept_scores.append(s)
        scores = kept_scores

    def _bind(rows: list[dict]) -> tuple[list[dict], int]:
        bound: list[dict] = []
        dropped = 0
        for s in rows:
            fp = s.get("input_fingerprint")
            key = (s.get("case_id"), s.get("candidate_id"))
            prop_sha = s.get("proposal_sha256")
            pair = (fp, prop_sha)
            # Round-2 P1/P2 closures: schema-3 comparative rows must carry a
            # non-empty proposal_sha256 (matching the run record) and every
            # measurement section the renderer dereferences; structurally
            # incomplete rows are refused, never rendered with defaults.
            complete = all(
                section in s
                for section in (
                    "case_id",
                    "candidate_id",
                    "scenario",
                    "counts",
                    "denominators",
                    "discontinuities",
                    "timing_errors_final_us",
                )
            )
            if (
                isinstance(fp, str)
                and fp
                and isinstance(prop_sha, str)
                and prop_sha
                and complete
                and _sections_valid(s)
                and pair in run_fingerprints.get(key, set())
            ):
                bound.append(s)
            else:
                dropped += 1
        return bound, dropped

    scores, dropped_unbound_cur = _bind(scores)
    # D3 (schema-appropriate binding): schema-2 score rows never carried a
    # proposal_sha256 (that binding arrived with schema 3). Legacy rows bind to
    # a fingerprint-matching run.json (the pre-schema-3 rule) and render ONLY
    # in the labeled non-comparative legacy section.
    legacy_bound: list[dict] = []
    dropped_unbound_legacy = 0
    for s in legacy2:
        fp = s.get("input_fingerprint")
        key = (s.get("case_id"), s.get("candidate_id"))
        if fp and fp in run_fingerprint_names.get(key, set()):
            legacy_bound.append(s)
        else:
            dropped_unbound_legacy += 1
    legacy2 = legacy_bound
    dropped_unbound = dropped_unbound_cur + dropped_unbound_legacy
    # F05: cases whose CURRENT case/source evidence cannot be established are
    # never rendered as comparative rows; their self-consistent historical
    # run/score pairs move to the labeled unverified section (fail-closed).
    historical_scores = [s for s in scores if s.get("case_id") in unverified]
    scores = [s for s in scores if s.get("case_id") not in unverified]
    runs_comparative = [r for r in runs if r.get("case_id") not in unverified]
    lines: list[str] = []
    lines.append("# Benchmark comparison report")
    lines.append("")
    lines.append(
        "**Caveat:** synthetic-timing recovery measures recovery of injected errors only. It is not evidence"
    )
    lines.append(
        "about real-speech synchronization, and it is not a production threshold. See denominators."
    )
    lines.append(
        "**Score-number provenance:** comparative rows are admitted only from a"
        " directory whose run.json passes the proposal-byte check; the row"
        " bullets' recorded input fingerprint and proposal hash are the audit"
        " anchors. Numbers fabricated *inside* a score.json that pairs with an"
        " admitted, byte-verified run record render as recorded — regenerate"
        " score.json with `score` rather than editing it."
    )
    lines.append("")
    lines.append(
        f"dropped unbound score rows: {dropped_unbound} (scores with no "
        "fingerprint-matching run.json, schema-3 rows missing a proposal hash "
        "pair, structurally incomplete rows, and planted numbers are never "
        "rendered)"
    )
    lines.append(
        f"dropped stale-generation rows: {dropped_stale_generation} (schema-3 scores "
        "bound to a run.json whose recorded fingerprint differs from the current "
        "case generation are never rendered)"
    )
    lines.append(
        f"legacy schema-2 rows rendered separately: {len([s for s in legacy2 if s.get('case_id') not in unverified])} "
        "(schema 2 counted unguarded proposals as 'accepted' — pre-F06 semantics; "
        "kept in a labeled non-comparative section, never mixed into schema-3 "
        "comparisons)"
    )
    lines.append(
        f"dropped obsolete-acceptance rows: {len(acceptance_stale)} (b1-va scores "
        "whose validated base run/proposal no longer matches the current base "
        "artifacts are never rendered; re-run the base arm and re-validate)"
    )
    lines.append(
        f"dropped tampered/removed proposal rows: {len(proposal_stale)} (run.json "
        "proposal_sha256 no longer matches proposal.json bytes on disk at report "
        "time; the run/score pair is never rendered comparably; re-run the arm)"
    )
    lines.append(
        f"unreadable artifacts skipped: {len(artifact_problems)} (run/score JSON "
        "that cannot be parsed, and score.json files with no pairing admitted "
        "run.json in the same directory, are reported here, never rendered as "
        "a number, and do not abort the rest of the report)"
    )
    for cid, reason in acceptance_stale:
        lines.append(f"- case `{cid}`: obsolete acceptance — {reason[:300]}")
    for cid, reason in proposal_stale:
        lines.append(f"- case `{cid}`: tampered/removed proposal — {reason[:300]}")
    for cid, reason in artifact_problems:
        lines.append(f"- case `{cid}`: unreadable artifact — {reason[:200]}")
    if acceptance_stale or proposal_stale or artifact_problems:
        lines.append("")
    if tool_versions:
        lines.append("## Tool/model versions")
        lines.append("")
        for name, ver in sorted(tool_versions.items()):
            lines.append(f"- `{name}`: {ver}")
        lines.append("")

    for case_id in case_ids:
        if case_id in unverified:
            continue
        case_runs = [r for r in runs_comparative if r.get("case_id") == case_id]
        case_scores = [s for s in scores if s["case_id"] == case_id]
        if not case_runs and not case_scores:
            continue
        lines.append(
            f"## Case `{case_id}` (scenario {case_scores[0]['scenario'] if case_scores else '?'})"
        )
        lines.append("")
        lines.append(
            "| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |"
        )
        lines.append(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
        )
        lines.append(
            "**Column semantics (schema 3):** `Acc validated` = automatically "
            "accepted nonzero cues from a real AcceptanceRecord (b1-va only); "
            "`If blind` = unguarded proposal nonzero (counterfactual: what "
            "blind application would have changed — no validator ran); "
            "`repaired/worsened` show accepted-side / blindly-applied-side "
            "counts (`—` where that side does not apply); `final onset err` "
            "statistics use the arm's final semantics per row below."
        )
        lines.append("")
        for s in case_scores:
            c = s["counts"]
            d = s["denominators"]
            dis = s["discontinuities"]
            te = s["timing_errors_final_us"]
            run = next(
                (r for r in case_runs if r.get("candidate_id") == s["candidate_id"]),
                {},
            )
            local = dis.get("local_cue_adjustments", 0)
            lines.append(
                "| {cand} | {status} | {prop} | {acc} | {blind} | {rep} | {wor} | {hp}/{hb}/{ha} | {med} / {p90} / {p95} | {imp}/{mat}/{fp} ({loc}) | {unres}/{tb} | {tot}/{alt}/{unalt} |".format(
                    cand=s["candidate_id"],
                    status=run.get("status", "scored"),
                    prop=c["proposals_nonzero"],
                    acc=c.get("accepted_nonzero", "—"),
                    blind=c.get("if_blindly_applied_nonzero", "—"),
                    rep=f"{c.get('repaired', '—')}/{c.get('repaired_if_blindly_applied', '—')}",
                    wor=f"{c.get('worsened_unaltered', '—')}/{c.get('worsened_unaltered_if_blindly_applied', '—')}",
                    hp=c["harmful_proposed"],
                    hb=c.get("harmful_if_blindly_applied", "—"),
                    ha=c.get("harmful_accepted", "—"),
                    med=_fmt_us(te["median_abs_us"]),
                    p90=_fmt_us(te["p90_abs_us"]),
                    p95=_fmt_us(te["p95_abs_us"]),
                    imp=dis["detected_breakpoints"],
                    mat=dis["matched_true_breakpoints"],
                    fp=dis["false_positive_breakpoints"],
                    loc=local,
                    unres=dis["unresolved_true_breakpoints"],
                    tb=dis["true_breakpoints"],
                    tot=d["total_cues"],
                    alt=d["altered_cues"],
                    unalt=d["unaltered_cues"],
                )
            )
        lines.append("")
        for s in case_scores:
            lines.append(
                f"- `{s['candidate_id']}` final timeline = "
                f"{s.get('final_semantics', 'legacy (schema 2: proposal counted as accepted)')}"
            )
        for s in case_scores:
            dis = s["discontinuities"]
            lines.append(
                f"- `{s['candidate_id']}` discontinuities: candidate-implied breakpoints "
                f"{dis['detected_breakpoints']} (matched {dis['matched_true_breakpoints']} "
                f"of {dis['true_breakpoints']} true, false-positive "
                f"{dis['false_positive_breakpoints']}, ambiguous "
                f"{dis.get('ambiguous_breakpoints', 0)}, jump threshold "
                f"{dis['jump_threshold_us'] / 1000:.0f} ms); final timeline still "
                f"discontinuous at {dis['unresolved_true_breakpoints']} of "
                f"{dis['true_breakpoints']} true breakpoints "
                f"({dis['true_breakpoints_without_straddle_pair']} without a straddling cue pair)"
                + (
                    f"; {dis['local_cue_adjustments']} local cue adjustments "
                    "(transient isolated-cue corrections, counted separately, "
                    "not release discontinuities)"
                    if dis.get("local_cue_adjustments", 0)
                    else ""
                )
                + (
                    f"; {dis['ambiguous_offset_regions']} ambiguous short "
                    "offset regions (borderline local-vs-release regions: "
                    "breakpoint claims kept, cues never auto-counted as local, "
                    "descriptors in score.json — explicit, never silent)"
                    if dis.get("ambiguous_offset_regions", 0)
                    else ""
                )
                + (
                    f"; {dis['edge_ambiguous_regions']} track-boundary "
                    "one-cue correction(s) (isolated edge adjustment vs "
                    "release-boundary offset ambiguity: claims kept for "
                    "localization, cues never auto-counted as local, "
                    f"unmatched edge claims {dis.get('unmatched_edge_ambiguous_claims', 0)} "
                    "recorded explicitly instead of auto-declared false "
                    "release discontinuities — descriptors in score.json, "
                    "never silent)"
                    if dis.get("edge_ambiguous_regions", 0)
                    else ""
                )
            )
        for s in case_scores:
            dis = s["discontinuities"]
            matched = [
                m
                for m in dis.get("matched_breaks", [])
                if isinstance(m, dict)
                and all(
                    _numeric(m.get(k))
                    for k in (
                        "true_breakpoint_us",
                        "bracket_start_us",
                        "bracket_end_us",
                        "bracket_width_us",
                    )
                )
            ]
            if not matched:
                continue
            parts = []
            for m in matched:
                precise = (
                    f"precise ±{m['precise_residual_us'] / 1000:.0f} ms"
                    if m.get("precise_within_tol")
                    and _numeric(m.get("precise_residual_us"))
                    else "localization uncertain"
                )
                parts.append(
                    "true {tb:.2f} s in bracket [{bs:.2f}, {be:.2f}] s "
                    "(width {w:.2f} s; {precise})".format(
                        tb=m["true_breakpoint_us"] / 1_000_000,
                        bs=m["bracket_start_us"] / 1_000_000,
                        be=m["bracket_end_us"] / 1_000_000,
                        w=m["bracket_width_us"] / 1_000_000,
                        precise=precise,
                    )
                )
            lines.append(
                f"- `{s['candidate_id']}` breakpoint localization (bracketing anchors, "
                "credit from the bracket not the time tolerance): " + "; ".join(parts)
            )
        for s in case_scores:
            o = s.get("offset_recovery")
            if isinstance(o, dict) and all(
                _numeric(o.get(k))
                for k in (
                    "true_offset_us",
                    "applied_shift_us",
                    "recovered_offset_us",
                    "residual_us",
                )
            ):
                lines.append(
                    f"- `{s['candidate_id']}` offset recovery: true {o['true_offset_us'] / 1000:.0f} ms, "
                    f"applied shift {o['applied_shift_us'] / 1000:.0f} ms, recovered "
                    f"{o['recovered_offset_us'] / 1000:.0f} ms, residual "
                    f"{o['residual_us'] / 1000:.0f} ms (applied shift is what the "
                    "candidate moved the subtitles; exact recovery means applied_shift == -true_offset)"
                )
        for r in case_runs:
            bits = [f"- `{r.get('candidate_id', '?')}`: {r.get('status', '?')}"]
            if _schema_of(r) >= 2 and isinstance(r.get("input_fingerprint"), str):
                bits.append(f"input {str(r['input_fingerprint'])[:16]}…")
            else:
                bits.append(
                    "legacy unverified run (no input fingerprint; re-run to bind "
                    "provenance)"
                )
            if r.get("validated_candidate_id"):
                bits.append(
                    f"validated base {r['validated_candidate_id']} @ run "
                    f"{r.get('base_run_id', '?')!s} fp "
                    f"{str(r.get('base_input_fingerprint', ''))[:16]}…"
                )
            vc = r.get("validation_config")
            if isinstance(vc, dict):
                bits.append(
                    f"validation seed {vc.get('seed')} langs "
                    f"{vc.get('language')}/{vc.get('subtitle_language')} "
                    f"asr={vc.get('asr_model')} verifier={vc.get('verifier_model')} "
                    f"pad {vc.get('pad_us')} ms ratio {vc.get('min_match_ratio')} "
                    f"tol {vc.get('timing_tolerance_us')} ms"
                )
            if r.get("reason"):
                bits.append(f"reason: {str(r['reason'])[:400]}")
            if _numeric(r.get("wall_seconds")):
                bits.append(f"wall {r['wall_seconds']:.1f}s")
            if _numeric(r.get("preprocessing_seconds")):
                bits.append(f"preprocess {r['preprocessing_seconds']:.1f}s")
            if _numeric(r.get("candidate_seconds")):
                bits.append(f"candidate {r['candidate_seconds']:.1f}s")
            if _numeric(r.get("asr_calls")) and r["asr_calls"]:
                bits.append(
                    f"asr calls {r['asr_calls']} / "
                    f"{r.get('asr_seconds') if _numeric(r.get('asr_seconds')) else 0.0:.1f}s"
                )
            if _numeric(r.get("verifier_calls")) and r["verifier_calls"]:
                bits.append(
                    f"verifier calls {r['verifier_calls']} / "
                    f"{r.get('semantic_seconds') if _numeric(r.get('semantic_seconds')) else 0.0:.1f}s"
                )
            if (
                _numeric(r.get("asr_calls"))
                and r["asr_calls"]
                and _numeric(r.get("inference_seconds_total"))
            ):
                bits.append(f"inference total {r['inference_seconds_total']:.1f}s")
            lines.append(" · ".join(bits))
        lines.append("")

    if unverified and (
        historical_scores or any(r.get("case_id") in unverified for r in runs)
    ):
        lines.append("## Unverified historical results (NOT COMPARABLE)")
        lines.append("")
        lines.append(
            "**No current case manifest / registered source evidence exists for "
            "these cases.** The rows below are self-consistent historical run/score "
            "pairs only; they are NOT re-verifiable against present-day inputs, are "
            "excluded from every comparative table above, and must not be used for "
            "any comparison, decision, or acceptance."
        )
        lines.append("")
        reasons = dict(unverified_reasons or {})
        for cid in sorted(unverified):
            reason = reasons.get(cid)
            if reason:
                lines.append(f"- case `{cid}`: {reason[:300]}")
        if any(reasons.get(cid) for cid in unverified):
            lines.append("")
        for s in historical_scores:
            te = s.get("timing_errors_final_us", {})
            lines.append(
                f"- case `{s.get('case_id')}` / `{s.get('candidate_id')}`: "
                f"median final onset err {_fmt_us(te.get('median_abs_us'))} "
                f"(fp {str(s.get('input_fingerprint', ''))[:16]}…) — "
                "unverified: current case/source evidence missing"
            )
        for r in runs:
            if r.get("case_id") in unverified:
                lines.append(
                    f"- case `{r.get('case_id')}` / `{r.get('candidate_id', '?')}` "
                    f"run: {r.get('status', '?')} — unverified historical run"
                )
        lines.append("")

    legacy_comparative = [s for s in legacy2 if s.get("case_id") not in unverified]
    if legacy_comparative:
        lines.append("## Legacy schema-2 measurements (NOT COMPARABLE)")
        lines.append("")
        lines.append(
            "**schema_version 2 scored the raw proposal as 'accepted' for arms "
            "with no validator (third-review F06).** These rows are preserved "
            "as recorded history only; the F04/F06 measurement semantics "
            "(local-cue-adjustment separation, counterfactual labeling) do not "
            "exist in them. Do not compare these numbers with schema-3 rows."
        )
        lines.append("")
        for s in legacy_comparative:
            c = s.get("counts", {})
            lines.append(
                f"- case `{s.get('case_id')}` / `{s.get('candidate_id')}` "
                f"(schema 2, legacy semantics: proposals_nonzero="
                f"{c.get('proposals_nonzero', '?')}, accepted_nonzero="
                f"{c.get('accepted_nonzero', '?')}, repaired="
                f"{c.get('repaired', '?')}, harmful_accepted="
                f"{c.get('harmful_accepted', '?')}) — pre-F06 measurement"
            )
        lines.append("")

    lines.append("## Tolerances used")
    tolerance_source = next(
        (
            s
            for s in list(scores) + list(legacy2) + list(historical_scores)
            if isinstance(s.get("tolerances"), dict)
            and all(
                _numeric(s["tolerances"].get(k))
                for k in ("good_us", "severe_us", "break_match_us")
            )
        ),
        None,
    )
    if tolerance_source is not None:
        t = tolerance_source["tolerances"]
        lines.append(
            f"- good ±{t['good_us'] // 1000} ms, severe >±{t['severe_us'] // 1000} ms, breakpoint match ±{t['break_match_us'] // 1000} ms "
            f"({t.get('meaning', 'unlabeled')})"
        )
    else:
        lines.append("- no scored rows available in this report")
    lines.append("")
    return "\n".join(lines)


def write_report(path: Path, text: str) -> None:
    from .paths import ensure_scratch_path

    # Validate the exact destination FIRST: a refused path must create nothing.
    resolved = ensure_scratch_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(text, encoding="utf-8")
