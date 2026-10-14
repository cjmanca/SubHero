from fractions import Fraction

import pytest
from bench.timeline import CueShift, InvalidTime, Segment, Transform, quantize


def test_quantize_half_to_even_on_grid():
    assert quantize(Fraction(15_000), 10_000) == 20_000
    assert quantize(Fraction(25_000), 10_000) == 20_000
    assert quantize(Fraction(35_000), 10_000) == 40_000


def test_global_offset_roundtrip():
    tf = Transform((Segment(0, None, 30_000_000),))
    grid = 10_000
    inv = tf.inverse(grid)
    for t in (0, 10_000, 5_000_000, 60_000_000):
        s, e = tf.apply_cue("c", t, t + 10_000, grid)
        assert inv.apply_cue("c", s, e, grid) == (t, t + 10_000)


def test_scale_roundtrip_within_grid_quantization():
    grid = 10_000
    for num, den in [
        (25_000, 23_976),
        (23_976, 25_000),
        (1_001_000, 1_000_000),
        (999_000, 1_000_000),
    ]:
        tf = Transform((Segment(0, None, 0, Fraction(num, den)),))
        inv = tf.inverse(grid)
        for t in range(0, 60_000_000, 1_000_000):
            s, e = tf.apply_cue("c", t, t + 2_000_000, grid)
            rs, re = inv.apply_cue("c", s, e, grid)
            assert abs(rs - t) <= grid and abs(re - (t + 2_000_000)) <= grid, (
                num,
                den,
                t,
            )


def test_piecewise_roundtrip_and_boundaries():
    grid = 10_000
    tf = Transform(
        (
            Segment(0, 20_000_000, 0),
            Segment(20_000_000, 40_000_000, -5_000_000),
            Segment(40_000_000, None, -5_000_000 + 10_000_000),
        )
    )
    cues = {f"t{t:08d}": t for t in range(0, 60_000_001, 500_000)}
    inv = tf.inverse(grid, {cid: tf.segment_index_for(t) for cid, t in cues.items()})
    for cid, t in cues.items():
        s, e = tf.apply_cue(cid, t, t + 10_000, grid)
        assert inv.apply_cue(cid, s, e, grid) == (t, t + 10_000), t


def test_cue_shift_composition_inverse():
    grid = 10_000
    tf = Transform(
        (Segment(0, 30_000_000, 0), Segment(30_000_000, None, 2_000_000)),
        (CueShift("e0002", -1_500_000, -1_000_000),),
    )
    cues = {
        "e0000": (1_000_000, 2_000_000),
        "e0002": (31_000_000, 33_000_000),
        "e0003": (35_000_000, 36_000_000),
    }
    inv = tf.inverse(
        grid, {cid: tf.segment_index_for(s) for cid, (s, e) in cues.items()}
    )
    for cid, (s, e) in cues.items():
        cs, ce = tf.apply_cue(cid, s, e, grid)
        assert inv.apply_cue(cid, cs, ce, grid) == (s, e)


def test_negative_result_detected_not_clamped():
    tf = Transform((Segment(0, None, -30_000_000),))
    with pytest.raises(InvalidTime):
        tf.apply_cue("c", 5_000_000, 6_000_000, 10_000)


def test_segment_validation_rejects_gaps():
    tf = Transform((Segment(0, 10_000_000, 0), Segment(20_000_000, None, 5_000_000)))
    with pytest.raises(InvalidTime):
        tf.validate()
