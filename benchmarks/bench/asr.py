"""Bounded targeted-ASR integration boundary (local, explicitly configured only).

No cloud/external inference is ever contacted. If no endpoint is configured,
`get_transcriber()` returns None and dependent experiments record `not_run`.
Mock transcribers exist for tests only and are labeled as mocks everywhere.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Transcription:
    text: str
    confidence: float
    seconds: float
    model: str
    mock: bool = False


class TranscriberUnavailable(RuntimeError):
    pass


class MockTranscriber:
    """Test double; requires explicit canned utterances. Never used for real reports."""

    def __init__(self, utterances: dict[str, str], model: str = "mock"):
        self.utterances = dict(utterances)
        self.model = model

    def transcribe_window(
        self, wav_path: Path, language: str, key: str | None = None
    ) -> Transcription:
        started = time.monotonic()
        text = self.utterances.get(key or str(wav_path), "")
        return Transcription(
            text=text,
            confidence=1.0,
            seconds=time.monotonic() - started,
            model=self.model,
            mock=True,
        )


class HTTPLocalTranscriber:
    """OpenAI-compatible `/audio/transcriptions` on an explicitly configured LOCAL endpoint.

    Configuration is opt-in via environment variables; nothing is contacted
    unless BENCH_ASR_BASE_URL and BENCH_ASR_MODEL are set. Media/audio leaves
    the machine only to that endpoint, so users must confirm it is local and
    permitted for private media before configuring it.
    """

    def __init__(self) -> None:
        self.base_url = os.environ.get("BENCH_ASR_BASE_URL", "").rstrip("/")
        self.model = os.environ.get("BENCH_ASR_MODEL", "")
        self.api_key = os.environ.get("BENCH_ASR_API_KEY", "")
        if not self.base_url or not self.model:
            raise TranscriberUnavailable(
                "BENCH_ASR_BASE_URL/BENCH_ASR_MODEL not configured"
            )

    def transcribe_window(
        self, wav_path: Path, language: str, key: str | None = None
    ) -> Transcription:
        import requests

        started = time.monotonic()
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        with open(wav_path, "rb") as fh:
            resp = requests.post(
                f"{self.base_url}/audio/transcriptions",
                headers=headers,
                files={"file": (wav_path.name, fh, "audio/wav")},
                data={
                    "model": self.model,
                    "language": language,
                    "response_format": "verbose_json",
                },
                timeout=300,
            )
        secs = time.monotonic() - started
        resp.raise_for_status()
        payload = resp.json()
        segments = payload.get("segments") or []
        confidence = float(segments[0].get("avg_logprob", -1.0)) if segments else -1.0
        return Transcription(
            text=payload.get("text", ""),
            confidence=confidence,
            seconds=secs,
            model=self.model,
        )


def get_transcriber():
    try:
        return HTTPLocalTranscriber()
    except TranscriberUnavailable:
        return None
