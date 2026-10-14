"""Human-readable comparison reports over machine-readable results."""

from __future__ import annotations

from pathlib import Path


def _fmt_us(value) -> str:
    if value is None:
        return "-"
    return f"{value / 1000:.0f} ms"


def build_report(
    case_ids: list[str],
    runs: list[dict],
    scores: list[dict],
    tool_versions: dict[str, str],
) -> str:
    """Render schema_version-2 scores; v1 (residual-domain detection) rows are ignored."""
    scores = [s for s in scores if int(s.get("schema_version", 0)) == 2]
    lines: list[str] = []
    lines.append("# Benchmark comparison report")
    lines.append("")
    lines.append(
        "**Caveat:** synthetic-timing recovery measures recovery of injected errors only. It is not evidence"
    )
    lines.append(
        "about real-speech synchronization, and it is not a production threshold. See denominators."
    )
    lines.append("")
    if tool_versions:
        lines.append("## Tool/model versions")
        lines.append("")
        for name, ver in sorted(tool_versions.items()):
            lines.append(f"- `{name}`: {ver}")
        lines.append("")

    for case_id in case_ids:
        case_runs = [r for r in runs if r["case_id"] == case_id]
        case_scores = [s for s in scores if s["case_id"] == case_id]
        if not case_runs and not case_scores:
            continue
        lines.append(
            f"## Case `{case_id}` (scenario {case_scores[0]['scenario'] if case_scores else '?'})"
        )
        lines.append("")
        lines.append(
            "| Candidate | Status | Proposals | Accepted | Repaired | Worsened | Harmful prop/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |"
        )
        lines.append(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
        )
        for s in case_scores:
            c = s["counts"]
            d = s["denominators"]
            dis = s["discontinuities"]
            te = s["timing_errors_final_us"]
            run = next(
                (r for r in case_runs if r["candidate_id"] == s["candidate_id"]), {}
            )
            lines.append(
                "| {cand} | {status} | {prop} | {acc} | {rep} | {wor} | {hp}/{ha} | {med} / {p90} / {p95} | {imp}/{mat}/{fp} | {unres}/{tb} | {tot}/{alt}/{unalt} |".format(
                    cand=s["candidate_id"],
                    status=run.get("status", "scored"),
                    prop=c["proposals_nonzero"],
                    acc=c["accepted_nonzero"],
                    rep=c["repaired"],
                    wor=c["worsened_unaltered"],
                    hp=c["harmful_proposed"],
                    ha=c["harmful_accepted"],
                    med=_fmt_us(te["median_abs_us"]),
                    p90=_fmt_us(te["p90_abs_us"]),
                    p95=_fmt_us(te["p95_abs_us"]),
                    imp=dis["detected_breakpoints"],
                    mat=dis["matched_true_breakpoints"],
                    fp=dis["false_positive_breakpoints"],
                    unres=dis["unresolved_true_breakpoints"],
                    tb=dis["true_breakpoints"],
                    tot=d["total_cues"],
                    alt=d["altered_cues"],
                    unalt=d["unaltered_cues"],
                )
            )
        lines.append("")
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
            )
        for s in case_scores:
            dis = s["discontinuities"]
            matched = dis.get("matched_breaks", [])
            if not matched:
                continue
            parts = []
            for m in matched:
                precise = (
                    f"precise ±{m['precise_residual_us'] / 1000:.0f} ms"
                    if m.get("precise_within_tol")
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
            if s.get("offset_recovery"):
                o = s["offset_recovery"]
                lines.append(
                    f"- `{s['candidate_id']}` offset recovery: true {o['true_offset_us'] / 1000:.0f} ms, "
                    f"applied shift {o['applied_shift_us'] / 1000:.0f} ms, recovered "
                    f"{o['recovered_offset_us'] / 1000:.0f} ms, residual "
                    f"{o['residual_us'] / 1000:.0f} ms (applied shift is what the "
                    "candidate moved the subtitles; exact recovery means applied_shift == -true_offset)"
                )
        for r in case_runs:
            bits = [f"- `{r['candidate_id']}`: {r['status']}"]
            if r.get("reason"):
                bits.append(f"reason: {r['reason'][:400]}")
            if r.get("wall_seconds") is not None:
                bits.append(f"wall {r['wall_seconds']:.1f}s")
            if r.get("preprocessing_seconds") is not None:
                bits.append(f"preprocess {r['preprocessing_seconds']:.1f}s")
            if r.get("candidate_seconds") is not None:
                bits.append(f"candidate {r['candidate_seconds']:.1f}s")
            if r.get("asr_calls"):
                bits.append(
                    f"asr calls {r['asr_calls']} / {r.get('asr_seconds', 0.0):.1f}s"
                )
            lines.append(" · ".join(bits))
        lines.append("")

    lines.append("## Tolerances used")
    for s in scores[:1]:
        t = s["tolerances"]
        lines.append(
            f"- good ±{t['good_us'] // 1000} ms, severe >±{t['severe_us'] // 1000} ms, breakpoint match ±{t['break_match_us'] // 1000} ms "
            f"({t['meaning']})"
        )
    lines.append("")
    return "\n".join(lines)


def write_report(path: Path, text: str) -> None:
    from .paths import ensure_scratch_path

    # Validate the exact destination FIRST: a refused path must create nothing.
    resolved = ensure_scratch_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(text, encoding="utf-8")
