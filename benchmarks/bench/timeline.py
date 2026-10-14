"""Common episode timeline: integer microseconds with exact rational scales.

Documented conventions:
- All times are integer microseconds on a common episode timeline.
- Scales are exact fractions (no implicit float equality).
- Application quantizes to the source subtitle grid (ASS: 10 ms, SRT: 1 ms)
  using round-half-to-even; generation parameters are grid multiples.
- Source subtitle time, media time and speech time are kept distinct.
- Subtitle display duration is NOT assumed to equal spoken-dialogue duration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

GRID_US_ASS = 10_000
GRID_US_SRT = 1_000

FORMAT_GRID_US = {"ass": GRID_US_ASS, "srt": GRID_US_SRT}


class InvalidTime(ValueError):
    """Raised when timestamps are negative, unordered, off-grid, or segments overlap."""


def quantize(value: Fraction, grid_us: int) -> int:
    if grid_us <= 0:
        raise InvalidTime(f"bad grid {grid_us}")
    steps = Fraction(value) / grid_us
    return round(steps) * grid_us


@dataclass(frozen=True)
class Segment:
    """Piecewise-linear region: t' = (t - start) * scale + start + offset."""

    start_us: int
    end_us: int | None
    offset_us: int
    scale: Fraction = Fraction(1)

    def apply(self, t_us: int, grid_us: int) -> int:
        value = (
            Fraction(t_us - self.start_us) * self.scale + self.start_us + self.offset_us
        )
        return quantize(value, grid_us)

    def inverse(self, grid_us: int) -> Segment:
        start = self.start_us + self.offset_us
        end = None if self.end_us is None else self.apply(self.end_us, grid_us)
        return Segment(start, end, -self.offset_us, 1 / self.scale)

    def to_dict(self) -> dict:
        num, den = self.scale.as_integer_ratio()
        return {
            "start_us": self.start_us,
            "end_us": self.end_us,
            "offset_us": self.offset_us,
            "scale": [num, den],
        }

    @staticmethod
    def from_dict(d: dict) -> Segment:
        num, den = d["scale"]
        return Segment(
            int(d["start_us"]), d["end_us"], int(d["offset_us"]), Fraction(num, den)
        )


@dataclass(frozen=True)
class CueShift:
    """Per-cue isolated shift applied after the region transform."""

    cue_id: str
    start_delta_us: int
    end_delta_us: int

    def inverse(self) -> CueShift:
        return CueShift(self.cue_id, -self.start_delta_us, -self.end_delta_us)

    def to_dict(self) -> dict:
        return {
            "cue_id": self.cue_id,
            "start_delta_us": self.start_delta_us,
            "end_delta_us": self.end_delta_us,
        }

    @staticmethod
    def from_dict(d: dict) -> CueShift:
        return CueShift(
            str(d["cue_id"]), int(d["start_delta_us"]), int(d["end_delta_us"])
        )


