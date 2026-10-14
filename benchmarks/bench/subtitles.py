"""Canonical cue model over ASS/SRT with stable event identity.

Cue IDs (`eNNNN`) are assigned by event order when loading a file; every
benchmark transformation preserves event count and order, so IDs stay stable.
Only timing fields are ever modified; text, styles, layers, effects and
formatting are round-tripped through pysubs2 untouched. ASS event files keep
stable identity. SRT identity assumes standard time-ordered source files:
because SRT writers re-sort by start time, a deliberately out-of-order SRT
source is not a supported benchmark track type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pysubs2

from .timeline import FORMAT_GRID_US, InvalidTime


@dataclass
class Cue:
    cue_id: str
    start_us: int
    end_us: int
    text: str
    style: str = "Default"
    layer: int = 0
    order: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


def _detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".ass":
        return "ass"
    if suffix == ".srt":
        return "srt"
    if suffix == ".ssa":
        return "ass"
    raise ValueError(f"unsupported subtitle format: {path}")


@dataclass
class Track:
    source_path: Path
    format: str
    grid_us: int
    cues: list[Cue]

    @staticmethod
    def load(path: Path, fmt: str | None = None) -> Track:
        fmt = fmt or _detect_format(path)
        grid = FORMAT_GRID_US[fmt]
        doc = pysubs2.SSAFile.load(path, format=fmt, keep_privates=True)
        cues: list[Cue] = []
        for i, ev in enumerate(doc.events):
            cues.append(
                Cue(
                    cue_id=f"e{i:04d}",
                    start_us=ev.start * 1000,
                    end_us=ev.end * 1000,
                    text=ev.text,
                    style=ev.style,
                    layer=ev.layer,
                    order=i,
                    extra={"source_order": i},
                )
            )
        return Track(path, fmt, grid, cues)

    def save_with_times(
        self, out_path: Path, times: dict[str, tuple[int, int]]
    ) -> None:
        doc = pysubs2.SSAFile.load(
            self.source_path, format=self.format, keep_privates=True
        )
        source_index = {c.cue_id: c.extra["source_order"] for c in self.cues}
        for cue in self.cues:
            start_us, end_us = times.get(cue.cue_id, (cue.start_us, cue.end_us))
            if start_us < 0 or end_us < start_us:
                raise InvalidTime(
                    f"refusing to write invalid span {cue.cue_id}: {start_us}..{end_us}"
                )
            if start_us % self.grid_us or end_us % self.grid_us:
                raise InvalidTime(
                    f"times off {self.format} grid ({self.grid_us} us): {cue.cue_id} {start_us}..{end_us}"
                )
            ev = doc.events[source_index[cue.cue_id]]
            ev.start = start_us // 1000
            ev.end = end_us // 1000
        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(out_path, format=self.format)

    def time_map(self) -> dict[str, tuple[int, int]]:
        return {c.cue_id: (c.start_us, c.end_us) for c in self.cues}
