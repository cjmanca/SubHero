# Track inventory, language, forced and commentary correction

**Owner:** metadata engine · **Related:** [Plex/sidecars](plex-and-sidecars.md), [model routing](../30-app/models-and-resources.md), [scoring](../30-app/quality-and-triage.md).

## Inventory and semantics

- Inspect **every audio and subtitle stream** and matching external text subtitle, regardless of track order, for language code, IETF language tag where available, title/name, default/forced/commentary/original/SDH flags, type/format, channel count/layout and other relevant stream metadata.
- Metadata audit and correction are **independent** from subtitle enhancement; no full-episode ASR is required for ordinary metadata processing.
- Treat actual primary spoken language, actual written subtitle language, purpose, track flags and preferred playback ordering as separate properties. Do not equate the first audio track with the original-language source.

## Audio-language classification

- Extract several **stratified speech-rich samples** distributed through the recording (rather than one arbitrary clip). Avoid silence, intro/outro music, credits, background-only speech and incidental foreign-language snippets when assessing the **dominant** spoken language.
- Aggregate languages, consistency, sample quality and conflicting results into explainable evidence; optionally resample/escalate. Support audio with occasional foreign language without falsely relabeling the whole stream.
- Distinguish original-language audio, dubs, and possible commentary when evidence allows. Commentary may be labeled and flagged secondary; ambiguous commentary remains unchanged/reviewed.
- Separate optional track reorder from header metadata edits. Plex may choose among language matches partly based on actual client/audio format; keep channel layout in policy rather than blindly sorting stereo/5.1. Reordering is configurable and requires remux.

## Subtitle-language/type classification

- Extract text from embedded and external **text** subtitles, normalize styling without erasing meaningful dialogue, sample across the episode, and classify **dominant written language**. Permit scattered Japanese/Chinese karaoke lyrics in an otherwise English subtitle track.
- For **bitmap** PGS/VobSub, raw images do not provide directly classifiable written text. Use existing reliable metadata/evidence, or **optionally** escalate to OCR when enabled and supported. Without adequate OCR or other evidence, mark language **unassessed / needs OCR** and leave a possibly valid label unchanged; never report a confident autonomous language correction inferred from bitmap stream order or filename alone.
- Detect likely full-dialogue vs reduced signs/songs/forced vs SDH vs dub-matched vs commentary vs unknown. Count, temporal coverage, dialogue correspondence, positions/styles, song/sign patterns, and subset relationships with full tracks; counts alone are insufficient.
- A reduced signs/songs track is often a subset of a full track (full tracks themselves usually include signs/songs). After classifying candidates as genuinely **reduced/non-full**, prefer the more **complete signs/songs candidate**, with **number of distinct relevant entries and episode coverage** useful tie-breakers; never classify a full-dialogue track as forced merely because it has the most entries. Subset relationships, dialogue density and semantic purpose matter more than raw counts. Only set forced where it sensibly accompanies **same-language audio**, with Plex selection verified separately.
- **Correct false forced flags as well as missing forced flags.** Prefer non-commentary for normal selection; encode commentary flags/titles where supported but don't assume Plex will honor them as exclusion.
- Language metadata must remain standards-compliant. Do not incorrectly label English as Japanese merely to change Plex preferences. The reversible `und` workaround belongs to [Plex/sidecars](plex-and-sidecars.md).

## Confidence and action policy

- Configurable thresholds **per classification/action**, lower default evidentiary burden for unknown→known than overriding a contradictory valid label; calibrate empirically, not arbitrary 90–98% thresholds.
- Separate observations (sample votes, ASR coherence, track purpose, existing labels) from a potentially uncalibrated model score. Aggregate to a decision with uncertainty and explanation.
- Apply safe high-evidence corrections unattended; unresolved conflicts go to metadata review. Allow audit-only mode and manual override. Never propagate a bad classification to all tracks on the strength of one sample.
- Track titles may be enhanced to indicate dub-matched, commentary, original language or generated origin when justified; preserve existing useful titles.
