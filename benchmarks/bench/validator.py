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
"""

from __future__ import annotations

import re
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
    """
    overlap: list[dict] = []
    padding: list[dict] = []
    for seg in segments:
        media_start = win_off_us + seg["start_us"]
        media_end = win_off_us + seg["end_us"]
        if media_start < end_us + tol_us and media_end > start_us - tol_us:
            overlap.append(seg)
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
    region_content_present: dict[int, bool] = {}
    mock_verifier_used = False
    audio_identity = normalize_language(language)
    subtitle_identity = normalize_language(subtitle_language)
    same_identity = (
        audio_identity is not None
        and subtitle_identity is not None
        and audio_identity == subtitle_identity
    )

    def run_verifier(
        region: int,
        subtitle_text: str,
        transcript_text: str,
        reliable: bool | None,
        timing_verified: bool,
    ) -> None:
        """Send one sample to the semantic verifier boundary and record its verdict.

        The verifier is translation-tolerant and receives the RESOLVED language
        hints (never a hardcoded "und"). match + usable transcript reliability
        (F07 gate) + time-local evidence (F03: the judged transcript text
        covers the proposed interval, not the whole padded window) -> accept;
        a match without time-local evidence is
        ``semantic_content_present_in_window`` and abstains, never accepts
        (recorded as its own abstention counter); no_match -> reject (verifier
        evidence, not an acceptance path); unknown/exception -> abstain (no
        usable verdict)."""
        nonlocal semantic_seconds, verifier_no_verdict, low_confidence_abstentions
        nonlocal mock_verifier_used, timing_unverified_match, verifier_calls
        verifier_calls += 1
        try:
            sv = verifier.verdict(
                subtitle_text, transcript_text, subtitle_language, language
            )
            semantic_seconds += sv.seconds
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
            if reliable is not True:
                verdicts.setdefault(region, []).append("abstain")
                low_confidence_abstentions += 1
                (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                    f"{cid}: verifier match not accepted: ASR reliability signal "
                    "missing/unusable; abstained\n"
                )
            elif not timing_verified:
                verdicts.setdefault(region, []).append("abstain")
                timing_unverified_match += 1
                region_content_present[region] = True
                (scratch_dir / "asr_notes.log").open("a", encoding="utf-8").write(
                    f"{cid}: verifier match over the padded window only: "
                    "semantic_content_present_in_window, timing correspondence "
                    "unverified; abstained\n"
                )
            else:
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
            # F03: the verifier judges the segments that overlap the proposed
            # interval (time-local candidates). With no in-interval utterance
            # at all, a padded-window match proves only
            # semantic_content_present_in_window and abstains in run_verifier.
            # The F07 reliability gate applies to the verifier's ACCEPT verdict
            # inside run_verifier; no_match stays a verifier-evidence reject.
            if verifier is None:
                verdicts.setdefault(region, []).append("abstain")
                no_verifier_cross_lang += 1
                continue
            if timing is not None and timing["n_overlap"] > 0:
                run_verifier(
                    region,
                    subtitle_text,
                    timing["overlap_text"],
                    reliable,
                    timing_verified=True,
                )
            else:
                run_verifier(
                    region,
                    subtitle_text,
                    result.text,
                    reliable,
                    timing_verified=False,
                )
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
            # evidence. Route to the verifier when configured, judging the
            # in-interval candidates when available (never reject on an
            # unverified identity without verifier evidence).
            if timing["n_overlap"] > 0:
                run_verifier(
                    region,
                    subtitle_text,
                    timing["overlap_text"],
                    reliable,
                    timing_verified=True,
                )
            else:
                run_verifier(
                    region,
                    subtitle_text,
                    result.text,
                    reliable,
                    timing_verified=False,
                )
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
    if mock_verifier_used:
        notes_parts.append("mock semantic verifier used (test-only)")
    no_evidence = (
        no_verifier_cross_lang
        + verifier_no_verdict
        + identity_unknown_abstentions
        + timing_evidence_unavailable
        + timing_unverified_match
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
