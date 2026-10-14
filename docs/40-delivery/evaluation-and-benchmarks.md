# Algorithm/model benchmark requirements (before final implementation plan)

**Owner:** experiments · **Related:** [acceptance](acceptance-and-regression-policy.md), [open questions](open-questions-and-experiments.md), [models](../30-app/models-and-resources.md).

**Detailed experiment protocols:** [benchmark index](benchmarks/README.md) (corpus, CLI artifacts, scoring, synchronization, ASR, matching, translation, consolidation and deferred experiments). This page owns **overall benchmark requirements**; specific protocols describe how to evaluate them. **No benchmark outcomes are recorded yet.**

## Initial research goal

Do not lock in expensive or custom pipelines before comparing existing tools on representative material. First prove independent timestamped original-language ASR; then cross-language correspondence and robust timing; then selective translation correction, readability, and format-preserving multi-source consolidation. Background-dialogue recovery is last.

## Corpus creation

**No benchmark episodes are presently supplied.** Build a small, versioned and legally redistributable synthetic benchmark plus a separate permissioned/private real-media benchmark. Synthetic corruptions provide exact ground truth; realistic TV/anime examples test noise, styles and translations.

Coverage matrix (minimum meaningful cases):

1. A correctly synchronized track that MUST remain unchanged.
2. Constant early/late offset; framerate or gradual drift.
3. Abrupt middle-of-episode jump (ads/cut/intro changes) and properly aligned regions adjacent to it.
4. Individual erroneous cue; 1:N/N:1 dialogue; intentionally condensed/repeated phrases.
5. Missing foreground line and false missing-dialogue alarms from overlap/background/music/ASR hallucinations.
6. Signs/writing and opening/ending karaoke not speech anchors; complex ASS layers, fonts and moving off-screen signs.
7. Multiple English/target subtitles with independent vs shared ancestry, competing translations and incomplete signs/dialogue.
8. Mandarin ambiguous pronouns, negation/numbers/names, a good translation that must not change, and a genuine mistranslation.
9. Poor CPS/too-short durations, competing neighbors, speakers overlapping; separately OCR bitmap subtitles.
10. Mixed languages within tracks, incorrectly labeled audio/subtitles, commentary, forced/SDH mistakes and hardlinked/simultaneously modified files.

Generate controlled timing corruption from known good reference media and subtitles; human annotate challenging real samples with actual speech, good translation and acceptable timing where practical. Document source licensing and redistribution constraints.

## Experiments to compare

| Benchmark | Alternatives / questions |
| --- | --- |
| Fast synchronization | ffsubsync global/piecewise, ALASS, temp dialogue-only proxy, VAD variants; no-change control |
| Validation | ffsubsync output alone vs targeted ASR + semantic check; sampling placement around discontinuities |
| Full transcription | Qwen3-ASR-1.7B (or other candidates) Chinese/Japanese/Korean with music/crosstalk; optional independent second ASR |
| Alignment | Qwen3-ForcedAligner vs available alternatives, alignment errors with imperfect ASR, segment overlap/window limits |
| Cross-language matching | direct multilingual embeddings vs translate-first vs hybrid constrained sequence matching |
| Translation | Hy-MT2-1.8B vs 7B and source-grounded critique; evaluate false positive edits, not only fluency |
| Consolidation | per-track alignment, dedup/subset detection, ASS style/coordinate conversion and rendering invariants |
| Metadata | stratified language samples; commentary/forced classifiers; exact-inventory/low-confidence controls |
| Playback | external vs embedded auto-selection and font behavior across relevant Plex configurations; `FlagCommentary=1` scanner compatibility on actual Linux/Unraid Plex versions |
| Storage | Unraid `/mnt/user` tested atomic commit under actual disk/pool paths, hardlink preservation, Tdarr race |

## Required artifacts from each experiment

- Input files/sample hashes and their provenance/license status; ground truth and intentionally introduced defects.
- Config/model/tool version and commands; output artifacts; timing/semantic change evidence; runtime/VRAM/I/O/cost.
- Quantitative metrics, illustrative successes/failures, regression rates and confidence threshold calibration.
- **Decision record**: candidate accepted/rejected/conditional with applicability limits, and which requirement/algorithm section must be updated.
