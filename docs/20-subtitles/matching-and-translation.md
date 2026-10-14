# Cross-language correspondence and selective translation correction

**Owner:** semantic engine · **Related:** [sources](source-selection-and-ancestry.md), [ASR](asr-and-forced-alignment.md), [glossary](series-glossary.md).

## Matching problem

Audio-derived utterances (source-language text + absolute times) and each existing target-language subtitle track may differ in translation wording, segmentation, timing, source-release edit, omissions and non-dialogue content. Preserve relationships `1:1`, `1:N`, `N:1`, unmatched speech, unmatched cues and uncertain candidate sets. A subtitle's initial timestamp is **weak or conditional evidence**—it can be many seconds off.

Candidate methods to benchmark:
- Direct cross-lingual sentence embeddings (e.g. LaBSE/SONAR-family) to propose source↔translated cue candidates, without translating all utterances solely for matching.
- English/target-language translation of utterances for semantic candidate generation and comparison.
- Lexical/context constraints plus monotonic dynamic programming or sequence alignment with gaps, merges/splits and piecewise release mappings.
- Targeted multilingual LLM adjudication for ambiguous candidates; source-subtitle consensus weighted by **translation ancestry** rather than number of files.

Do not force every utterance into some subtitle. Do not interpret a missing direct match as proof of omission; neighboring cues may combine/condense repeated speech. Treat signs/song lyrics/SDH descriptions as event types separate from ordinary audio-speech matching.

## Detect genuine mistranslations without degrading good lines

- Compare original-language text, existing translation, candidate independent translation or direct source-grounded critique, nearby dialogue, established glossary, alternative subtitles, and (when relevant) dub dialogue. Track distinct confidence for ASR text, correspondence, translation meaning, terminology and layout.
- Explicitly check high-impact contrasts: **negation, numbers, quantity, names, speakers/referents, time, omitted clauses, idioms, emotional tone**. An embedding similarity score can remain high even when a negation is reversed.
- ASR can be wrong; when source text and existing translation disagree, use source-language subs, replay/targeted ASR, secondary models or manual review instead of automatically replacing an existing translation.
- Mandarin spoken **tā** cannot establish written 他/她/它 or referent gender. Speaker's voice does not identify who is *being discussed*. Keep ambiguity unresolved if context cannot justify a choice.
- Distinguish legitimate translation style from actual errors. Default to **base-track style and semantic fidelity**, leaving acceptable translations unchanged.

## Translation profiles and missing dialogue

- Configurable global/per-series translation policy: faithful vs natural vs more localized, retention of honorifics/cultural idioms, named entities, dub-influenced style **only by explicit preference**. Users primarily prefer subtitle-based translation, not default dub rewriting.
- Distinguish translation for **matching** (semantically faithful paraphrase) from translation for **final display** (natural, concise, readable without loss). Candidate `Hy-MT2-1.8B` vs `7B`; evaluate on target media; swappable provider/size.
- To add dialogue, verify that it is intelligible foreground speech not already represented by merged lines, ASR hallucination, incidental repeat, overlapping/background speech, or a different cut. Generate new cue using **measured aligned timestamps**, then optimize display. Confidence thresholds and review apply per change.
- No existing target-language subtitle: optionally generate entire translation from original-language audio, improved by trustworthy native-language subtitles. Multiple target languages depend on configured model support.

## Evidence product

Store per-source utterance/cue candidates, selected links, competing translations, source context, reasons for change/preservation, reviewed decisions and model settings. Reuse correspondences when translation models change; re-evaluate only dependencies that actually changed.

**Potential source:** [Hy-MT2](https://github.com/Tencent-Hunyuan/Hy-MT2). *Quality claims are not accepted without independent benchmarks on representative content.*
