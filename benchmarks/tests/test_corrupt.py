import shutil
from pathlib import Path

import pytest
from bench.corrupt import prepare_case
from bench.media import sha256_file
from bench.subtitles import Track
from bench.timeline import InvalidTime, Transform


def _copy_fixture_episode(dst: Path) -> Path:
    src = Path(__file__).resolve().parent.parent / "fixtures" / "Fx00" / "episode.ass"
    dst = dst / "episode.ass"
    shutil.copy(src, dst)
    return dst


def test_s00_control_is_unchanged(tmp_path, fixture_dir):
    src = fixture_dir / "episode.ass"
    case = prepare_case(
        "Fx00", "c-s00", "S00", 7, src, tmp_path / "out.ass", track_id="episode"
    )
    original = Track.load(src)
    generated = Track.load(Path(case.generated_path))
    assert original.time_map() == generated.time_map()
    assert [c.text for c in original.cues] == [c.text for c in generated.cues]
    assert case.injected_cue_deltas and all(
        ds == 0 and de == 0 for ds, de in case.injected_cue_deltas.values()
    )


def test_determinism_same_seed(tmp_path, fixture_dir):
    src = fixture_dir / "episode.ass"
    c1 = prepare_case(
        "Fx00", "c1", "S03", 42, src, tmp_path / "a" / "out.ass", track_id="episode"
    )
    c2 = prepare_case(
        "Fx00", "c2", "S03", 42, src, tmp_path / "b" / "out.ass", track_id="episode"
    )
    assert c1.generated_subtitle_sha256 == c2.generated_subtitle_sha256
    assert c1.transform == c2.transform
    assert c1.injected_cue_deltas == c2.injected_cue_deltas
    assert (tmp_path / "a" / "out.ass").read_bytes() == (
        tmp_path / "b" / "out.ass"
    ).read_bytes()


def test_inverse_recovers_originals_for_all_scenarios(tmp_path, fixture_dir):
    src = fixture_dir / "episode.ass"
    track = Track.load(src)
    for scenario in ("S01", "S02", "S03", "S04"):
        case = prepare_case(
            "Fx00",
            f"c-{scenario}",
            scenario,
            11,
            src,
            tmp_path / f"{scenario}.ass",
            notes=scenario,
            track_id="episode",
        )
        inv = Transform.from_dict(case.transform).inverse(track.grid_us)
        generated = Track.load(Path(case.generated_path))
        for cue in generated.cues:
            s, e = inv.apply_cue(cue.cue_id, cue.start_us, cue.end_us, track.grid_us)
            orig_s, orig_e = case.original_times_us[cue.cue_id]
            if scenario == "S02":
                # grid quantization of a rational scale cannot always reproduce the original grid exactly;
                # scoring ground truth is the stored per-cue original times, not an inverse re-derivation
                assert (
                    abs(s - orig_s) <= track.grid_us
                    and abs(e - orig_e) <= track.grid_us
                ), (scenario, cue.cue_id)
            else:
                assert (s, e) == (orig_s, orig_e), (scenario, cue.cue_id)


def test_cue_identity_and_text_preserved(tmp_path, fixture_dir):
    src = fixture_dir / "episode.ass"
    original = Track.load(src)
    case = prepare_case(
        "Fx00", "c-id", "S03", 5, src, tmp_path / "out.ass", track_id="episode"
    )
    generated = Track.load(Path(case.generated_path))
    assert [c.cue_id for c in original.cues] == [c.cue_id for c in generated.cues]
    assert [c.text for c in original.cues] == [c.text for c in generated.cues]
    assert [c.style for c in original.cues] == [c.style for c in generated.cues]
    assert [c.layer for c in original.cues] == [c.layer for c in generated.cues]
    assert case.true_breakpoints_us


def test_negative_start_is_rejected(tmp_path):
    import pysubs2

    ass = tmp_path / "tiny.ass"
    doc = pysubs2.SSAFile()
    doc.events.append(pysubs2.SSAEvent(start=0, end=2_000, text="Line at zero"))
    doc.save(ass, format="ass")
    with pytest.raises(InvalidTime):
        for seed in range(500):
            prepare_case(
                "T",
                f"n{seed}",
                "S01",
                seed,
                ass,
                tmp_path / f"out{seed}.ass",
                track_id="tiny",
            )
        pytest.fail(
            "no seed produced an invalid negative timeline; generator guards untested"
        )


def test_original_never_overwritten(tmp_path, fixture_dir):
    src = fixture_dir / "episode.ass"
    with pytest.raises(ValueError):
        prepare_case("Fx00", "bad", "S01", 3, src, src, track_id="episode")


def test_source_file_immutable_after_prepare(tmp_path, fixture_dir):
    src = fixture_dir / "episode.ass"
    before = sha256_file(src)
    prepare_case("Fx00", "imm", "S02", 9, src, tmp_path / "out.ass", track_id="episode")
    assert sha256_file(src) == before
