# Readability, secondary dialogue, SDH and lyrics

**Owner:** subtitle presentation · **Related:** [format preservation](consolidation-and-formats.md), [review](../30-app/web-ui-and-review.md).

## Ordinary dialogue presentation

- Track speaking interval **separately** from final subtitle display interval. Don't force cues to disappear with the final spoken phoneme; target-language text may need substantially more reading time.
- Compute per-cue characters per second (CPS), usable display duration, long lines, line count, gaps, overlap and scene-change risk. Initial configurable English guideline: **target about 15–17 CPS**, flag **~20+ CPS**; these are starting points, not universal acceptance rules.
- Prefer extending an undersized duration when there's room; otherwise consider careful condensation, splitting, merging or restructuring while preserving important meaning, tone and correct sequence. Never extend blindly over the next line, across an inappropriate scene cut or through important positioned text.
- Optimize neighboring cues jointly, not only independently; merge/split operations form review **dependency groups**. Respect user-configurable minimum/maximum durations, line-length, line-count and reading speed policies per target language and style.
- Positioned signs often appear only briefly in the video; do not force sign durations to match ordinary dialogue CPS. For static sign translations, keep source timing or high-confidence release mapping; visual OCR validation is optional later.

## Foreground vs background

- **Foreground dialogue** is the clear default priority. Preserve meaningful narration, radio/TV speech and intelligible relevant secondary lines where justified, without subtitle clutter.
- Optional **experimental, late-phase background-dialogue enhancement** is disabled by default. Multiple passes with diarization/speech separation/ASR may discover overlooked concurrent speech. Do not assume diarization alone separates voices or identifies characters.
- Configurable policy: **A** merge background line with foreground using speaker markers; **B** put secondary line in available safe space (often top), with bounded movement/resizing; if B fails, fallback to A or **C** omit from generated output and add proposal to review. Never choose **D**: overlapping unreadable text by default.
- Preserve role labels and provenance internally even if output is SRT and cannot display separate layers. Future visual placement near speaker is not currently required.

## SDH and songs

- Permit converting an existing SDH track into standard dialogue subtitles by removing appropriate sound-effect/speaker-description cues while preserving meaningful dialogue. **Do not promise reliable SDH creation from ordinary dialogue** without strong speaker/sound evidence; optionally generate both only if defensible.
- Song/opening/ending translations and karaoke effects should be preserved where present. Do not generate lyrics for all background music by default. Do not classify all karaoke as spoken-dialogue sync anchors.
- Sign translations, sound effects, narration and overlapping speakers require distinct subtitle-type labels for matching, timing and scoring.
