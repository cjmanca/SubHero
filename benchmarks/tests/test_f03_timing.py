"""Third-review F03 focused regressions: match-at-time vs text-found-near-time.

The padded-window validator previously accepted a cue because the enlarged
window transcript CONTAINED the subtitle text — a wrongly shifted cue next to
the real speech could pass. These regressions reproduce the review's exact
scenarios against the new timing-correspondence gate:

* two distinct adjacent dialogue lines: the line shifted onto its neighbor's
  time is refused (padding-only content), the correctly localized line accepts;
* the same line repeated in the padding outside the proposed interval → the
  position is ambiguous → abstain, never accept;
* a wrong shift whose padded transcript still contains the subtitle text →
  abstain with semantic_content_present_in_window, timing unverified;
* a correctly localized positive control accepts with
  timing_correspondence_verified;
* a backend with NO segment timestamps never gets a text-only timing proof
  (abstain, no accept, no reject);
* cross-language accepts require verifier evidence over in-interval segments;
  a padded-window-only verifier match abstains; no_match still rejects.
"""

from __future__ import annotations

from pathlib import Path

from bench import validator
from bench.asr import MockSemanticVerifier, Transcription
from bench.manifests import CaseManifest, ProposalRecord
from bench.validator import _segment_timing, validate_proposal

