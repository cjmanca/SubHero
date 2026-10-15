"""M2: cross-language timing-ambiguity gate.

The same-language F03 path abstains when the matching dialogue appears BOTH
at the proposed interval and in the padded window (repeated/adjacent lines make
the position ambiguous). The cross-language path previously accepted on a single
semantic-verifier "match" over the in-interval text WITHOUT checking that the
same original-language utterance does not also occur in the padding, and it
treated an ASR segment that spans interval AND padding as precise time-local
evidence for one specific utterance.

These regressions pin the corrective behaviour:

* correctly positioned translated dialogue (unique in-interval, no competing
  occurrence) keeps auto-accepting (positive control);
* matching original-language dialogue ONLY in the padding still abstains
  (F03 timing_verified=False path preserved);
* identical/repeated dialogue in-interval AND in the padding, verified as
  matching both, ABSTAINS (the plan's Japanese repeated-line example);
* a near-duplicate padding occurrence the verifier says does NOT match the
  subtitle stays ACCEPT (unambiguous; a translation whose surface words differ
  from the transcript is accepted on verifier evidence, never lexical words);
* unrelated padding dialogue accepts with NO extra verifier call (bounded
  additional verification only when a near-duplicate competitor exists);
* a single broad ASR segment crossing the interval boundary (it mixes the
  matched utterance with past-interval speech) ABSTAINS, never auto-accepts;
* a verifier match on a competitor that yields no usable verdict fails closed.

Verifier-call accounting is asserted so the bounded extra probes are counted in
verifier_calls/semantic_seconds while asr_calls stays transcription-only (F07
separation preserved).
"""

from __future__ import annotations

from pathlib import Path

from bench import validator
from bench.asr import MockSemanticVerifier, SemanticVerdict, Transcription
from bench.manifests import CaseManifest, ProposalRecord
from bench.validator import _near_duplicate, validate_proposal

SECOND = 1_000_000

EN_SUB = "I will protect this city."
JA_IN = "この街はわたしが守る"
JA_REPEAT = "この街はわたしが守る"  # identical repeated line (padding)
# Exact 0.80 floor pair (pinned by the boundary unit test; NOT used as a
# knife-edge accept fixture).
JA_NEG = "この街はわたしが守らない"  # "I do NOT protect this city"
# Margin fixtures for the accept (no_match-competitor) control: a longer shared
# prefix keeps the padding negation comfortably ABOVE the 0.80 floor.
JA_IN_MARGIN = "いつもこの街はわたしが守る"
JA_NEG_MARGIN = "いつもこの街はわたしが守らない"
JA_NEAR_NO_MATCH = JA_NEG  # kept name for the padding no_match competitor
JA_UNRELATED = "すばらしい天気だね"  # "lovely weather"
# Reviewer dilution geometries: a second, unrelated precise in-interval line and
# a punctuation/spacing + full-width noise repeat of the in-interval line.
JA_OTHER = "その本を読む"  # "read that book"
JA_NOISE_REPEAT = "この街は、わたしが 守る！"  # same line, punctuation/spacing only
JA_SPLIT_HEAD = "この街は"  # repeat split by ASR: head half ...
JA_SPLIT_TAIL = "わたしが守る"  # ... tail half


def _mk_case(original, proposal_times, regions, case_id):
    case = CaseManifest(
        case_id=case_id,
        source_id="S",
        scenario="S01",
        seed=1,
        track_id="ep",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": "S01"},
        transform={},
        expected_inverse={},
        injected_cue_deltas={cid: (0, 0) for cid in original},
        original_times_us=dict(original),
        true_breakpoints_us=[],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )
    proposal = ProposalRecord(
        case_id, "b1-px-fg", "1:1-order-preserving", regions, dict(proposal_times), []
    )
    return case, proposal