@dataclass(frozen=True)
class Transform:
    segments: tuple[Segment, ...] = ()
    cue_shifts: tuple[CueShift, ...] = ()

    def validate(self) -> None:
        prev_end = 0
        for seg in self.segments:
            if seg.start_us < 0 or seg.start_us % 1:
                raise InvalidTime(f"segment start negative: {seg.start_us}")
            if seg.start_us != prev_end:
                raise InvalidTime(
                    f"segment starts must be contiguous from 0: {seg.start_us} != {prev_end}"
                )
            if seg.end_us is not None and seg.end_us <= seg.start_us:
                raise InvalidTime(f"bad segment span {seg.start_us}..{seg.end_us}")
            prev_end = seg.end_us if seg.end_us is not None else None
        if self.segments and self.segments[-1].end_us is not None:
            raise InvalidTime("last segment must be open-ended")
        for c in self.cue_shifts:
            if c.start_delta_us % 1 or c.end_delta_us % 1:
                raise InvalidTime(f"non-integer cue delta for {c.cue_id}")

    def segment_index_for(self, t_us: int) -> int:
        idx = 0
        for i, s in enumerate(self.segments):
            if t_us >= s.start_us:
                idx = i
        return idx

    def segment_for(self, t_us: int) -> Segment:
        if not self.segments:
            return Segment(0, None, 0, Fraction(1))
        return self.segments[self.segment_index_for(t_us)]

    def cue_shift_for(self, cue_id: str) -> CueShift | None:
        for c in self.cue_shifts:
            if c.cue_id == cue_id:
                return c
        return None

    def apply_time(self, t_us: int, grid_us: int) -> int:
        return self.segment_for(t_us).apply(t_us, grid_us)

    def apply_cue(
        self, cue_id: str, start_us: int, end_us: int, grid_us: int
    ) -> tuple[int, int]:
        # Region membership is decided by the cue START; the region transform is
        # then applied RIGIDLY to both endpoints so cues spanning a breakpoint
        # never split into an unordered span.
        seg = self.segment_for(start_us)
        ns = seg.apply(start_us, grid_us)
        ne = seg.apply(end_us, grid_us)
        shift = self.cue_shift_for(cue_id)
        if shift is not None:
            ns += shift.start_delta_us
            ne += shift.end_delta_us
        if ns < 0 or ne < ns:
            raise InvalidTime(
                f"corruption produced invalid cue span {cue_id}: {ns}..{ne}"
            )
        return ns, ne

    def inverse(
        self, grid_us: int, cue_regions: dict[str, int] | None = None
    ) -> InverseTransform:
        return InverseTransform(
            tuple(s.inverse(grid_us) for s in self.segments),
            tuple(c.inverse() for c in self.cue_shifts),
            dict(cue_regions or {}),
        )

    def to_dict(self) -> dict:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "cue_shifts": [c.to_dict() for c in self.cue_shifts],
        }

    @staticmethod
    def from_dict(d: dict) -> Transform:
        return Transform(
            tuple(Segment.from_dict(s) for s in d.get("segments", [])),
            tuple(CueShift.from_dict(c) for c in d.get("cue_shifts", [])),
        )

    @staticmethod
    def identity() -> Transform:
        return Transform()


@dataclass(frozen=True)
class InverseTransform:
    """Exact inverse of a Transform: undoes cue shifts first, then regions.

    With negative piecewise jumps, later regions can overlap earlier region
    images, so time-domain lookup is ambiguous. Generation records a
    per-cue region correspondence (`cue_regions`); when present it is used
    to select the exact inverse region for each original cue.
    """

    segments: tuple[Segment, ...] = ()
    cue_shifts: tuple[CueShift, ...] = ()
    cue_regions: dict[str, int] = field(default_factory=dict)

    def segment_for(self, t_us: int) -> Segment:
        seg = Segment(0, None, 0, Fraction(1))
        for s in self.segments:
            if t_us >= s.start_us:
                seg = s
        return seg

    def cue_shift_for(self, cue_id: str) -> CueShift | None:
        for c in self.cue_shifts:
            if c.cue_id == cue_id:
                return c
        return None

    def apply_cue(
        self, cue_id: str, start_us: int, end_us: int, grid_us: int
    ) -> tuple[int, int]:
        shift = self.cue_shift_for(cue_id)
        if shift is not None:
            start_us += shift.start_delta_us
            end_us += shift.end_delta_us
        idx = self.cue_regions.get(cue_id)
        seg = (
            self.segments[idx]
            if idx is not None and idx < len(self.segments)
            else self.segment_for(start_us)
        )
        ns = seg.apply(start_us, grid_us)
        ne = seg.apply(end_us, grid_us)
        if ns < 0 or ne < ns:
            raise InvalidTime(f"inverse produced invalid cue span {cue_id}: {ns}..{ne}")
        return ns, ne

    def to_dict(self) -> dict:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "cue_shifts": [c.to_dict() for c in self.cue_shifts],
            "cue_regions": dict(self.cue_regions),
        }

    @staticmethod
    def from_dict(d: dict) -> InverseTransform:
        return InverseTransform(
            tuple(Segment.from_dict(s) for s in d.get("segments", [])),
            tuple(CueShift.from_dict(c) for c in d.get("cue_shifts", [])),
            dict(d.get("cue_regions", {})),
        )