SECOND = 1_000_000


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

    Segment timestamps are RELATIVE to the extracted window start, exactly
    like verbose_json segments of the window file.
    """

    def __init__(
        self, by_key: dict[str, tuple[str, list[dict]]], confidence: float = 1.0
    ):
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


def test_adjacent_lines_shifted_onto_neighbor_abstains_localized_accepts(
    tmp_path, monkeypatch
):
    # True speech: cue A line at media [1s,2s], cue B line at [3s,4s].
    # Candidate keeps A at its speech (correct) and shifts B onto A's time
    # (wrong). A's window [0s,3.5s] contains BOTH utterances; B's proposed
    # interval [1s,2s]±tol covers only the alpha utterance, whose text
    # matches A (not B): B's own line appears only in the padding.
    original = {"eA": (1 * SECOND, 2 * SECOND), "eB": (3 * SECOND, 4 * SECOND)}
    corrupted = {"eA": (1 * SECOND, 2 * SECOND), "eB": (3 * SECOND, 4 * SECOND)}
    proposal_times = {"eA": (1 * SECOND, 2 * SECOND), "eB": (1 * SECOND, 2 * SECOND)}
    regions = [
        {"start_us": 0, "end_us": 2 * SECOND, "offset_us": 0},
        {"start_us": 2 * SECOND, "end_us": None, "offset_us": -1 * SECOND},
    ]
    cue_text = {"eA": "alpha bravo charlie", "eB": "delta echo foxtrot"}
    case, proposal = _mk_case(original, proposal_times, regions, "f03-adj")
    asr = _SegASR(
        {
            # window for eA: [0, 3.5s] -> alpha media [1,2] rel [1,2];
            # delta media [3,3.5] clipped rel [3,3.5]
            "eA": (
                "alpha bravo charlie delta echo foxtr",
                [
                    _seg(1 * SECOND, 2 * SECOND, "alpha bravo charlie"),
                    _seg(3 * SECOND, 3 * SECOND + 500_000, "delta echo foxtr"),
                ],
            ),
            # window for eB (proposed [1,2]): identical geometry
            "eB": (
                "alpha bravo charlie delta echo foxtr",
                [
                    _seg(1 * SECOND, 2 * SECOND, "alpha bravo charlie"),
                    _seg(3 * SECOND, 3 * SECOND + 500_000, "delta echo foxtr"),
                ],
            ),
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "en"
    )
    assert acc.status == "success"
    assert len(acc.accepted_regions) == 1
    assert acc.accepted_regions[0]["start_us"] == 0
    assert acc.accepted_regions[0]["timing_correspondence_verified"] is True
    assert acc.accepted_times_us["eA"] == (1 * SECOND, 2 * SECOND)
    # The shifted cue's region is NOT accepted; its original timing is retained.
    assert acc.accepted_times_us["eB"] == corrupted["eB"]
    abstained = [r for r in acc.abstained_regions if r["start_us"] == 2 * SECOND]
    assert len(abstained) == 1
    assert abstained[0]["semantic_content_present_in_window"] is True
    assert abstained[0]["timing_correspondence_verified"] is False
    assert (
        "1 samples: the matching utterance was found only in the 1.5 s window padding"
        in acc.notes
    )
    notes_log = (tmp_path / "run-f03-adj" / "asr_notes.log").read_text(encoding="utf-8")
    assert "matching utterance found only in window padding" in notes_log


def test_line_repeated_in_padding_outside_interval_is_ambiguous_not_accepted(
    tmp_path, monkeypatch
):
    # Cue proposed at [1s,2s] with its line spoken there, AND the same line
    # repeated in the padding at [3s,3.5s]: the position is ambiguous, so the
    # sample abstains and nothing is accepted.
    original = {"eR": (1 * SECOND, 2 * SECOND)}
    corrupted = {"eR": (1 * SECOND, 2 * SECOND)}
    proposal_times = {"eR": (1 * SECOND, 2 * SECOND)}
    regions = [{"start_us": 0, "end_us": None, "offset_us": 0}]
    cue_text = {"eR": "the door is open"}
    case, proposal = _mk_case(original, proposal_times, regions, "f03-rep")
    asr = _SegASR(
        {
            "eR": (
                "the door is open the door is open",
                [
                    _seg(1 * SECOND, 2 * SECOND, "the door is open"),
                    _seg(3 * SECOND, 3 * SECOND + 500_000, "the door is open"),
                ],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "en"
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    notes_log = (tmp_path / "run-f03-rep" / "asr_notes.log").read_text(encoding="utf-8")
    assert "position ambiguous; abstained" in notes_log
    assert (
        "1 samples: the subtitle text matched both at the proposed interval and in the window padding"
        in acc.notes
    )
    assert acc.abstained_regions[0]["semantic_content_present_in_window"] is True


def test_wrong_shift_with_text_in_padding_never_accepts(tmp_path, monkeypatch):
    # Review scenario: the padded transcript of a wrongly shifted cue STILL
    # contains the subtitle text (the line is spoken 1 s before the proposed
    # interval). Text presence near the window is not timing proof.
    original = {"eW": (1 * SECOND, 2 * SECOND)}
    corrupted = {"eW": (10 * SECOND, 11 * SECOND)}
    proposal_times = {"eW": (3 * SECOND, 4 * SECOND)}
    regions = [{"start_us": 0, "end_us": None, "offset_us": -7 * SECOND}]
    cue_text = {"eW": "the door is open"}
    case, proposal = _mk_case(original, proposal_times, regions, "f03-shift")
    asr = _SegASR(
        {
            # window [1.5s, 5.5s]: speech media [1,2] clipped to [1.5,2]
            "eW": (
                "the door is open",
                [_seg(0, 500_000, "the door is open")],
            )
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "en"
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert acc.rejected_regions == []
    assert acc.abstained_regions[0]["semantic_content_present_in_window"] is True
    assert acc.abstained_regions[0]["timing_correspondence_verified"] is False
    assert "timing correspondence unverified" in acc.notes
    assert "the wrongly-shifted-cue accept the review reproduced" in acc.notes


def test_correctly_localized_positive_control_accepts_with_timing_flag(
    tmp_path, monkeypatch
):
    original = {"eP": (1 * SECOND, 2 * SECOND)}
    corrupted = {"eP": (10 * SECOND, 11 * SECOND)}
    proposal_times = {"eP": (1 * SECOND, 2 * SECOND)}
    regions = [{"start_us": 0, "end_us": None, "offset_us": -9 * SECOND}]
    cue_text = {"eP": "the door is open"}
    case, proposal = _mk_case(original, proposal_times, regions, "f03-good")
    asr = _SegASR(
        {
            # window [0, 3.5s]: speech media [1,2] rel [1,2] overlaps [0.5,2.5]
            "eP": (
                "the door is open",
                [_seg(1 * SECOND, 2 * SECOND, "the door is open")],
            ),
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "en"
    )
    assert acc.status == "success"
    assert len(acc.accepted_regions) == 1
    assert acc.accepted_regions[0]["timing_correspondence_verified"] is True
    assert acc.accepted_regions[0]["semantic_content_present_in_window"] is True
    assert "time-local ASR segment evidence" in acc.accepted_regions[0]["reason"]
    assert acc.accepted_times_us["eP"] == proposal_times["eP"]


def test_no_segment_timestamps_never_proves_timing(tmp_path, monkeypatch):
    # Same positive-control geometry, but the backend reports NO segment
    # timestamps: the text-only window match is content evidence only.
    original = {"eT": (1 * SECOND, 2 * SECOND)}
    corrupted = {"eT": (10 * SECOND, 11 * SECOND)}
    proposal_times = {"eT": (1 * SECOND, 2 * SECOND)}
    regions = [{"start_us": 0, "end_us": None, "offset_us": -9 * SECOND}]
    cue_text = {"eT": "the door is open"}
    case, proposal = _mk_case(original, proposal_times, regions, "f03-nots")
    asr = _SegASR({"eT": ("the door is open", [])})
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "en"
    )
    assert acc.accepted_regions == []
    assert acc.rejected_regions == []
    assert acc.accepted_times_us == corrupted
    assert "no usable segment timestamps" in acc.notes
    assert (
        "semantic_content_present_in_window, never timing_correspondence_verified"
        in acc.notes
    )
    assert acc.status == "not_run"  # no usable evidence at all


def test_cross_language_accept_requires_in_interval_verifier_evidence(
    tmp_path, monkeypatch
):
    en_line = "I will protect this city."
    ja_line = "この街はわたしが守る"
    original = {"eX": (1 * SECOND, 2 * SECOND)}
    corrupted = {"eX": (10 * SECOND, 11 * SECOND)}
    proposal_times = {"eX": (1 * SECOND, 2 * SECOND)}
    regions = [{"start_us": 0, "end_us": None, "offset_us": -9 * SECOND}]
    cue_text = {"eX": en_line}
    case, proposal = _mk_case(original, proposal_times, regions, "f03-xa")
    verifier = MockSemanticVerifier({en_line: "match"})
    asr = _SegASR(
        {
            "eX": (ja_line, [_seg(1 * SECOND, 2 * SECOND, ja_line)]),
        }
    )
    acc = _run_validate(
        tmp_path,
        monkeypatch,
        case,
        proposal,
        corrupted,
        cue_text,
        asr,
        "ja",
        verifier=verifier,
    )
    assert acc.status == "success"
    assert len(acc.accepted_regions) == 1
    assert acc.accepted_regions[0]["timing_correspondence_verified"] is True
    assert acc.accepted_times_us["eX"] == proposal_times["eX"]
    # The verifier was asked about the IN-INTERVAL segment text, not the
    # whole padded window transcript.
    assert verifier.calls
    assert verifier.calls[0][0] == en_line
    assert verifier.calls[0][2] == "ja"
    assert verifier.transcripts[0] == ja_line


def test_cross_language_padding_only_verifier_match_abstains(tmp_path, monkeypatch):
    en_line = "I will protect this city."
    ja_line = "この街はわたしが守る"
    original = {"eY": (1 * SECOND, 2 * SECOND)}
    corrupted = {"eY": (10 * SECOND, 11 * SECOND)}
    # Proposal shifts the cue 2 s past the real speech; the line is audible
    # only in the padding window.
    proposal_times = {"eY": (3 * SECOND, 4 * SECOND)}
    regions = [{"start_us": 0, "end_us": None, "offset_us": -7 * SECOND}]
    cue_text = {"eY": en_line}
    case, proposal = _mk_case(original, proposal_times, regions, "f03-xb")
    verifier = MockSemanticVerifier({en_line: "match"})
    asr = _SegASR(
        {
            # window [1.5s,5.5s]: speech media [1,2] clipped to [1.5,2] rel [0,0.5]
            "eY": (ja_line, [_seg(0, 500_000, ja_line)]),
        }
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert (
        "1 cross-language samples: the semantic verifier matched the padded window without time-local segment evidence; abstained (never accepted)"
        in acc.notes
    )
    assert acc.status == "not_run"


def test_cross_language_no_match_rejects_despite_padding_content(tmp_path, monkeypatch):
    en_line = "I will protect this city."
    ja_contradiction = "翌日の午前10時に出発する"
    original = {"eZ": (1 * SECOND, 2 * SECOND)}
    corrupted = {"eZ": (10 * SECOND, 11 * SECOND)}
    proposal_times = {"eZ": (1 * SECOND, 2 * SECOND)}
    regions = [{"start_us": 0, "end_us": None, "offset_us": -9 * SECOND}]
    cue_text = {"eZ": en_line}
    case, proposal = _mk_case(original, proposal_times, regions, "f03-xc")
    verifier = MockSemanticVerifier({en_line: "no_match"})
    asr = _SegASR(
        {"eZ": (ja_contradiction, [_seg(1 * SECOND, 2 * SECOND, ja_contradiction)])}
    )
    acc = _run_validate(
        tmp_path, monkeypatch, case, proposal, corrupted, cue_text, asr, "ja", verifier
    )
    assert len(acc.rejected_regions) == 1
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted


def test_segment_timing_overlap_semantics_units():
    # Segment spans media [3s,4s], proposal [4s,5s]: touching at a single
    # point is NOT positive overlap at zero tolerance.
    alpha = _seg(0, 1_000_000, "alpha bravo")
    res = _segment_timing(
        "alpha bravo",
        [alpha],
        win_off_us=3_000_000,
        start_us=4_000_000,
        end_us=5_000_000,
        tol_us=0,
    )
    assert res["n_overlap"] == 0
    assert res["in_ratio"] == 0.0
    assert res["padding_ratio"] > 0.9
    # Documented tolerance: the same segment overlaps [4s,5s] by 0.5 s of
    # positive intersection (start - tol) and supports time-local matching.
    res2 = _segment_timing(
        "alpha bravo",
        [alpha],
        win_off_us=3_000_000,
        start_us=4_000_000,
        end_us=5_000_000,
    )
    assert res2["n_overlap"] == 1
    assert res2["in_ratio"] > 0.9
    assert res2["padding_ratio"] == 0.0
    # A cue spanning two consecutive in-segments is joined; a join never
    # mixes an in-segment with a padding segment.
    segs = [
        _seg(1_000_000, 1_500_000, "alpha"),
        _seg(1_500_000, 2_000_000, "bravo charlie"),
        _seg(4_000_000, 4_500_000, "delta"),
    ]
    res3 = _segment_timing(
        "alpha bravo charlie", segs, win_off_us=0, start_us=1_000_000, end_us=2_000_000
    )
    assert res3["n_overlap"] == 2
    assert res3["in_ratio"] > 0.9
    assert res3["padding_ratio"] < 0.45
    assert "delta" not in res3["overlap_text"]