class _SegASR:
    """Non-mock fake ASR with canned per-key window text + segment timestamps.

    Segment timestamps are RELATIVE to the extracted window start, exactly like
    verbose_json segments of the window file.
    """

    def __init__(self, by_key: dict[str, tuple[str, list[dict]]], confidence=1.0):
        self.by_key = dict(by_key)
        self.confidence = confidence

    def transcribe_window(self, wav_path, language, key=None):
        text, segs = self.by_key[key]
        return Transcription(
            text=text,
            confidence=self.confidence,
            seconds=0.0,
            model="fake",
            mock=False,
            segments=list(segs) if segs else None,
        )


class _TranscriptVerifier:
    """Fake semantic verifier keyed by the TRANSCRIPT text it is asked to judge.

    This lets a test give a "match" for the in-interval utterance and a
    "no_match" for a near-duplicate padding occurrence, modelling a verifier
    that distinguishes the two occurrences by meaning (not surface identity).
    """

    def __init__(self, answers: dict[str, str]):
        self.answers = dict(answers)
        self.calls: list[tuple[str, str, str]] = []
        self.transcripts: list[str] = []

    def verdict(
        self,
        subtitle_text,
        transcript_text,
        subtitle_language_hint,
        transcript_language_hint,
    ):
        self.calls.append(
            (subtitle_text, subtitle_language_hint, transcript_language_hint)
        )
        self.transcripts.append(transcript_text)
        return SemanticVerdict(
            verdict=self.answers.get(transcript_text, "unknown"),
            seconds=0.05,
            model="fake-verify",
            mock=False,
        )


def _run_validate(
    tmp_path,
    monkeypatch,
    case,
    proposal,
    corrupted,
    cue_text,
    asr,
    language,
    verifier=None,
    subtitle_language="en",
):
    monkeypatch.setattr(validator, "extract_audio_window", lambda *a, **k: 0.1)
    return validate_proposal(
        case,
        proposal,
        "b1-px-fg",
        corrupted,
        cue_text,
        Path("fake.wav"),
        tmp_path / f"run-{case.case_id}",
        asr,
        language,
        1,
        verifier=verifier,
        subtitle_language=subtitle_language,
    )


def _seg(start_us, end_us, text):
    return {"start_us": start_us, "end_us": end_us, "text": text}


_SINGLE_REGION = [{"start_us": 0, "end_us": None, "offset_us": 0}]


# --- 1. correctly positioned translated dialogue (positive control) ------------


