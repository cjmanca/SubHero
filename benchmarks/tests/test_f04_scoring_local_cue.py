"""Third-review F04 + F05 + F06 + F07 focused regressions (scoring/reporting).

F04: perfect isolated-cue repairs (transient, reversing corrections) score as
``local_cue_adjustments`` with ZERO release-break false positives, while
sustained regional steps keep their claims and bracketing credit.

F05: with a valid bound run/score pair, deleting the source registry (or the
case manifest) makes ``report`` fail CLOSED: the rows appear only in the
labeled, non-comparative *Unverified historical results* section, never as
current comparative numbers.

F06: arms without any validator never get "accepted" labels — they carry
``*_if_blindly_applied`` counts and ``final_semantics``; the b1-va arm carries
accepted names. The report renders the semantics explicitly.

F07: semantic-verifier wall time and call counts are recorded separately from
ASR time (fake transcriber/verifier with distinct known durations).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from bench import cli
from bench.asr import MockTranscriber, SemanticVerdict, Transcription
from bench.manifests import CaseManifest, ProposalRecord
from bench.scoring import Tolerances, score_case
from bench.subtitles import Track
from bench.validator import validate_proposal

FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg required")

SECOND = 1_000_000
TOL = Tolerances(good_us=50_000, severe_us=250_000, break_match_us=500_000)
ASR_ENV = (
    "BENCH_ASR_BASE_URL",
    "BENCH_ASR_MODEL",
    "BENCH_ASR_API_KEY",
    "BENCH_SEM_VERIFY_BASE_URL",
    "BENCH_SEM_VERIFY_MODEL",
    "BENCH_SEM_VERIFY_API_KEY",
)


def _ffmpeg(*args: str) -> None:
    import subprocess

    subprocess.run(
        [FFMPEG, "-y", "-v", "error", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _build_mkv(tmp_path: Path) -> Path:
    media_dir = tmp_path / "media"
    media_dir.mkdir(exist_ok=True)
    out = media_dir / "episode.mkv"
    a440 = tmp_path / "e-440.wav"
    a880 = tmp_path / "e-880.wav"
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2",
        "-c:a",
        "pcm_s16le",
        str(a440),
    )
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=880:duration=2",
        "-c:a",
        "pcm_s16le",
        str(a880),
    )
    _ffmpeg(
        "-i",
        str(a440),
        "-i",
        str(a880),
        "-map",
        "0:a:0",
        "-map",
        "1:a:0",
        "-c:a",
        "pcm_s16le",
        "-metadata:s:a:0",
        "language=jpn",
        "-metadata:s:a:1",
        "language=eng",
        str(out),
    )
    return out


def _cli_add(
    root: Path, media: Path, extra: tuple[str, ...], source_id: str = "MS"
) -> int:
    return cli.main(
        [
            "--root",
            str(root),
            "source",
            "add",
            "--path",
            str(media),
            "--source-id",
            source_id,
            "--rights",
            "private-local",
            *extra,
        ]
    )


def _setup(tmp_path: Path, fixture_dir: Path) -> Path:
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    sidecar = tmp_path / "episode.ass"
    shutil.copy2(fixture_dir / "episode.ass", sidecar)
    assert (
        _cli_add(
            root,
            media,
            ("--audio", "lang:eng", "--subtitle", f"main=sidecar:{sidecar}"),
        )
        == 0
    )
    return root


def _prepare(root: Path, case_id: str, scenario: str, seed: int) -> int:
    return cli.main(
        [
            "--root",
            str(root),
            "case",
            "prepare",
            "--source-id",
            "MS",
            "--track-id",
            "main",
            "--scenario",
            scenario,
            "--seed",
            str(seed),
            "--case-id",
            case_id,
        ]
    )


def _run(root: Path, case_id: str, cand: str = "b1-n") -> int:
    return cli.main(
        ["--root", str(root), "run", "--case", case_id, "--candidate", cand]
    )


def _run_va(root: Path, case_id: str) -> int:
    return cli.main(
        [
            "--root",
            str(root),
            "run",
            "--case",
            case_id,
            "--candidate",
            "b1-va",
            "--base-candidate",
            "b1-n",
        ]
    )


def _score(root: Path, case_id: str, cand: str) -> int:
    return cli.main(
        ["--root", str(root), "score", "--case", case_id, "--candidate", cand]
    )


def _report(root: Path, case_id: str) -> tuple[int, str]:
    rc = cli.main(["--root", str(root), "report", "--case", case_id])
    return rc, (root / "results" / "report.md").read_text(encoding="utf-8")


def _cand_dir(root: Path, case_id: str, cand: str) -> Path:
    return root / "results" / case_id / cand


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _cue_text(root: Path, case_id: str) -> dict[str, str]:
    paths = cli._paths(root)
    case = cli._load_case(cli._lookup_case_path(paths, case_id))
    track = Track.load(cli._resolve_generated(paths, case), case.fmt)
    return {c.cue_id: c.text for c in track.cues}


def _mock_va(monkeypatch, cue_text: dict[str, str]):
    for var in ASR_ENV:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(cli, "get_transcriber", lambda: MockTranscriber(dict(cue_text)))
    monkeypatch.setattr(cli, "get_semantic_verifier", lambda: None)


def _mk_case(case_id: str, original: dict, true_breaks: list[int], deltas: dict):
    return CaseManifest(
        case_id=case_id,
        source_id="S",
        scenario="S04",
        seed=1,
        track_id="ep",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": "S04"},
        transform={},
        expected_inverse={},
        injected_cue_deltas={cid: (d, d) for cid, d in deltas.items()},
        original_times_us=dict(original),
        true_breakpoints_us=list(true_breaks),
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )


def _shift(corrupted: dict, applied: dict) -> dict:
    return {
        cid: (s + applied[cid], e + applied[cid]) for cid, (s, e) in corrupted.items()
    }


def _proposal(case_id: str, proposed: dict) -> ProposalRecord:
    return ProposalRecord(
        case_id,
        "b1-test",
        "1:1-order-preserving",
        [{"start_us": 0, "end_us": None, "offset_us": 0}],
        proposed,
        [],
        "",
    )


# ---------------------------------------------------------------------------
# F04 — isolated cue repair vs release discontinuities
# ---------------------------------------------------------------------------


def _three_cues():
    original = {
        "e0000": (1 * SECOND, 2 * SECOND),
        "e0001": (10 * SECOND, 11 * SECOND),
        "e0002": (20 * SECOND, 21 * SECOND),
    }
    corrupted = dict(original)
    corrupted["e0001"] = (12 * SECOND, 13 * SECOND)  # S04 isolated +2 s shift
    return original, corrupted


def test_perfect_isolated_s04_repair_has_zero_release_breaks():
    original, corrupted = _three_cues()
    case = _mk_case(
        "f04-solo", original, [], {"e0000": 0, "e0001": 2 * SECOND, "e0002": 0}
    )
    # Ideal inverse: only the middle cue moves back by -2 s; neighbors untouched.
    perfect = _proposal(
        case.case_id, _shift(corrupted, {"e0000": 0, "e0001": -2 * SECOND, "e0002": 0})
    )
    score = score_case(case, perfect, corrupted, None, TOL)
    dis = score["discontinuities"]
    # Before the fix: the [0, -2 s, 0] delta pair implied TWO false release
    # discontinuities. After: zero implied breaks, zero false positives.
    assert dis["detected_breakpoints"] == 0
    assert dis["implied_breakpoint_times_us"] == []
    assert dis["false_positive_breakpoints"] == 0
    assert dis["ambiguous_breakpoints"] == 0
    # The repair itself is credited, and recorded as a local cue adjustment.
    assert dis["local_cue_adjustments"] == 1
    assert dis["local_cue_adjusted_cue_ids"] == ["e0001"]
    assert score["counts"]["repaired_if_blindly_applied"] == 1
    assert score["counts"]["worsened_unaltered_if_blindly_applied"] == 0
    assert score["timing_errors_final_us"]["max_abs_us"] == 0


def test_two_isolated_shifts_score_as_two_local_adjustments_zero_breaks():
    # Five cues; isolated shifts on cues 1 and 3, with the unshifted cue 2 and
    # unshifted ends giving stable equal support on BOTH sides of every shifted
    # block: [0, -2, 0, -3, 0] is two transient local corrections, zero
    # release discontinuities.
    original = {
        "e0000": (1 * SECOND, 2 * SECOND),
        "e0001": (10 * SECOND, 11 * SECOND),
        "e0002": (20 * SECOND, 21 * SECOND),
        "e0003": (30 * SECOND, 31 * SECOND),
        "e0004": (40 * SECOND, 41 * SECOND),
    }
    corrupted = {
        "e0000": (1 * SECOND, 2 * SECOND),
        "e0001": (12 * SECOND, 13 * SECOND),
        "e0002": (20 * SECOND, 21 * SECOND),
        "e0003": (33 * SECOND, 34 * SECOND),
        "e0004": (40 * SECOND, 41 * SECOND),
    }
    case = _mk_case(
        "f04-two",
        original,
        [],
        {
            "e0000": 0,
            "e0001": 2 * SECOND,
            "e0002": 0,
            "e0003": 3 * SECOND,
            "e0004": 0,
        },
    )
    applied = {
        "e0000": 0,
        "e0001": -2 * SECOND,
        "e0002": 0,
        "e0003": -3 * SECOND,
        "e0004": 0,
    }
    score = score_case(
        case, _proposal(case.case_id, _shift(corrupted, applied)), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    assert dis["detected_breakpoints"] == 0
    assert dis["false_positive_breakpoints"] == 0
    assert dis["local_cue_adjustments"] == 2
    assert dis["local_cue_adjusted_cue_ids"] == ["e0001", "e0003"]
    assert score["counts"]["repaired_if_blindly_applied"] == 2


def test_trailing_shift_block_without_right_support_stays_a_claim():
    # [0, -2, -3]: the shifted block runs to the sequence edge with no stable
    # support on its right side, so it is NOT classified transient — the
    # regional change-point claim (and its false-positive penalty) survives.
    original = {
        "e0000": (1 * SECOND, 2 * SECOND),
        "e0001": (10 * SECOND, 11 * SECOND),
        "e0002": (20 * SECOND, 21 * SECOND),
    }
    corrupted = {
        "e0000": (1 * SECOND, 2 * SECOND),
        "e0001": (12 * SECOND, 13 * SECOND),
        "e0002": (23 * SECOND, 24 * SECOND),
    }
    case = _mk_case(
        "f04-tail",
        original,
        [],
        {"e0000": 0, "e0001": 2 * SECOND, "e0002": 3 * SECOND},
    )
    applied = {"e0000": 0, "e0001": -2 * SECOND, "e0002": -3 * SECOND}
    score = score_case(
        case, _proposal(case.case_id, _shift(corrupted, applied)), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    assert dis["detected_breakpoints"] == 2
    assert dis["false_positive_breakpoints"] == 2
    assert dis["local_cue_adjustments"] == 0


def test_spurious_lasting_step_in_control_keeps_false_positive():
    # S00-style control: NO true breakpoints, NO injected error. A candidate
    # that steps the last two cues by +5 s (and KEEPS that offset: a sustained
    # regional change point) must keep its false-positive release break.
    original, corrupted = _three_cues()
    corrupted["e0001"] = (10 * SECOND, 11 * SECOND)
    corrupted["e0002"] = (20 * SECOND, 21 * SECOND)
    case = _mk_case("f04-ctrl", original, [], {"e0000": 0, "e0001": 0, "e0002": 0})
    applied = {"e0000": 0, "e0001": 5 * SECOND, "e0002": 5 * SECOND}
    score = score_case(
        case, _proposal(case.case_id, _shift(corrupted, applied)), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    assert dis["detected_breakpoints"] == 1
    assert dis["false_positive_breakpoints"] == 1
    assert dis["local_cue_adjustments"] == 0


def test_spurious_reversing_step_pair_also_counts_as_local():
    # [0, +5 s, 0]: a single cue stepped and reversed — transient local
    # adjustment, NOT a release discontinuity (mirrors the F04 fix direction).
    original, corrupted = _three_cues()
    corrupted["e0001"] = (10 * SECOND, 11 * SECOND)
    case = _mk_case("f04-rev", original, [], {"e0000": 0, "e0001": 0, "e0002": 0})
    applied = {"e0000": 0, "e0001": 5 * SECOND, "e0002": 0}
    score = score_case(
        case, _proposal(case.case_id, _shift(corrupted, applied)), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    assert dis["detected_breakpoints"] == 0
    assert dis["false_positive_breakpoints"] == 0
    assert dis["local_cue_adjustments"] == 1
    # The shift moves the cue AWAY from its correct time: zero repair credit.
    assert score["counts"]["repaired_if_blindly_applied"] == 0


def test_sustained_gap_step_keeps_bracket_credit():
    # S03-like: true breakpoint in a cue gap; a sustained offset change keeps
    # its bracketing detection credit (one-to-one) — transient suppression must
    # NOT swallow sustained regional steps.
    original = {
        "e0000": (1 * SECOND, 2 * SECOND),
        "e0001": (10 * SECOND, 11 * SECOND),
        "e0002": (20 * SECOND, 21 * SECOND),
        "e0003": (30 * SECOND, 31 * SECOND),
    }
    true_breaks = [15 * SECOND]  # inside the gap between cue 1 and cue 2
    corrupted = {
        "e0000": (1 * SECOND, 2 * SECOND),
        "e0001": (10 * SECOND, 11 * SECOND),
        "e0002": (25 * SECOND, 26 * SECOND),
        "e0003": (35 * SECOND, 36 * SECOND),
    }
    case = CaseManifest(
        case_id="f04-gap",
        source_id="S",
        scenario="S03",
        seed=1,
        track_id="ep",
        fmt="ass",
        grid_us=10_000,
        params={"scenario": "S03"},
        transform={},
        expected_inverse={},
        injected_cue_deltas={
            "e0000": (0, 0),
            "e0001": (0, 0),
            "e0002": (5 * SECOND, 5 * SECOND),
            "e0003": (5 * SECOND, 5 * SECOND),
        },
        original_times_us=dict(original),
        true_breakpoints_us=true_breaks,
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )
    applied = {"e0000": 0, "e0001": 0, "e0002": -5 * SECOND, "e0003": -5 * SECOND}
    score = score_case(
        case, _proposal(case.case_id, _shift(corrupted, applied)), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    assert dis["detected_breakpoints"] == 1
    assert dis["matched_true_breakpoints"] == 1
    assert dis["false_positive_breakpoints"] == 0
    assert dis["local_cue_adjustments"] == 0
    assert dis["unresolved_true_breakpoints"] == 0


# ---------------------------------------------------------------------------
# F06 — counterfactual labeling, tool-only vs validated acceptance
# ---------------------------------------------------------------------------


def test_tool_only_score_uses_counterfactual_names(tmp_path, fixture_dir):
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "LBL1", "S01", 1) == 0
    assert _run(root, "LBL1") == 0
    # b1-al (tool unavailable => unsupported) is not scoreable; use a real
    # shifted proposal: run b1-px-fg is tool-bound too. Score the noop arm and
    # a synthetic shifted proposal via the noop arm's ground-truth scoring:
    # noop has zero proposals, so use the CLI-scored noop for the label check
    # plus the direct perfect inverse below.
    assert _score(root, "LBL1", "b1-n") == 0
    score = _load(_cand_dir(root, "LBL1", "b1-n") / "score.json")
    assert score["schema_version"] == 3
    assert score["final_semantics"] == "unguarded_proposal_if_blindly_applied"
    assert "accepted_nonzero" not in score["counts"]
    assert "if_blindly_applied_nonzero" in score["counts"]
    assert "repaired_if_blindly_applied" in score["counts"]
    assert "harmful_accepted" not in score["counts"]


def test_b1va_score_keeps_accepted_names_and_semantics(
    tmp_path, fixture_dir, monkeypatch
):
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "LBL2", "S01", 1) == 0
    assert _run(root, "LBL2") == 0
    _mock_va(monkeypatch, _cue_text(root, "LBL2"))
    assert _run_va(root, "LBL2") == 0
    assert _score(root, "LBL2", "b1-va") == 0
    score = _load(_cand_dir(root, "LBL2", "b1-va") / "score.json")
    assert score["final_semantics"] == "accepted_output"
    assert "accepted_nonzero" in score["counts"]
    assert "if_blindly_applied_nonzero" not in score["counts"]
    assert "harmful_accepted" in score["counts"]


def test_report_documents_per_arm_final_semantics(tmp_path, fixture_dir, monkeypatch):
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "SEM1", "S01", 1) == 0
    assert _run(root, "SEM1") == 0
    _mock_va(monkeypatch, _cue_text(root, "SEM1"))
    assert _run_va(root, "SEM1") == 0
    assert _score(root, "SEM1", "b1-n") == 0
    assert _score(root, "SEM1", "b1-va") == 0
    rc, report = _report(root, "SEM1")
    assert rc == 0
    assert "Acc validated" in report
    assert "If blind" in report
    assert "`b1-n` final timeline = unguarded_proposal_if_blindly_applied" in report
    assert "`b1-va` final timeline = accepted_output" in report
    assert "no validator ran" in report


# ---------------------------------------------------------------------------
# F05 — report fail-closed when current case/source evidence is missing
# ---------------------------------------------------------------------------


def test_source_registry_deletion_moves_rows_to_unverified_section(
    tmp_path, fixture_dir
):
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "EVD1", "S01", 1) == 0
    assert _run(root, "EVD1") == 0
    assert _score(root, "EVD1", "b1-n") == 0
    rc, report = _report(root, "EVD1")
    assert rc == 0
    assert "| b1-n |" in report
    assert "Unverified historical results" not in report  # before: fully verified

    sources = root / "cases" / "sources.json"
    sources.unlink()
    rc, report = _report(root, "EVD1")
    assert rc == 0
    assert "Unverified historical results (NOT COMPARABLE)" in report
    assert "current case/source evidence missing" in report
    # The stale self-consistent pair never renders as a comparative row.
    lines = [ln for ln in report.splitlines()]
    comparative = lines[
        : lines.index("## Unverified historical results (NOT COMPARABLE)")
    ]
    assert not any(ln.startswith("| b1-n |") for ln in comparative)
    assert any(
        "EVD1" in ln and "b1-n" in ln
        for ln in lines[
            lines.index("## Unverified historical results (NOT COMPARABLE)") :
        ]
    )

    # Restoring the registry (same media byte-identity) restores comparative
    # rendering — the stale pair was never deleted, just demoted.
    media = tmp_path / "media" / "episode.mkv"
    sidecar = tmp_path / "episode.ass"
    assert (
        _cli_add(
            root,
            media,
            ("--audio", "lang:eng", "--subtitle", f"main=sidecar:{sidecar}"),
        )
        == 0
    )
    rc, report = _report(root, "EVD1")
    assert rc == 0
    assert "| b1-n |" in report
    assert "Unverified historical results" not in report


def test_case_manifest_deletion_is_unverified(tmp_path, fixture_dir):
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "EVD2", "S01", 1) == 0
    assert _run(root, "EVD2") == 0
    assert _score(root, "EVD2", "b1-n") == 0
    manifest = cli._lookup_case_path(cli._paths(root), "EVD2")
    assert manifest is not None
    manifest.unlink()
    rc, report = _report(root, "EVD2")
    assert rc == 0
    assert "Unverified historical results (NOT COMPARABLE)" in report
    lines = report.splitlines()
    idx = lines.index("## Unverified historical results (NOT COMPARABLE)")
    assert not any(ln.startswith("| b1-n |") for ln in lines[:idx])
    assert any("EVD2" in ln for ln in lines[idx:])


# ---------------------------------------------------------------------------
# F07 — verifier time/calls recorded separately from ASR time
# ---------------------------------------------------------------------------


class _TimedASR:
    def __init__(self, texts: dict[str, str], seconds: float):
        self.texts = dict(texts)
        self.seconds = seconds

    def transcribe_window(self, wav_path, language, key=None):
        return Transcription(
            text=self.texts[key],
            confidence=1.0,
            seconds=self.seconds,
            model="timed-asr",
            mock=False,
            segments=[
                {"start_us": 1 * SECOND, "end_us": 2 * SECOND, "text": self.texts[key]}
            ],
        )


class _TimedVerifier:
    def __init__(self, verdict: str, seconds: float):
        self.verdict_name = verdict
        self.seconds = seconds
        self.calls = 0

    def verdict(
        self,
        subtitle_text,
        transcript_text,
        subtitle_language_hint,
        transcript_language_hint,
    ):
        self.calls += 1
        return SemanticVerdict(
            verdict=self.verdict_name, seconds=self.seconds, model="timed-verifier"
        )


def test_verifier_time_never_charged_as_asr_time(tmp_path, monkeypatch):
    monkeypatch.setattr("bench.validator.extract_audio_window", lambda *a, **k: 0.1)
    en_line = "I will protect this city."
    ja_line = "この街はわたしが守る"
    original = {"e0000": (1 * SECOND, 2 * SECOND)}
    corrupted = {"e0000": (10 * SECOND, 11 * SECOND)}
    proposal = ProposalRecord(
        "f07-t",
        "b1-px-fg",
        "1:1-order-preserving",
        [{"start_us": 0, "end_us": None, "offset_us": -9 * SECOND}],
        dict(original),
        [],
        "",
    )
    case = _mk_case("f07-t", original, [], {"e0000": 9 * SECOND})
    asr = _TimedASR({"e0000": ja_line}, seconds=7.0)
    verifier = _TimedVerifier("match", seconds=3.0)
    acc = validate_proposal(
        case,
        proposal,
        "b1-px-fg",
        corrupted,
        {"e0000": en_line},
        Path("fake.wav"),
        tmp_path / "run-f07",
        asr,
        "ja",
        1,
        verifier=verifier,
        subtitle_language="en",
    )
    n_samples = len(acc.sample_cue_ids)
    assert acc.asr_calls == n_samples
    assert acc.asr_seconds == pytest.approx(7.0 * n_samples)
    assert acc.verifier_calls == n_samples
    assert acc.semantic_seconds == pytest.approx(3.0 * n_samples)
    # The old bug: asr_seconds included verifier seconds. It must not.
    assert acc.asr_seconds < acc.asr_seconds + acc.semantic_seconds
    total = acc.asr_seconds + acc.semantic_seconds
    assert total == pytest.approx(10.0 * n_samples)
    assert acc.accepted_regions, (
        "timed verifier match with in-interval segments accepts"
    )


def test_b1va_run_json_records_separated_metrics(tmp_path, fixture_dir, monkeypatch):
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "MET1", "S01", 1) == 0
    assert _run(root, "MET1") == 0
    _mock_va(monkeypatch, _cue_text(root, "MET1"))
    assert _run_va(root, "MET1") == 0
    run = _load(_cand_dir(root, "MET1", "b1-va") / "run.json")
    assert run["asr_seconds"] >= 0.0
    assert run["semantic_seconds"] == 0.0  # no verifier configured in this flow
    assert run["verifier_calls"] == 0
    assert run["inference_seconds_total"] == pytest.approx(run["asr_seconds"])


# ---------------------------------------------------------------------------
# Adversarial review round 1 closures: D3 legacy rendering, P3 counting,
# and the tolerances section surviving an all-unverified report
# ---------------------------------------------------------------------------


def test_schema2_pair_renders_only_in_legacy_section(tmp_path, fixture_dir):
    """Review D3: schema-2 rows must render in the labeled legacy section
    (fp-only binding, the schema-appropriate rule), never as schema-3
    comparative numbers and never silently vanished."""
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "LGCY", "S01", 1) == 0
    assert _run(root, "LGCY") == 0
    assert _score(root, "LGCY", "b1-n") == 0
    d = _cand_dir(root, "LGCY", "b1-n")
    run = _load(d / "run.json")
    score = _load(d / "score.json")
    c = score["counts"]
    # Rewrite the pair to the schema-2 era format: legacy count names,
    # schema 2, no per-score proposal byte binding.
    run["schema_version"] = 2
    (d / "run.json").write_text(
        json.dumps(run, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    legacy_counts = {
        "repaired": c.get("repaired_if_blindly_applied", 0),
        "repaired_proposed": c.get("repaired_proposed", 0),
        "worsened_unaltered": c.get("worsened_unaltered_if_blindly_applied", 0),
        "worsened_unaltered_proposed": c.get("worsened_unaltered_proposed", 0),
        "harmful_proposed": c.get("harmful_proposed", 0),
        "harmful_accepted": c.get("harmful_if_blindly_applied", 0),
        "severe_final": c.get("severe_if_blindly_applied", 0),
        "proposals_nonzero": c.get("proposals_nonzero", 0),
        "accepted_nonzero": c.get("if_blindly_applied_nonzero", 0),
        "abstained_regions": c.get("abstained_regions", 0),
        "regions_total": c.get("regions_total", 0),
        "accepted_regions": c.get("accepted_regions", 0),
        "rejected_regions": c.get("rejected_regions", 0),
        "abstention_regions": c.get("abstention_regions", 0),
    }
    score["schema_version"] = 2
    score["counts"] = legacy_counts
    score.pop("final_semantics", None)
    (d / "score.json").write_text(
        json.dumps(score, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    rc, report = _report(root, "LGCY")
    assert rc == 0
    assert "Legacy schema-2 measurements (NOT COMPARABLE)" in report
    assert "pre-F06 measurement" in report
    assert "legacy schema-2 rows rendered separately: 1" in report
    # The legacy row never renders in the schema-3 comparative table.
    lines = report.splitlines()
    idx = lines.index("## Legacy schema-2 measurements (NOT COMPARABLE)")
    assert not any(ln.startswith("| b1-n |") for ln in lines[:idx])


def test_oscillation_counts_only_shifted_cues_as_local():
    # [0, -2, 0, -2, 0]: two isolated shifted cues around an untouched middle
    # cue. Zero release-break claims, and the middle untouched cue is NOT
    # counted as a local adjustment (it was never adjusted).
    original = {
        "e0000": (1 * SECOND, 2 * SECOND),
        "e0001": (10 * SECOND, 11 * SECOND),
        "e0002": (20 * SECOND, 21 * SECOND),
        "e0003": (30 * SECOND, 31 * SECOND),
        "e0004": (40 * SECOND, 41 * SECOND),
    }
    corrupted = {
        "e0000": (1 * SECOND, 2 * SECOND),
        "e0001": (12 * SECOND, 13 * SECOND),
        "e0002": (20 * SECOND, 21 * SECOND),
        "e0003": (32 * SECOND, 33 * SECOND),
        "e0004": (40 * SECOND, 41 * SECOND),
    }
    case = _mk_case(
        "f04-osc",
        original,
        [],
        {
            "e0000": 0,
            "e0001": 2 * SECOND,
            "e0002": 0,
            "e0003": 2 * SECOND,
            "e0004": 0,
        },
    )
    applied = {
        "e0000": 0,
        "e0001": -2 * SECOND,
        "e0002": 0,
        "e0003": -2 * SECOND,
        "e0004": 0,
    }
    score = score_case(
        case, _proposal(case.case_id, _shift(corrupted, applied)), corrupted, None, TOL
    )
    dis = score["discontinuities"]
    assert dis["detected_breakpoints"] == 0
    assert dis["false_positive_breakpoints"] == 0
    assert dis["local_cue_adjustments"] == 2
    assert dis["local_cue_adjusted_cue_ids"] == ["e0001", "e0003"]


def test_unverified_report_still_documents_tolerances(tmp_path, fixture_dir):
    root = _setup(tmp_path, fixture_dir)
    assert _prepare(root, "TOL1", "S01", 1) == 0
    assert _run(root, "TOL1") == 0
    assert _score(root, "TOL1", "b1-n") == 0
    manifest = cli._lookup_case_path(cli._paths(root), "TOL1")
    assert manifest is not None
    manifest.unlink()
    rc, report = _report(root, "TOL1")
    assert rc == 0
    assert "Unverified historical results (NOT COMPARABLE)" in report
    assert "## Tolerances used" in report
    assert "good ±50 ms" in report
