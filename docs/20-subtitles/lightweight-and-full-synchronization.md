# Subtitle timing: light proposals, verification and full alignment

**Owner:** synchronization engine · **Related:** [ASR](asr-and-forced-alignment.md), [matching](matching-and-translation.md), [readability](readability-and-accessibility.md).

## Required problem coverage

Constant global offset; piecewise jumps due to commercial insertion/removal, altered scenes/intros/transitions; linear or nonlinear drift; individual cue timing mistakes; properly aligned regions that must remain unchanged; separately retimed source tracks; subtitles without spoken dialogue.

## Lightweight entry path (no cached transcript required)

1. Classify ordinary speech-like events vs signs, writing, songs, sound descriptions, complex animations. Build a **temporary dialogue-only synchronization proxy**; do not feed raw styled ASS output into a tool that may flatten it.
2. Use **ffsubsync as a first-line candidate generator**, evaluating global offset and experimental `--split-penalty` piecewise mode; consider framerate and sparse multi-segment options. Optionally compare ALASS baselines. Version/pin tools.
3. Extract mapping/candidate changes from tool output, not its rendered/rewritten subtitle as the source of truth. Preserve original structured cues and styles.
4. Select **targeted validation regions**, including beginning, middle/end, before/after every jump, uncertain or high-change regions, plus distributed control samples. Transcribe selected audio and validate semantic correspondence to subtitle text (possibly using native-language subtitles, multilingual embeddings or selective translation). ASR seeing speech alone is *insufficient* proof the line matches.
5. Apply confirmed regions only; if suspicious, escalate (targeted verification, full ASR per configuration) or leave unchanged + review. Do not trust ffsubsync/ALASS's best score unconditionally.
6. Cached full-episode ASR and correspondence, when valid, may allow inexpensive subsequent retiming without re-ASR.

## Full enhancement timing path

- Perform **full-episode, independent ASR** of reference original-language audio; forced-align validated source-language text, segment into speech utterances. Separate actual speech intervals from desired subtitle display intervals.
- Match audio utterances to **every** source subtitle track independently; derive robust high-confidence anchors per track. Support 1:1, N:1, 1:N, unmatched, reordered/edited release regions. Do not force low-confidence matches.
- Fit timeline region mapping with global offset, piecewise discontinuities, and gradual drift where justified. Anchors have uncertainty/weight; avoid forcing continuity through missing footage. Permit regions lacking evidence to remain unmapped/unchanged.
- Correct individual dialogue cue boundaries after broad mapping using audio onset/end and neighboring events, then apply **deterministic display-duration/readability rules**. An English subtitle can legitimately display longer than the source utterance.

## Protected event classes

- Signs and on-screen text have no speech anchor; apply only high-confidence release timeline mapping or later visual corroboration. A **signs-only/karaoke-only track may have no speech anchors at all**: infer its mapping only from a demonstrably same-release sibling full track, reliable text/visual anchors, or another validated relationship. Otherwise mark regions **unmapped/uncertain**, preserve their original timing or route them to review—never invent an independent speech-derived map. Do not assume sign duration should equal speech.
- Karaoke, moving/animated ASS signs, songs, narration, multi-speaker events and SDH captions require type-aware timing. Rigid event shifting is safer than stretching animations with duration-relative motion/karaoke. Preserve event-relative animation time unless a transformation is proven safe.
- If a timing fix would create overlap/layout problems, recompute adjacent intervals and submit dependent changes as a review group.

**Tool status:** ffsubsync supports experimental piecewise `--split-penalty`; evaluate empirically against ALASS and full ASR. References: [ffsubsync](https://github.com/smacke/ffsubsync), [ALASS](https://github.com/kaegi/alass).
