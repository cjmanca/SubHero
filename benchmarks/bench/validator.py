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

Acceptance quality gate (P2 fix F07): automatic acceptance requires a usable
ASR reliability signal on the sampled transcript in EVERY language path. A
semantic-verifier "match" over an unreliable transcript — the documented -1.0
no-metric sentinel, confidence below MIN_CONFIDENCE, or a signal this module
cannot interpret — abstains and never accepts; acceptance quality must not
depend on which language path fired. Verifier "no_match" rejection is verifier
evidence (not an acceptance path) and does not depend on transcript
reliability. ASR-reliability abstentions are recorded with their own note
counter so a later targeted-re-sampling feature (explicitly out of scope) can
act on the abstention reason.

Timing-correspondence gate (P1 fix F03, third review): the extracted window is
the proposed interval PLUS 1.5 s of padding on each side, so an ASR transcript
of the whole window proves only that matching speech exists SOMEWHERE NEARBY
(semantic_content_present_in_window), never that it was spoken AT the proposed
time. Acceptance therefore requires TIME-LOCAL evidence: when the ASR backend
provides per-segment timestamps (verbose_json ``segments``; the targeted
transcription endpoint already returns them — no new aligner architecture is
needed), only segments intersecting the proposed interval within
TIMING_TOLERANCE_US may support an automatic accept, and a match found only in
the padding (or both in-interval and in padding, i.e. repeated/adjacent
dialogue with ambiguous position) abstains. Cross-language verifier accepts
judge the OVERLAPPING segments' text, not the whole padded window. When a
backend provides NO usable segment timestamps, a text-only window match can
never be promoted to timing proof: the sample abstains (measured outcome)
and is counted, and abstained regions record
``semantic_content_present_in_window`` while accepted regions record
``timing_correspondence_verified``.

Cross-language timing-ambiguity gate (M2, fourth review): the same-language path
abstains when the matching dialogue appears both in the proposed interval and in
the padding, and the cross-language path must carry the same burden. A verifier
"match" over the PRECISE in-interval text is accepted only after a BOUNDED extra
verification (capped by ``MAX_EXTRA_VERIFIER_CALLS``, counted in
``verifier_calls``/``semantic_seconds``) probes each near-duplicate ORIGINAL-
LANGUAGE occurrence found in the padding: a competitor the verifier ALSO matches
makes the two occurrences indistinguishable and ABSTAINS
(``cross_language_ambiguity``, mirroring ``multi_utterance_ambiguity`` and
recording content-present); a competitor the verifier does NOT match leaves the
in-interval match unambiguous (accept); a probe with no usable verdict, or more
competitors than the cap allows, fails closed (``cross_language_ambiguity_budget``,
an unprobed occurrence — not a matched-both claim). Competitors are detected PER
SEGMENT: each precise in-interval utterance is compared against every padding
segment, the joined padding group, and every broad boundary-crossing segment, so
a repeated line is never diluted by being joined against unrelated in-interval
speech. Near-duplicate detection compares transcript<->transcript text after
``_dup_normalize`` (NFKC + whitespace/punctuation/symbol stripping + casefold) at
the INCLUSIVE ``PAD_NEAR_DUPLICATE_RATIO`` floor, with a verbatim-substring
containment rule for a short line embedded in a longer segment — cross-language
transcript<->subtitle lexical scores remain non-evidence, so a valid translation
is never rejected for words differing from the transcript. A single ASR segment
that crosses the interval boundary into the padding mixes in-interval with
past-interval speech and is NOT precise time-local evidence for one utterance: a
match supported only by such a broad segment abstains (``broad_segment_matches``)
instead of auto-accepting.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np

from .asr import MISSING_CONFIDENCE_SENTINEL
from .manifests import AcceptanceRecord, CaseManifest, ProposalRecord
from .media import extract_audio_window

