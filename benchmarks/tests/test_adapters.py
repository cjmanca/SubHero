import sys
from pathlib import Path

from bench.adapters import ToolConfig, run_candidate
from bench.corrupt import prepare_case
from bench.subtitles import Track

STUB = Path(__file__).resolve().parent / "stubs" / "stub_ffsubsync.py"


def _tools(offset_ms: int) -> ToolConfig:
    tools = ToolConfig()
    prefix = [sys.executable, str(STUB), "--offset-ms", str(offset_ms)]
    tools.command_overrides = {
        "b1-fg": prefix,
        "b1-fp": prefix,
        "b1-px-fg": prefix,
        "b1-px-fp": prefix,
    }
    return tools


def test_noop_proposes_nothing(fixture_dir, tmp_path):
    src = fixture_dir / "episode.ass"
    case = prepare_case(
        "Fx00", "ad-noop", "S01", 3, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path))
    proposal, _meta = run_candidate(
        "b1-n",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run",
        ToolConfig(),
        50_000,
    )
    assert proposal.mapping_status == "noop"
    assert all(
        t == corrupted.time_map()[cid] for cid, t in proposal.proposed_times_us.items()
    )


def test_stub_adapter_produces_global_region_proposal(fixture_dir, tmp_path):
    src = fixture_dir / "episode.ass"
    case = prepare_case(
        "Fx00", "ad-fg", "S01", 3, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path))
    proposal, _meta = run_candidate(
        "b1-fg",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run",
        _tools(2000),
        50_000,
    )
    assert proposal.mapping_status == "1:1-order-preserving"
    assert len(proposal.regions) == 1
    assert proposal.regions[0]["offset_us"] == 2_000_000
    assert all(
        proposal.proposed_times_us[cid][0] == corrupted.time_map()[cid][0] + 2_000_000
        for cid in proposal.proposed_times_us
    )


def test_proxy_adapter_maps_back_by_cue_id(fixture_dir, tmp_path):
    src = fixture_dir / "episode.ass"
    case = prepare_case(
        "Fx00", "ad-px", "S01", 3, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path))
    proposal, _meta = run_candidate(
        "b1-px-fg",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run",
        _tools(2000),
        50_000,
        gold_classification_path=fixture_dir / "gold_episode.json",
    )
    assert proposal.mapping_status == "1:1-order-preserving"
    n_proxy = len(proposal.proposed_times_us)
    n_total = len(corrupted.cues)
    assert 0 < n_proxy < n_total
    assert set(proposal.unmapped_cue_ids) == set(corrupted.time_map()) - set(
        proposal.proposed_times_us
    )
    for cid in proposal.proposed_times_us:
        assert (
            proposal.proposed_times_us[cid][0]
            == corrupted.time_map()[cid][0] + 2_000_000
        )


def test_signs_only_proxy_abstains_without_inventing_map(fixture_dir, tmp_path):
    src = fixture_dir / "signs.ass"
    case = prepare_case(
        "Fx00", "ad-px-signs", "S01", 3, src, tmp_path / "out.ass", track_id="signs"
    )
    corrupted = Track.load(Path(case.generated_path))
    proposal, _meta = run_candidate(
        "b1-px-fg",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run",
        _tools(2000),
        50_000,
        gold_classification_path=fixture_dir / "gold_signs.json",
    )
    assert proposal.mapping_status == "abstain_no_speech_anchors"
    assert proposal.proposed_times_us == {}


def test_missing_ffsubsync_is_not_run(tmp_path, fixture_dir):
    src = fixture_dir / "episode.ass"
    case = prepare_case(
        "Fx00", "ad-missing", "S00", 3, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path))
    tools = ToolConfig()
    tools.ffsubsync = None
    proposal, _meta = run_candidate(
        "b1-fg",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run",
        tools,
        50_000,
    )
    assert proposal.mapping_status == "not_run"


def test_missing_alass_is_unsupported(tmp_path, fixture_dir):
    src = fixture_dir / "episode.ass"
    case = prepare_case(
        "Fx00", "ad-al", "S00", 3, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path))
    tools = ToolConfig()
    tools.alass = None
    proposal, _meta = run_candidate(
        "b1-al",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run",
        tools,
        50_000,
    )
    assert proposal.mapping_status == "unsupported"


def test_count_mismatch_output_is_mapping_failure(tmp_path, fixture_dir):
    src = fixture_dir / "episode.ass"
    case = prepare_case(
        "Fx00", "ad-bad", "S00", 3, src, tmp_path / "out.ass", track_id="episode"
    )
    corrupted = Track.load(Path(case.generated_path))
    stub = tmp_path / "stub_drop.py"
    stub.write_text(
        "import argparse, pysubs2\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('reference', nargs='?', default=None)\n"
        "p.add_argument('-i', '--srtin'); p.add_argument('-o', '--srtout'); p.add_argument('--log-dir-path', default=None)\n"
        "a = p.parse_args()\n"
        "d = pysubs2.SSAFile.load(a.srtin, format='srt')\n"
        "out = pysubs2.SSAFile()\n"
        "for ev in list(d.events)[:-1]:\n"
        "    out.events.append(ev)\n"
        "out.save(a.srtout, format='srt')\n",
        encoding="utf-8",
    )
    tools = ToolConfig()
    tools.command_overrides = {"b1-fg": [sys.executable, str(stub)]}
    proposal, _meta = run_candidate(
        "b1-fg",
        case,
        corrupted.time_map(),
        Path(case.generated_path),
        tmp_path / "ref.wav",
        tmp_path / "run",
        tools,
        50_000,
    )
    assert proposal.mapping_status == "mapping_failure_count_mismatch"
