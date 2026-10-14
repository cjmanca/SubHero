from pathlib import Path

from bench.asr import MockTranscriber
from bench.corrupt import prepare_case
from bench.manifests import ProposalRecord
from bench.subtitles import Track
from bench.validator import (
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
    case = prepare_case("Fx00", "va-samp", "S00", 2, src, tmp_path / "out.ass")
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
    case = prepare_case("Fx00", "va-notrun", "S01", 2, src, tmp_path / "out.ass")
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
    case = prepare_case("Fx00", "va-mock", "S01", 2, src, tmp_path / "out.ass")
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
