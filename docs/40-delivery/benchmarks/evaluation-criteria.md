# Benchmark scoring, non-regression and decision gates

**Status:** measurement definitions proposed; no calibrated cutoffs or results yet. **Owner:** shared scoring and evaluation policy. Related: [acceptance](../acceptance-and-regression-policy.md), [corpus](corpus-and-fixtures.md).

## Fair comparisons

Use identical cases, input stream, cue subset and permissible preprocessing for paired candidate comparisons. Record any additional evidence available only to one method. First compare algorithms on **fixed verified upstream transcripts/matches**; separately measure end-to-end degradation with actual ASR errors. Stratify by episode, language, scenario, overlap/sign density and **timeline region**, not just overall mean.

Compare **proposal quality** and **automatically accepted quality** separately. Count abstentions, rejects, false accepts, auto-accepted good edits, and review burden; no-op is an explicit baseline. Do not reward a method for silently editing more cues. A clean/reference track and each unaffected segment are first-class negative controls.

## Primary measures

| Component | Main measures | Failure mode to expose |
| --- | --- | --- |
| Synchronization | Absolute error on correctly linked cue onsets/ends; median, P90/P95, shift/drift/breakpoint error; segment-level success | New shifts in previously good regions; large tail errors masked by median |
| Candidate validation | Correctness of *accepted* changes, false acceptance, abstention/coverage, ASR seconds per accepted safe correction | Speech detected but **wrong** dialogue matched |
| ASR | Language-appropriate CER/WER, omission/hallucination rate, semantic-critical negation/name/number errors | Wrong transcript mistaken for ground truth |
| Forced alignment | Word/character and utterance onset/end absolute errors *conditional on transcript correctness*; segmentation failures | Precise-looking timestamps for wrong words |
| Semantic matching | Link precision/recall for 1:1 and grouped links, wrong forced match rate, gap/unmatched correctness | False correspondence cascading into timing changes |
| Translation correction | Genuine-error correction precision/recall; fraction of already-good lines modified incorrectly, severity, human adequacy | Fluency improvements hiding changed meaning |
| Consolidation/layout | Text duplication or loss, unintended overlaps, broken style/font/layers/animation, intentional overlap retained | Semantically correct output rendered incorrectly |
| Metadata/quality | Classification confusion/abstention; calibrated quality and opportunity deltas, ranked recommendation utility | False forced/commentary edits; misleading cross-coverage delta |
| Cost | Wall time/audio-hour, inference calls/tokens, RAM/VRAM peak, scratch bytes and external billable costs | Faster method only because preparation excluded |

A corrected subtitle's **display end** need not coincide with speech end; score alignment-to-speech and human-acceptable display intervals **separately**. Synthetic inverse timing maps have exact parameters but are not evidence that pristine timing is universally optimal. Define harmful change using annotation tolerance or a declared evaluation tolerance *before* a run; report the tolerance alongside results. Count severe failures separately (large offset, lost dialogue or destructive formatting).

## Statistical safeguards

- Report counts and denominators (e.g. accepted candidates, **number of independent episodes**, altered vs unaltered cues). Don't imply hundreds of correlated cue observations represent hundreds of independent episodes.
- A fixed or paired confidence interval can be reported where useful; aggregate at episode or source-release level for generalization claims, not overconfident cue-level intervals.
- Separate a development/tuning set from an untouched held-out episode/series; variants from the same original stay together. Pilot results identify promising directions but **cannot calibrate final production thresholds**.
- Document operating points across configurable thresholds: precision–coverage–abstention and resource cost. Allow a safe 'review/unknown/unchanged' outcome.

## Experiment gates (not numeric pass criteria)

| Gate | Minimum evidence to continue | If not achieved |
| --- | --- | --- |
| G0 | Clean controls verified, gold labels plausible, media originals immutable, artifacts reproducible | Fix corpus/annotations first |
| G1 | Light timing method with validation measurably improves useful fixes **without unacceptable accepted regressions** on clean/jump cases | Keep unchanged/review; investigate failure before custom implementation |
| G2 | ASR+aligner yield reliable usable utterance anchors on representative speech with known failure bounds | Alternative model, selective verification or constrained feature coverage |
| G3 | Matching reliably represents true links and explicit gaps/uncertainty under release edits and paraphrase | Avoid missing-line/correction automation based on ambiguous links |
| G4 | Selective semantic repairs and consolidation outperform base track on verified cases while preserving good text/formatting | Restrict to review or defer risky features |
| G5 | Plex/storage/metadata operation demonstrates safety on actual supported environments and versions | Disable or gate incompatible automatic mutation |

The user rejected fixed illustrative 90–98% thresholds. **No percentage here is a configured production default.** After results, propose per-operation cutoffs (higher evidentiary burden for overwriting known labels than filling `und`), with coverage, uncertainty and version/corpus applicability documented. Preserve the findings when a different engine becomes superior later.
