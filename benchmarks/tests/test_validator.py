from pathlib import Path

from bench.asr import MockSemanticVerifier, MockTranscriber, Transcription
from bench.corrupt import prepare_case
from bench.manifests import CaseManifest, ProposalRecord
from bench.subtitles import Track
from bench.validator import (
    is_cross_language,
    normalize_text,
    plan_samples,
    semantic_match,
    validate_proposal,
)


def _proposal(corrupted_times, offset_us=5_000_000):
    proposed = {
        cid: (s + offset_us, e + offset_us) for cid, (s, e) in corrupted_times.items()
    }
    regions = [{"start_us": 0, "end_us": None, "offset_us": offset_us}]
    return ProposalRecord(
        "c", "b1-px-fg", "1:1-order-preserving", regions, proposed, []
    )


def test_semantic_match_requires_correspondence_not_activity():
    a = "The kettle is whistling again"
    assert semantic_match(a, "kettle whistling again") > 0.5
    assert semantic_match(a, "someone is talking about lamps") < 0.45
    assert normalize_text(r"{\k100}Sing{\k100}ing") == "singing"


def test_samples_cover_edges_split_sides_and_controls(fixture_dir, tmp_path):
    src = fixture_dir / "episode.ass"
    case = prepare_case(
        "Fx00", "va-samp", "S00", 2, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path))
    times = corrupted.time_map()
    proposal = _proposal(times)
    samples = plan_samples(case, proposal, times, seed=7)
    ordered = sorted(times, key=lambda cid: times[cid][0])
    assert ordered[0] in samples
    assert ordered[-1] in samples
    assert len(samples) >= 6


def test_validator_without_model_is_not_run_not_fabricated(fixture_dir, tmp_path):
    src = fixture_dir / "episode.ass"
    case = prepare_case(
        "Fx00", "va-notrun", "S01", 2, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path))
    proposal = _proposal(corrupted.time_map())
    acc = validate_proposal(
        case,
        proposal,
        "b1-px-fg",
        corrupted.time_map(),
        {c.cue_id: c.text for c in corrupted.cues},
        tmp_path / "ref.wav",
        tmp_path / "run",
        None,
        "und",
        1,
    )
    assert acc.status == "not_run"
    assert acc.accepted_times_us == corrupted.time_map()


def test_mock_transcriber_never_auto_accepts(fixture_dir, tmp_path):
    src = fixture_dir / "episode.ass"
    case = prepare_case(
        "Fx00", "va-mock", "S01", 2, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path))
    cue_text = {c.cue_id: c.text for c in corrupted.cues}
    proposal = _proposal(corrupted.time_map())
    mock = MockTranscriber({cid: cue_text[cid] for cid in cue_text})
    from bench import media, validator

    validator.extract_audio_window = lambda *a, **k: (
        0.1
    )  # stub out ffmpeg windows for mock test
    try:
        acc = validate_proposal(
            case,
            proposal,
            "b1-px-fg",
            corrupted.time_map(),
            cue_text,
            Path("fake.wav"),
            tmp_path / "run",
            mock,
            "und",
            1,
        )
    finally:
        validator.extract_audio_window = media.extract_audio_window
    assert acc.status == "abstain"
    assert acc.asr_calls >= 1
    assert acc.accepted_times_us == corrupted.time_map()
    assert all(
        r["reason"].startswith(("no samples", "mixed", "insufficient"))
        for r in acc.abstained_regions
    )


class _FakeASR:
    """Non-mock test transcriber with canned per-cue texts, confidence, and
    (F03) canned per-cue window-relative segment timestamps."""

    def __init__(
        self,
        texts: dict[str, str],
        confidence: float = 1.0,
        segments: dict[str, list[dict]] | None = None,
    ):
        self.texts = dict(texts)
        self.confidence = confidence
        self.segments = dict(segments) if segments else None

    def transcribe_window(self, wav_path, language, key=None):
        return Transcription(
            text=self.texts[key],
            confidence=self.confidence,
            seconds=0.0,
            model="fake",
            mock=False,
            segments=(
                self.segments[key] if self.segments and key in self.segments else None
            ),
        )


def _hand_case(cue_text: dict[str, str]):
    original = {
        cid: (1_000_000 + i * 10_000_000, 2_000_000 + i * 10_000_000)
        for i, cid in enumerate(sorted(cue_text))
    }
    corrupted = {
        cid: (s + 5_000_000, e + 5_000_000) for cid, (s, e) in original.items()
    }
    case = CaseManifest(
        case_id="sem-lex",
        source_id="SEM",
        scenario="S01",
        seed=1,
        track_id="episode",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": "S01", "offset_us": 5_000_000},
        transform={},
        expected_inverse={},
        injected_cue_deltas={cid: (5_000_000, 5_000_000) for cid in cue_text},
        original_times_us=original,
        true_breakpoints_us=[],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )
    proposal = ProposalRecord(
        "sem-lex",
        "b1-px-fg",
        "1:1-order-preserving",
        [{"start_us": 0, "end_us": None, "offset_us": -5_000_000}],
        dict(original),
        [],
        "",
    )
    return case, proposal, corrupted


