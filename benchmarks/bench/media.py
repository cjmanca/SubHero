"""Read-only media probing/fingerprinting and scratch-only derivations.

Source media is never written. Derived audio/artifacts must land under an
explicit scratch root (outside registered source trees and library roots).
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .paths import ensure_scratch_path


class ToolMissing(FileNotFoundError):
    pass


def _tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise ToolMissing(f"{name} not found on PATH")
    return found


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def ffprobe_streams(media_path: Path) -> dict[str, Any]:
    ffprobe = _tool("ffprobe")
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {proc.stderr.strip()}")
    return __import__("json").loads(proc.stdout)


def extract_audio(
    media_path: Path,
    out_wav: Path,
    sample_rate: int = 16000,
    audio_stream: str | None = None,
) -> float:
    """Decode reference audio to scratch wav; returns wall seconds."""
    import time

    ffmpeg = _tool("ffmpeg")
    ensure_scratch_path(out_wav)
    map_args = ["-map", audio_stream] if audio_stream else ["-map", "0:a:0"]
    started = time.monotonic()
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(media_path),
            *map_args,
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "wav",
            str(out_wav),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"audio extraction failed: {proc.stderr.strip()}")
    return time.monotonic() - started


def extract_audio_window(
    media_path: Path,
    out_wav: Path,
    start_s: float,
    end_s: float,
    audio_stream: str | None = None,
) -> float:
    import time

    ffmpeg = _tool("ffmpeg")
    ensure_scratch_path(out_wav)
    if start_s < 0 or end_s <= start_s:
        raise ValueError(f"bad window {start_s}..{end_s}")
    map_args = ["-map", audio_stream] if audio_stream else ["-map", "0:a:0"]
    started = time.monotonic()
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-ss",
            f"{start_s:.3f}",
            "-to",
            f"{end_s:.3f}",
            "-i",
            str(media_path),
            *map_args,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            str(out_wav),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"audio window extraction failed: {proc.stderr.strip()}")
    return time.monotonic() - started


def extract_subtitle_stream(media_path: Path, sidx: int, out_ass: Path) -> None:
    """Copy one embedded subtitle stream out of the container into scratch (read-only input).

    ``sidx`` is the ffmpeg **subtitle-relative** index used in ``-map 0:s:<sidx>``:
    the 0-based position of the stream among subtitle streams in ffprobe order.
    It is **not** the ffprobe global stream index; callers resolve global-index
    and language specs to this ``sidx`` once, at source registration, and persist
    the normalized identity.
    """
    ffmpeg = _tool("ffmpeg")
    ensure_scratch_path(out_ass)
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(media_path),
            "-map",
            f"0:s:{int(sidx)}",
            "-c:s",
            "ass",
            str(out_ass),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"subtitle stream extraction failed: {proc.stderr.strip()}")
