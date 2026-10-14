"""Generate the small redistributable synthetic fixture Fx00 (self-authored).

Everything here is synthetic: invented text and tone bursts. It exercises the
pipeline plumbing (transformation determinism, proxy mapping, adapter I/O,
scoring math). It does NOT contain speech and validates NO real synchronization
accuracy. Regenerating with the same inputs produces byte-identical files.

Usage:  python benchmarks/fixtures/make_fixture.py
"""

from __future__ import annotations

import hashlib
import wave
from pathlib import Path

import numpy as np
import pysubs2

HERE = Path(__file__).resolve().parent
OUT = HERE / "Fx00"
DURATION_S = 60
SAMPLE_RATE = 8000

DIALOGUE = [
    (2_000, 5_000, "Opening line, hello there."),
    (6_000, 9_000, "The kettle is whistling again."),
    (10_000, 13_500, "I heard that too."),
    (14_000, 17_000, "Did you finish the chapter?"),
    (18_000, 21_000, "Almost. Two more pages."),
    (21_500, 24_000, "The rain has started."),
    (24_500, 27_500, "Perfect weather for staying in."),
    (28_000, 31_000, "Pass me the tea, please."),
    (31_500, 35_000, "It is hot. Careful."),
    (36_000, 39_000, "The kettle is whistling again."),
    (40_000, 43_000, "That is the third time today."),
    (44_000, 47_000, "Someone must be thirsty."),
    (48_000, 51_000, "I will make fresh leaves."),
    (51_500, 54_000, "Bring the second cup too."),
    (54_500, 57_000, "Here you are. Enjoy the quiet."),
]
SIGNS = [
    (3_000, 6_500, "TITLE: KETTLE DAYS"),
    (20_000, 23_000, "NOTE: written on the shop window"),
    (33_000, 36_500, "SIGN: tea leaves, second shelf"),
    (45_000, 48_500, "Letter on the table: leave soon"),
    (55_500, 59_000, "END CARD: to be continued"),
]
KARAOKE = [
    (12_000, 15_000, r"{\k100}Sing{\k100}ing {\k100}loud"),
    (49_000, 52_000, "♪ La la la, the kettle song ♪"),
]
SDH = [
    (7_500, 9_500, "[door slams]"),
    (26_000, 28_000, "[distant thunder]"),
]
SIGNS_ONLY = [
    (5_000, 9_000, "SHOP WINDOW: fresh leaves today"),
    (16_000, 20_000, "MAP drawn in pencil"),
    (30_000, 34_000, "NEWSPAPER headline: rains return"),
    (43_000, 46_000, "NOTE pinned by the door"),
    (56_000, 59_500, "END TITLE: see you next week"),
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_episode_ass(path: Path) -> None:
    doc = pysubs2.SSAFile()
    doc.info["Title"] = "Fx00 synthetic fixture"
    doc.info["ScriptType"] = "V4.00+"
    for name in ("Dialogue", "Sign", "Karaoke", "SDH"):
        doc.styles[name] = pysubs2.SSAStyle(
            fontname="DejaVu Sans",
            fontsize=28,
            primarycolor=pysubs2.Color(255, 255, 255),
        )
    events = []
    for s, e, t in DIALOGUE:
        events.append(
            pysubs2.SSAEvent(start=s, end=e, text=t, style="Dialogue", layer=0)
        )
    for s, e, t in SIGNS:
        events.append(pysubs2.SSAEvent(start=s, end=e, text=t, style="Sign", layer=1))
    for s, e, t in KARAOKE:
        events.append(
            pysubs2.SSAEvent(start=s, end=e, text=t, style="Karaoke", layer=2)
        )
    for s, e, t in SDH:
        events.append(pysubs2.SSAEvent(start=s, end=e, text=t, style="SDH", layer=1))
    doc.events = sorted(events, key=lambda ev: (ev.start, ev.end))
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path, format="ass")


def build_signs_only_ass(path: Path) -> None:
    doc = pysubs2.SSAFile()
    doc.styles["Sign"] = pysubs2.SSAStyle(fontname="DejaVu Sans", fontsize=26)
    for s, e, t in SIGNS_ONLY:
        doc.events.append(
            pysubs2.SSAEvent(start=s, end=e, text=t, style="Sign", layer=1)
        )
    doc.save(path, format="ass")


def build_reference_wav(path: Path) -> None:
    rng = np.random.default_rng(20260001)
    n = DURATION_S * SAMPLE_RATE
    samples = (rng.random(n) * 2 - 1) * 120
    for s_ms, e_ms, _ in DIALOGUE:
        a, b = int((s_ms / 1000) * SAMPLE_RATE), int((e_ms / 1000) * SAMPLE_RATE)
        t = np.arange(b - a) / SAMPLE_RATE
        burst = (
            np.sin(2 * np.pi * 300 * t)
            * 9000
            * (0.6 + 0.4 * np.sin(2 * np.pi * 2.5 * t))
        ).astype(np.int16)
        samples[a:b] = burst
    samples = samples.astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(samples.tobytes())


def build_gold(path: Path, cues: list[tuple[int, int, str, str]]) -> None:
    import json

    ordered = sorted(cues, key=lambda c: (c[0], c[1]))
    labels = {
        f"e{i:04d}": ("speech_like" if style == "Dialogue" else "non_speech")
        for i, (_, _, _, style) in enumerate(ordered)
    }
    path.write_text(
        json.dumps(labels, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    episode = OUT / "episode.ass"
    signs = OUT / "signs.ass"
    wav = OUT / "reference.wav"
    build_episode_ass(episode)
    build_signs_only_ass(signs)
    build_reference_wav(wav)

    doc = pysubs2.SSAFile.load(episode, format="ass")
    episode_cues = [(ev.start, ev.end, ev.text, ev.style) for ev in doc.events]
    build_gold(OUT / "gold_episode.json", episode_cues)
    doc2 = pysubs2.SSAFile.load(signs, format="ass")
    signs_cues = [(ev.start, ev.end, ev.text, ev.style) for ev in doc2.events]
    build_gold(OUT / "gold_signs.json", signs_cues)

    import json

    manifest = {
        "schema_version": 1,
        "fixture_id": "Fx00",
        "synthetic": True,
        "contains_real_speech": False,
        "purpose": "pipeline plumbing smoke tests only; no speech-synchronization validity",
        "duration_s": DURATION_S,
        "audio": {
            "sample_rate": SAMPLE_RATE,
            "content": "tone bursts in dialogue windows, silence elsewhere",
        },
        "files": {
            p.name: _sha(p)
            for p in sorted(OUT.glob("*"))
            if p.is_file() and p.name != "manifest.json"
        },
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"fixture written to {OUT}")
    for k, v in manifest["files"].items():
        print(f"  {k}: sha256 {v[:16]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
