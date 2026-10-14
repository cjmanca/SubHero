"""Semantic verification boundary: cross-language verdicts, not_run posture,
mock labeling, and mocked-transport HTTP layer (no live network)."""

from __future__ import annotations

from pathlib import Path

import pytest
from bench import validator
from bench.asr import (
    HTTPSemanticVerifier,
    MockSemanticVerifier,
    SemanticVerdict,
    Transcription,
    VerifierUnavailable,
    get_semantic_verifier,
    get_transcriber,
)
from bench.manifests import CaseManifest, ProposalRecord

EN_SUB = "I will protect this city."
JA_MATCH = "この街はわたしが守る"
ZH_MATCH = "这城市我来保护"
EN_OTHER = "The ship departs at dawn"
JA_CONTRADICTION = "翌日の午前10時に出発する"

_ENV_KEYS = (
    "BENCH_SEM_VERIFY_BASE_URL",
    "BENCH_SEM_VERIFY_MODEL",
    "BENCH_SEM_VERIFY_API_KEY",
    "BENCH_ASR_BASE_URL",
    "BENCH_ASR_MODEL",
    "BENCH_ASR_API_KEY",
)


class _FakeASR:
    def __init__(self, texts: dict[str, str], confidence: float = 1.0):
        self.texts = dict(texts)
        self.confidence = confidence

    def transcribe_window(self, wav_path, language, key=None):
        return Transcription(
            text=self.texts[key],
            confidence=self.confidence,
            seconds=0.0,
            model="fake",
            mock=False,
        )


class _RaisingVerifier:
    def verdict(
        self,
        subtitle_text,
        transcript_text,
        subtitle_language_hint,
        transcript_language_hint,
    ):
        raise RuntimeError("verifier endpoint timeout")


def _hand_case(cue_text: dict[str, str]):
    cids = sorted(cue_text)
    original = {
        cid: (1_000_000 + i * 10_000_000, 2_000_000 + i * 10_000_000)
        for i, cid in enumerate(cids)
    }
    corrupted = {
        cid: (s + 5_000_000, e + 5_000_000) for cid, (s, e) in original.items()
    }
    case = CaseManifest(
        case_id="sem-boundary",
        source_id="SEM",
        scenario="S01",
        seed=1,
        track_id="episode",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": "S01", "offset_us": 5_000_000},
        transform={},
        expected_inverse={},
        injected_cue_deltas={cid: (5_000_000, 5_000_000) for cid in cids},
        original_times_us=original,
        true_breakpoints_us=[],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )
    proposal = ProposalRecord(
        "sem-boundary",
        "b1-px-fg",
        "1:1-order-preserving",
        [{"start_us": 0, "end_us": None, "offset_us": -5_000_000}],
        dict(original),
        [],
        "",
    )
    return case, proposal, corrupted


def _validate(tmp_path, monkeypatch, cue_text, transcript, verifier, language):
    monkeypatch.setattr(validator, "extract_audio_window", lambda *a, **k: 0.1)
    case, proposal, corrupted = _hand_case(cue_text)
    asr = _FakeASR({cid: transcript for cid in cue_text})
    acc = validator.validate_proposal(
        case,
        proposal,
        "b1-px-fg",
        corrupted,
        cue_text,
        Path("fake.wav"),
        tmp_path / "run",
        asr,
        language,
        1,
        verifier=verifier,
    )
    return acc, proposal, corrupted


def _clean_env(monkeypatch):
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


# --- cross-language: verifier decides, never lexical --------------------------------


