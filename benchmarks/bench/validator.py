"""B1-VA: targeted ASR + semantic validation of an existing proposal arm.

The validator evaluates proposals from a base candidate so the validator's
incremental benefit is measured. It requires semantic correspondence between
the subtitle text and the specific spoken utterance: speech activity at a
timestamp is insufficient. When evidence is insufficient the region is
rejected/abstained and original timing is retained. Ground-truth
correspondence labels are never fed to the validator.

Cross-language verdicts (P1 fix): a Japanese/Chinese audio transcript against
an ENGLISH subtitle is a translation, so lexical overlap is ~0 — lexical
comparison is NEITHER accept-support NOR reject evidence across languages.
Same-script pairs keep the lexical Dice decision; cross-script pairs are
decided only by an explicitly configured semantic verifier
(`BENCH_SEM_VERIFY_*`, translation-tolerant), and abstain without one.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from .manifests import AcceptanceRecord, CaseManifest, ProposalRecord
from .media import extract_audio_window

PAD_US = 1_500_000
MIN_MATCH_RATIO = 0.45
MIN_CONFIDENCE = -0.5
CJK_RANGE_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
LATIN_RANGE_RE = re.compile(r"[A-Za-z]")
SCRIPT_MAJORITY = 0.5


def normalize_text(text: str) -> str:
    """Strip ASS override tags, convert line breaks (\\N and native newlines)
    to newlines, collapse whitespace, case-fold. Final output matches the
    historical behavior for all existing callers (collapsed whitespace)."""
    text = re.sub(r"\\N", "\n", text)
    text = re.sub(r"\{[^}]*\}", "", text)
    text = re.sub(r"[^\w\s'â€™\-\u3040-\u30ff\u4e00-\u9fff]", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _dice(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


def script_profile(text: str) -> tuple[float, float]:
    """(CJK kana/ideograph ratio, Latin ratio) over alphabetic characters."""
    normalized = normalize_text(text)
    letters = [ch for ch in normalized if ch.isalpha()]
    if not letters:
        return (0.0, 0.0)
    cjk = sum(1 for ch in letters if CJK_RANGE_RE.match(ch))
    latin = sum(1 for ch in letters if LATIN_RANGE_RE.match(ch))
    return (cjk / len(letters), latin / len(letters))


def is_cross_language(subtitle_text: str, transcript_text: str) -> bool:
    """True when one side is majority-Latin and the other majority-CJK.

    Heuristic: a script is "majority" when its ratio of alphabetic characters
    exceeds SCRIPT_MAJORITY (0.5). Cross-language means the lexical score is
    meaningless as agreement evidence.
    """
    s_cjk, s_latin = script_profile(subtitle_text)
    t_cjk, t_latin = script_profile(transcript_text)
    return (s_latin > SCRIPT_MAJORITY and t_cjk > SCRIPT_MAJORITY) or (
        s_cjk > SCRIPT_MAJORITY and t_latin > SCRIPT_MAJORITY
    )


def semantic_match(subtitle_text: str, transcript_text: str) -> float:
    """Token Dice coefficient with a character-bigram fallback for space-less scripts.

    Measures correspondence of the specific utterance, not audio activity.
    """
    a, b = normalize_text(subtitle_text), normalize_text(transcript_text)
    if not a or not b:
        return 0.0
    word_score = _dice(set(a.split()), set(b.split()))
    char_score = _dice(
        {a[i : i + 2] for i in range(len(a) - 1)},
        {b[i : i + 2] for i in range(len(b) - 1)},
    )
    return max(word_score, char_score)


def cue_region(cue_start_us: int, regions: list[dict]) -> int | None:
    for i, r in enumerate(regions):
        end = r.get("end_us")
        if cue_start_us >= r["start_us"] and (end is None or cue_start_us <= end):
            return i
    return None


def plan_samples(
    case: CaseManifest,
    proposal: ProposalRecord,
    cue_times: dict[str, tuple[int, int]],
    seed: int,
    n_random: int = 6,
) -> list[str]:
    mapped = [cid for cid in proposal.proposed_times_us if cid in cue_times]
    if not mapped:
        return []
    ordered = sorted(mapped, key=lambda cid: cue_times[cid][0])
    rng = np.random.default_rng(seed)
    picks: list[str] = []

    def add(cid: str | None) -> None:
        if cid and cid not in picks:
            picks.append(cid)

    add(ordered[0])
    add(ordered[len(ordered) // 2])
    add(ordered[-1])
    for region in proposal.regions:
        start, end = region.get("start_us"), region.get("end_us")
        before = [
            cid for cid in ordered if end is not None and cue_times[cid][0] <= end + 1
        ]
        after = [
            cid
            for cid in ordered
            if start is not None and cue_times[cid][0] >= start - 1
        ]
        add(before[-1] if before else None)
        add(after[0] if after else None)
    big = sorted(
        mapped,
        key=lambda cid: abs(proposal.proposed_times_us[cid][0] - cue_times[cid][0]),
        reverse=True,
    )
    for cid in big[:5]:
        add(cid)
    for _ in range(n_random):
        add(ordered[int(rng.integers(0, len(ordered)))])
    return picks


def validate_proposal(
    case: CaseManifest,
    proposal: ProposalRecord,
    base_candidate_id: str,
    corrupted_times: dict[str, tuple[int, int]],
    cue_text: dict[str, str],
    reference_media: Path,
    scratch_dir: Path,
    transcriber,
    language: str,
    seed: int,
    audio_stream: str | None = None,
    verifier=None,
) -> AcceptanceRecord:
    """Validate a base arm's proposals with targeted ASR windows.

    ``audio_stream`` is the ffmpeg map string (e.g. ``0:a:1``) for the source's
    registered audio track; ``None`` keeps legacy behavior (``0:a:0``).
    ``verifier`` is an optional semantic verifier (translation-tolerant) used
    ONLY for cross-language samples; transcription and verification are
    independently configured boundaries.
    """
    if transcriber is None:
        return AcceptanceRecord(
            case_id=case.case_id,
            candidate_id="b1-va",
            validated_candidate_id=base_candidate_id,
            status="not_run",
            accepted_regions=[],
            rejected_regions=[],
            abstained_regions=[],
            accepted_times_us=dict(corrupted_times),
            sample_cue_ids=[],
            asr_seconds=0.0,
            asr_calls=0,
            notes="no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained",
        )
    if proposal.mapping_status not in ("1:1-order-preserving",):
        return AcceptanceRecord(
            case_id=case.case_id,
            candidate_id="b1-va",
            validated_candidate_id=base_candidate_id,
            status="abstain",
            accepted_regions=[],
            rejected_regions=[],
            abstained_regions=list(proposal.regions),
            accepted_times_us=dict(corrupted_times),
            sample_cue_ids=[],
            asr_seconds=0.0,
            asr_calls=0,
            notes=f"base proposal unusable ({proposal.mapping_status}); abstaining",
        )

    samples = plan_samples(case, proposal, corrupted_times, seed)
    scratch_dir.mkdir(parents=True, exist_ok=True)
    from .paths import ensure_scratch_path

    ensure_scratch_path(scratch_dir)
    asr_seconds = 0.0
    asr_calls = 0
    verdicts: dict[int, list[str]] = {}
    no_verifier_cross_lang = 0
    verifier_no_verdict = 0
    mock_verifier_used = False
    for cid in samples:
        start_us, end_us = proposal.proposed_times_us[cid]
        region = cue_region(corrupted_times[cid][0], proposal.regions)
        if region is None:
            continue
        wav = scratch_dir / f"asr_{cid}.wav"
        try:
            extract_audio_window(
                reference_media,
                wav,
                max(0.0, (start_us - PAD_US) / 1_000_000),
                (end_us + PAD_US) / 1_000_000,
                audio_stream=audio_stream,
            )
            result = transcriber.transcribe_window(wav, language, key=cid)
        except Exception as exc:  # noqa: BLE001 -- boundary failures are abstentions, not passes
            verdicts.setdefault(region, []).append("abstain")
            asr_seconds += 0.0
            asr_calls += 1
            (scratch_dir / "asr_errors.log").open("a", encoding="utf-8").write(
                f"{cid}: {exc}\n"
            )
            continue
        asr_seconds += result.seconds
        asr_calls += 1
        subtitle_text = cue_text.get(cid, "")
        ratio = semantic_match(subtitle_text, result.text)
        if result.mock:
            verdicts.setdefault(region, []).append("abstain")
            (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                f"{cid}: mock transcriber used; verdict forced to abstain\n"
            )
        elif is_cross_language(subtitle_text, result.text):
            # Lexical score is never accept-support and never reject evidence
            # across languages; only the semantic verifier boundary decides.
            if verifier is None:
                verdicts.setdefault(region, []).append("abstain")
                no_verifier_cross_lang += 1
                continue
            try:
                sv = verifier.verdict(subtitle_text, result.text, "und", language)
                asr_seconds += sv.seconds
            except Exception as exc:  # noqa: BLE001 -- verifier boundary failures abstain
                verdicts.setdefault(region, []).append("abstain")
                verifier_no_verdict += 1
                (scratch_dir / "asr_errors.log").open("a", encoding="utf-8").write(
                    f"{cid}: semantic verifier: {exc}\n"
                )
                continue
            if sv.mock:
                mock_verifier_used = True
                (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                    f"{cid}: mock semantic verifier used; test-only\n"
                )
            if sv.verdict == "match":
                verdicts.setdefault(region, []).append("accept")
            elif sv.verdict == "no_match":
                verdicts.setdefault(region, []).append("reject")
            else:
                verdicts.setdefault(region, []).append("abstain")
                verifier_no_verdict += 1
        elif ratio >= MIN_MATCH_RATIO and result.confidence >= MIN_CONFIDENCE:
            verdicts.setdefault(region, []).append("accept")
        elif ratio < MIN_MATCH_RATIO and result.confidence >= MIN_CONFIDENCE:
            # Same-script pair: lexical disagreement IS meaningful evidence.
            verdicts.setdefault(region, []).append("reject")
        else:
            verdicts.setdefault(region, []).append("abstain")

    accepted_regions: list[dict] = []
    rejected_regions: list[dict] = []
    abstained_regions: list[dict] = []
    accepted_times = dict(corrupted_times)
    mock_tag = "; mock semantic verifier (test-only)" if mock_verifier_used else ""
    for i, region in enumerate(proposal.regions):
        verdict = verdicts.get(i, [])
        if not verdict:
            abstained_regions.append({**region, "reason": "no samples resolved"})
            continue
        if "reject" in verdict:
            rejected_regions.append(
                {**region, "reason": "semantic mismatch in samples" + mock_tag}
            )
        elif all(v == "accept" for v in verdict):
            accepted_regions.append(
                {**region, "reason": "all samples semantically matched" + mock_tag}
            )
            for cid, (ps, pe) in proposal.proposed_times_us.items():
                if cue_region(corrupted_times[cid][0], [region]) == 0:
                    accepted_times[cid] = (ps, pe)
        else:
            abstained_regions.append(
                {
                    **region,
                    "reason": "mixed samples (accept+abstain); insufficient evidence",
                }
            )

    usable_verdicts = sum(
        1 for vs in verdicts.values() for v in vs if v in ("accept", "reject")
    )
    notes_parts = [
        "sampling: edges/split-sides/largest-changes/fixed+seeded-random controls",
        "mock runs never accepted",
    ]
    if no_verifier_cross_lang:
        notes_parts.append(
            f"{no_verifier_cross_lang} cross-language samples abstained: semantic "
            "verifier not configured (BENCH_SEM_VERIFY_*); cross-language lexical "
            "differences are not evidence"
        )
    if verifier_no_verdict:
        notes_parts.append(
            f"{verifier_no_verdict} cross-language samples: semantic verifier gave "
            "no usable verdict (unknown/failure); abstained"
        )
    if mock_verifier_used:
        notes_parts.append("mock semantic verifier used (test-only)")
    no_evidence = (no_verifier_cross_lang + verifier_no_verdict) > 0
    if (
        not accepted_regions
        and not rejected_regions
        and usable_verdicts == 0
        and no_evidence
    ):
        status = "not_run"
        notes_parts.insert(
            0,
            "semantic verification not run (no usable evidence); original timing "
            "retained",
        )
    else:
        status = "success" if accepted_regions or rejected_regions else "abstain"
    return AcceptanceRecord(
        case_id=case.case_id,
        candidate_id="b1-va",
        validated_candidate_id=base_candidate_id,
        status=status,
        accepted_regions=accepted_regions,
        rejected_regions=rejected_regions,
        abstained_regions=abstained_regions,
        accepted_times_us=accepted_times,
        sample_cue_ids=samples,
        asr_seconds=asr_seconds,
        asr_calls=asr_calls,
        notes="; ".join(notes_parts),
    )
