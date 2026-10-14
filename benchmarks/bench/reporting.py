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
            "| Candidate | Status | Proposals | Accepted | Repaired | Worsened | Harmful prop/acc | Median/P90/P95 final onset err | Breaks true/det/false+ | Denominator (cues: total/altered/unaltered) |"
        )
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for s in case_scores:
            c = s["counts"]
            d = s["denominators"]
            dis = s["discontinuities"]
            te = s["timing_errors_final_us"]
            run = next(
                (r for r in case_runs if r["candidate_id"] == s["candidate_id"]), {}
            )
            lines.append(
                "| {cand} | {status} | {prop} | {acc} | {rep} | {wor} | {hp}/{ha} | {med} / {p90} / {p95} | {tb}/{db}/{fp} | {tot}/{alt}/{unalt} |".format(
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
                    tb=dis["matched_true_breakpoints"],
                    db=dis["detected_breakpoints"],
                    fp=dis["false_positive_breakpoints"],
                    tot=d["total_cues"],
                    alt=d["altered_cues"],
                    unalt=d["unaltered_cues"],
                )
            )
        lines.append("")
        for s in case_scores:
            if s.get("offset_recovery"):
                o = s["offset_recovery"]
                lines.append(
                    f"- `{s['candidate_id']}` offset recovery: true {o['true_offset_us'] / 1000:.0f} ms, "
                    f"estimated correction {o['estimated_correction_us'] / 1000:.0f} ms, residual {o['residual_us'] / 1000:.0f} ms"
                )
        for r in case_runs:
            bits = [f"- `{r['candidate_id']}`: {r['status']}"]
            if r.get("reason"):
                bits.append(f"reason: {r['reason'][:180]}")
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