@pytest.mark.parametrize(
    ("transcript", "language"),
    [(JA_MATCH, "ja"), (ZH_MATCH, "zh")],
)
def test_cross_language_verifier_match_accepts(
    tmp_path, monkeypatch, transcript, language
):
    cue_text = {cid: EN_SUB for cid in ("e0000", "e0001", "e0002")}
    verifier = MockSemanticVerifier({EN_SUB: "match"})
    acc, proposal, _corrupted = _validate(
        tmp_path, monkeypatch, cue_text, transcript, verifier, language
    )
    assert acc.status == "success"
    assert len(acc.accepted_regions) == 1
    assert acc.rejected_regions == []
    assert acc.accepted_times_us == proposal.proposed_times_us
    notes_log = (tmp_path / "run" / "asr_notes.log").read_text(encoding="utf-8")
    assert "mock semantic verifier used; test-only" in notes_log
    assert "mock semantic verifier (test-only)" in acc.accepted_regions[0]["reason"]
    assert "mock semantic verifier used (test-only)" in acc.notes


def test_cross_language_verifier_no_match_rejects(tmp_path, monkeypatch):
    cue_text = {cid: EN_OTHER for cid in ("e0000", "e0001", "e0002")}
    verifier = MockSemanticVerifier({EN_OTHER: "no_match"})
    acc, _proposal, corrupted = _validate(
        tmp_path,
        monkeypatch,
        cue_text,
        JA_CONTRADICTION,
        verifier,
        "ja",
    )
    assert acc.status == "success"
    assert len(acc.rejected_regions) == 1
    assert acc.accepted_times_us == corrupted


def test_cross_language_without_verifier_is_not_run_not_rejected(tmp_path, monkeypatch):
    # Regression proof: under the old lexical rule this valid translation
    # (EN subtitle vs ja transcript) was systematically FALSE-REJECTED.
    cue_text = {cid: EN_SUB for cid in ("e0000", "e0001", "e0002")}
    acc, _proposal, corrupted = _validate(
        tmp_path, monkeypatch, cue_text, JA_MATCH, None, "ja"
    )
    assert acc.status == "not_run"
    assert acc.rejected_regions == []
    assert acc.accepted_times_us == corrupted
    assert "semantic verifier not configured (BENCH_SEM_VERIFY_*)" in acc.notes
    assert "cross-language lexical differences are not evidence" in acc.notes


def test_verifier_unknown_abstains_and_reports_no_usable_verdict(tmp_path, monkeypatch):
    cue_text = {cid: EN_SUB for cid in ("e0000", "e0001", "e0002")}
    verifier = MockSemanticVerifier({})  # every subtitle -> unknown
    acc, _proposal, corrupted = _validate(
        tmp_path, monkeypatch, cue_text, JA_MATCH, verifier, "ja"
    )
    assert acc.status == "not_run"
    assert acc.rejected_regions == []
    assert acc.accepted_times_us == corrupted
    assert "no usable verdict (unknown/failure)" in acc.notes


def test_verifier_exception_abstains_and_logs_error(tmp_path, monkeypatch):
    cue_text = {cid: EN_SUB for cid in ("e0000", "e0001", "e0002")}
    acc, _proposal, _corrupted = _validate(
        tmp_path, monkeypatch, cue_text, JA_MATCH, _RaisingVerifier(), "ja"
    )
    assert acc.status == "not_run"
    assert acc.rejected_regions == []
    errors = (tmp_path / "run" / "asr_errors.log").read_text(encoding="utf-8")
    assert "semantic verifier: verifier endpoint timeout" in errors


def test_mock_transcriber_still_forces_abstain_even_with_match_verifier(
    tmp_path, monkeypatch
):
    from bench.asr import MockTranscriber

    monkeypatch.setattr(validator, "extract_audio_window", lambda *a, **k: 0.1)
    cue_text = {cid: EN_SUB for cid in ("e0000", "e0001", "e0002")}
    case, proposal, corrupted = _hand_case(cue_text)
    mock_asr = MockTranscriber({cid: JA_MATCH for cid in cue_text})
    verifier = MockSemanticVerifier({EN_SUB: "match"})
    acc = validator.validate_proposal(
        case,
        proposal,
        "b1-px-fg",
        corrupted,
        cue_text,
        Path("fake.wav"),
        tmp_path / "run-mock-asr",
        mock_asr,
        "ja",
        1,
        verifier=verifier,
    )
    assert acc.status == "abstain"
    assert acc.accepted_regions == []
    assert acc.accepted_times_us == corrupted


