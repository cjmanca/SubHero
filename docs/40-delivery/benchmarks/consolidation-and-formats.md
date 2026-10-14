# B5 — Multi-source consolidation and ASS/SRT integrity

**Status: pending; after correspondence/timing are trustworthy.** **Requirements owner:** [consolidation/format policies](../../20-subtitles/consolidation-and-formats.md) and [source selection](../../20-subtitles/source-selection-and-ancestry.md). **Shared scoring:** [criteria](evaluation-criteria.md).

## Evaluation target

A complete **watchable single enhanced track** based on a strong target-language base, optionally using alternative translations, original-language subtitles, positioned signs, songs and verified ASR omissions. We must **deduplicate equivalent events**, preserve base writing style and formatting, and avoid treating multiple incomplete tracks as already providing a complete viewing experience.

## Candidate comparisons

- **Base-only no-change** output versus source selection from ranked tracks (including known-good release-group priors and observed track quality).
- Best single base with **selective borrowing** versus competing base-track candidates whose *resulting enhanced outputs* are individually evaluated; don't pick by number of events alone.
- Cross-track matching with independent source alignment and ancestry-aware agreement versus naive time-overlap or concatenation baseline (negative control only; never publish it).
- ASS structural compositor with **format/class policy**: (1) allow SRT→ASS promotion when beneficial, (2) retain selected base's SRT/ASS class and conservatively degrade incompatible borrowed content, (3) force SRT with explicit loss/review. Include original ASS base with alternate SRT and vice versa.

## Hard fixtures

- Full dialogue subtitles typically also contain signs/songs; a reduced forced track may be a **subset** with better typesetting. Borrow equivalent positioned signs rather than duplicating a normal top/bottom cue.
- Signs-only track with no speech anchor; different-release subtitle streams; intentional overlaps **within one source** versus newly introduced cross-source collisions.
- Distinct ASS `PlayResX/Y`, style names with different values, scaled `\pos`, `\move`, `\org`, `\clip`, overrides and fonts/attachments; multiple layers, fades, karaoke and clipping/scrolled signs intentionally off-frame.
- ASS animated event moved rigidly versus its duration changed; recognize that unbounded motion timing may change if event duration is stretched. Do not treat an off-screen animation endpoint as an error.
- Missing foreground dialogue added from ASR, overlapping background dialogue (later **opt-in** only), dense CPS, split/merged cues, adjacent scheduling conflicts and required review groups.

## Assertions and review

Structural checks by default: parser round-trip, cue/event identity and source provenance, style/attachment resolution, coordinate-transform preservation, layer precedence, event-local animation semantics, no accidental duplicate or unintended collision. Optional **procedural** frame-render checks may be used for selected changed events; **no AI vision requirement**, and no blanket fail for legitimate movement off-screen.

Report semantic/text omission or duplication, correct added events, intentional/unintentional overlap, class/format loss, readability before/after, and per-event risk. In force-SRT mode record what could not be represented; never silently drop narratively essential dialogue. If no safe layout exists, abstain or route a dependent correction group to review.

At G4/G5 choose safe compositing primitives and conditional output policies, not a universal claim of perfect ASS animation preservation. Output must remain attributable to **its source events**, not only its generated track.
