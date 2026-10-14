# STATUS — execution ledger (B0/B1 correction assignment)

**Plan:** `PLAN.md` (Correct SubHero B0/B1 Benchmark Issues, 2026-10-14)
**Approved PLAN.md SHA-256:** `1e0cc75c94a6f47bd58158d9d2437f63ab7d98255fc51dcd24e7ee91a335dcf3` — recorded 2026-10-14 at ledger (re)initialization for this plan version. `PLAN.md` is immutable during execution; progress is recorded only here.
**Branch/HEAD at init:** `main` @ `06f8ae6` (the reviewed commit). Working tree at init contained user-authored uncommitted `PLAN.md` (new assignment version replacing the B0+B1 plan) and an emptied `STATUS.md`; ledger reinitialized by the orchestrator for this assignment.
**Ledger initialized:** 2026-10-14 by top-level orchestrator implementing the authorized correction brief (Milestones M1–M6 + final verification).

**Authoritative sources:** `PLAN.md` (gates), `AGENTS.md`/`ORCHESTRATION.md` (procedure). The `SubHero_Qwen_B0_B1_Review_Handoff_2026-10-14.md` referenced by the plan is **not present in the repository**; the milestone text of `PLAN.md` is treated as the authoritative correction specification. Findings fixed earlier (commit `06f8ae6` message) remain in effect; the reviewer's six milestone areas are re-derived from code inspection against the plan gates.

## Baseline (observed 2026-10-14, this session, at `06f8ae6`)

- `python -m pytest benchmarks\tests -q` → **49 passed**
- `ruff check .` → clean; `ruff format --check .` → 74 files already formatted
- Tools: Python 3.14.0, ffmpeg/ffprobe present, ffsubsync 0.5.1 (`--split-penalty` advertised), pysubs2 1.9.0, pytest 9.1.1, ruff 0.17.0, numpy/scipy/torch/transformers present. `alass` absent → `b1-al` = `unsupported`. No ASR/semantic endpoint configured → `b1-va` integration boundary only.

## Milestones

| Slice | State | Evidence |
| --- | --- | --- |
| M1 Private benchmark data protection | **accepted** | `.gitignore` ignores `benchmarks/private/*` (only `README.md` stub committed); `benchmarks/private/README.md` documents layout; CLI (`cli.py`) refuses in-repo media/sidecar/gold registration outside `private/`+`fixtures/` before any writes; case manifests routed: committed `cases/` only for `redistributable-synthetic-fixture`, all others → ignored `private/cases/`; `case list`/`run`/`score`/`report` scan both. Orchestrator-verified at acceptance: `pytest benchmarks\tests -q` → **67 passed** (49 baseline + 18 new); `ruff check .` clean; `ruff format --check .` clean; `git check-ignore -v` matched `benchmarks/private/E01/episode.mkv` and `benchmarks/private/cases/E01-S01.case.json` (rule `.gitignore:232`), README not ignored; `git ls-files` → 7 Fx00 manifests + `benchmarks/private/README.md` tracked |
| M2 Correct source-stream selection | **accepted** | `source add --audio index:\|sidx:\|lang:` validated against ffprobe at registration (persisted `audio_selected`/`audio_spec`); multi-audio without selection → registration refused; single-audio → persisted default. Normalized `mkv:sidx:<n>` subtitle specs (`index:`/`lang:` resolved at registration; legacy bare `mkv:<n>` refused); selection used by `_get_reference_audio` (sync), threaded into `validate_proposal` → `extract_audio_window` (targeted ASR). Cache-staleness guard: `preprocess.json` records `audio_stream`+`media_sha256`; re-registration with new selection forces re-extraction (P2 found in review, fixed + test). Multi-track synthetic MKV tests (distinct 440/880 Hz tones, tagged subs): selection fidelity proven by sha256 equality vs direct ffmpeg decode. Orchestrator-verified: `pytest benchmarks\tests -q` → **79 passed**; `ruff check .` clean; `ruff format --check .` clean (77 files); `git diff --check` clean; diff inspected |
| M3 Correct benchmark scoring | **accepted** | Schema v2: candidate-implied breakpoints derived from applied corrections (`proposed−corrupted` steps > `max(2·good_us, 250 ms)` floor), residual steps grant **no** detection credit; separate `unresolved_true_breakpoints` (final accepted/proposed timeline still stepping at true breakpoints; conservative no-straddle counting reported separately); offset recovery reports `applied_shift_us`/`recovered_offset_us = −applied_shift`/`residual = |recovered − true|` with sign direction verified against `timeline.py Segment.apply` + committed `Fx00-S01` (+1_900_000 injected == params.offset_us); noop/1:1 gate. Reporting renders v2 fields, ignores v1 rows. Four mandated properties tested (noop zero-credit on hand-S03 + committed S04; perfect piecewise full credit zero FP; extra step → FP 1; synchronized-cue protection worsened/harmful) + offset pinning (exact inverse residual 0; noop residual = |true|; wrong sign residual = 2·|true|). One prior assertion updated (noop residual-domain free-credit, coverage strengthened, documented). Orchestrator-verified: **90 passed**; `ruff check` clean; `ruff format --check` clean (78 files); `git diff --check` clean; full diff inspected |
| M4 Remove ground-truth leakage | **accepted** | Default candidates (incl. `b1-px-fg`/`b1-px-fp`) can no longer receive gold cue labels — two-layer boundary: `cli.cmd_run` passes gold path only to oracle arms; `adapters.run_candidate` independently ignores gold for non-oracle ids. Gold retained in manifests for evaluation only. New diagnostic arms `b1-pxo-fg`/`b1-pxo-fp` (oracle-assisted, marker in notes/run.json, **excluded from `--all`**, explicit selection only). Discriminating tests: heuristic-non-speech + gold-speech_like track → default px arm abstains, oracle arm maps (proof default ignores gold). No prior assertions weakened. Orchestrator-verified: **98 passed**; `ruff check` clean; `ruff format --check` clean (79 files); `git diff --check` clean; diff inspected |
| M5 Correct targeted ASR validation | **pending** | — |
| M6 Harden output mapping & filesystem safety | **pending** | — |
| Final verification (tests, lint, review, findings, real-media readiness) | **pending** | — |

## Standing constraints

- No B2–B5 work; no production application infrastructure.
- `PLAN.md` immutable; no Git pushes without authorization; local commits by orchestrator after accepted slices.
- G0/G1 remain **blocked** (real known-good episodes E01/E02 not supplied). No gate claims; no invented thresholds; findings updated only with genuinely executed measurements.

## Next action

Delegate M1 (private benchmark data protection) as a bounded brief: `.gitignore` + `benchmarks/private/` layout + CLI registration safeguards + `git check-ignore`/`status`/`ls-files` validation + tests.
