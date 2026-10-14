import pytest
from bench import paths
from bench.media import sha256_file
from bench.subtitles import Track


def setup_function(_):
    paths.reset()


def test_scratch_guard_rejects_outside_writes(tmp_path):
    scratch = tmp_path / "scratch"
    outside = tmp_path / "elsewhere"
    scratch.mkdir()
    outside.mkdir()
    paths.configure([scratch], [], [])
    with pytest.raises(RuntimeError, match="not inside a scratch root"):
        paths.ensure_scratch_path(outside / "x.wav")
    ok = paths.ensure_scratch_path(scratch / "x.wav")
    assert ok == (scratch / "x.wav").resolve()


def test_scratch_guard_rejects_source_roots(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    paths.configure([tmp_path], [library], [])
    with pytest.raises(RuntimeError, match="read-only source root"):
        paths.ensure_scratch_path(library / "episode.ass")


def test_forbidden_roots_rejected(tmp_path):
    plex = tmp_path / "plex_watched"
    plex.mkdir()
    paths.configure([tmp_path], [], [plex])
    with pytest.raises(RuntimeError, match="forbidden"):
        paths.ensure_scratch_path(plex / "movie.srt")


def test_configure_required(tmp_path):
    paths.reset()
    with pytest.raises(RuntimeError, match="not configured"):
        paths.ensure_scratch_path(tmp_path / "x")


def test_sha256_file(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"hello")
    assert (
        sha256_file(f)
        == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_subtitle_roundtrip_preserves_styles_layers(fixture_dir, tmp_path):
    paths.configure([tmp_path], [fixture_dir], [])
    track = Track.load(fixture_dir / "episode.ass")
    times = {c.cue_id: (c.start_us + 100_000, c.end_us + 100_000) for c in track.cues}
    out = tmp_path / "out.ass"
    track.save_with_times(out, times)
    reloaded = Track.load(out)
    assert [c.text for c in reloaded.cues] == [c.text for c in track.cues]
    assert [c.style for c in reloaded.cues] == [c.style for c in track.cues]
    assert [c.layer for c in reloaded.cues] == [c.layer for c in track.cues]
    assert all(c.start_us % 10_000 == 0 for c in reloaded.cues)


def test_save_rejects_off_grid_times(fixture_dir, tmp_path):
    track = Track.load(fixture_dir / "episode.ass")
    times = dict(track.time_map())
    first = next(iter(times))
    times[first] = (times[first][0] + 5, times[first][1])
    with pytest.raises(ValueError):
        track.save_with_times(tmp_path / "out.ass", times)


def test_save_rejects_negative_times(fixture_dir, tmp_path):
    track = Track.load(fixture_dir / "episode.ass")
    times = dict(track.time_map())
    first = next(iter(times))
    times[first] = (-1_000, times[first][1])
    with pytest.raises(ValueError):
        track.save_with_times(tmp_path / "out.ass", times)
