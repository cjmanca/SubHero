# Subtitle quality, metadata health, enhancement opportunity and triage

**Owner:** scoring/dashboard · **Related:** [UI](web-ui-and-review.md), [metadata](../10-media/track-metadata-and-classification.md), [review policy](../00-foundation/processing-profiles.md).

## Multi-dimensional scoring

| Dimension | Example inputs | May remain unknown? |
| --- | --- | --- |
| Timing | suspicious offsets, bad individual cues, drift, verification evidence | Yes |
| Readability | CPS, short display, long lines, duration constraints | No for parseable text |
| Completeness | source-track gaps; optionally VAD/ASR-confirmed omissions | Yes |
| Formatting | parse errors, collisions/overlap, ASS style validity | Partially |
| Translation | source-grounded meaning, contradictions, human review | Yes (often) |
| Language/track purpose | dominant language, forced/SDH/commentary classification | Partially |

Calculate per-subtitle-track quality, metadata health separately, and one **best individually usable full target-language track** score at file level. Signs-only tracks don't replace full-track scores; do **not** award a composite of two simultaneously unavailable tracks as if users could see them at once.

## User-facing aggregate and evidence coverage

- Present a **combined subtitle quality score** and **combined media health/metadata score** (weights configurable), alongside all component dimensions. Unassessed translation quality is **unknown**, not zero or implicitly perfect.
- Publish assessment coverage/depth and uncertainty alongside numbers to distinguish a fully verified 90 from a structural-only 90. Initial scoring formulas/weights are experimental and must be calibrated; avoid unsupported precision.
- A **file** may have high readability yet incorrect language flags; expose metadata vs actual subtitle experience separately.

## Enhancement opportunity and review sorting

- Estimate the **potential quality of an enhanced/consolidated track** using signals like complementary source coverage, suspicious gaps, timing defects, glossary inconsistencies and alternative track evidence. This is a forecast with uncertainty, **not** the quality of a track that doesn't exist yet.
- Where scores are **comparable**, show `opportunity_delta = estimated_potential_after_enhancement - best_existing_full_track_quality`, plus uncertainty/coverage, as a sortable/filterable column in the review and recommendation queues. Both operands must use the **same target language, scoring rubric, evaluated dimensions, normalization and assessment assumptions**; a structural-only existing score cannot be subtracted from a comprehensive semantic forecast without normalization or a matched-dimension re-score.
- If inputs have insufficient or mismatched coverage, or the estimate is too uncertain to support a number, show **unknown / not comparable** (and a qualitative enhancement recommendation) rather than a misleading numeric delta. Do not treat unknown translation quality as zero or implicitly good. If no eligible full subtitle track exists, report **no baseline full track** and a missing-subtitle/generation opportunity, not a fictitious `0/100` quality baseline.
- Sort numeric deltas only within a defined comparable cohort; group unknown/not-comparable cases separately, retaining their recommendation and urgency flags. Where useful, show a calibrated interval or uncertainty band instead of spurious precision.
- If no single full track is sufficient but multiple tracks are complementary, recommend/escalate source consolidation and review rather than counting them as an already high-quality viewing experience.
- Configurable recommendation thresholds; automatic queueing of full enhancement above a threshold is **optional**, not the unattended default. Recommendations can suggest only metadata correction, light retiming/glossary, or full enhancement based on issue type.
- Keep separate expected improvement vs confidence and cost to improve so priority can include effort/budget, but don't hide the plain delta.

## Calibration and regression monitoring

Ground weights and thresholds in scored reference clips. Measure post-enhancement *actual* track quality separately from predicted opportunity; compare predicted versus realized improvements over time. Avoid using model self-ratings as definitive quality percentages. Escalate uncertain/misclassified sources to review.
