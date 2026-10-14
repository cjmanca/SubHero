# Settled decisions and interpretation notes

Use this short page to prevent a future planning agent from reopening settled product behavior. Algorithm choices still require benchmarking; see [experiments](../40-delivery/open-questions-and-experiments.md).

| Key | Settled decision |
| --- | --- |
| D01 | Python, Docker, local-first. Queue invoked from web UI, API or MCP; automatic discovery via watchers, scans, webhooks. |
| D02 | Metadata correction autonomously covers every applicable embedded/external track. Full subtitle enhancement is chiefly on demand. |
| D03 | Preserve original subtitle **text**; generated tracks are separate and explicitly identifiable. User may opt to correct original **timing** directly instead. |
| D04 | Subsequent enhancement of a generated track replaces the prior generated track, while history and approved changes remain available. |
| D05 | Metadata and subtitle jobs can run individually or jointly; full enhancement examines the whole file and several potential sources. |
| D06 | Prefer original-language audio as semantic truth; dub is supplementary, with explicit selection/style overrides. User generally prefers subtitles, not dub-style translation by default. |
| D07 | Prefer a strong base English (or target-language) subtitle track; selectively borrow best meaning, omissions and formatted sign/song events from others. Never simply concatenate tracks. |
| D08 | Align each source track independently to a shared media timeline. Full enhancement ASRs the whole episode. Lightweight sync starts with ffsubsync then targeted ASR validation. |
| D09 | Inferred terms and confirmed terms are distinct; confirmed/user-edited glossary overrides inferred rankings; series-wide prep and optional retrospective updates. |
| D10 | Prefer external generated sidecars for inexpensive review/iteration; embed if requested or needed. Plex external auto-selection and forced flags must be tested, not assumed. |
| D11 | Offer three output-format policies: allow promotion to ASS; preserve SRT/ASS source class; force SRT with documented losses. |
| D12 | Experimental background-dialogue enhancement is opt-in and late; no requirement to synthesize full SDH from normal subtitles. SDH-to-ordinary stripping is supported. |
| D13 | Quality = best individually usable full track, **not** a hypothetical union; assess potential improvements separately and show estimated enhancement-opportunity delta. |
| D14 | When processing a non-MKV item for an operation that needs a modified media-container output, target MKV where safely feasible, using remux/stream copy rather than lossy re-encoding. This is **not** an instruction to bulk-convert untouched library items; audit-only and sidecar-only jobs do not implicitly remux. |
| D15 | Stop/requeue jobs upon source changes; never publish an output derived from a stale source or expose half-copied files to Plex. |
| D16 | Independent local/remote inference configuration and default/escalation models per role; cloud escalation requires permission and budgets. |
| D17 | No sample episode corpus currently exists; construct/safely source benchmarks before hard performance thresholds or irreversible tool choices. |

**Nuance:** Changing an original English subtitle's metadata language to `und` and **appending** `Original English` to any existing descriptive title to favor an external generated file is an **optional, reversible Plex-specific workaround**, not normal language correction. Preserve exact pre-change language/title/flags for rollback; correct languages remain correct in standard metadata mode.
