# Audio transcription, forced alignment and utterance segmentation

**Owner:** reference-audio analysis · **Related:** [sync](lightweight-and-full-synchronization.md), [matching](matching-and-translation.md), [models](../30-app/models-and-resources.md).

## Reference-audio workflow

1. Inventory audio languages, dubs/commentary; select the actual original-language dialogue audio by policy and evidence, with explicit user override. Do not assume first track is original.
2. Decode audio in manageable, bounded segments with overlapping context; retain original media offsets and source stream ID. Analyze long episodes without unbounded GPU/memory use. Avoid duplicate utterances in overlapping windows.
3. Independently transcribe **the full episode** for full enhancement using the source language. Preserve recognized text, language, model identifier/hash/version/configuration, segment provenance, diagnostics and any supported confidence signals.
4. Align **source-language ASR text to corresponding source-language audio** with a forced aligner. English translated subtitles are *not* fed to the forced aligner. Convert relative word/character times to absolute media timestamps.
5. Segment aligned units into logical utterances by pauses, punctuation, VAD, conversation turns and optional diarization. Preserve word-level timing; speech utterances are not assumed to correspond one-to-one to subtitle cues.
6. Use source-language subtitle text or selective secondary ASR to investigate disagreements; the audio is authoritative but **ASR interpretation is fallible**. Misrecognition of negation, names, numbers and short responses is especially dangerous.

## Candidate models and capability envelope

- **Candidate default:** `Qwen3-ASR-1.7B` + `Qwen3-ForcedAligner-0.6B`, integrated or separately called. Compare alternative ASR (e.g. Whisper-family) or alignment engines if necessary; never hardwire the pipeline to Qwen.
- Document the 11-language intersection for full ASR+alignment with this default backend: **Mandarin Chinese, Cantonese, English, French, German, Italian, Japanese, Korean, Portuguese, Russian, Spanish**. Other languages can be metadata-classified and can become full-pipeline supported with appropriate model capabilities.
- **Forced aligner runtime limits need version testing:** Qwen documentation describes up to five-minute inputs while its repository's inference toolkit contains shorter input guards in some paths. Always use conservatively bounded windows and derive effective limits from installed backend.
- `Qwen3-ASR` can process speech/song audio but song detection does not establish lyric translation quality. Music, effects, intense anime delivery, crosstalk, whispering, Cantonese/Mandarin switches and different speaker voices are explicit evaluation risks.
- Forced alignment **places provided words**; it does not prove that the words were spoken, separate speakers, or assign final subtitle display lengths.

## Multiple speakers and future extensions

- Ordinary ASR covers foreground dialogue. Diarization may assign provisional speaker IDs but cannot reliably identify characters or disambiguate Mandarin *tā* referenced gender.
- Optional source separation + targeted secondary ASR may recover overlapping/background speakers; opt-in **experimental late phase**. Future visual speaker matching is not a first-phase requirement.
- Cache transcript and per-token alignment indexed by audio-stream identity plus model/settings. Extracted/decoded audio is **temporary by default** and cleaned up after processing.

**Primary reference:** [Qwen3-ASR repository](https://github.com/QwenLM/Qwen3-ASR).