def _stub_windows(monkeypatch):
    monkeypatch.setattr("bench.validator.extract_audio_window", lambda *a, **k: 0.1)


def _hand_segments(cue_text: dict[str, str], text: str) -> dict[str, list[dict]]:
    """F03 timing evidence localized to each cue's PROPOSED interval.

    Matches `_hand_case` geometry: cue i spans original [1 s + i*10 s,
    2 s + i*10 s] and the proposal restores it exactly; window starts at
    max(0, start - PAD_US), so segment timestamps are window-relative.
    """
    segments: dict[str, list[dict]] = {}
    for i, cid in enumerate(sorted(cue_text)):
        start = 1_000_000 + i * 10_000_000
        win_off = max(0, start - 1_500_000)
        segments[cid] = [
            {
                "start_us": start - win_off,
                "end_us": start - win_off + 1_000_000,
                "text": text,
            }
        ]
    return segments


def test_same_language_lexical_accept_preserved(tmp_path, monkeypatch):
    _stub_windows(monkeypatch)
    cue_text = {"e0000": "the door is open", "e0001": "the door is open"}
    case, proposal, corrupted = _hand_case(cue_text)
    asr = _FakeASR(
        {cid: "the door is open" for cid in cue_text},
        segments=_hand_segments(cue_text, "the door is open"),
    )
    acc = validate_proposal(
        case,
        proposal,
        "b1-px-fg",
        corrupted,
        cue_text,
        Path("fake.wav"),
        tmp_path / "run-lex-accept",
        asr,
        "en",
        1,
        verifier=None,
    )
    assert acc.status == "success"
    assert len(acc.accepted_regions) == 1
    assert acc.accepted_times_us == proposal.proposed_times_us


def test_same_language_lexical_reject_preserved(tmp_path, monkeypatch):
    _stub_windows(monkeypatch)
    cue_text = {"e0000": "the door is open", "e0001": "the door is open"}
    case, proposal, corrupted = _hand_case(cue_text)
    asr = _FakeASR(
        {cid: "lamps hum on the table" for cid in cue_text},
        segments=_hand_segments(cue_text, "lamps hum on the table"),
    )
    acc = validate_proposal(
        case,
        proposal,
        "b1-px-fg",
        corrupted,
        cue_text,
        Path("fake.wav"),
        tmp_path / "run-lex-reject",
        asr,
        "en",
        1,
        verifier=None,
        subtitle_language="en",
    )
    assert acc.status == "success"
    assert len(acc.rejected_regions) == 1
    assert acc.accepted_times_us == corrupted


def test_same_language_lexical_accept_requires_reliable_transcript(
    tmp_path, monkeypatch
):
    _stub_windows(monkeypatch)
    cue_text = {"e0000": "the door is open", "e0001": "the door is open"}
    case, proposal, corrupted = _hand_case(cue_text)
    asr = _FakeASR(
        {cid: "the door is open" for cid in cue_text},
        confidence=-1.0,
        segments=_hand_segments(cue_text, "the door is open"),
    )
    acc = validate_proposal(
        case,
        proposal,
        "b1-px-fg",
        corrupted,
        cue_text,
        Path("fake.wav"),
        tmp_path / "run-lex-sentinel",
        asr,
        "en",
        1,
        verifier=None,
        subtitle_language="en",
    )
    # Shared F07 gate: a perfect lexical match over a missing-sentinel transcript
    # is NOT automatic-accept evidence; the region abstains.
    assert acc.status == "abstain"
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted
    assert (
        f"{len(acc.sample_cue_ids)} samples: ASR transcript reliability signal "
        "missing/unusable" in acc.notes
    )


def test_cross_language_pairing_detection(tmp_path, monkeypatch):
    _stub_windows(monkeypatch)
    cue_text = {
        "e0000": "I will protect this city.",
        "e0001": "I will protect this city.",
    }
    case, proposal, corrupted = _hand_case(cue_text)
    assert is_cross_language("I will protect this city.", "この街はわたしが守る")
    assert not is_cross_language("the door is open", "the door is wide open")
    ja_line = "この街はわたしが守る"
    asr = _FakeASR(
        {cid: ja_line for cid in cue_text},
        segments=_hand_segments(cue_text, ja_line),
    )
    # Cross-language pairs are NOT lexically rejected; verifier decides.
    lexical = semantic_match(cue_text["e0000"], "この街はわたしが守る")
    assert lexical < 0.45  # old rule would have false-rejected
    verifier = MockSemanticVerifier({cue_text["e0000"]: "match"})
    acc = validate_proposal(
        case,
        proposal,
        "b1-px-fg",
        corrupted,
        cue_text,
        Path("fake.wav"),
        tmp_path / "run-cross",
        asr,
        "ja",
        1,
        verifier=verifier,
    )
    assert acc.status == "success"
    assert acc.rejected_regions == []
    assert len(acc.accepted_regions) == 1
    assert "mock semantic verifier (test-only)" in acc.accepted_regions[0]["reason"]
    assert "mock semantic verifier used (test-only)" in acc.notes
