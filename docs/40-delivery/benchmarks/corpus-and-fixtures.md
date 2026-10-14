# Benchmark corpus, gold annotations and synthetic fixtures

**Status:** planned. No user media is included in this repository. **Owner:** benchmark inputs and ground truth. Related: [scoring](evaluation-criteria.md), [runner artifacts](harness-and-artifacts.md).

## Source material and rights

Begin with **two user-provided known-good full episodes**, adding independent material when coverage demands it:

| ID | Preferred source | Principal challenge |
| --- | --- | --- |
| E01 | Japanese anime with original-language audio and accurately timed ASS, ideally signs/karaoke/fonts and alternative tracks | VAD false matches, overlapping layers, moving ASS elements |
| E02 | Mandarin drama/donghua with original audio, accurate English subtitles and ideally native-language subtitles | Fast dialogue, segmented/condensed text, pronouns, CPS |
| E03 (later) | Korean content or independently sourced different-release cut | Out-of-language and release generalization |

A *known-good* release is **not** a perfect oracle. Manually inspect beginning/middle/end and sign/music-heavy regions **before** introducing errors. Verify language/audio stream and source-vs-dub identity; check translation accuracy separately from timing accuracy. Keep private/licensed media outside Git and Plex-watched benchmark outputs; mount library inputs read-only. Track license/redistribution restrictions; publishing a derived clip may also require permission.

Use short, representative excerpts for quick iteration and full episodes for drift, discontinuities, full-ASR, and throughput. Group all variants from the **same source episode** in the same evaluation split. Never tune on one corruption variant and declare a different corruption of the *same episode* a held-out independent test. Keep at least one separate episode/series as a later holdout.

## Distinct gold labels

Do not conflate these reference facts:

- **Original media:** exact source file and audio stream, hash, container duration/timebase, selected subtitle track ID, source subtitle cue/event identity, style and language.
- **Speech ground truth:** spoken original-language words/utterances and *actual audio* onset/end (with human annotation uncertainty), speaker if known.
- **Subtitle correspondence:** links from source utterances to subtitle cue groups (1:1, 1:N, N:1, unmatched, condensed/repeated), with signs/songs explicitly typed non-speech.
- **Subtitle display ground truth:** acceptable display interval/range, not necessarily equal to speech bounds; intentional overlap and ASS effects noted.
- **Translation judgments:** verified meaning and alternative acceptable renderings, genuine errors versus stylistic variation; ambiguous Mandarin referents allowed to remain unresolved.

Start with **small stratified human-labeled subsets** (illustratively dozens of dialogue relationships and hard examples), not a demand to annotate an entire season. Use independent human review where feasible. Preserve label provenance, uncertainty and annotation revisions. A synthetic inverse transform tests recovery of injected errors, **not** whether the reference subtitle was already optimally readable.

## Synthetic scenarios (run against copied subtitles)

| Case | Perturbation | Gold target / negative condition |
| --- | --- | --- |
| S00 | Untouched clean control, including intentional ASS overlaps | No harmful modifications |
| S01 | Small/large ± global shifts | Recover stable offset; don't introduce cue-by-cue jitter |
| S02 | Linear drift / sample 23.976↔25 time scaling | Recover scale without spurious jumps |
| S03 | One or more piecewise offset discontinuities | Restore regions on **both sides** of every breakpoint |
| S04 | Individual mistimed dialogue cues | Don't shift entire correct regions |
| S05 | Remove/duplicate/merge/split dialogue cues | Preserve unmatched and group relationships |
| S06 | Insert sign-only, karaoke and SDH cues among speech; standalone signs-only track | Non-speech cannot become audio anchors |
| S07 | Two related/retimed tracks plus truly independent and complementary tracks | No duplicate evidence, unsafe merges or style loss |
| S08 | Verified mistranslations: negation, numbers, names, speaker/referent; good paraphrase controls | Fix real errors, preserve valid text |
| S09 | Too-high CPS, adjacent crowding, intentional layers/animated motion | Legibility without unintended layout changes |
| S10 | Wrong or unknown language, forced/commentary/SDH labels, mixed-language intro/credits | Safe corrections/abstention by class |

Use deterministic parameters and seeds; keep exact original cue IDs/ordering, corruption manifest, and expected inverse map. Ensure negative or out-of-file timestamps are detected rather than silently clamped in the scoring reference. Ensure all generated output goes to scratch, never to the input library.

**True release edits are a separate fixture type:** shifting subtitle timestamps is *not* the same as removing/adding video scenes. Make a small media derivative with an actual removed/added section (stream-copy when feasible, otherwise document any decode/re-encode and codec/timestamp side effects), and record media↔source-timeline mapping including **unmatched** intervals. Validate actual edit boundaries and keyframe behavior. A benchmark that only fabricates timestamp jumps cannot prove handling of changed footage.

## Prevent contaminated comparisons

- Fix **episode and cue gold data** before model comparisons. Keep prompts, model inputs, and evaluation clips frozen within a paired experiment.
- Stratify reports by language, scenario, dialogue density, and cue type. Test sign-heavy samples explicitly; don't treat absent anchors as algorithm failure if the safe output is abstention.
- Provide a truly independent holdout for later threshold calibration. Do not leak manual corrections or target labels into inference prompts except in a separately labeled oracle-input ablation.
