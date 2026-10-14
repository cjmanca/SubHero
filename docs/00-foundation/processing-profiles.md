# Operations, profiles, and correction policies

**Owner:** job semantics · **Related:** [queue](../30-app/workflows-and-queue.md), [synchronization](../20-subtitles/lightweight-and-full-synchronization.md), [quality](../30-app/quality-and-triage.md).

## Independently queueable operations

- `metadata-audit` / `metadata-correct`: entire file, all audio/subtitle tracks and matching external sidecars; language, forced, commentary and optional ordering/title; low-confidence work enters review.
- `subtitle-audit`: no edits; structural quality, per-track scores, file-level best-track score, assessment coverage, enhancement opportunity.
- `subtitle-light`: low-risk new generated subtitle: basic timing correction verified with targeted audio/ASR, applied glossary updates, simple readability fixes; escalate by policy.
- `subtitle-full`: independent full-audio ASR/alignment, per-track matching, omission/mistranslation detection, selective correction, multi-source consolidation, readability; produce/revise generated track.
- `subtitle-ocr`: bitmap PGS/VobSub to text as a standalone task, without mandatory full enhancement.
- `series-prepare`: scan series for preliminary names/terms and source-quality evidence before batch enhancement.
- `finalize-embed` / `apply`: after necessary approval, atomically publish sidecar or integrate/remux into MKV; optional modification/retiming of originals.
- Manual discovery scan and configured automatic triggers create appropriate jobs. A request MAY combine metadata and subtitle operations in one file-wide queued submission.

## Depth vs. action is orthogonal

- **Depth:** audit / lightweight / full and (inside full) fast/balanced/thorough/escalated model analysis. Full enhancement **always independently ASRs the entire reference audio** so speech gaps and full-release timing can be examined.
- **Action policy per feature:** audit-only, conservative automatic, more aggressive automatic, or human approval; thresholds and escalation rules configurable separately for metadata overwrite, forced/commentary, timing, glossary, translation, omissions, layout, OCR.
- A scheduled metadata correction may be fully unattended; full enhancement generally requires or supports review, with automatic high-confidence sections permitted.
- `subtitle-light` still generates an **AI-generated track**, not a rewritten original. Retiming originals is a distinct opt-in capability, not a side effect of glossary or translation changes.
- External subtitle publication (temporary or final) and embedding are separate decisions; users can keep sidecars indefinitely.

## Submission parameters (conceptual, not a fixed API)

File/media identity; requested operations; target language; original/dub audio preference/override; source track overrides; output mode; ASS/SRT policy; per-feature action thresholds; review requirement; model selection/escalation policy; duplicate/reprocess intent; dry-run flag and optional per-series overrides.
