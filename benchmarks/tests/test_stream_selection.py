"""Stream selection: --audio specs, mkv subtitle grammar, persistence, propagation."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from bench import cli
from bench.manifests import CaseManifest, ProposalRecord
from bench.media import extract_audio, extract_subtitle_stream, sha256_file
from bench.subtitles import Track

FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg required")

JPN_MARKER = "JPNMARKER4471"
ENG_MARKER = "ENGMARKER9135"
SRT_TMPL = "1\n00:00:01,000 --> 00:00:02,000\n{marker}\n"


def _ffmpeg(*args: str) -> None:
    subprocess.run(
        [FFMPEG, "-y", "-v", "error", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _decode(media, stream: str, out) -> str:
    _ffmpeg(
        "-i",
        str(media),
        "-map",
        stream,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(out),
    )
    return sha256_file(out)


def _build_mkv(
    tmp_path,
    name="episode.mkv",
    a0_lang="jpn",
    a1_lang="eng",
    s0_lang="jpn",
    s1_lang="eng",
):
    """Two sine audio streams (440 Hz / 880 Hz) + two ASS subtitle tracks, tagged."""
    media_dir = tmp_path / "media"
    media_dir.mkdir(exist_ok=True)
    out = media_dir / name
    a440 = tmp_path / f"{name}-440.wav"
    a880 = tmp_path / f"{name}-880.wav"
    s_jpn = tmp_path / f"{name}-jpn.srt"
    s_eng = tmp_path / f"{name}-eng.srt"
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
    s_jpn.write_text(SRT_TMPL.format(marker=JPN_MARKER), encoding="utf-8")
    s_eng.write_text(SRT_TMPL.format(marker=ENG_MARKER), encoding="utf-8")
    _ffmpeg(
        "-i",
        str(a440),
        "-i",
        str(a880),
        "-i",
        str(s_jpn),
        "-i",
        str(s_eng),
        "-map",
        "0:a:0",
        "-map",
        "1:a:0",
        "-map",
        "2:s:0",
        "-map",
        "3:s:0",
        "-c:a",
        "pcm_s16le",
        "-c:s",
        "ass",
        "-metadata:s:a:0",
        f"language={a0_lang}",
        "-metadata:s:a:1",
        f"language={a1_lang}",
        "-metadata:s:s:0",
        f"language={s0_lang}",
        "-metadata:s:s:1",
        f"language={s1_lang}",
        str(out),
    )
    return out


def _cli_add(root, media, extra=(), source_id="MS"):
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


def _record(root, source_id):
    data = json.loads((root / "cases" / "sources.json").read_text(encoding="utf-8"))
    return data["sources"][source_id]


def test_multi_audio_registration_refused_without_audio(tmp_path, capsys):
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    rc = _cli_add(root, media)
    captured = capsys.readouterr()
    assert rc == 2
    assert "REFUSED (audio selection)" in captured.err
    assert "2 audio streams" in captured.err
    assert "--audio" in captured.err
    for expected in ("sidx=0", "sidx=1", "index=0", "index=1", "jpn", "eng"):
        assert expected in captured.err
    assert not (root / "cases" / "sources.json").exists()


def test_audio_lang_index_sidx_forms_agree_and_persist(tmp_path):
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    for sid, spec in (
        ("MS-ENG", "lang:eng"),
        ("MS-IDX", "index:1"),
        ("MS-SIDX", "sidx:1"),
    ):
        assert _cli_add(root, media, ["--audio", spec], source_id=sid) == 0
    selected = _record(root, "MS-ENG")["audio_selected"]
    assert selected == {
        "index": 1,
        "sidx": 1,
        "language": "eng",
        "codec_name": "pcm_s16le",
    }
    for sid in ("MS-IDX", "MS-SIDX"):
        assert _record(root, sid)["audio_selected"] == selected
    assert _record(root, "MS-ENG")["audio_spec"] == "lang:eng"
    assert _record(root, "MS-IDX")["audio_spec"] == "index:1"


def test_single_audio_registration_persists_default_selection(tmp_path):
    media = tmp_path / "single.wav"
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=600:duration=1",
        "-c:a",
        "pcm_s16le",
        str(media),
    )
    root = tmp_path / "benchroot"
    assert _cli_add(root, media) == 0
    rec = _record(root, "MS")
    assert rec["audio_selected"] == {
        "index": 0,
        "sidx": 0,
        "language": None,
        "codec_name": "pcm_s16le",
    }
    assert rec["audio_spec"] == "sidx:0"


def test_ambiguous_language_and_bad_index_refused(tmp_path, capsys):
    dup = _build_mkv(tmp_path, name="dupeng.mkv", a0_lang="eng", a1_lang="eng")
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    refusals = [
        (dup, "lang:eng", "DUP"),
        (media, "index:2", "SUBIDX"),
        (media, "sidx:5", "RANGE"),
        (media, "bogus:1", "SHAPE"),
    ]
    for path, spec, sid in refusals:
        capsys.readouterr()
        assert _cli_add(root, path, ["--audio", spec], source_id=sid) == 2
    registry_path = root / "cases" / "sources.json"
    registry = (
        registry_path.read_text(encoding="utf-8") if registry_path.exists() else ""
    )
    for sid in ("DUP", "SUBIDX", "RANGE", "SHAPE"):
        assert sid not in registry


def test_selected_audio_decode_matches_direct_map(tmp_path):
    from bench import paths

    media = _build_mkv(tmp_path)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    paths.configure([scratch], [media.parent], [])
    selected_wav = scratch / "selected.wav"
    extract_audio(media, selected_wav, audio_stream="0:a:1")
    assert sha256_file(selected_wav) == _decode(
        media, "0:a:1", scratch / "direct880.wav"
    )
    assert sha256_file(selected_wav) != _decode(
        media, "0:a:0", scratch / "direct440.wav"
    )


def test_subtitle_spec_forms_normalize_persist_and_extract(tmp_path):
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    rc = _cli_add(
        root,
        media,
        [
            "--audio",
            "lang:eng",
            "--subtitle",
            "by_lang=mkv:lang:eng",
            "--subtitle",
            "by_index=mkv:index:3",
            "--subtitle",
            "by_sidx=mkv:sidx:1",
            "--subtitle",
            "jpn=mkv:sidx:0",
        ],
    )
    assert rc == 0
    rec = _record(root, "MS")
    for tid in ("by_lang", "by_index", "by_sidx"):
        assert rec["subtitle_specs"][tid] == "mkv:sidx:1"
        sel = rec["subtitle_selected"][tid]
        assert sel["sidx"] == 1 and sel["index"] == 3 and sel["language"] == "eng"
    assert rec["subtitle_selected"]["jpn"]["sidx"] == 0
    for tid, marker in (("by_lang", ENG_MARKER), ("jpn", JPN_MARKER)):
        out = root / "_scratch" / f"{tid}.ass"
        extract_subtitle_stream(media, rec["subtitle_selected"][tid]["sidx"], out)
        text = " ".join(cue.text for cue in Track.load(out).cues)
        assert marker in text


def test_legacy_bare_mkv_subtitle_spec_refused(tmp_path, capsys):
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    rc = _cli_add(
        root,
        media,
        ["--audio", "lang:eng", "--subtitle", "old=mkv:0"],
        source_id="LEGACY",
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "ambiguous" in captured.err
    for form in ("mkv:sidx:", "mkv:index:", "mkv:lang:"):
        assert form in captured.err
    assert not (root / "cases" / "sources.json").exists()


def test_subtitle_ambiguous_language_refused(tmp_path):
    media = _build_mkv(tmp_path, name="dupsubs.mkv", s0_lang="eng", s1_lang="eng")
    root = tmp_path / "benchroot"
    rc = _cli_add(
        root,
        media,
        ["--audio", "lang:eng", "--subtitle", "t=mkv:lang:eng"],
        source_id="DUPSUB",
    )
    assert rc == 2
    assert not (root / "cases" / "sources.json").exists()


def _case_manifest(case_id: str, source_id: str) -> CaseManifest:
    return CaseManifest(
        case_id=case_id,
        source_id=source_id,
        scenario="S00",
        seed=1,
        track_id="main",
        fmt="ass",
        grid_us=10_000,
        params={},
        transform={},
        expected_inverse={},
        injected_cue_deltas={},
        original_times_us={},
        true_breakpoints_us=[],
        original_subtitle_sha256="0" * 64,
        generated_subtitle_sha256="0" * 64,
        generated_path="gen.ass",
    )


def test_reference_audio_fails_closed_without_selection(tmp_path):
    from bench.cli import StreamSelectionError

    paths_dict = cli._paths(tmp_path / "root")
    media = tmp_path / "e.mkv"
    media.write_bytes(b"stub-media")
    media_sha = sha256_file(media)
    ref_dir = paths_dict["scratch"] / "c1"
    ref_dir.mkdir(parents=True)
    (ref_dir / "reference.wav").write_bytes(b"cached")

    def _cache_meta(audio_stream):
        (ref_dir / "preprocess.json").write_text(
            json.dumps(
                {
                    "audio_extraction_seconds": 0.0,
                    "audio_stream": audio_stream,
                    "media_sha256": media_sha,
                }
            ),
            encoding="utf-8",
        )

    case = _case_manifest("c1", "MS")
    multi_no_sel = {
        "sources": {
            "MS": {
                "media_path": str(tmp_path / "e.mkv"),
                "streams": [
                    {"index": 1, "codec_type": "audio"},
                    {"index": 2, "codec_type": "audio"},
                ],
            }
        }
    }
    with pytest.raises(StreamSelectionError, match="no persisted audio_selected"):
        cli._get_reference_audio(paths_dict, case, multi_no_sel)
    _cache_meta(None)
    legacy_single = {
        "sources": {
            "MS": {
                "media_path": str(tmp_path / "e.mkv"),
                "streams": [{"index": 0, "codec_type": "audio"}],
            }
        }
    }
    ref, audio_stream = cli._get_reference_audio(paths_dict, case, legacy_single)
    assert ref == ref_dir / "reference.wav"
    assert audio_stream is None
    _cache_meta("0:a:1")
    persisted = {
        "sources": {
            "MS": {
                "media_path": str(tmp_path / "e.mkv"),
                "streams": [],
                "audio_selected": {"index": 1, "sidx": 1, "language": "eng"},
            }
        }
    }
    _ref, audio_stream = cli._get_reference_audio(paths_dict, case, persisted)
    assert audio_stream == "0:a:1"


def test_validate_proposal_threads_audio_stream(fixture_dir, tmp_path, monkeypatch):
    from bench import validator
    from bench.asr import MockTranscriber
    from bench.corrupt import prepare_case

    calls: list[dict] = []

    def _fake_extract(*args, **kwargs):
        calls.append(kwargs)
        return 0.1

    monkeypatch.setattr(validator, "extract_audio_window", _fake_extract)
    case = prepare_case(
        "Fx00", "va-thread", "S01", 2, fixture_dir / "episode.ass", tmp_path / "out.ass"
    )
    corrupted = Track.load(case.generated_path, case.fmt)
    times = corrupted.time_map()
    cue_text = {c.cue_id: c.text for c in corrupted.cues}
    offset = 5_000_000
    proposed = {cid: (s + offset, e + offset) for cid, (s, e) in times.items()}
    proposal = ProposalRecord(
        "va-thread",
        "b1-px-fg",
        "1:1-order-preserving",
        [{"start_us": 0, "end_us": None, "offset_us": offset}],
        proposed,
        [],
    )
    mock = MockTranscriber({cid: cue_text[cid] for cid in cue_text})
    validator.validate_proposal(
        case,
        proposal,
        "b1-px-fg",
        times,
        cue_text,
        tmp_path / "ref.wav",
        tmp_path / "run1",
        mock,
        "und",
        1,
        audio_stream="0:a:1",
    )
    assert calls
    assert all(k.get("audio_stream") == "0:a:1" for k in calls)
    calls.clear()
    validator.validate_proposal(
        case,
        proposal,
        "b1-px-fg",
        times,
        cue_text,
        tmp_path / "ref.wav",
        tmp_path / "run2",
        mock,
        "und",
        1,
    )
    assert calls and all(k.get("audio_stream") is None for k in calls)


def test_cmd_run_decodes_selected_audio(tmp_path):
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    sidecar = tmp_path / "episode.ass"
    shutil.copy2(
        Path(__file__).resolve().parent.parent / "fixtures" / "Fx00" / "episode.ass",
        sidecar,
    )
    assert (
        _cli_add(
            root,
            media,
            ["--audio", "lang:eng", "--subtitle", f"main=sidecar:{sidecar}"],
        )
        == 0
    )
    assert (
        cli.main(
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
                "S00",
                "--seed",
                "1",
                "--case-id",
                "RUN1",
            ]
        )
        == 0
    )
    assert (
        cli.main(["--root", str(root), "run", "--case", "RUN1", "--candidate", "b1-n"])
        == 0
    )
    ref_wav = root / "_scratch" / "RUN1" / "reference.wav"
    assert ref_wav.is_file()
    decoded = sha256_file(ref_wav)
    assert decoded == _decode(media, "0:a:1", tmp_path / "direct880.wav")
    assert decoded != _decode(media, "0:a:0", tmp_path / "direct440.wav")


def test_reference_audio_reextracts_after_selection_change(tmp_path):
    media = _build_mkv(tmp_path)
    root = tmp_path / "benchroot"
    sidecar = tmp_path / "episode.ass"
    shutil.copy2(
        Path(__file__).resolve().parent.parent / "fixtures" / "Fx00" / "episode.ass",
        sidecar,
    )
    add_args = ["--subtitle", f"main=sidecar:{sidecar}"]
    assert _cli_add(root, media, ["--audio", "lang:eng", *add_args]) == 0
    assert (
        cli.main(
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
                "S00",
                "--seed",
                "1",
                "--case-id",
                "RUN2",
            ]
        )
        == 0
    )
    run_argv = ["--root", str(root), "run", "--case", "RUN2", "--candidate", "b1-n"]
    assert cli.main(run_argv) == 0
    ref_wav = root / "_scratch" / "RUN2" / "reference.wav"
    preprocess = root / "_scratch" / "RUN2" / "preprocess.json"
    eng_sha = _decode(media, "0:a:1", tmp_path / "direct880.wav")
    jpn_sha = _decode(media, "0:a:0", tmp_path / "direct440.wav")
    meta = json.loads(preprocess.read_text(encoding="utf-8"))
    assert meta["audio_stream"] == "0:a:1"
    assert meta["media_sha256"] == sha256_file(media)
    assert sha256_file(ref_wav) == eng_sha
    assert sha256_file(ref_wav) != jpn_sha

    # Valid cache is reused unchanged (no re-extraction, meta identical).
    before_meta = preprocess.read_bytes()
    assert cli.main(run_argv) == 0
    assert preprocess.read_bytes() == before_meta

    # Missing/corrupt preprocess.json forces re-extraction, rewritten with meta.
    preprocess.write_bytes(b"{ not json")
    assert cli.main(run_argv) == 0
    meta = json.loads(preprocess.read_text(encoding="utf-8"))
    assert meta["audio_stream"] == "0:a:1"
    assert meta["media_sha256"] == sha256_file(media)

    # Re-registering the same source id with a different selection must re-decode.
    registry_path = root / "cases" / "sources.json"
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    del data["sources"]["MS"]
    registry_path.write_text(json.dumps(data), encoding="utf-8")
    assert _cli_add(root, media, ["--audio", "lang:jpn", *add_args]) == 0
    assert cli.main(run_argv) == 0
    meta = json.loads(preprocess.read_text(encoding="utf-8"))
    assert meta["audio_stream"] == "0:a:0"
    assert meta["media_sha256"] == sha256_file(media)
    assert sha256_file(ref_wav) == jpn_sha
    assert sha256_file(ref_wav) != eng_sha
