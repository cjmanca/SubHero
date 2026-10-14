# B2 — Full ASR, forced alignment and source segmentation

**Status: pending; start after B1 has informative cases.** **Requirements owner:** [ASR/forced alignment](../../20-subtitles/asr-and-forced-alignment.md). **Shared scoring:** [criteria](evaluation-criteria.md).

## Primary questions

Can full independent transcription of original-language **Japanese, Mandarin and Korean** episodes give trustworthy utterances and times? How much does forced alignment improve word/character boundaries, and how often does it place **incorrect ASR words with deceptively plausible precision**? Are secondary ASR or source-language subtitles useful for targeted disagreements?

## Paired experiment arms

- Start with candidate **Qwen3-ASR-1.7B** on full-episode original-language audio; compare an alternative (e.g. appropriate Whisper-family model) on the **same audio and annotated regions** if accuracy or cost warrants it.
- Align **Qwen3-ASR source-language text** to matching source audio using **Qwen3-ForcedAligner-0.6B**. Never pass English translated subtitles as forced-aligner text for Japanese/Chinese/Korean speech.
- Align **human-corrected/native-language source transcripts** as an oracle-input ablation to quantify transcription-error contribution separately from aligner error; label oracle inputs explicitly.
- Test targeted **second-ASR** or verified native-language subtitle substitution on disputed segments, with and without nearby dialogue context.
- Test runtime variants (window length, overlap, decoding channel, ASR segmentation, VAD) one variable at a time before combining.

The Qwen project describes eleven forced-alignment languages, including primary test languages, and an up-to-five-minute input envelope, but actual **runtime/toolkit limits can be narrower**; pin installed versions and choose conservative bounded windows. Document observed failures instead of assuming README limits always apply. Other language coverage must be advertised as capability-dependent.

## Required correctness checks

- Decode the **chosen original-language dialogue stream** (not blindly Audio 0 or commentary); log stream ID, channel selection/downmix, sample rate, segment origin and sample-accurate-to-media timestamp mapping.
- Use bounded overlapping segments; verify deduplication and recognition **around segment edges**, long silence, music, overlapping speakers, and anime shouting/whispering.
- Annotate representative speech-rich windows, uncommon terms/names, numbers, negation and short interjections; also include silence, music and effects as **hallucination controls**.
- Record transcript content and diagnostics independently of alignment output. An aligner's ability to timestamp a word does not validate that it was said; speaker diarization is **not** implicit in forced alignment.
- Separate spoken word/character boundaries from **subtitle display** timing and sentence/utterance segmentation.

## Measurements and decision

Record CER/WER with documented language-specific segmentation and normalization, intelligible utterance omission, hallucination in non-speech, semantic-critical errors (negation/pronoun/name), speech onset/end error distributions, bad-but-precise forced matches, boundary-dedup failures, runtime per audio hour, peak VRAM/RAM and setup overhead. Provide both **clean-transcript conditional aligner error** and **end-to-end ASR→aligner error**.

At G2 decide: sufficient original-language anchors for downstream correspondence; a selective verification/fallback strategy; or constrained language/content coverage. Do not convert a single good transcript into a universal model recommendation. [Primary model documentation](https://github.com/QwenLM/Qwen3-ASR).