# --- HTTP layer: mocked transport only -------------------------------------------


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


def _chat_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_http_verifier_posts_to_configured_local_chat_completions(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("BENCH_SEM_VERIFY_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setenv("BENCH_SEM_VERIFY_MODEL", "local-verify")
    monkeypatch.setenv("BENCH_SEM_VERIFY_API_KEY", "sekret")
    calls: list[dict] = []

    def _fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        calls.append({"url": url, "headers": headers, "json": json})
        return _FakeResponse(_chat_response('{"verdict": "match"}'))

    import requests

    monkeypatch.setattr(requests, "post", _fake_post)
    verifier = get_semantic_verifier()
    assert isinstance(verifier, HTTPSemanticVerifier)
    verdict = verifier.verdict(EN_SUB, JA_MATCH, "en", "ja")
    assert verdict.verdict == "match"
    assert verdict.mock is False
    call = calls[0]
    assert call["url"] == "http://127.0.0.1:9999/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer sekret"
    assert call["json"]["model"] == "local-verify"
    prompt = call["json"]["messages"][0]["content"]
    assert EN_SUB in prompt and JA_MATCH in prompt
    assert '"verdict"' in prompt
    assert "translation" in prompt.lower()


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ('{"verdict": "match"}', "match"),
        ('{"verdict": "no_match"}', "no_match"),
        ('{"verdict": "unknown"}', "unknown"),
        ('Sure! {"verdict": "match"} thanks', "match"),
        ("not json at all", "unknown"),
        ('{"verdict": "banana"}', "unknown"),
        ("{}", "unknown"),
        ("", "unknown"),
    ],
)
def test_http_verifier_parses_defensively(monkeypatch, content, expected):
    _clean_env(monkeypatch)
    monkeypatch.setenv("BENCH_SEM_VERIFY_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setenv("BENCH_SEM_VERIFY_MODEL", "local-verify")

    def _fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        return _FakeResponse(_chat_response(content))

    import requests

    monkeypatch.setattr(requests, "post", _fake_post)
    verdict = HTTPSemanticVerifier().verdict("sub", "transcript", "en", "ja")
    assert verdict.verdict == expected


def test_http_verifier_missing_payload_structure_is_unknown(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("BENCH_SEM_VERIFY_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setenv("BENCH_SEM_VERIFY_MODEL", "local-verify")

    def _fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        return _FakeResponse({"choices": []})

    import requests

    monkeypatch.setattr(requests, "post", _fake_post)
    verdict = HTTPSemanticVerifier().verdict("sub", "t", "en", "ja")
    assert verdict == SemanticVerdict(
        verdict="unknown", seconds=verdict.seconds, model="local-verify", mock=False
    )


def test_getters_are_independent_and_none_when_unconfigured(monkeypatch):
    _clean_env(monkeypatch)
    assert get_semantic_verifier() is None
    assert get_transcriber() is None
    # ASR configured, semantic verifier not: transcriber only.
    monkeypatch.setenv("BENCH_ASR_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("BENCH_ASR_MODEL", "asr-model")
    assert get_transcriber() is not None
    assert get_semantic_verifier() is None
    # Semantic verifier configured, ASR cleared: verifier only.
    monkeypatch.delenv("BENCH_ASR_BASE_URL")
    monkeypatch.delenv("BENCH_ASR_MODEL")
    monkeypatch.setenv("BENCH_SEM_VERIFY_BASE_URL", "http://127.0.0.1:8100/v1")
    monkeypatch.setenv("BENCH_SEM_VERIFY_MODEL", "verify-model")
    assert get_semantic_verifier() is not None
    assert get_transcriber() is None


def test_partial_env_raises_verifier_unavailable(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("BENCH_SEM_VERIFY_BASE_URL", "http://127.0.0.1:8100/v1")
    with pytest.raises(VerifierUnavailable):
        HTTPSemanticVerifier()
