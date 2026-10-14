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
| M2 Correct source-stream selection | **pending** | — |
| M3 Correct benchmark scoring | **pending** | — |
| M4 Remove ground-truth leakage | **pending** | — |
| M5 Correct targeted ASR validation | **pending** | — |
| M6 Harden output mapping & filesystem safety | **pending** | — |
| Final verification (tests, lint, review, findings, real-media readiness) | **pending** | — |

## Standing constraints

- No B2–B5 work; no production application infrastructure.
- `PLAN.md` immutable; no Git pushes without authorization; local commits by orchestrator after accepted slices.
- G0/G1 remain **blocked** (real known-good episodes E01/E02 not supplied). No gate claims; no invented thresholds; findings updated only with genuinely executed measurements.

## Next action

Delegate M1 (private benchmark data protection) as a bounded brief: `.gitignore` + `benchmarks/private/` layout + CLI registration safeguards + `git check-ignore`/`status`/`ls-files` validation + tests.