PAD_US = 1_500_000
MIN_MATCH_RATIO = 0.45
MIN_CONFIDENCE = -0.5
SCRIPT_MAJORITY = 0.5
# F03: documented time-local tolerance. A segment supports an automatic
# accept only when it positively overlaps the proposed subtitle interval
# widened by this slack. It is NOT the 1.5 s window padding (padding presence
# is content evidence only, never timing proof).
TIMING_TOLERANCE_US = 500_000
# M2 (fourth review): near-duplicate threshold for the cross-language timing
# ambiguity gate. A padding/broad ASR candidate is a "near-duplicate" of an
# in-interval utterance when, after ``_dup_normalize`` (NFKC + strip
# whitespace/punctuation/symbols + casefold, so spacing and full/half-width and
# punctuation noise are neutralized), the lexical ``semantic_match`` of the two
# ORIGINAL-LANGUAGE (ASR transcript) texts reaches this ratio — the same-language
# transcript<->transcript comparison is meaningful (both are source-language
# text), unlike a cross-language transcript<->subtitle lexical score, which
# stays non-evidence. The floor is INCLUSIVE (``>= 0.80`` qualifies). A short
# utterance repeated VERBATIM inside a longer (e.g. broad) segment also counts
# via the documented substring-containment rule, because a substring of a longer
# span falls below the floor yet is the SAME line. A 0.80 token/character-bigram
# Dice floor flags repeated or near-identical lines (the ambiguity trigger)
# while ignoring unrelated padding dialogue; it never lowers F03's accept/reject
# gates.
PAD_NEAR_DUPLICATE_RATIO = 0.80
# M2: minimum normalized length for the verbatim-substring near-duplicate rule.
# 2 characters is the shortest common CJK word unit (a repeat that short is a
# genuine ambiguous anchor); a short Latin fragment over-triggering is accepted
# as a bounded extra-probe cost (it only requests verification, never accepts).
NEAR_DUPLICATE_SUBSTRING_MIN_CHARS = 2
# M2: hard cap on the bounded ADDITIONAL semantic-verifier calls made per sample
# to disambiguate a competing near-duplicate padding occurrence. Extra probes
# are counted in verifier_calls/semantic_seconds exactly like run_verifier. If a
# sample has more competitors than this cap allows, it fails closed (abstains)
# rather than auto-accepting an unprobed position.
MAX_EXTRA_VERIFIER_CALLS = 2
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


def _transcript_reliable(result) -> bool | None:
    """Usable-transcript gate shared by every language path for automatic acceptance.

    True  -> the transcription carries usable reliability evidence
             (``confidence >= MIN_CONFIDENCE``);
    False -> it reports low reliability (usable signal, below threshold);
    None  -> this backend/result carries NO usable reliability signal at all
             (the documented ``-1.0`` no-metric sentinel = absence of evidence,
             a missing attribute, or a signal this helper cannot interpret).

    Only True may support an automatic accept; False and None abstain (unknown
    signals NEVER auto-accept). A future backend with a different reliability
    signal (per-token score, status flag, ...) slots in here without touching
    the decision paths.
    """
    confidence = getattr(result, "confidence", None)
    if confidence is None:
        return None
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return None
    if confidence == MISSING_CONFIDENCE_SENTINEL:
        return None
    return bool(confidence >= MIN_CONFIDENCE)


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


def _dup_normalize(text: str) -> str:
    """Deterministic near-duplicate comparison form for transcript<->transcript text.

    NFKC-normalizes (folding full-width/half-width forms and compatibility
    variants), then keeps only letters, combining marks and numbers
    (``unicodedata.category`` first letter ``L``/``M``/``N``), dropping
    whitespace and every punctuation/symbol/control character, then case-folds.
    This neutralizes surface noise that must NOT hide a repeated line: Japanese
    punctuation (``、`` ``！``), spacing, and full/half-width forms all collapse.
    It deliberately folds NO words and translates nothing — 私 vs わたし (kanji
    vs hiragana of the same word) stay distinct, so this is a conservative
    surface-normalizer for detecting the SAME verbatim/near-verbatim line, not a
    semantic-identity test.
    """
    nfkc = unicodedata.normalize("NFKC", text)
    return "".join(
        ch for ch in nfkc if unicodedata.category(ch)[0] in ("L", "M", "N")
    ).casefold()


