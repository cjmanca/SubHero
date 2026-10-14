# Benchmark protocols — index

**Status: proposed; no benchmark runs or model selections have been completed.** These documents define repeatable experiments and reporting rules, **not** the final application implementation plan. Start with [the benchmark requirements](../evaluation-and-benchmarks.md); safety and non-regression requirements remain in [invariants](../../00-foundation/invariants.md) and [acceptance policy](../acceptance-and-regression-policy.md).

## What the experiments must decide

- Whether **ffsubsync (global/piecewise)** or **ALASS**, guarded by targeted source-grounded ASR checks, can safely correct timing without custom synchronization machinery.
- Whether full-episode **ASR + forced alignment** gives reliable anchors for original-language Chinese, Japanese and Korean TV/anime.
- Whether **direct multilingual embeddings**, **translation-first**, or **hybrid constrained alignment** best links audio-derived utterances to subtitle events, including gaps and release edits.
- Whether selective translation correction and multi-track consolidation genuinely improve subtitles without degrading already-good translations, readable timing, or ASS formatting.
- Which metadata, glossary, score-prediction, playback and filesystem behaviors require measured safeguards or fallback policies.

These are candidate approaches, not commitments. Record cases where **doing nothing or abstaining** beats an unsafe repair.

## Choose the smallest relevant document set

| Task | Read | Optional background (only when needed) |
| --- | --- | --- |
| Obtain/generate benchmark inputs | [Corpus and fixtures](corpus-and-fixtures.md), [Harness and artifacts](harness-and-artifacts.md) | [Evaluation criteria](evaluation-criteria.md) |
| Score runs / establish thresholds | [Evaluation criteria](evaluation-criteria.md), [Findings](findings.md) | [Harness and artifacts](harness-and-artifacts.md) |
| **First experiment: light synchronization** | [Synchronization](synchronization.md), [Evaluation criteria](evaluation-criteria.md) | [Corpus](corpus-and-fixtures.md), [subtitle sync requirements](../../20-subtitles/lightweight-and-full-synchronization.md) |
| ASR and forced alignment | [ASR and alignment](asr-and-alignment.md) | [Corpus](corpus-and-fixtures.md), [ASR requirements](../../20-subtitles/asr-and-forced-alignment.md) |
| Source/target semantic correspondence | [Semantic matching](semantic-matching.md) | [ASR](asr-and-alignment.md), [matching requirements](../../20-subtitles/matching-and-translation.md) |
| Translation quality and correction | [Translation](translation.md) | [Semantic matching](semantic-matching.md), [glossary requirements](../../20-subtitles/series-glossary.md) |
| Multi-source formatted output | [Consolidation and formats](consolidation-and-formats.md) | [format requirements](../../20-subtitles/consolidation-and-formats.md) |
| Metadata, scores, Plex, storage, OCR | [Secondary experiments](secondary-experiments.md) | Only the corresponding owning requirement document |
| Record or reevaluate a result | [Findings / decision template](findings.md), [Evaluation criteria](evaluation-criteria.md) | Specific experiment protocol |

## Experimental order and gates

1. **B0 — Corpus and minimal CLI runner.** Verify reference quality, preserve originals, define manifests and scoring.
2. **B1 — Synchronization.** Compare no-op, ffsubsync global/piecewise, ALASS and targeted-ASR validation. **Only B0+B1 are the initial implementation scope.**
3. **B2 — ASR/alignment.** Measure model transcription and timestamp reliability independently.
4. **B3 — Cross-language matching.** Compare equivalent inputs and matching algorithms.
5. **B4 — Translation correction**, then **B5 — multi-source consolidation** when correspondence is trustworthy.
6. **B6+ — Secondary tests:** metadata, glossary, quality/opportunity, OCR, Plex selection, Unraid publication, Tdarr concurrency. Experimental background dialogue last.

Benchmark outputs should be reusable as regression evidence, but **the harness is a standalone Python CLI**, not a premature implementation of the production queue, UI, MCP, API, database or model-management architecture. A future `benchmarks/README.md` beside the *runner code* will explain actual commands **once those commands exist**.

Results and adopted choices belong in [findings](findings.md) and [the open-experiments register](../open-questions-and-experiments.md). Update exactly one owning requirements document when a benchmark proves that a requirement's proposed approach needs revision.
