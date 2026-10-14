"""Dialogue-only synchronization proxy with cue-ID correspondence.

Styled ASS tracks must not be fed blindly into audio-alignment tools: signs,
karaoke/songs, SDH sound descriptions and other non-speech events are
excluded as anchors. The proxy keeps explicit correspondence to original cue
IDs; proposals project back only onto cues present in the proxy. A
signs-only track with no speech anchors is unmapped (abstain), never given
an invented speech-derived map. Rigid shifts are preferred; animation
stretching is not performed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pysubs2

from .manifests import write_json
from .subtitles import Cue, Track

NON_SPEECH_STYLE_RE = re.compile(
    r"(?i)\b(sign|karaoke|song|music|notes?|credits?|editor|op|ed)\b"
)
KARAOKE_RE = re.compile(r"\{[^}]*\\k")
MUSIC_RE = re.compile("[\u266a\u266b\u266c\u1d17\U0001d17f]")
BRACKET_DESC_RE = re.compile(r"^\s*[\[(<{][^\])>}]*[\])>}]")


@dataclass
class ProxyMapping:
    proxy_index_to_cue: list[str]
    cue_to_proxy_index: dict[str, int]

    def to_json(self) -> dict:
        return {
            "schema_version": 1,
            "proxy_index_to_cue_id": self.proxy_index_to_cue,
            "cue_id_to_proxy_index": self.cue_to_proxy_index,
        }


def classify_cue(cue: Cue, gold: dict[str, str] | None = None) -> str:
    """Conservative speech-like vs non-speech classification.

    Gold classification labels (from verified fixture/corpus annotations)
    take precedence when the corpus provides them for benchmark use. This is
    evaluation reference data: DEFAULT candidates must never receive gold
    labels, because that leaks ground-truth answers into ordinary
    synchronization candidates. The control lives at the cli/adapters
    boundary — `run_candidate` accepts a gold path only for the
    oracle-assisted diagnostic arms (b1-pxo-*) and ignores it for every
    default candidate, including b1-px-fg/b1-px-fp, which classify anchors
    with these heuristics only.
    """
    if gold is not None and cue.cue_id in gold:
        return gold[cue.cue_id]
    text = cue.text
    if KARAOKE_RE.search(text) or MUSIC_RE.search(text):
        return "non_speech"
    if NON_SPEECH_STYLE_RE.search(cue.style):
        return "non_speech"
    if BRACKET_DESC_RE.match(text.replace("\\N", "\n").split("\n")[0].strip()):
        return "non_speech"
    return "speech_like"


def build_proxy(
    track: Track,
    out_srt: Path,
    mapping_json: Path,
    gold_classification_path: Path | None = None,
) -> ProxyMapping:
    gold: dict[str, str] | None = None
    if gold_classification_path is not None and Path(gold_classification_path).exists():
        import json

        gold = json.loads(Path(gold_classification_path).read_text(encoding="utf-8"))

    selected: list[Cue] = []
    for cue in track.cues:
        if classify_cue(cue, gold) == "speech_like":
            selected.append(cue)
    selected.sort(key=lambda c: (c.start_us, c.end_us, c.cue_id))

    mapping = ProxyMapping(
        proxy_index_to_cue=[c.cue_id for c in selected],
        cue_to_proxy_index={c.cue_id: i for i, c in enumerate(selected)},
    )

    doc = pysubs2.SSAFile()
    for cue in selected:
        doc.events.append(
            pysubs2.SSAEvent(
                start=cue.start_us // 1000, end=cue.end_us // 1000, text=cue.text
            )
        )
    out_srt.parent.mkdir(parents=True, exist_ok=True)
    from .paths import ensure_scratch_path

    ensure_scratch_path(out_srt)
    doc.save(out_srt, format="srt")
    write_json(mapping_json, mapping.to_json())
    return mapping


def fit_regions(
    deltas_by_time: list[tuple[int, int]], grid_us: int, tol_us: int
) -> list[dict]:
    """Estimate global/region-level offsets from per-cue proposed deltas.

    Intentionally simple and explicit: single global offset (median) when the
    deltas do not step; otherwise split where consecutive cue deltas step by
    more than 2*tol and each resulting run spans at least 3 cues. This is a
    measured estimator for scoring, not a production mapper.
    """
    if not deltas_by_time:
        return []
    deltas_by_time = sorted(deltas_by_time)
    values = [d for _, d in deltas_by_time]
    import statistics

    global_offset = statistics.median(values)
    step = 2 * tol_us + 1
    cuts: list[int] = []
    for i in range(1, len(values)):
        if abs(values[i] - values[i - 1]) > step:
            cuts.append(i)
    segments: list[tuple[int, int]] = []
    prev = 0
    for c in cuts:
        if c > prev:
            segments.append((prev, c))
        prev = c
    if len(values) > prev:
        segments.append((prev, len(values)))
    merged: list[tuple[int, int]] = []
    for seg in segments:
        merged.append(seg)
        while len(merged) > 1 and (merged[-1][1] - merged[-1][0]) < 3:
            tail = merged.pop()
            merged[-1] = (merged[-1][0], tail[1])
    runs = merged
    if not runs:
        return [
            {
                "start_us": deltas_by_time[0][0],
                "end_us": deltas_by_time[-1][0],
                "offset_us": int(global_offset),
                "kind": "global",
                "confidence": "global-median",
            }
        ]
    regions = []
    kind = "global" if len(runs) == 1 else "piecewise"
    for a, b in runs:
        seg = deltas_by_time[a:b]
        regions.append(
            {
                "start_us": seg[0][0],
                "end_us": seg[-1][0],
                "offset_us": int(statistics.median(v for _, v in seg)),
                "kind": kind,
                "confidence": "run-median",
            }
        )
    return regions