def _near_duplicate(a: str, b: str) -> bool:
    """True when two ORIGINAL-LANGUAGE (ASR transcript) texts are near-duplicates.

    M2 cross-language ambiguity gate: this compares transcript<->transcript,
    i.e. both sides are source-language text, so the lexical Dice coefficient
    (``semantic_match``) is a meaningful near-duplicate measure — repeated or
    near-identical lines score high, unrelated padding dialogue scores low.
    Cross-language transcript<->SUBTITLE lexical scores are deliberately NOT
    used here (they are never evidence across languages); the semantic verifier
    decides semantic correspondence, this helper only flags which padding
    occurrences need that bounded extra verification.

    Both texts go through ``_dup_normalize`` first (whitespace/punctuation/
    full-half-width noise neutralized). A pair qualifies when the Dice reaches the
    INCLUSIVE floor ``PAD_NEAR_DUPLICATE_RATIO``, OR when the SHORTER normalized
    text is a VERBATIM substring of the longer one (>= 2 chars): a repeated line
    embedded in a longer/broader segment is the SAME utterance even though its
    substring Dice falls below the floor. Deterministic, no model, no translation.
    """
    na, nb = _dup_normalize(a), _dup_normalize(b)
    if not na or not nb:
        return False
    if semantic_match(na, nb) >= PAD_NEAR_DUPLICATE_RATIO:
        return True
    short, long = (na, nb) if len(na) <= len(nb) else (nb, na)
    return len(short) >= NEAR_DUPLICATE_SUBSTRING_MIN_CHARS and short in long


def cue_region(cue_start_us: int, regions: list[dict]) -> int | None:
    for i, r in enumerate(regions):
        end = r.get("end_us")
        if cue_start_us >= r["start_us"] and (end is None or cue_start_us <= end):
            return i
    return None


def _window_segments(result) -> list[dict]:
    """Usable per-segment timestamps from a transcription (F03), if any.

    Timestamps are relative to the extracted window start; segments without
    interpretable non-inverted times are dropped (missing timestamps are
    MISSING evidence, never guessed positions).
    """
    segs = getattr(result, "segments", None)
    if not segs:
        return []
    out: list[dict] = []
    for seg in segs:
        try:
            start_us = int(seg["start_us"])
            end_us = int(seg["end_us"])
        except (KeyError, TypeError, ValueError):
            continue
        if start_us < 0 or end_us < start_us:
            continue
        out.append(
            {"start_us": start_us, "end_us": end_us, "text": str(seg.get("text", ""))}
        )
    return sorted(out, key=lambda s: s["start_us"])


