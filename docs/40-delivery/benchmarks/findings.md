# Benchmark findings and algorithm decision records

**Status: harness executed on synthetic plumbing fixtures; no real-media experiments yet.** This page is an index of actual evidence and decisions, not a prediction of winners. Source requirements remain in their owning feature documents; unresolved items remain in [the experiments register](../open-questions-and-experiments.md).

## Experiment status

| ID | Purpose | Current state | Evidence/decision |
| --- | --- | --- | --- |
| B0 | Corpus, labels, minimal runner | **in_progress** — runner + synthetic fixture complete | `benchmarks/` CLI implemented; offline runs on `Fx00` fixture produced machine-readable proposals/scores; real-media clean controls (G0) **pending** user episodes E01/E02 |
| B1 | ffsubsync / ALASS / targeted ASR validation | **in_progress** — arms executable, plumbing matrix run | ffsubsync 0.5.1 global + `--split-penalty` executed; ALASS absent → arm records `unsupported`; `b1-va` → `not_run` (no local ASR endpoint configured). No algorithm selection; G1 **blocked** pending real media |
| B2 | Full source-language ASR + forced alignment | **Not started** | None |
| B3 | Cross-language utterance/cue matching | **Not started** | None |
| B4 | Translation correction | **Not started** | None |
| B5 | Source consolidation and ASS/SRT integrity | **Not started** | None |
| B6+ | Metadata, glossary, quality, OCR, Plex, Unraid | **Not started** | None |

Mark `not_run`, `blocked`, `in_progress`, `completed` or `invalidated` explicitly. Never change a row to completed solely because a runner produced output files: a finished experiment must have inspected evidence and a conclusion.

## Observed B0/B1 infrastructure evidence (2026-10-14, offline synthetic only)

- Environment: Python 3.14.0; `ffsubsync 0.5.1` (installed; `--split-penalty`, framerate flags verified against installed version); `ffmpeg`/`ffprobe` present; **ALASS not installed**; no ASR model endpoint configured.
- Harness behavior verified on the redistributable `Fx00` synthetic fixture (tone bursts filling dialogue windows — plumbing validation only):
  - Deterministic corruption generators S00–S04/S06 with recorded per-cue injected deltas and exact inverse maps; repeated same-seed preparation produces byte-identical output; invalid timestamp injections (negative starts) raise `InvalidTime` and are rejected, never clamped.
  - Clean S00 controls produced zero harmful accepted corrections for global arms (`b1-fg`, `b1-px-fg`); piecewise arms introduced small 6–44 ms tails on controls on the tone fixture.
  - Signs-only tracks: proxy arms record `abstain_no_speech_anchors` and leave timing unchanged; direct arms produced harmful accepted corrections (3.6 s median residual), i.e. the negative control exposes exactly the false-anchor hazard the proxy design targets.
  - Tool-absent states recorded as `unsupported` (ALASS) and `not_run` (targeted-ASR without endpoint); `not_run`/`unsupported`/`abstain`/mapping-failure states recorded honestly, with no synthetic zero-scores fabricated.
  - 49 focused offline tests pass; `ruff check`/`ruff format --check` clean.
  - Independent read-only adversarial review conducted; accepted findings fixed and locked with regression tests: central scratch-root write guards on manifests/reports/subtitle saves/proxy outputs/tool outputs/validator logs (CLI-refused `report --out` outside scratch roots), fingerprint verification before every `run`/`score` (aborts with SOURCE CHECK FAILED on tamper), full-track tool-output mapping by preserved file order (unsorted-event regression test), S02 zero-injection guard (drift scales that quantize away are rejected), validated arm relabeled as `b1-va` in scores, end-boundary timing errors scored alongside onsets, abstention-status exactness, breakpoint detection computed in the original timeline domain, and repo-root-relative paths in committed case manifests.
- Sample machine-readable + human report: `benchmarks/reports/Fx00-plumbing-report.md` (synthetic denominators: 1 fixture episode; all variants correlated).
- **Conclusion so far:** the harness can execute the B1 matrix and score it honestly; **no candidate is adopted**, and the G1 gate has no real-media evidence. Real-episode registration procedure and stream-selection requirements are documented in `benchmarks/README.md`.


## Decision record template

Copy into a **new** decision record under `docs/40-delivery/benchmarks/decisions/` only after running that experiment. Use stable IDs such as `BENCH-SYNC-001.md`. Do not fill sample scores or invent outcomes.

```markdown
# BENCH-<DOMAIN>-<NUMBER>: <Decision title>

- Status: proposed | validated | conditional | rejected | superseded
- Date: YYYY-MM-DD
- Requirements: <links to owning documents>
- Open question IDs: E07, ...
- Corpus: <episode/source IDs, held-out status, annotation version>
- Candidate versions: <exact code/model/weight revisions and settings>
- Run artifacts: <local results path or committed redacted aggregate>

## Hypothesis and controlled comparisons
<conditions, baseline and negative controls; what was held fixed>

## Observations
<metrics with denominators/uncertainty, regression counts, runtime/cost>

## Failure analysis and scope
<important false accepts, language/content limits, unsupported cases>

## Decision
<adopt | adopt conditionally | defer | reject and why>

## Safe fallback and reevaluation triggers
<abstention/escalation when uncertain, upstream changes, new corpus>

## Follow-up documentation changes
<owning requirement document and open-experiments register update>
```

A conditional decision should state **where** it applies (e.g. global offsets only, not sign-heavy piecewise releases). If comparable candidates have insufficient evidence, explicitly record *no selection*, with the smallest additional experiment needed.

## Reporting discipline

- Publish aggregate tables and actionable failure examples **without copying private episode content** into public docs. Track local media paths and private annotations via access-controlled manifests.
- Document each candidate's **unmodified-control regression** rate, acceptance versus abstention, and failures around discontinuities; never show a winner by mean timing error alone.
- Separate measured facts from inference; attach input and command hashes, software/model versions, human-label uncertainty and usable reproduction steps.
- Calibrate automated thresholds only after independent holdouts; record version- and language-specific limitations, and reevaluate decisions after upstream model/tool changes.
- Update the [open-experiments register](../open-questions-and-experiments.md) and one owning requirements document when necessary. Do not silently promote a provisional result into a product requirement.
