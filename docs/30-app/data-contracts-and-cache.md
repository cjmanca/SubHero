# Internal evidence model and reusable stage artifacts

**Owner:** shared contracts/storage · **Related:** [profiles](../00-foundation/processing-profiles.md), [provenance](../20-subtitles/output-and-provenance.md), [queue](workflows-and-queue.md).

This is a **conceptual data contract**, not a required SQL schema or commitment to particular queue/db libraries. Keep immutable evidence distinct from mutable decisions/publication status.

## Main entities

| Entity | Required conceptual fields |
| --- | --- |
| `MediaIdentity` | path(s), fingerprints (file/stream), duration, codec/probe info, ingest/source generation, version changes |
| `MediaTrack` | embedded/external identity, track/stream ID, language, title, flags, codec, audio channels, source-file relation, scan evidence |
| `SubtitleSource` | original format and raw-content fingerprint/bytes where retained; encoding/BOM/newline/Unicode diagnostics; ASS script metadata/styles/fonts/attachments; type, independent track timeline, suspected ancestry, source-group |
| `Cue` | stable ID, parent source, immutable original timestamps/text/ASS event tags, type (dialogue/sign/song/SDH/etc.), speaker if known |
| `Utterance` | original-language text, absolute audio times, word alignment, source segment, language/speaker, confidence diagnostics/model |
| `Match` | source utterance IDs ↔ one/many cue IDs, hypotheses, evidence, uncertainty, alternatives and version |
| `TimeMapRegion` | source track interval → media interval, offsets/drift/jumps, anchor IDs, confidence/gaps |
| `ProposedChange` | separate proposed text, timing, add/delete, layout or flag changes with reasons, evidence, action threshold, status |
| `ChangeGroup` | dependent corrections that must be applied/revalidated together; approvals/rejections and actor/time |
| `GlossaryEntry` | term/aliases, translation, scope, confirmed/inferred/review status, supporting independent evidence |
| `QualityAssessment` | per-dimension observations/scores, coverage, uncertainty, track/file/metadata/opportunity score versions |
| `GeneratedRevision` | draft/staged vs published state and private location; output sidecar/track identity, output hash/metadata, parent inputs, applied changes, reviewer, rollback artifact |
| `CorrectionReport` | per-pass export/schema version, input/revision IDs, proposed vs applied edits, confidence/evidence, review status and validation/publication outcomes |
| `Job` / `StageReceipt` | submitted operations/ACL, state/progress, stage keys/models/settings, cached outputs, source version, attempts, errors |

Store intermediate evidence as structured, inspectable data (e.g. JSON or database records). Do not insert diagnostics in SRT (no standard comments) or embed large reports in the subtitle track.

## Keyed cache / invalidation boundaries

- **Audio changed:** invalidates ASR, forced alignment and downstream matches/translation/timing based on that audio.
- **ASR model/segmentation changed:** invalidates its transcript/alignment and downstream references, but not original subtitle parsing or metadata inventory.
- **Subtitle track text/content changed:** invalidates affected parsing, matching and correction proposals; audio transcript may remain valid.
- **Subtitle timestamp-only change:** update affected track mapping and presentation; may reuse utterance transcript and semantic matches after validation.
- **Translation model/style/glossary changed:** invalidate relevant translation, terminology and layout outputs, not audio ASR.
- **Readability thresholds changed:** rerun scheduling/formatting, not transcription.
- **OCR model changed:** invalidate bitmap-derived text and dependent matches, not original bitmap assets.
- **Container remux/Tdarr:** compare **stream identities**, not just container hash, to reuse audio analysis when decoded content is unchanged.

## Retention defaults and limits

- Extracted audio/temp PCM removed immediately after successful processing (and cleaned after failure/restart); configurable retention period may override.
- Keep ASR transcripts, matches, approval history and glossary entries **indefinitely by default**, associated with model version. Configurable retention for each cache class.
- Limit cache size/storage by configurable quota, evict recomputable artifacts preferentially, never silently delete approved history or original rollback metadata required by policy.
- Store time in a consistent high-precision format, retaining original SRT/ASS precision and source-frame/time-base metadata. Every edit must be attributable to an input/revision and reproducible policy.