def _segment_timing(
    subtitle_text: str,
    segments: list[dict],
    win_off_us: int,
    start_us: int,
    end_us: int,
    tol_us: int = TIMING_TOLERANCE_US,
) -> dict:
    """Split window segments into in-interval vs padding; match each side (F03).

    A segment is IN the proposed interval only when it POSITIVELY intersects
    ``[start_us - tol_us, end_us + tol_us]`` (the documented time-local
    slack; touching-at-a-point adjacency is not overlap). Candidate joins
    cover a cue spanning two consecutive in-segments; a join never mixes an
    in-segment with a padding segment, so padding text can never lend
    time-local support.

    M2 (fourth review) split within the overlap set: a segment is PRECISE
    time-local only when its whole span stays inside the tolerant interval
    (``media_start >= start_us - tol_us and media_end <= end_us + tol_us``).
    A segment that intersects the tolerant interval but runs PAST it on either
    side (into the padding) is a BROAD segment: its text mixes in-interval
    speech with past-interval speech and is NOT precise evidence for one
    specific utterance. ``precise_*``/``broad_*`` are reported alongside the
    existing ``overlap``/``padding`` fields so the same-language ratio logic
    (which joins the whole overlap set) stays unchanged.

    ``precise_texts``/``padding_texts``/``broad_texts`` expose the PER-SEGMENT
    texts (plus the joined ``precise_overlap_text``) so ``probe_padding_ambiguity``
    can compare EACH precise in-interval utterance against EACH padding segment,
    the joined padding group, and each broad segment — a near-duplicate is never
    diluted by being joined against unrelated in-interval speech. Text
    normalization for that comparison is ``_dup_normalize`` (whitespace/
    punctuation/full-half-width neutralized).
    """
    overlap: list[dict] = []
    padding: list[dict] = []
    precise: list[dict] = []
    broad: list[dict] = []
    for seg in segments:
        media_start = win_off_us + seg["start_us"]
        media_end = win_off_us + seg["end_us"]
        if media_start < end_us + tol_us and media_end > start_us - tol_us:
            overlap.append(seg)
            if media_start >= start_us - tol_us and media_end <= end_us + tol_us:
                precise.append(seg)
            else:
                broad.append(seg)
        else:
            padding.append(seg)

    def best(cands: list[list[dict]]) -> float:
        score = 0.0
        for cand in cands:
            joined = " ".join(s["text"] for s in cand)
            score = max(score, semantic_match(subtitle_text, joined))
        return score

    in_cands: list[list[dict]] = [[s] for s in overlap]
    if len(overlap) > 1:
        in_cands.append(overlap)
        in_cands += [overlap[i : i + 2] for i in range(len(overlap) - 1)]
    pad_cands: list[list[dict]] = [[s] for s in padding]
    if len(padding) > 1:
        pad_cands.append(padding)
    return {
        "in_ratio": best(in_cands) if in_cands else 0.0,
        "padding_ratio": best(pad_cands) if pad_cands else 0.0,
        "n_overlap": len(overlap),
        "overlap_text": " ".join(s["text"] for s in overlap),
        "n_precise_overlap": len(precise),
        "precise_overlap_text": " ".join(s["text"] for s in precise),
        "precise_texts": [s["text"] for s in precise],
        "broad_texts": [s["text"] for s in broad],
        "padding_texts": [s["text"] for s in padding],
    }


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

    F03 timing-correspondence gate: window extraction covers the proposed
    interval plus 1.5 s padding on each side, so a transcript of the whole
    window proves only that matching speech exists NEARBY. Automatic
    acceptance requires time-local evidence: an ASR segment with usable
    timestamps that positively overlaps the proposed interval within
    TIMING_TOLERANCE_US (cross-language accepts are decided on the
    overlapping segments' text). Matches found only in the padding, matches
    that are ambiguous between interval and padding (repeated/adjacent
    dialogue), and windows whose backend reports no usable segment
    timestamps all ABSTAIN — text presence in the enlarged window is recorded
    as ``semantic_content_present_in_window`` and never promoted to
    ``timing_correspondence_verified``. This stays a B1-targeted experiment;
    no forced-alignment pipeline is introduced.

    M2 (fourth review) closes the cross-language half of that gate: a verifier
    "match" over the PRECISE in-interval text auto-accepts only when a bounded
    extra verification rules out a near-duplicate ORIGINAL-LANGUAGE occurrence
    in the padding. Competitors are detected PER SEGMENT (each precise
    in-interval utterance vs every padding segment, the joined padding group,
    and every broad boundary-crossing segment), with ``_dup_normalize``
    neutralizing spacing/punctuation/full-half-width noise at the inclusive
    ``PAD_NEAR_DUPLICATE_RATIO`` floor plus a verbatim-substring rule. An
    indistinguishable competitor, a probe with no usable verdict, a competitor
    count over the cap, or a broad boundary-crossing segment as the sole
    time-local source all abstain, never accept, so cross-language acceptance
    requires unambiguous evidence that the matching utterance occurred at the
    proposed time. Genuinely unique in-interval matches keep the single-call
    accept.

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
    # F07 (third review): semantic-verification wall time and call counts are
    # tracked SEPARATELY; asr_seconds is transcription-only so component costs
    # compare fairly.
    semantic_seconds = 0.0
    verifier_calls = 0
    verdicts: dict[int, list[str]] = {}
    no_verifier_cross_lang = 0
    verifier_no_verdict = 0
    identity_unknown_abstentions = 0
    low_confidence_abstentions = 0
    timing_evidence_unavailable = 0
    padding_only_matches = 0
    multi_utterance_ambiguity = 0
    timing_unverified_match = 0
    # M2 (fourth review): cross-language timing-ambiguity gates.
    cross_language_ambiguity = 0  # matching dialogue in-interval AND near-duplicate in padding (verifier matched both)
    cross_language_ambiguity_budget = (
        0  # competing occurrences exceed the extra-verification cap -> fail-closed
    )
    broad_segment_matches = (
        0  # sole time-local source is a broad segment crossing the boundary
    )
    region_content_present: dict[int, bool] = {}
    mock_verifier_used = False
    audio_identity = normalize_language(language)
    subtitle_identity = normalize_language(subtitle_language)
    same_identity = (
        audio_identity is not None
        and subtitle_identity is not None
        and audio_identity == subtitle_identity
    )

    def _query_verifier(subtitle_text: str, transcript_text: str):
        """One raw verifier round-trip; counts calls/seconds (F07 separation)."""
        nonlocal semantic_seconds, verifier_calls
        verifier_calls += 1
        sv = verifier.verdict(
            subtitle_text, transcript_text, subtitle_language, language
        )
        semantic_seconds += sv.seconds
        return sv

    def run_verifier(
        region: int,
        subtitle_text: str,
        transcript_text: str,
        reliable: bool | None,
        timing_verified: bool,
        broad: bool = False,
    ) -> str:
        """Send one sample to the semantic verifier boundary and RETURN its verdict.

        The verifier is translation-tolerant and receives the RESOLVED language
        hints (never a hardcoded "und"). The caller appends the returned verdict
        to ``verdicts``. match + usable transcript reliability (F07 gate) +
        PRECISE time-local evidence (F03: the judged transcript text lies inside
        the proposed interval, not the whole padded window) -> "accept"; a match
        whose only evidence is the padded window is ``semantic_content_present_in_window``
        and abstains as ``timing_unverified_match``; a match supported ONLY by a
        broad ASR segment that crosses the proposed-interval boundary (M2: it
        mixes in-interval speech with past-interval speech, so it localizes no
        single utterance) abstains as ``broad_segment_matches``, never accepts.
        no_match -> "reject" (verifier evidence, not an acceptance path);
        unknown/exception -> abstain (no usable verdict)."""
        nonlocal verifier_no_verdict, low_confidence_abstentions
        nonlocal mock_verifier_used, timing_unverified_match, broad_segment_matches
        try:
            sv = _query_verifier(subtitle_text, transcript_text)
        except Exception as exc:  # noqa: BLE001 -- verifier boundary failures abstain
            verifier_no_verdict += 1
            (scratch_dir / "asr_errors.log").open("a", encoding="utf-8").write(
                f"{cid}: semantic verifier: {exc}\n"
            )
            return "abstain"
        if sv.mock:
            mock_verifier_used = True
            (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                f"{cid}: mock semantic verifier used; test-only\n"
            )
        if sv.verdict == "match":
            if reliable is not True:
                low_confidence_abstentions += 1
                (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                    f"{cid}: verifier match not accepted: ASR reliability signal "
                    "missing/unusable; abstained\n"
                )
                return "abstain"
            if not timing_verified:
                region_content_present[region] = True
                if broad:
                    broad_segment_matches += 1
                    (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                        f"{cid}: a broad ASR segment crosses the proposed interval "
                        "boundary and mixes in-interval with past-interval speech; "
                        "it does not localize the matched utterance "
                        "(semantic_content_present_in_window, timing correspondence "
                        "unverified); abstained\n"
                    )
                else:
                    timing_unverified_match += 1
                    (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                        f"{cid}: verifier match over the padded window only: "
                        "semantic_content_present_in_window, timing correspondence "
                        "unverified; abstained\n"
                    )
                return "abstain"
            return "accept"
        elif sv.verdict == "no_match":
            return "reject"
        verifier_no_verdict += 1
        return "abstain"

    def probe_padding_ambiguity(region: int, subtitle_text: str, timing: dict) -> str:
        """Bounded extra verification of competing near-duplicate occurrences (M2).

        An in-interval verifier "match" fixes the proposed timing only when NO
        original-language near-duplicate of that utterance also occurs in the
        padding. Competitors are matched PER SEGMENT, not only against the joined
        in-interval text: each PRECISE in-interval segment (and the joined precise
        text) is a probe target, and each PADDING candidate — every individual
        padding segment, the full joined padding group (the split-repeat geometry,
        mirroring ``_segment_timing``'s ``pad_cands`` join), and every broad
        boundary-crossing segment — qualifies when it near-duplicates ANY precise
        in-interval utterance. Each qualifying competitor is probed with the
        semantic verifier (capped by ``MAX_EXTRA_VERIFIER_CALLS``, counted in
        verifier_calls/semantic_seconds like every other verifier call): a
        competitor the verifier ALSO matches means the in-interval and padding
        occurrences are indistinguishable -> ABSTAIN (``cross_language_ambiguity``,
        mirroring the same-language ``multi_utterance_ambiguity`` gate, recording
        content-present); a competitor the verifier does NOT match leaves the
        in-interval match unambiguous; a probe with no usable verdict fails closed
        (abstain); and when there are more competitors than the cap allows, the
         sample fails closed as ``cross_language_ambiguity_budget`` (an
         UNPROBED competing occurrence, not a matched-both result). Every
         abstention here records ``semantic_content_present_in_window`` (the
         in-interval verifier "match" already proved the content is present; only
         its position is ambiguous), matching the ``timing_unverified_match`` and
         same-language ambiguity convention. With no near-duplicate competitor it
         returns "accept" at zero extra cost. Returns the final verdict to record
         ("accept" or "abstain")."""
        nonlocal cross_language_ambiguity, cross_language_ambiguity_budget
        nonlocal verifier_no_verdict, mock_verifier_used
        in_candidates: list[str] = []
        for t in list(timing["precise_texts"]) + [timing["precise_overlap_text"]]:
            if t and t not in in_candidates:
                in_candidates.append(t)
        pad_texts = timing["padding_texts"]
        pad_candidates: list[str] = list(pad_texts)
        if len(pad_texts) > 1:
            pad_candidates.append(" ".join(pad_texts))
        pad_candidates += list(timing["broad_texts"])
        competitors: list[str] = []
        for cand in pad_candidates:
            if not cand or cand in competitors:
                continue
            if any(_near_duplicate(in_t, cand) for in_t in in_candidates):
                competitors.append(cand)
        if not competitors:
            return "accept"
        used = 0
        for comp in competitors:
            if used >= MAX_EXTRA_VERIFIER_CALLS:
                cross_language_ambiguity_budget += 1
                region_content_present[region] = True
                (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                    f"{cid}: competing near-duplicate occurrence(s) in the window "
                    "padding exceed the bounded extra-verification budget; the "
                    "position was NOT disambiguated; fail-closed abstain (no "
                    "verifier matched-both claim)\n"
                )
                return "abstain"
            used += 1
            try:
                sv = _query_verifier(subtitle_text, comp)
            except Exception as exc:  # noqa: BLE001 -- verifier boundary failures abstain
                verifier_no_verdict += 1
                region_content_present[region] = True
                (scratch_dir / "asr_errors.log").open("a", encoding="utf-8").write(
                    f"{cid}: cross-language padding-ambiguity probe: {exc}\n"
                )
                return "abstain"
            if sv.mock:
                mock_verifier_used = True
                (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                    f"{cid}: mock semantic verifier used; test-only\n"
                )
            if sv.verdict == "match":
                cross_language_ambiguity += 1
                region_content_present[region] = True
                (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                    f"{cid}: the matching dialogue occurs in the proposed interval "
                    "AND as a near-duplicate in the window padding, and the "
                    "semantic verifier matched both occurrences; utterance "
                    "position ambiguous; abstained\n"
                )
                return "abstain"
            if sv.verdict == "no_match":
                continue
            verifier_no_verdict += 1
            region_content_present[region] = True
            return "abstain"
        return "accept"

    def cross_lang_route(
        region: int,
        subtitle_text: str,
        timing: dict | None,
        result,
        reliable: bool | None,
    ) -> None:
        """Verifier-decided acceptance path carrying the M2 timing-ambiguity gates.

        Shared by the cross-language branch and the unverified-identity verifier
        fallback so a verifier accept always has the same evidence burden: the
        verifier judges the PRECISE in-interval segments, a match is accepted
        only after the bounded padding near-duplicate probe rules out competing
        occurrences, a match supported only by a broad boundary-crossing segment
        abstains, and a padded-window match with no in-interval utterance
        abstains."""
        nonlocal no_verifier_cross_lang
        if verifier is None:
            verdicts.setdefault(region, []).append("abstain")
            no_verifier_cross_lang += 1
            return
        if timing is not None and timing["n_precise_overlap"] > 0:
            verdict = run_verifier(
                region,
                subtitle_text,
                timing["precise_overlap_text"],
                reliable,
                timing_verified=True,
            )
            if verdict == "accept":
                verdict = probe_padding_ambiguity(region, subtitle_text, timing)
            verdicts.setdefault(region, []).append(verdict)
        elif timing is not None and timing["n_overlap"] > 0:
            verdicts.setdefault(region, []).append(
                run_verifier(
                    region,
                    subtitle_text,
                    result.text,
                    reliable,
                    timing_verified=False,
                    broad=True,
                )
            )
        else:
            verdicts.setdefault(region, []).append(
                run_verifier(
                    region, subtitle_text, result.text, reliable, timing_verified=False
                )
            )

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
        reliable = _transcript_reliable(result)
        segments = _window_segments(result)
        win_off_us = max(0, start_us - PAD_US)
        timing = (
            _segment_timing(subtitle_text, segments, win_off_us, start_us, end_us)
            if segments
            else None
        )
        if result.mock:
            verdicts.setdefault(region, []).append("abstain")
            (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                f"{cid}: mock transcriber used; verdict forced to abstain\n"
            )
        elif is_cross_language(subtitle_text, result.text, language, subtitle_language):
            # Lexical score is never accept-support and never reject evidence
            # across languages; only the semantic verifier boundary decides.
            # F03/M2: the verifier judges the PRECISE in-interval segments; a
            # verifier match auto-accepts only after the bounded padding
            # near-duplicate probe rules out a competing occurrence, a match
            # supported only by a broad boundary-crossing segment abstains, and
            # a padded-window match with no in-interval utterance abstains.
            # cross_lang_route applies every gate; no_match stays a
            # verifier-evidence reject, the F07 reliability gate applies to the
            # ACCEPT verdict, and the no-verifier abstention is preserved.
            cross_lang_route(region, subtitle_text, timing, result, reliable)
        elif reliable is not True:
            # Shared quality gate (F07): a lexical-path accept requires a usable
            # ASR reliability signal; a missing sentinel / low / uninterpretable
            # signal is NOT accept evidence. Reject stays available only with
            # usable reliability on a verified same-language pair (below).
            verdicts.setdefault(region, []).append("abstain")
            low_confidence_abstentions += 1
            (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                f"{cid}: ASR reliability signal missing/unusable; abstained\n"
            )
        elif timing is None:
            # F03: the backend reported no usable segment timestamps. Text
            # presence in the enlarged padded window is NOT timing proof; the
            # sample abstains (never auto-accept, and never a padded-window
            # text-only reject either).
            verdicts.setdefault(region, []).append("abstain")
            timing_evidence_unavailable += 1
            (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                f"{cid}: ASR backend provided no segment timestamps; text "
                "presence in the padded window is content evidence only "
                "(semantic_content_present_in_window), not "
                "timing_correspondence_verified; abstained\n"
            )
        elif (
            timing["in_ratio"] >= MIN_MATCH_RATIO
            and timing["padding_ratio"] < MIN_MATCH_RATIO
        ):
            # F03: a matching utterance overlaps the proposed interval within
            # the documented tolerance and NO padding-only match competes for
            # the same text: timing correspondence verified -> accept.
            verdicts.setdefault(region, []).append("accept")
        elif timing["in_ratio"] >= MIN_MATCH_RATIO:
            # Matches BOTH in-interval and in padding: repeated/adjacent
            # dialogue makes the position ambiguous; abstain, keep original.
            verdicts.setdefault(region, []).append("abstain")
            multi_utterance_ambiguity += 1
            region_content_present[region] = True
            (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                f"{cid}: matching utterances in the proposed interval AND in "
                "the window padding; position ambiguous; abstained\n"
            )
        elif timing["padding_ratio"] >= MIN_MATCH_RATIO:
            # The matching line is spoken only in the 1.5 s padding outside
            # the proposed interval: content present, timing correspondence
            # NOT verified (this is exactly the wrongly-shifted-cue accept the
            # review reproduced); abstain.
            verdicts.setdefault(region, []).append("abstain")
            padding_only_matches += 1
            region_content_present[region] = True
            (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                f"{cid}: matching utterance found only in window padding; "
                "semantic_content_present_in_window, timing correspondence "
                "unverified; abstained\n"
            )
        elif same_identity:
            # Verified same-language pair with usable reliability and segment
            # evidence: NO utterance in the window (in-interval or padding)
            # matches the subtitle text -> genuine CONTRADICTION evidence.
            verdicts.setdefault(region, []).append("reject")
        elif verifier is not None:
            # Identity not verified: low overlap is NOT sufficient negative
            # evidence. Route to the verifier when configured (never reject on an
            # unverified identity without verifier evidence). cross_lang_route
            # applies the same M2 gates: a verifier accept requires precise
            # in-interval evidence AND a padding near-duplicate probe that
            # rules out a competing occurrence; broad-segment and padded-window
            # matches abstain.
            cross_lang_route(region, subtitle_text, timing, result, reliable)
        else:
            verdicts.setdefault(region, []).append("abstain")
            identity_unknown_abstentions += 1

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
            # F03: an accepted region carries explicit evidence labels — the
            # matching utterances were time-local to the proposed interval
            # (within TIMING_TOLERANCE_US), not merely present in the window.
            accepted_regions.append(
                {
                    **region,
                    "reason": (
                        "all samples semantically matched with time-local ASR "
                        "segment evidence at the proposed interval" + mock_tag
                    ),
                    "timing_correspondence_verified": True,
                    "semantic_content_present_in_window": True,
                }
            )
            for cid, (ps, pe) in proposal.proposed_times_us.items():
                if cue_region(corrupted_times[cid][0], [region]) == 0:
                    accepted_times[cid] = (ps, pe)
        else:
            abstained = {
                **region,
                "reason": "mixed samples (accept+abstain); insufficient evidence",
            }
            if region_content_present.get(i):
                abstained["semantic_content_present_in_window"] = True
                abstained["timing_correspondence_verified"] = False
            abstained_regions.append(abstained)

    usable_verdicts = sum(
        1 for vs in verdicts.values() for v in vs if v in ("accept", "reject")
    )
    notes_parts = [
        "sampling: edges/split-sides/largest-changes/fixed+seeded-random controls",
        "mock runs never accepted",
    ]
    if low_confidence_abstentions:
        notes_parts.append(
            f"{low_confidence_abstentions} samples: ASR transcript reliability "
            "signal missing/unusable (no-metric sentinel -1.0, below "
            "MIN_CONFIDENCE, or unavailable for this backend); automatic "
            "acceptance requires usable reliability evidence in every language "
            "path; abstained (targeted re-sampling is a later feature keyed on "
            "this note)"
        )
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
    if timing_evidence_unavailable:
        notes_parts.append(
            f"{timing_evidence_unavailable} samples: ASR backend provided no "
            "usable segment timestamps for the padded window; text presence in "
            "the enlarged window is semantic_content_present_in_window, never "
            "timing_correspondence_verified; abstained (a bounded per-segment "
            "verifier path consumes verbose_json timestamps; a full forced-"
            "aligner pipeline is explicitly out of scope for B1-VA)"
        )
    if padding_only_matches:
        notes_parts.append(
            f"{padding_only_matches} samples: the matching utterance was found "
            "only in the 1.5 s window padding outside the proposed interval "
            "(semantic_content_present_in_window, timing correspondence "
            "unverified — the wrongly-shifted-cue accept the review "
            "reproduced); abstained"
        )
    if multi_utterance_ambiguity:
        notes_parts.append(
            f"{multi_utterance_ambiguity} samples: the subtitle text matched "
            "both at the proposed interval and in the window padding "
            "(repeated/adjacent dialogue; utterance position ambiguous); "
            "abstained"
        )
    if timing_unverified_match:
        notes_parts.append(
            f"{timing_unverified_match} cross-language samples: the semantic "
            "verifier matched the padded window without time-local segment "
            "evidence; abstained (never accepted)"
        )
    if cross_language_ambiguity:
        notes_parts.append(
            f"{cross_language_ambiguity} cross-language samples: the matching "
            "dialogue occurs at the proposed interval AND as a near-duplicate in "
            "the window padding, and the semantic verifier matched both "
            "occurrences (repeated dialogue; utterance position ambiguous); "
            "abstained (never auto-accepted)"
        )
    if cross_language_ambiguity_budget:
        notes_parts.append(
            f"{cross_language_ambiguity_budget} cross-language samples: competing "
            "near-duplicate padding occurrence(s) exceeded the bounded "
            "extra-verification budget; the position was NOT disambiguated by any "
            "verifier verdict (fail-closed, no verifier matched-both claim); "
            "abstained (never auto-accepted)"
        )
    if broad_segment_matches:
        notes_parts.append(
            f"{broad_segment_matches} cross-language samples: the verifier match "
            "rested on a broad ASR segment crossing the proposed-interval "
            "boundary (in-interval speech mixed with past-interval speech; it "
            "localizes no single utterance — synthetic broad segments are not "
            "forced-alignment evidence); abstained (never accepted)"
        )
    if mock_verifier_used:
        notes_parts.append("mock semantic verifier used (test-only)")
    no_evidence = (
        no_verifier_cross_lang
        + verifier_no_verdict
        + identity_unknown_abstentions
        + timing_evidence_unavailable
        + timing_unverified_match
        + cross_language_ambiguity
        + cross_language_ambiguity_budget
        + broad_segment_matches
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
        semantic_seconds=semantic_seconds,
        verifier_calls=verifier_calls,
        notes="; ".join(notes_parts),
    )
