# Candidate subtitle selection and source relationships

**Owner:** enhancement source inventory · **Related:** [matching](matching-and-translation.md), [consolidation](consolidation-and-formats.md), [glossary](series-glossary.md).

## Input evidence

- Discover **all** embedded and associated external subtitle tracks (full translations, alternatives, forced signs/songs, SDH, source-language subtitles, dub-matched captions, and OCR text if available), plus all audio tracks. Exclude previously generated tracks as *independent* reference translations while allowing their approved corrections to inform reprocessing.
- Automatically select a **base subtitle** in requested target language by available track quality, accuracy, completeness, timing and style. User can override base, alternative evidence sources and reference audio.
- When several plausible bases compete, support an **optional, benchmarked candidate-comparison path**: evaluate alternative base-derived enhanced outcomes (or a cheaper representative subset) on consistent criteria, then select the best *validated* result rather than assuming the highest initial source score always wins. Do not require multiple full generations for every file by default; record which bases were compared, cost, uncertainties and why one was selected.
- Original-language audio is the primary evidence for what was spoken. Source-language text tracks can be better than ASR at particular words but may omit lines or be timed to another release. A dubbed audio stream may supply context or a localization option but can diverge significantly; the default does **not** favor dub dialogue.
- Classify likely dub-matched transcript vs source-language translation using titles, text/audio correspondence or other evidence. If high confidence and unlabeled, propose/optionally append a short useful track title description; never misrepresent uncertain origin.

## Comparing tracks

- Prefer base-track **translation style and voice**; borrow other lines when clearly better, to repair mistakes, fill gaps or carry superior formatted sign/song events. Do not produce a stylistic patchwork by independently selecting the highest-scored paraphrase for each cue.
- Detect relationship among source subtitles: retimes, punctuation edits, modified copies, alternate releases, genuinely independent translations. Correlated sources are not multiple independent votes in terminology/translation confidence.
- Score translation accuracy, sync reliability, completeness, readability and formatting independently; don't assume that "official" vs "fansub" is reliably labeled. A user-maintained trusted-release-group list is evidence weighting, not infallible truth.
- Track relationships may be N:1, 1:N or unmatched. Preserve provenance and uncertainty at **individual event** level; compare signs/songs using semantic and visual-style role, not only text.
- Each source must have its **own timeline mapping** to the actual episode before borrowing events, especially for releases with removed ads or different openings. A purely signs/karaoke track may inherit a mapping from a **proven same-release sibling** or reliable independent non-speech anchors, with evidence recorded; it must not be assigned a speech map merely because another track exists. If mapping is unresolved, do not time-shift/merge it speculatively: preserve the source event or flag it for review. Use the common audio timeline and don't merge on raw timestamps.

## Special cases

- A full dialogue track normally includes relevant signs/songs because a typical player shows only one subtitle track. A reduced forced signs/songs track often overlaps as a subset of the full track. Its mere existence does **not** make the user experience complete or establish a high file-level quality score.
- Select original-language vs dub-influenced translation policy separately from which audio stream supplies timing. Preserve target-language choice (English default, other languages supported when configured models can handle them).
- No subtitles: allow generation of a complete target-language track from audio ASR/translation. Source-language subtitles, if present, should inform the result rather than relying solely on ASR.
