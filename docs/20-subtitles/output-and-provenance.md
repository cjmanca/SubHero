# Generated subtitle output, revisions and lineage

**Owner:** publishing + subtitle provenance · **Related:** [safe writes](../10-media/safe-media-writes.md), [sidecars](../10-media/plex-and-sidecars.md), [data](../30-app/data-contracts-and-cache.md).

## Outputs and destinations

- Audit-only jobs publish reports, not modified media. Lightweight/full enhancement create **one new generated target-language subtitle track** derived from existing material when available; original text tracks remain intact (original **timing** correction is separately optional).
- **Stage before publishing:** generate pending-review `.ass`/`.srt` artifacts in a private working/review store **outside Plex-watched library roots**, never as a discoverable `Episode.en.ass` beside live media. Serve previews through the authorized UI/API. A draft must not shadow the selected subtitle or be auto-selected by Plex before approval. An explicit, separately authorized *live Plex preview* may temporarily publish a candidate with a defined cleanup/restore path; it is not normal review behavior.
- After applicable approval and validation, atomically publish the staged candidate as a discoverable external `Episode.en.ass`/`.srt` sidecar (no video remux), or embed it as requested. Unattended high-evidence output may be published automatically **only** under its configured action/approval policy. An external subtitle can remain the permanent result; repeated generations replace only the previous generated output identity.
- Embedded generated tracks should have clear titles, e.g. `English [AI Enhanced]` or `[AI Generated - Lightweight]`, with actual language and appropriate forced/SDH flags and provenance tags when feasible. **External sidecars cannot rely on a custom player-visible track title**; record identity elsewhere.
- Subsequent enhancement passes **replace the existing generated track/sidecar** for the same output identity, rather than accumulating revisions as live player options. Preserve revision history/rollback and manually approved corrections as authoritative evidence. Reprocessing starts from originals + approved prior changes, NOT blindly from previous AI output.
- Optional Plex-specific promotion/muting of originals is documented separately. Avoid rewriting an MKV only to add an external subtitle if Plex already selects it as desired.

## Per-pass report and inspectable evidence

- Every subtitle light/full enhancement pass must provide an **exportable, structured machine-readable correction report** (e.g. versioned JSON), independently of its final SRT/ASS file. Include source media/track/revision IDs, model/settings and pipeline versions, original vs proposed cue text and timestamps, additions/removals, timing regions and match references, evidence/rationale, confidence/uncertainty by dimension, change-group dependencies, validation issues, per-change review/approval actor/status, and what was actually published.
- Expose the report for authorized download via web UI/API and retain relevant inspectable intermediate stage artifacts (ASR, alignment, matching, translation, timeline mappings) according to cache policy. A report remains available even if publication is rejected or the job fails after proposals were generated; distinguish proposals from committed changes.
- Keep diagnostic annotations **out of subtitle playback text** (SRT has no standard comment syntax). Redact secrets/private endpoint credentials from exports; link evidence by stable identifiers.

## Provenance survives as much as possible

Use redundant layers, because third-party remux/transcode may remove some:
1. Embedded stream title and Matroska application tags when supported.
2. Format metadata/comments (ASS script info/comments) when safe; not portable/reliable through every remux.
3. Normalized subtitle dialogue+timing fingerprints, with optional approximate comparison tolerant of formatting/rounding changes.
4. Database links: source media identity/stream IDs, original cue ancestry, content hash, model/settings, generation/revision IDs, author/review provenance.
5. Media audio/video fingerprints to re-associate renamed or transcoded material, subject to expensive validation and uncertainty.

Do **not** rely on invisible/off-screen or end-of-video subtitle events as the normal ID system: they can leak into playback, trigger parser/renderer behavior and be stripped. A future explicitly experimental watermark could be assessed separately, but isn't required. When identity is ambiguous, **flag for review** instead of treating a possibly generated track as an independent human source.

## Revision/rollback semantics

- Preserve original cue text/timestamps, per-change evidence and approval status, previous generated revisions (possibly archived subtitle artifacts, not complete media copies), commit records and known file/track identity changes.
- Supports rolling back generated output and optional original timing edits. A glossary-only update may publish after local validation, while full subtitle re-enhancement requires its configured review policy.
- After Tdarr remux/transcode, sanity-check retained metadata/provenance, reapply known metadata if demonstrably lost, and rebuild or review generated tracks when fingerprints/text conflict.
