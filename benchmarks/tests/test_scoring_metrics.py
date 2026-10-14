from bench.corrupt import prepare_case
from bench.manifests import ProposalRecord
from bench.scoring import Tolerances, score_case
from bench.subtitles import Track


def _case(tmp_path):
    src = tmp_path / "episode.ass"
    src.write_text(
        "[Script Info]\nScriptType: v4.00+\n\n[V4 Styles]\nFormat: Name, Fontname, Fontsize\nStyle: Dialog,Arial,28\n\n[Events]\nFormat: Layer, Start, End, Style, Text\nDialogue: 0,0:00:01.00,0:00:03.00,Dialog,Hello\nDialogue: 0,0:00:11.00,0:00:13.00,Dialog,World\nDialogue: 0,0:00:21.00,0:00:23.00,Dialog,Again\n",
        encoding="utf-8",
    )
    return prepare_case("T", "c1", "S01", 3, src, tmp_path / "out.ass")


def test_exact_offset_recovery_residual_zero(tmp_path):
    case = _case(tmp_path)
    corrupted = Track.load(case.generated_path, case.fmt)
    tol = Tolerances(good_us=50_000, severe_us=250_000, break_match_us=500_000)
    exact = ProposalRecord(
        case_id="c1",
        candidate_id="b1-test",
        mapping_status="1:1-order-preserving",
        regions=[
            {
                "start_us": 0,
                "end_us": None,
                "offset_us": -int(case.params["offset_us"]),
                "kind": "global",
                "confidence": "high",
            }
        ],
        proposed_times_us=dict(case.original_times_us),
        unmapped_cue_ids=[],
        notes="",
    )
    score = score_case(case, exact, corrupted.time_map(), None, tol)
    assert score["counts"]["repaired"] == 3
    assert score["counts"]["worsened_unaltered"] == 0
    assert score["counts"]["harmful_accepted"] == 0
    assert score["offset_recovery"]["residual_us"] == 0


def test_noop_proposal_keeps_injected_error(tmp_path):
    case = _case(tmp_path)
    corrupted = Track.load(case.generated_path, case.fmt)
    tol = Tolerances(good_us=50_000, severe_us=250_000, break_match_us=500_000)
    noop = ProposalRecord("c1", "b1-n", "noop", [], dict(corrupted.time_map()), [], "")
    score = score_case(case, noop, corrupted.time_map(), None, tol)
    assert score["counts"]["repaired"] == 0
    assert score["counts"]["proposals_nonzero"] == 0
    assert score["timing_errors_final_us"]["median_abs_us"] == abs(
        int(case.params["offset_us"])
    )


def test_clean_control_shift_counts_worsened_and_harmful(tmp_path):
    case = _case(tmp_path)
    corrupted = Track.load(case.generated_path, case.fmt)
    tol = Tolerances(good_us=50_000, severe_us=250_000, break_match_us=500_000)
    shifted = {
        cid: (s + 5_000_000, e + 5_000_000)
        for cid, (s, e) in corrupted.time_map().items()
    }
    bad = ProposalRecord(
        "c1",
        "b1-test",
        "1:1-order-preserving",
        [{"start_us": 0, "end_us": None, "offset_us": 5_000_000}],
        shifted,
        [],
        "",
    )
    score = score_case(case, bad, corrupted.time_map(), None, tol)
    assert score["counts"]["harmful_proposed"] == 3
    assert score["counts"]["harmful_accepted"] == 3
    assert score["counts"]["severe_final"] >= 1