def test_unique_in_interval_translated_dialogue_accepts(tmp_path, monkeypatch):
    # In-interval precise line matches; the only padding line is unrelated.
    original = {"e1": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e1": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e1": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e1": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-uniq")
    verifier = MockSemanticVerifier({EN_SUB: "match"})
    asr = _SegASR(
        {
            "e1": (
                JA_IN + " " + JA_UNRELATED,
                [
                    _seg(1 * SECOND, 2 * SECOND, JA_IN),
                    _seg(3 * SECOND, 3 * SECOND + 500_000, JA_UNRELATED),
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.status == "success"
    assert len(acc.accepted_regions) == 1
    assert acc.accepted_regions[0]["timing_correspondence_verified"] is True
    assert acc.accepted_times_us["e1"] == proposal_times["e1"]


# --- 2. matching dialogue only in padding (F03 path preserved) -----------------


def test_matching_dialogue_only_in_padding_abstains(tmp_path, monkeypatch):
    # Proposal shifts the cue 2 s past the real speech; the line is audible only
    # in the 1.5 s padding window (no in-interval overlap at all).
    original = {"e2": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e2": (10 * SECOND, 11 * SECOND)}
    proposal_times = {"e2": (3 * SECOND, 4 * SECOND)}
    regions = [{"start_us": 0, "end_us": None, "offset_us": -7 * SECOND}]
    cue_text = {"e2": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, regions, "m2-pad")
    verifier = MockSemanticVerifier({EN_SUB: "match"})
    asr = _SegASR(
        {"e2": (JA_IN, [_seg(0, 500_000, JA_IN)])}  # window [1.5,5.5]: media clipped
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert (
        "1 cross-language samples: the semantic verifier matched the padded window "
        "without time-local segment evidence; abstained (never accepted)" in acc.notes
    )


# --- 3. repeated identical dialogue in-interval AND padding -> abstain ---------


def test_repeated_dialogue_inside_and_padding_abstains(tmp_path, monkeypatch):
    # Plan's Japanese example: "この街はわたしが守る" at the proposed time AND
    # identically in the padding; the verifier matches both -> position ambiguous.
    original = {"e3": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e3": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e3": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e3": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-rep")
    verifier = MockSemanticVerifier({EN_SUB: "match"})
    asr = _SegASR(
        {
            "e3": (
                JA_IN + " " + JA_REPEAT,
                [
                    _seg(1 * SECOND, 2 * SECOND, JA_IN),
                    _seg(3 * SECOND, 3 * SECOND + 500_000, JA_REPEAT),
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert len(acc.abstained_regions) == 1
    assert acc.abstained_regions[0]["semantic_content_present_in_window"] is True
    assert acc.abstained_regions[0]["timing_correspondence_verified"] is False
    notes_log = (tmp_path / "run-m2-rep" / "asr_notes.log").read_text(encoding="utf-8")
    assert "position ambiguous; abstained" in notes_log
    assert "near-duplicate in the window padding" in acc.notes


# --- 4. near-duplicate padding that does NOT match -> accept -------------------


def test_near_duplicate_padding_no_match_accepts(tmp_path, monkeypatch):
    # Padding near-duplicate "I do NOT protect this city" is a near-duplicate
    # transcript (same-language lexical) but the verifier says it does NOT
    # correspond to the subtitle; the in-interval match is therefore
    # unambiguous. Surface words (EN subtitle vs JA transcript) differ, so this
    # also proves acceptance never requires transcript words == subtitle words.
    original = {"e4": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e4": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e4": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e4": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-near")
    verifier = _TranscriptVerifier({JA_IN_MARGIN: "match", JA_NEG_MARGIN: "no_match"})
    asr = _SegASR(
        {
            "e4": (
                JA_IN_MARGIN + " " + JA_NEG_MARGIN,
                [
                    _seg(1 * SECOND, 2 * SECOND, JA_IN_MARGIN),
                    _seg(3 * SECOND, 3 * SECOND + 500_000, JA_NEG_MARGIN),
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.status == "success"
    assert len(acc.accepted_regions) == 1
    assert acc.accepted_regions[0]["timing_correspondence_verified"] is True
    assert acc.accepted_times_us["e4"] == proposal_times["e4"]
    # The bounded extra probe was made on the competing near-duplicate padding
    # occurrence: the in-interval utterance first, then the padding text.
    assert verifier.transcripts[0] == JA_IN_MARGIN
    assert JA_NEG_MARGIN in verifier.transcripts


# --- 5. unrelated padding -> accept with NO extra verifier call ----------------


def test_unrelated_padding_accepts_without_extra_call(tmp_path, monkeypatch):
    # Same positive geometry as scenario 1, asserting the boundedness rule:
    # extra verification is spent only when a near-duplicate competitor exists.
    original = {"e5": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e5": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e5": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e5": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-unrel")
    verifier = _TranscriptVerifier({JA_IN: "match", JA_UNRELATED: "no_match"})
    asr = _SegASR(
        {
            "e5": (
                JA_IN + " " + JA_UNRELATED,
                [
                    _seg(1 * SECOND, 2 * SECOND, JA_IN),
                    _seg(3 * SECOND, 3 * SECOND + 500_000, JA_UNRELATED),
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.status == "success"
    assert len(acc.accepted_regions) == 1
    assert acc.accepted_times_us["e5"] == proposal_times["e5"]
    # Single sample -> exactly one verifier call, no bounded extra probes.
    assert acc.verifier_calls == 1
    assert verifier.calls and len(verifier.calls) == 1


# --- 6. broad ASR segment crossing the interval boundary -> abstain ------------


def test_broad_segment_crossing_boundary_not_accepted(tmp_path, monkeypatch):
    # ONE ASR segment spans the proposed interval AND runs into the padding,
    # mixing the matched utterance with past-interval speech. Its verifier
    # "match" must NOT be promoted to a precise timing accept.
    original = {"e6": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e6": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e6": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e6": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-broad")
    verifier = MockSemanticVerifier({EN_SUB: "match"})
    asr = _SegASR(
        {
            "e6": (
                JA_IN + " " + JA_UNRELATED,
                [
                    # window [0,3.5]: media [1,4] clipped to [1,3.5] rel [1,3.5]
                    _seg(1 * SECOND, 3 * SECOND + 500_000, JA_IN + " " + JA_UNRELATED)
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert len(acc.abstained_regions) == 1
    assert acc.abstained_regions[0]["semantic_content_present_in_window"] is True
    notes_log = (tmp_path / "run-m2-broad" / "asr_notes.log").read_text(
        encoding="utf-8"
    )
    assert "broad" in notes_log and "crosses" in notes_log


# --- 7. verifier probe with no usable verdict fails closed --------------------


def test_competitor_probe_without_verdict_fails_closed(tmp_path, monkeypatch):
    # The in-interval utterance matches; the padding near-duplicate probe
    # returns no usable verdict (unknown) -> fail closed, never accept.
    original = {"e7": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e7": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e7": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e7": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-fail")
    # JA_IN matches; the padding near-duplicate JA_NEAR_NO_MATCH has NO canned
    # answer, so probing that competing occurrence yields an unusable verdict.
    verifier = _TranscriptVerifier({JA_IN: "match"})
    asr = _SegASR(
        {
            "e7": (
                JA_IN + " " + JA_NEAR_NO_MATCH,
                [
                    _seg(1 * SECOND, 2 * SECOND, JA_IN),
                    _seg(3 * SECOND, 3 * SECOND + 500_000, JA_NEAR_NO_MATCH),
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert "no usable verdict (unknown/failure)" in acc.notes
    # Fail-closed abstention still records content-present: the in-interval
    # verifier "match" proved the content, only its position stayed unresolved.
    assert len(acc.abstained_regions) == 1
    assert acc.abstained_regions[0]["semantic_content_present_in_window"] is True
    assert acc.abstained_regions[0]["timing_correspondence_verified"] is False


# --- 8. verifier-call accounting (F07 separation preserved) --------------------


def test_extra_padding_probe_calls_are_accounted(tmp_path, monkeypatch):
    # Scenario 3 with a transcript-keyed verifier so both occurrences can be
    # probed: the extra padding call is counted in verifier_calls/semantic_seconds
    # while asr_calls stays transcription-only (F07 separation).
    original = {"e8": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e8": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e8": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e8": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-count")
    verifier = _TranscriptVerifier({JA_IN: "match", JA_REPEAT: "match"})
    asr = _SegASR(
        {
            "e8": (
                JA_IN + " " + JA_REPEAT,
                [
                    _seg(1 * SECOND, 2 * SECOND, JA_IN),
                    _seg(3 * SECOND, 3 * SECOND + 500_000, JA_REPEAT),
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.accepted_regions == []
    # one main verifier call + one bounded extra padding probe.
    assert acc.verifier_calls == 2
    assert acc.asr_calls == 1
    assert (
        acc.semantic_seconds >= 0.10
    )  # two 0.05 s probe verdicts, transcription-only asr
    assert len(verifier.transcripts) == 2


# --- 9. per-segment dilution: two precise in-interval utterances, padding =====
#    repeats ONE of them verbatim -> the joined precise text dilutes the ratio,
#    so the old joined-only comparison auto-accepted. Must abstain. ===========


def test_repeat_of_one_of_two_precise_lines_abstains(tmp_path, monkeypatch):
    # Interval holds precise A + precise B; padding repeats A verbatim.
    original = {"e9": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e9": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e9": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e9": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-dil1")
    verifier = MockSemanticVerifier({EN_SUB: "match"})
    asr = _SegASR(
        {
            "e9": (
                JA_IN + " " + JA_OTHER + " " + JA_IN,
                [
                    _seg(1 * SECOND, 150_000 + 1 * SECOND, JA_IN),
                    _seg(1_600_000, 2_100_000, JA_OTHER),
                    _seg(3 * SECOND, 3 * SECOND + 500_000, JA_IN),  # verbatim repeat
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert acc.abstained_regions[0]["semantic_content_present_in_window"] is True
    assert "the semantic verifier matched both occurrences" in acc.notes


# --- 10. precise A + broad segment "A other" (verbatim repeat embedded) --------


def test_broad_segment_with_embedded_repeat_abstains(tmp_path, monkeypatch):
    # Precise A in-interval; a BROAD segment (crosses the boundary) contains a
    # verbatim repeat of A plus extra speech. Its substring Dice against A is
    # below the floor, so the containment rule must catch it.
    original = {"e10": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e10": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e10": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e10": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-dil2")
    verifier = MockSemanticVerifier({EN_SUB: "match"})
    asr = _SegASR(
        {
            "e10": (
                JA_IN + " " + JA_OTHER,
                [
                    _seg(1 * SECOND, 2 * SECOND, JA_IN),
                    # broad: media [2.2,3.5] intersects tolerant [0.5,2.5], extends past
                    _seg(2_200_000, 3 * SECOND + 500_000, JA_IN + " " + JA_OTHER),
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert "the semantic verifier matched both occurrences" in acc.notes


# --- 11. padding repeat with punctuation/spacing + full-width noise ------------


def test_punctuation_spacing_noise_repeat_abstains(tmp_path, monkeypatch):
    # The padding "repeat" differs from the in-interval line only by punctuation
    # (、 ！), spacing and full-width forms; _dup_normalize neutralizes that.
    original = {"e11": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e11": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e11": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e11": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-dil3")
    verifier = MockSemanticVerifier({EN_SUB: "match"})
    asr = _SegASR(
        {
            "e11": (
                JA_IN + " " + JA_NOISE_REPEAT,
                [
                    _seg(1 * SECOND, 2 * SECOND, JA_IN),
                    _seg(3 * SECOND, 3 * SECOND + 500_000, JA_NOISE_REPEAT),
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert "the semantic verifier matched both occurrences" in acc.notes


# --- 12. padding repeat split by ASR into two segments (joined catches it) -----


def test_split_padding_repeat_joined_catches_abstains(tmp_path, monkeypatch):
    # The padding repeat is split into two segments; each half alone is short.
    # The joined padding group equals the in-interval line and must qualify.
    original = {"e12": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e12": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e12": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e12": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-dil4")
    verifier = MockSemanticVerifier({EN_SUB: "match"})
    asr = _SegASR(
        {
            "e12": (
                JA_IN + " " + JA_SPLIT_HEAD + " " + JA_SPLIT_TAIL,
                [
                    _seg(1 * SECOND, 2 * SECOND, JA_IN),
                    _seg(3 * SECOND, 3 * SECOND + 300_000, JA_SPLIT_HEAD),
                    _seg(3_400_000, 3 * SECOND + 600_000, JA_SPLIT_TAIL),
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert "the semantic verifier matched both occurrences" in acc.notes


# --- 13. budget exhaustion => fail-closed abstain with an ACCURATE note --------


def test_competitors_exceed_cap_fail_closed_note_accurate(tmp_path, monkeypatch):
    # Three distinct padding competitors each near-duplicate the in-interval
    # line (verbatim substring of a longer span); the cap (2) is exceeded, so the
    # unprobed third competitor fails closed. The note must NOT claim the
    # verifier matched both occurrences.
    original = {"e13": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e13": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e13": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e13": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-budget")
    # In-interval (precise) text matches; every padding competitor says no_match.
    verifier = _TranscriptVerifier(
        {
            JA_IN: "match",
            JA_IN + "その": "no_match",
            JA_IN + "よ": "no_match",
        }
    )
    asr = _SegASR(
        {
            "e13": (
                JA_IN + " " + (JA_IN + "その") + " " + (JA_IN + "よ"),
                [
                    _seg(1 * SECOND, 2 * SECOND, JA_IN),
                    _seg(3 * SECOND, 3 * SECOND + 300_000, JA_IN + "その"),
                    _seg(3_400_000, 3 * SECOND + 600_000, JA_IN + "よ"),
                    _seg(3_700_000, 3 * SECOND + 900_000, JA_IN + "その"),
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert "exceeded the bounded extra-verification budget" in acc.notes
    assert "no verifier matched-both claim" in acc.notes
    assert "the semantic verifier matched both occurrences" not in acc.notes
    # cap = MAX_EXTRA_VERIFIER_CALLS: two probes then fail-closed.
    assert acc.verifier_calls == 1 + validator.MAX_EXTRA_VERIFIER_CALLS
    # Budget fail-closed records content-present (in-interval match proved it).
    assert len(acc.abstained_regions) == 1
    assert acc.abstained_regions[0]["semantic_content_present_in_window"] is True
    assert acc.abstained_regions[0]["timing_correspondence_verified"] is False
    notes_log = (tmp_path / "run-m2-budget" / "asr_notes.log").read_text(
        encoding="utf-8"
    )
    assert "fail-closed abstain" in notes_log


# --- 15. probe EXCEPTION on a competitor fails closed + records content-present --


def test_padding_probe_exception_fails_closed_records_content(tmp_path, monkeypatch):
    class _ProbeRaises:
        def __init__(self, answers):
            self.answers = dict(answers)
            self.transcripts = []

        def verdict(self, subtitle_text, transcript_text, sl, tl):
            self.transcripts.append(transcript_text)
            if transcript_text in self.answers:
                return SemanticVerdict(
                    verdict=self.answers[transcript_text],
                    seconds=0.05,
                    model="fake-verify",
                    mock=False,
                )
            raise RuntimeError("verifier endpoint timeout")

    original = {"e15": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e15": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"e15": (1 * SECOND, 2 * SECOND)}
    cue_text = {"e15": EN_SUB}
    case, proposal = _mk_case(original, proposal_times, _SINGLE_REGION, "m2-probeexc")
    # In-interval JA_IN matches; the near-duplicate padding competitor is a
    # distinct text (verbatim substring of JA_IN) with NO canned answer, so the
    # probe raises.
    verifier = _ProbeRaises({JA_IN: "match"})
    asr = _SegASR(
        {
            "e15": (
                JA_IN + " " + (JA_IN + "その"),
                [
                    _seg(1 * SECOND, 2 * SECOND, JA_IN),
                    _seg(3 * SECOND, 3 * SECOND + 500_000, JA_IN + "その"),
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert "no usable verdict (unknown/failure)" in acc.notes
    errors = (tmp_path / "run-m2-probeexc" / "asr_errors.log").read_text(
        encoding="utf-8"
    )
    assert "cross-language padding-ambiguity probe: verifier endpoint timeout" in errors
    assert len(acc.abstained_regions) == 1
    assert acc.abstained_regions[0]["semantic_content_present_in_window"] is True
    assert acc.abstained_regions[0]["timing_correspondence_verified"] is False


# --- 16. _near_duplicate boundary + normalization units ------------------------


def test_near_duplicate_floor_is_inclusive_and_normalized():
    # Exact 0.80 pair at the inclusive floor qualifies.
    assert validator._dup_normalize(JA_IN) == validator._dup_normalize(JA_IN + "！")
    assert _near_duplicate(JA_IN, JA_NEG) is True  # scores exactly the floor
    # Margin pair (longer shared prefix) clears the floor with headroom.
    assert _near_duplicate(JA_IN_MARGIN, JA_NEG_MARGIN) is True
    # Punctuation/spacing/full-width noise is neutralized -> same line.
    assert _near_duplicate(JA_IN, JA_NOISE_REPEAT) is True
    # Verbatim containment: a short repeat embedded in a longer span counts.
    assert _near_duplicate(JA_IN, JA_IN + " " + JA_OTHER) is True
    # Split halves each contained in the in-interval line count.
    assert _near_duplicate(JA_IN, JA_SPLIT_HEAD) is True
    # Unrelated dialogue is NOT a near-duplicate (below floor, no containment).
    assert _near_duplicate(JA_IN, JA_UNRELATED) is False
