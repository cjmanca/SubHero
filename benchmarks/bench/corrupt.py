"""Deterministic subtitle corruption generators with exact recorded inverses.

All injected parameters are multiples of the source subtitle grid, seeded by
`numpy.random.default_rng(seed)`: repeated runs with the same seed produce
identical results. Cue identity, text, styles and layer order are preserved;
the original file stays untouched. Invalid (negative/unordered) results are
detected and raise, never silently clamped.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .manifests import CaseManifest
from .media import sha256_file
from .subtitles import Track
from .timeline import CueShift, InvalidTime, Segment, Transform

SCENARIOS = ("S00", "S01", "S02", "S03", "S04", "S06")


def _grid_multiple(value_us: int, grid_us: int) -> int:
    return round(value_us / grid_us) * grid_us


def _timeline_duration_us(track: Track) -> int:
    return max((c.end_us for c in track.cues), default=0)


def build_transform(
    scenario: str, track: Track, seed: int
) -> tuple[Transform, dict, list[int]]:
    grid = track.grid_us
    rng = np.random.default_rng(seed)
    duration = _timeline_duration_us(track)
    true_breakpoints: list[int] = []
    params: dict = {"scenario": scenario}

    if scenario == "S00":
        params["control"] = True
        return Transform(), params, []
    if scenario == "S06":
        params["classification_only"] = True
        return Transform(), params, []

    if scenario == "S01":
        magnitude_ms = (
            float(rng.uniform(200, 2_000))
            if rng.random() < 0.5
            else float(rng.uniform(5_000, 60_000))
        )
        sign = 1.0 if rng.random() < 0.5 else -1.0
        offset = _grid_multiple(int(sign * magnitude_ms * 1000), grid)
        params = {"scenario": "S01", "offset_us": offset}
        return Transform((Segment(0, None, offset),)), params, []

    if scenario == "S02":
        choices = [
            (25_000, 23_976),
            (23_976, 25_000),
            (1_001_000, 1_000_000),
            (999_000, 1_000_000),
        ]
        num, den = choices[int(rng.integers(0, len(choices)))]
        params = {"scenario": "S02", "scale": [num, den]}
        return Transform((Segment(0, None, 0, np_fraction(num, den)),)), params, []

    if scenario == "S03":
        k = int(rng.integers(1, 4))
        lo = _grid_multiple(max(grid, int(duration * 0.1)), grid)
        hi = _grid_multiple(max(lo + grid, int(duration * 0.9)), grid)
        boundaries = sorted(
            {
                _grid_multiple(int(t), grid)
                for t in rng.integers(lo, max(lo + 1, hi), size=k)
            }
        )
        offsets = [
            _grid_multiple(int(rng.uniform(-30, 30) * 1_000_000), grid)
            for _ in boundaries
        ]
        cumulative = 0
        segments = []
        prev = 0
        for b, off in zip(boundaries, offsets):
            segments.append(Segment(prev, b, cumulative))
            cumulative += off
            prev = b
            true_breakpoints.append(b)
        segments.append(Segment(prev, None, cumulative))
        params = {
            "scenario": "S03",
            "boundaries_us": boundaries,
            "jump_offsets_us": offsets,
        }
        return Transform(tuple(segments)), params, true_breakpoints

    if scenario == "S04":
        if len(track.cues) < 3:
            raise ValueError("S04 needs at least 3 cues")
        n = int(rng.integers(1, min(6, len(track.cues))))
        picks = rng.choice(len(track.cues), size=n, replace=False)
        shifts = []
        for idx in picks:
            cue = track.cues[int(idx)]
            d_start = _grid_multiple(int(rng.uniform(-5, 5) * 1_000_000), grid)
            d_end = d_start + _grid_multiple(int(rng.uniform(-1, 1) * 1_000_000), grid)
            shifts.append(CueShift(cue.cue_id, d_start, d_end))
        params = {
            "scenario": "S04",
            "cue_shifts": [s.to_dict() for s in shifts],
        }
        return Transform((), tuple(shifts)), params, []

    raise ValueError(f"unknown scenario {scenario}")


def np_fraction(num: int, den: int):
    from fractions import Fraction

    return Fraction(int(num), int(den))


def prepare_case(
    source_id: str,
    case_id: str,
    scenario: str,
    seed: int,
    source_track_path: Path,
    out_path: Path,
    fmt: str | None = None,
    gold_classification_path: Path | None = None,
    notes: str = "",
    *,
    track_id: str,
) -> CaseManifest:
    """Build one corrupted case from an explicitly selected source track.

    ``track_id`` is the caller's **registered subtitle-track identifier** and
    is persisted verbatim into the case manifest. It is never derived from
    ``source_track_path``: for sidecar registrations the file stem is not the
    registry key, and stem-derived identities broke registry lookups (language
    resolution, source fingerprints, gold annotations) for every case whose
    registered id differed from the sidecar filename.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of {SCENARIOS}")
    if not track_id:
        raise ValueError("track_id must be the registered subtitle-track identifier")
    if Path(out_path).resolve() == Path(source_track_path).resolve():
        raise ValueError(
            "refusing to write a corrupted case over the original source track"
        )
    track = Track.load(source_track_path, fmt)
    transform, params, true_breakpoints = build_transform(scenario, track, seed)
    transform.validate()

    times: dict[str, tuple[int, int]] = {}
    injected: dict[str, tuple[int, int]] = {}
    cue_regions: dict[str, int] = {}
    for cue in track.cues:
        cue_regions[cue.cue_id] = transform.segment_index_for(cue.start_us)
        new_start, new_end = transform.apply_cue(
            cue.cue_id, cue.start_us, cue.end_us, track.grid_us
        )
        if new_start < 0:
            raise InvalidTime(
                f"{scenario} injection would create a negative start on {cue.cue_id}; reject parameters"
            )
        times[cue.cue_id] = (new_start, new_end)
        injected[cue.cue_id] = (new_start - cue.start_us, new_end - cue.end_us)

    track.save_with_times(out_path, times)
    inverse = transform.inverse(track.grid_us, cue_regions)

    if scenario in ("S01", "S02", "S03", "S04") and all(
        ds == 0 and de == 0 for ds, de in injected.values()
    ):
        raise ValueError(
            f"{scenario} seed {seed} injected no grid-detectable timing change; choose a larger-magnitude seed"
        )

    return CaseManifest(
        case_id=case_id,
        source_id=source_id,
        scenario=scenario,
        seed=seed,
        track_id=track_id,
        fmt=track.format,
        grid_us=track.grid_us,
        params=params,
        transform=transform.to_dict(),
        expected_inverse=inverse.to_dict(),
        injected_cue_deltas=injected,
        original_times_us=track.time_map(),
        true_breakpoints_us=true_breakpoints,
        original_subtitle_sha256=sha256_file(source_track_path),
        generated_subtitle_sha256=sha256_file(out_path),
        generated_path=str(out_path),
        gold_classification_path=str(gold_classification_path)
        if gold_classification_path
        else None,
        notes=notes,
    )
