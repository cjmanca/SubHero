# STATUS — execution ledger

**Plan:** `PLAN.md` (Qwen Handoff — Benchmark Harness B0 + B1)
**Approved PLAN.md SHA-256:** `4503729c7b016c0f03a327ba30637cf9ae8f2a9e46c50cc68ef721525b2ac1d6` — verified 2026-10-14 against working tree; matches ledger.
**Branch/HEAD at init:** `main` @ `10966dd` (docs-only baseline; no benchmark code committed)
**Ledger initialized:** 2026-10-14 by top-level orchestrator implementing the authorized B0+B1 benchmark brief.

## Verified progress

| Slice | State | Evidence |
| --- | --- | --- |
| B0 harness (CLI, manifests, corruption, scoring, tests) | **implemented; offline-verified** | `benchmarks/` CLI (`run_bench.py` + `bench/` package); deterministic S00–S04/S06 generators with recorded injected deltas + exact inverses; same-seed byte-identical regeneration verified; invalid-timestamp injections raise `InvalidTime` (never clamped); read-only source fingerprints; scratch/source-root/forbidden-root write guards; 42 tests pass (`python -m pytest benchmarks\tests -q`); `ruff check` clean; `ruff format --check` clean |
| B1 sync candidates (N/FG/FP/AL/PX/VA) | **arms executable; synthetic matrix run** | Real ffsubsync 0.5.1 runs recorded for `b1-fg`/`b1-fp` (`--split-penalty` capability probed from installed help) and proxy arms `b1-px-fg`/`b1-px-fp`; `b1-al` → `unsupported` (binary absent); `b1-va` → `not_run` (no local ASR endpoint); signs-only fixture arm outputs `abstain_no_speech_anchors` while direct arms show harmful accepted corrections — negative control working. Sample: `benchmarks/reports/Fx00-plumbing-report.md` |
| G0 real-media controls | **blocked (external input)** | User has not supplied E01 (Japanese anime ASS)/E02 (Mandarin drama) known-good episodes; registration procedure documented in `benchmarks/README.md` |
| G1 sync decision gate | **blocked** | Requires G0 + real runs; no algorithm selected; no thresholds invented |

## Environment facts (observed 2026-10-14, this session)

- Python 3.14.0 (`C:\Python314\python.exe`); numpy 2.5.0, scipy 1.18.0, torch 2.12.1, transformers 5.12.1 present.
- `ffmpeg`/`ffprobe`: present at `C:\Program Files\ffmpeg\bin\`.
- `ffsubsync`: installed 0.5.1 (`pip install ffsubsync`); CLI signature `ffsubsync <reference> -i <subs> -o <out>`; `--split-penalty` advertised.
- `pysubs2` 1.9.0, `pytest` 9.1.1, `ruff` 0.17.0 installed.
- `alass`: not found ⇒ `b1-al` reports `unsupported`.
- No configured ASR/semantic endpoint ⇒ `b1-va` integration boundary only, experiments `not_run`.

## Execution notes / open findings

- **Concurrent-session reconciliation (2026-10-14):** two orchestrator sessions worked the same brief in parallel. A parallel session created the canonical `benchmarks/bench/` package, tests, `Fx00` fixture, `run_bench.py`, the docs commit `8f50610`, and this ledger. The other session built a prototype `benchlib/` harness; to keep a single harness, the prototype was backed up outside the repo (`%TEMP%\opencode\benchlib_backup_261014_024537\*.zip`) and removed from the tree. Canonical harness + full test suite retained; prototype scoring-sign bug fix was independently confirmed, and a sign bug in the canonical `offset_recovery` metric was found and fixed with a new locking test.
- `benchmarks/cases/sources.json` and scratch/results trees are git-ignored (absolute local paths must not be committed once private episodes exist). Case manifests reference scratch-absolute `generated_path` — local-only, noted as a hygiene item.
- Canonical adapter CLI flags pinned from installed versions (ffsubsync positional reference + `-i/-o`), verified by real execution.

## Outstanding findings

- Real reference episodes absent → G0/G1 remain blocked (external input required).
- No numeric acceptance thresholds calibrated (by design; single-fixture synthetic runs are correlated, denominators = 1 episode).
- Adversarial read-only review (2026-10-14) findings triaged: P1s fixed (central scratch write guards incl. CLI-refused `report --out` outside roots; full-track tool-output mapping by file order with unsorted-event regression test); P2s fixed (run/score fingerprint verification aborting on tamper; b1-va candidate stamping; S02 zero-injection guard + 1.00005 scale removed; ASR confidence no longer inverts low-logprob transcripts); P3s fixed (end-boundary scoring, abstention-status exactness, residual-domain breakpoint detection, repo-root-relative manifest paths, dead code removed, fixture-audio wording corrected). Reviewer note: ASR confidence inversion verified by trace only (no local endpoint configured); will need re-verification when a real endpoint is used.
- Deferred P3: memory/VRAM resource measurement not implemented (wall/preprocess/candidate/ASR seconds recorded); acceptable for B0 baseline.

## Next action

Ask the user to supply/register E01 (Japanese anime, original audio + known-good ASS, ideally signs/karaoke/multi-track) and E02 (Mandarin drama/donghua, original audio + known-good English subs, ideally native subs too) on a read-only mount, then run `source add` → reference-sync verification → case matrix → candidate matrix → G1 evaluation.
