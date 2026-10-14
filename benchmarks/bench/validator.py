"""B1-VA: targeted ASR + semantic validation of an existing proposal arm.

The validator evaluates proposals from a base candidate so the validator's
incremental benefit is measured. It requires semantic correspondence between
the subtitle text and the specific spoken utterance: speech activity at a
timestamp is insufficient. When evidence is insufficient the region is
rejected/abstained and original timing is retained. Ground-truth
correspondence labels are never fed to the validator.

Cross-language verdicts (P1 fix F03): a translated proposal (Korean/Russian/
French/Japanese/Chinese audio transcript against an ENGLISH subtitle) has ~0
lexical overlap, so lexical comparison is NEITHER accept-support NOR reject
evidence across languages. Routing is by verified source/target LANGUAGE
identity, with script detection only as a fallback signal:

* both spoken and subtitle identities known and EQUAL -> the lexical Dice
  decision stands (accept, and genuine CONTRADICTION reject);
* known and DIFFERENT -> cross-language: only an explicitly configured semantic
  verifier (`BENCH_SEM_VERIFY_*`, translation-tolerant) decides, never lexical;
* identity unknown/mixed -> low overlap is NOT sufficient negative evidence:
  route to the verifier when configured, otherwise abstain (never reject);
  positive lexical support with confidence is still valid.

Script profiling covers Hangul, Cyrillic, Greek, Arabic and Devanagari in
addition to kana/ideographs/Latin; a dominant-script contrast is one signal
among language identity, never the sole cross-language gate.
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
SCRIPT_MAJORITY = 0.5
# Script classes used for dominant-script detection. Lexical comparison is
# meaningful evidence only when both sides share the same language; a majority-
# script contrast is a *signal* that lexical comparison is meaningless, never
# the sole cross-language gate (language identity is authoritative when both
# identities are known — see is_cross_language / validate_proposal).
SCRIPT_RANGES: dict[str, re.Pattern[str]] = {
    "Kana": re.compile(r"[\u3040-\u30ff]"),
    "Han": re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]"),
    "Hangul": re.compile(r"[\u1100-\u11ff\u3130-\u318e\uac00-\ud7a3]"),
    "Cyrillic": re.compile(r"[\u0400-\u04ff\u0500-\u052f]"),
    "Greek": re.compile(r"[\u0370-\u03ff]"),
    "Latin": re.compile(r"[A-Za-z]"),
    "Arabic": re.compile(r"[\u0600-\u06ff\u0750-\u077f]"),
    "Devanagari": re.compile(r"[\u0900-\u097f]"),
}
CJK_RANGE_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
LATIN_RANGE_RE = re.compile(r"[A-Za-z]")
# Transliterated ASR output (romaji/pinyin) is all-Latin: script detection
# alone cannot see the translation relationship. When the ASR LANGUAGE is a
# CJK target (normalized subtag ja/zh: ja, jpn, zh, zh-CHS, zh-Hans, ...) and
# the subtitle is majority-Latin, the pair is treated as cross-language
# (verifier boundary) regardless of transcript surface script. Limitation: a
# transliterated transcript with language "und"/"en" stays on the same-script
# lexical path (documented residual — low overlap abstains, never rejects).
CJK_LANGUAGE_SUBTAGS = ("ja", "zh")
UNKNOWN_LANGUAGE_TAGS = ("", "und", "zbl", "mul", "mis")
# ffprobe reports ISO 639-2/B three-letter tags (eng, jpn, kor, rus, fre/fra)
# while the CLI --language hint uses BCP-47 two-letter forms (en, ja, ko, ru,
# fr). Normalize the primary subtag so the two conventions compare equal.
ISO3_TO_ISO1 = {
    "eng": "en",
    "jpn": "ja",
    "zho": "zh",
    "chi": "zh",
    "kor": "ko",
    "rus": "ru",
    "fre": "fr",
    "fra": "fr",
    "deu": "de",
    "ger": "de",
    "spa": "es",
    "ita": "it",
    "por": "pt",
    "nld": "nl",
    "dut": "nl",
    "pol": "pl",
    "tur": "tr",
    "heb": "he",
    "ara": "ar",
    "hin": "hi",
    "tha": "th",
    "vie": "vi",
    "ukr": "uk",
    "ell": "el",
    "gre": "el",
    "ces": "cs",
    "cze": "cs",
    "hun": "hu",
    "fin": "fi",
    "nob": "nb",
    "nor": "no",
    "dan": "da",
    "swe": "sv",
    "ron": "ro",
    "rum": "ro",
    "bul": "bg",
    "srp": "sr",
    "hrv": "hr",
    "slk": "sk",
    "slv": "sl",
    "lit": "lt",
    "lav": "lv",
    "est": "et",
    "cat": "ca",
    "ind": "id",
    "msa": "ms",
    "may": "ms",
    "fas": "fa",
    "per": "fa",
    "urd": "ur",
    "ben": "bn",
    "tam": "ta",
    "tel": "te",
    "mar": "mr",
    "guj": "gu",
    "kan": "kn",
    "mal": "ml",
}


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


def normalize_language(code: str | None) -> str | None:
    """Canonical primary language subtag, or None when undetermined.

    Lowercases, drops region/script subtags (``zh-Hans`` -> ``zh``), and maps
    the three-letter ISO 639-2/B tags ffprobe reports to their ISO 639-1 form
    (``eng``->``en``, ``kor``->``ko``) so CLI hints and registry tags compare
    equal. ``und``/empty and the multilingual sentinels are None (unknown)."""
    if not code:
        return None
    primary = code.strip().lower().split("-")[0]
    if primary in UNKNOWN_LANGUAGE_TAGS:
        return None
    return ISO3_TO_ISO1.get(primary, primary)


def script_profile(text: str) -> dict[str, float]:
    """Ratio of each SCRIPT_RANGES class over the letters in ``text``.

    Only letters matched by a SCRIPT_RANGES class are counted; the ratios sum
    to 1.0 over that recognized-letter set. Empty when there is no such letter.
    """
    normalized = normalize_text(text)
    letters = [ch for ch in normalized if ch.isalpha()]
    if not letters:
        return {}
    counts = {name: 0 for name in SCRIPT_RANGES}
    for ch in letters:
        for name, rng in SCRIPT_RANGES.items():
            if rng.match(ch):
                counts[name] += 1
                break
    total = sum(counts.values())
    if total == 0:
        return {}
    return {name: count / total for name, count in counts.items() if count}


def dominant_script(text: str) -> str | None:
    """Script class holding a strict majority of the text's letters, else None."""
    ratios = script_profile(text)
    if not ratios:
        return None
    name, ratio = max(ratios.items(), key=lambda kv: kv[1])
    return name if ratio >= SCRIPT_MAJORITY else None


