"""Bounded targeted-ASR integration boundary (local, explicitly configured only).

No cloud/external inference is ever contacted. If no endpoint is configured,
`get_transcriber()` returns None and dependent experiments record `not_run`.
Mock transcribers exist for tests only and are labeled as mocks everywhere.

Translation-assisted semantic verification is INDEPENDENTLY configured:
transcription uses `BENCH_ASR_*`; semantic match/no-match judgments use
`BENCH_SEM_VERIFY_*`. Cross-language subtitle/transcript pairs are never
decided lexically; they require an explicitly configured semantic verifier,
otherwise the validator abstains.
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


@dataclass
class SemanticVerdict:
    verdict: str  # "match" | "no_match" | "unknown"
    seconds: float
    model: str
    mock: bool = False


class TranscriberUnavailable(RuntimeError):
    pass


class VerifierUnavailable(RuntimeError):
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


def _parse_verdict(content: str) -> str:
    """Defensively parse strict JSON verdict output; unparseable -> unknown."""
    import json
    import re

    match = re.search(r"\{[^{}]*\}", content or "", re.DOTALL)
    if not match:
        return "unknown"
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return "unknown"
    value = data.get("verdict") if isinstance(data, dict) else None
    return value if value in ("match", "no_match", "unknown") else "unknown"


class MockSemanticVerifier:
    """Test double returning canned verdicts keyed by subtitle text. Test-only; the CLI never wires it."""

    def __init__(self, answers: dict[str, str], model: str = "mock-verifier"):
        self.answers = dict(answers)
        self.model = model

    def verdict(
        self,
        subtitle_text: str,
        transcript_text: str,
        subtitle_language_hint: str,
        transcript_language_hint: str,
    ) -> SemanticVerdict:
        started = time.monotonic()
        return SemanticVerdict(
            verdict=self.answers.get(subtitle_text, "unknown"),
            seconds=time.monotonic() - started,
            model=self.model,
            mock=True,
        )


class HTTPSemanticVerifier:
    """OpenAI-compatible `/chat/completions` semantic judgment on an explicitly configured LOCAL endpoint.

    Configuration is opt-in via environment variables; nothing is contacted
    unless BENCH_SEM_VERIFY_BASE_URL and BENCH_SEM_VERIFY_MODEL are set.
    Subtitle and transcript text leaves the machine only to that endpoint,
    so users must confirm it is local and permitted for private media
    before configuring it. This boundary is independent of transcription
    (`BENCH_ASR_*`); configuring one does not configure the other.
    """

    def __init__(self) -> None:
        self.base_url = os.environ.get("BENCH_SEM_VERIFY_BASE_URL", "").rstrip("/")
        self.model = os.environ.get("BENCH_SEM_VERIFY_MODEL", "")
        self.api_key = os.environ.get("BENCH_SEM_VERIFY_API_KEY", "")
        if not self.base_url or not self.model:
            raise VerifierUnavailable(
                "BENCH_SEM_VERIFY_BASE_URL/BENCH_SEM_VERIFY_MODEL not configured"
            )

    def verdict(
        self,
        subtitle_text: str,
        transcript_text: str,
        subtitle_language_hint: str,
        transcript_language_hint: str,
    ) -> SemanticVerdict:
        import requests

        started = time.monotonic()
        prompt = (
            "Decide whether the TRANSCRIPT and the SUBTITLE describe the SAME "
            "spoken utterance/meaning. They may be in different languages "
            f"(subtitle language hint: {subtitle_language_hint}; transcript "
            "language hint: "
            f"{transcript_language_hint}); a faithful translation of the same "
            "utterance is a match, and shared words, spelling, or script are "
            "NOT required. Semantic contradiction is no_match; undecidable is "
            'unknown. Reply with ONLY strict JSON: {"verdict": '
            '"match"|"no_match"|"unknown"}\n\n'
            f"SUBTITLE: {subtitle_text}\nTRANSCRIPT: {transcript_text}"
        )
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            },
            timeout=120,
        )
        secs = time.monotonic() - started
        resp.raise_for_status()
        payload = resp.json()
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = ""
        return SemanticVerdict(
            verdict=_parse_verdict(content),
            seconds=secs,
            model=self.model,
            mock=False,
        )


def get_semantic_verifier():
    try:
        return HTTPSemanticVerifier()
    except VerifierUnavailable:
        return None
