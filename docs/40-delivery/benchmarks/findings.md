# Benchmark findings and algorithm decision records

**Status: no experiments executed yet.** This page is an index of actual evidence and decisions, not a prediction of winners. Source requirements remain in their owning feature documents; unresolved items remain in [the experiments register](../open-questions-and-experiments.md).

## Experiment status

| ID | Purpose | Current state | Evidence/decision |
| --- | --- | --- | --- |
| B0 | Corpus, labels, minimal runner | **Not started** | None |
| B1 | ffsubsync / ALASS / targeted ASR validation | **Not started** | None |
| B2 | Full source-language ASR + forced alignment | **Not started** | None |
| B3 | Cross-language utterance/cue matching | **Not started** | None |
| B4 | Translation correction | **Not started** | None |
| B5 | Source consolidation and ASS/SRT integrity | **Not started** | None |
| B6+ | Metadata, glossary, quality, OCR, Plex, Unraid | **Not started** | None |

Mark `not_run`, `blocked`, `in_progress`, `completed` or `invalidated` explicitly. Never change a row to completed solely because a runner produced output files: a finished experiment must have inspected evidence and a conclusion.

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