def _transcript_language_is_cjk(language: str | None) -> bool:
    return normalize_language(language) in CJK_LANGUAGE_SUBTAGS


def is_cross_language(
    subtitle_text: str,
    transcript_text: str,
    language: str | None = None,
    subtitle_language: str | None = None,
) -> bool:
    """True when lexical comparison is meaningless as agreement evidence.

    Language identity is authoritative when BOTH the spoken (``language``) and
    target subtitle (``subtitle_language``) identities are known: the pair is
    cross-language exactly when the two identities differ. When an identity is
    unknown, fallback signals decide: (1) a dominant-script contrast over the
    broad script classes, and (2) the transliteration rule (a CJK-language ASR
    transcript against a majority-Latin subtitle, covering romaji/pinyin). A
    script contrast is one signal among identity, never the sole gate.
    """
    audio = normalize_language(language)
    subtitle = normalize_language(subtitle_language)
    if audio is not None and subtitle is not None:
        return audio != subtitle
    s_script = dominant_script(subtitle_text)
    t_script = dominant_script(transcript_text)
    if s_script is not None and t_script is not None and s_script != t_script:
        return True
    return _transcript_language_is_cjk(language) and s_script == "Latin"


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
    verifier=None,
    subtitle_language: str = "und",
) -> AcceptanceRecord:
    """Validate a base arm's proposals with targeted ASR windows.

    ``reference_media`` is the ALREADY-DECODED single-stream ``reference.wav``
    produced from the source's selected audio track at preprocessing time;
    window extraction always reads stream 0 of that WAV. The source-container
    stream-selection string (``0:a:<sidx>``) must never be threaded here:
    re-selecting a second stream on a one-stream WAV fails closed.
    ``verifier`` is an optional semantic verifier (translation-tolerant) used
    ONLY for cross-language samples; transcription and verification are
    independently configured boundaries.

    ``language`` is the resolved spoken/audio language hint and
    ``subtitle_language`` the resolved target-subtitle hint (defaults to "und"
    so existing call sites keep working). Routing keys on the verified identity
    pair: equal identities keep the lexical accept/contradiction-reject
    decision, differing identities are decided only by the verifier, and an
    unknown identity never rejects on low overlap (it routes to the verifier
    when configured, otherwise abstains). The verifier always receives the
    real resolved hints, never a hardcoded "und".
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
    identity_unknown_abstentions = 0
    mock_verifier_used = False
    audio_identity = normalize_language(language)
    subtitle_identity = normalize_language(subtitle_language)
    same_identity = (
        audio_identity is not None
        and subtitle_identity is not None
        and audio_identity == subtitle_identity
    )

    def run_verifier(region: int, subtitle_text: str, transcript_text: str) -> None:
        """Send one sample to the semantic verifier boundary and record its verdict.

        The verifier is translation-tolerant and receives the RESOLVED language
        hints (never a hardcoded "und"). match -> accept, no_match -> reject,
        unknown/exception -> abstain (no usable verdict)."""
        nonlocal asr_seconds, verifier_no_verdict, mock_verifier_used
        try:
            sv = verifier.verdict(
                subtitle_text, transcript_text, subtitle_language, language
            )
            asr_seconds += sv.seconds
        except Exception as exc:  # noqa: BLE001 -- verifier boundary failures abstain
            verdicts.setdefault(region, []).append("abstain")
            verifier_no_verdict += 1
            (scratch_dir / "asr_errors.log").open("a", encoding="utf-8").write(
                f"{cid}: semantic verifier: {exc}\n"
            )
            return
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
        elif is_cross_language(subtitle_text, result.text, language, subtitle_language):
            # Lexical score is never accept-support and never reject evidence
            # across languages; only the semantic verifier boundary decides.
            if verifier is None:
                verdicts.setdefault(region, []).append("abstain")
                no_verifier_cross_lang += 1
                continue
            run_verifier(region, subtitle_text, result.text)
        elif same_identity:
            # Verified same-language pair: lexical agreement is accept-support
            # and lexical disagreement is genuine CONTRADICTION evidence.
            if ratio >= MIN_MATCH_RATIO and result.confidence >= MIN_CONFIDENCE:
                verdicts.setdefault(region, []).append("accept")
            elif ratio < MIN_MATCH_RATIO and result.confidence >= MIN_CONFIDENCE:
                verdicts.setdefault(region, []).append("reject")
            else:
                verdicts.setdefault(region, []).append("abstain")
        elif ratio >= MIN_MATCH_RATIO and result.confidence >= MIN_CONFIDENCE:
            # Identity not fully verified and scripts do not contrast: positive
            # lexical support with confidence is still valid accept evidence.
            verdicts.setdefault(region, []).append("accept")
        elif ratio < MIN_MATCH_RATIO and result.confidence >= MIN_CONFIDENCE:
            # Identity not verified: low overlap is NOT sufficient negative
            # evidence. Route to the verifier when configured, else abstain
            # (never reject on an unverified identity).
            if verifier is not None:
                run_verifier(region, subtitle_text, result.text)
            else:
                verdicts.setdefault(region, []).append("abstain")
                identity_unknown_abstentions += 1
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
    if identity_unknown_abstentions:
        notes_parts.append(
            f"{identity_unknown_abstentions} samples: spoken/subtitle language "
            "identity not verified; low lexical overlap is not reject evidence "
            "(configure --language/--subtitle-language plus a semantic verifier "
            "to decide); abstained"
        )
    if mock_verifier_used:
        notes_parts.append("mock semantic verifier used (test-only)")
    no_evidence = (
        no_verifier_cross_lang + verifier_no_verdict + identity_unknown_abstentions
    ) > 0
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
