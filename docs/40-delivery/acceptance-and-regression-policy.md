# Verification gates, thresholds and proportional testing

**Owner:** quality and reliability acceptance · **Related:** [benchmarks](evaluation-and-benchmarks.md), [invariants](../00-foundation/invariants.md).

## What success means

- **Alignment:** speech utterance/cue match precision and recall, robustness to large release jumps, missing/merged cues, timing error distributions; importantly measure false corrections to good tracks and correctness **on both sides** of each discontinuity.
- **Translation:** precision of proposed meaning corrections, preservation rate for already-good translations, severity of negation/name/pronoun errors, human-rated semantic fidelity and readability; do not rank models only by fluency.
- **Omissions:** precision and recall for foreground missing dialogue; false detections caused by condensation, signs, background speech and ASR mistakes.
- **Presentation:** CPS/duration violations, adjacent conflict rate, stable formatting/ASS animation, invalid/off-screen **unintentional** rendering regressions, retained font/layer/style metadata.
- **Metadata:** dominant-language detection accuracy, commentary and forced precision/recall, sidecar naming compatibility, Plex observed track selection when that is the goal.
- **Operations:** atomicity and no Plex missing/partial file windows, exact original integrity where promised, recovery after interruption, source-change cancellation, correct hardlink behavior, idempotent reruns and provenance/rollback reliability.
- **Cost:** per-hour audio processing time, model loads, VRAM peak, storage space, external calls, ability to reuse prior stage artifacts.

## Threshold policy

No arbitrary percentages are fixed by this requirements baseline. The user specifically rejected excessively high illustrative 90–98% automatic thresholds. Establish calibrated defaults **per operation** on representative samples; require stronger evidence to overwrite a potentially valid value than to fill `und`, and stronger evidence for risky semantic edits than mechanical adjustments.

Confidence has distinct dimensions: model score, empirical evidence, decision safety, assessed coverage. A purported 0.95 LLM self-rating is not independently a 95% accuracy estimate. Require review/escalation when evidence contradicts or is missing; permit safe partial changes rather than all-or-nothing cue replacement.

## Safety gates before publication

- Validate generated subtitle parsability, output language/purpose, format constraints and dependent review changes. **Do not publish pending-review sidecars into Plex-watched roots**; approval/automatic authorization must precede final publication. Produce a structured correction report even when proposals are rejected.
- For remuxes, probe video/audio/subtitles/chapters/attachments and check stream preservation; verify media readable and source still current.
- For ASS, structural format/layer/coordinate validity is core; optional sampled **procedural** render validation may be disabled, with no naive off-screen failure for moving signs.
- Never publish a replacement using a non-atomic copy-over sequence or after another process changed source media.
- No silent loss of important text when forcing SRT; record omitted/degraded events and review outcomes.

## Testing philosophy

Test risk-bearing code paths and meaningful regressions proportionately: parser transforms, stream selection, timeline mappings, candidate matching, glossary application, cache invalidation, filesystem commits and API ACLs. Keep fixtures small and deterministic; avoid massive test harnesses or brittle tests that simply mirror mutable static data tables. Supplement algorithmic tests with real-world acceptance clips and explicit no-change baselines.
