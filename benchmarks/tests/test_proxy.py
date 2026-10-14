import json

from bench.proxy import build_proxy, classify_cue, fit_regions
from bench.subtitles import Track


def test_classification_excludes_non_speech(fixture_dir):
    track = Track.load(fixture_dir / "episode.ass")
    gold = json.loads((fixture_dir / "gold_episode.json").read_text(encoding="utf-8"))
    labels = {c.cue_id: classify_cue(c, gold) for c in track.cues}
    speech = [cid for cid, lab in labels.items() if lab == "speech_like"]
    assert len(speech) == len(
        [cid for cid, lab in gold.items() if lab == "speech_like"]
    )
    heur = {c.cue_id: classify_cue(c, None) for c in track.cues}
    for cue in track.cues:
        if gold[cue.cue_id] == "non_speech":
            assert heur[cue.cue_id] == "non_speech", cue.text


def test_proxy_preserves_1to1_cue_mapping(fixture_dir, tmp_path):
    track = Track.load(fixture_dir / "episode.ass")
    mapping = build_proxy(
        track,
        tmp_path / "proxy.srt",
        tmp_path / "map.json",
        fixture_dir / "gold_episode.json",
    )
    proxy_doc = __import__("pysubs2").SSAFile.load(tmp_path / "proxy.srt", format="srt")
    assert len(proxy_doc.events) == len(mapping.proxy_index_to_cue)
    assert len(set(mapping.proxy_index_to_cue)) == len(mapping.proxy_index_to_cue)
    for cue_id in mapping.proxy_index_to_cue:
        assert cue_id in mapping.cue_to_proxy_index
    assert len(mapping.proxy_index_to_cue) < len(track.cues)


def test_signs_only_track_has_no_anchors_and_stays_unmapped(fixture_dir, tmp_path):
    track = Track.load(fixture_dir / "signs.ass")
    mapping = build_proxy(
        track,
        tmp_path / "proxy.srt",
        tmp_path / "map.json",
        fixture_dir / "gold_signs.json",
    )
    assert mapping.proxy_index_to_cue == []


def test_fit_regions_global_median_single_region():
    deltas = [(i * 1_000_000, 2_000_000) for i in range(10)]
    regions = fit_regions(deltas, 10_000, 50_000)
    assert len(regions) == 1
    assert regions[0]["offset_us"] == 2_000_000
    assert regions[0]["kind"] == "global"


def test_fit_regions_detects_step():
    deltas = [(i * 1_000_000, 0) for i in range(6)] + [
        (i * 1_000_000, 10_000_000) for i in range(7, 13)
    ]
    regions = fit_regions(deltas, 10_000, 100_000)
    assert len(regions) == 2
    assert regions[0]["offset_us"] == 0
    assert regions[1]["offset_us"] == 10_000_000
    assert regions[0]["end_us"] == 5_000_000
    assert regions[1]["start_us"] == 7_000_000


def test_fit_regions_empty():
    assert fit_regions([], 10_000, 50_000) == []
