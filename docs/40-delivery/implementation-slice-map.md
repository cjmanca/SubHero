# Token-efficient implementation/planning slice map

**Purpose:** select minimal context for a future implementation task. This is a navigation aid and dependency graph, **not** a final implementation plan or tool/framework choice. Start with `AGENTS.md` at the repository root; for any changing-media or AI decision code also read `docs/00-foundation/invariants.md`. The root `README.md` is a user-facing overview, not agent implementation guidance.

| Slice | Read these owning documents | Additional document only if needed |
| --- | --- | --- |
| Container/workers and job states | `30-app/workflows-and-queue.md`, `00-foundation/processing-profiles.md` | `30-app/data-contracts-and-cache.md` |
| Watcher / scanner / stability | `10-media/discovery-and-stability.md`, `30-app/workflows-and-queue.md` | `10-media/safe-media-writes.md` |
| Media probe/track classification | `10-media/track-metadata-and-classification.md` | `10-media/plex-and-sidecars.md`, `30-app/models-and-resources.md` |
| External subtitle detection/renames | `10-media/plex-and-sidecars.md` | `10-media/discovery-and-stability.md`, `20-subtitles/output-and-provenance.md` |
| Safe media mutation / MKV conversion | `10-media/safe-media-writes.md` | `10-media/discovery-and-stability.md`, `30-app/integrations.md` |
| Plex / Tdarr adapters | `30-app/integrations.md`, `10-media/plex-and-sidecars.md` | `10-media/safe-media-writes.md` |
| Subtitle parsing and per-track evidence | `20-subtitles/source-selection-and-ancestry.md`, `30-app/data-contracts-and-cache.md` | `20-subtitles/consolidation-and-formats.md` |
| Lightweight timing | `20-subtitles/lightweight-and-full-synchronization.md` | `20-subtitles/asr-and-forced-alignment.md` |
| Full ASR / forced alignment | `20-subtitles/asr-and-forced-alignment.md`, `30-app/models-and-resources.md` | `30-app/data-contracts-and-cache.md` |
| Semantic matching / translation | `20-subtitles/matching-and-translation.md` | `20-subtitles/source-selection-and-ancestry.md`, `20-subtitles/series-glossary.md` |
| Merge/consolidate ASS and SRT | `20-subtitles/consolidation-and-formats.md` | `20-subtitles/readability-and-accessibility.md` |
| Readability / SDH / background speech | `20-subtitles/readability-and-accessibility.md` | `20-subtitles/consolidation-and-formats.md` |
| Bitmap OCR | `20-subtitles/bitmap-ocr.md` | `30-app/models-and-resources.md` |
| Series glossary | `20-subtitles/series-glossary.md` | `20-subtitles/matching-and-translation.md` |
| Output, revisions, provenance | `20-subtitles/output-and-provenance.md`, `10-media/safe-media-writes.md` | `30-app/data-contracts-and-cache.md` |
| Quality scores / opportunity | `30-app/quality-and-triage.md` | `30-app/web-ui-and-review.md` |
| Review web UI | `30-app/web-ui-and-review.md` | `30-app/quality-and-triage.md`, `30-app/data-contracts-and-cache.md` |
| Raw API/MCP ACL | `30-app/api-mcp-and-security.md` | `30-app/workflows-and-queue.md` |
| Model runtime/routing | `30-app/models-and-resources.md` | `20-subtitles/asr-and-forced-alignment.md` |
| Experiment selection | `40-delivery/evaluation-and-benchmarks.md`, `40-delivery/open-questions-and-experiments.md` | `40-delivery/benchmarks/README.md` |
| Benchmark corpus and CLI evidence | `40-delivery/benchmarks/corpus-and-fixtures.md`, `40-delivery/benchmarks/harness-and-artifacts.md` | `40-delivery/benchmarks/evaluation-criteria.md` |
| **Benchmark light sync (first experiment)** | `40-delivery/benchmarks/synchronization.md`, `40-delivery/benchmarks/evaluation-criteria.md` | `20-subtitles/lightweight-and-full-synchronization.md` |
| Benchmark ASR / forced alignment | `40-delivery/benchmarks/asr-and-alignment.md` | `40-delivery/benchmarks/evaluation-criteria.md`, `20-subtitles/asr-and-forced-alignment.md` |
| Benchmark cross-language matching | `40-delivery/benchmarks/semantic-matching.md` | `40-delivery/benchmarks/evaluation-criteria.md`, `20-subtitles/matching-and-translation.md` |
| Benchmark translation corrections | `40-delivery/benchmarks/translation.md` | `40-delivery/benchmarks/evaluation-criteria.md`, `20-subtitles/series-glossary.md` |
| Benchmark ASS/multi-source merge | `40-delivery/benchmarks/consolidation-and-formats.md` | `40-delivery/benchmarks/evaluation-criteria.md`, `20-subtitles/consolidation-and-formats.md` |
| Later benchmark: metadata, scoring, storage, Plex | `40-delivery/benchmarks/secondary-experiments.md` | Only the owning feature requirements file |
| Benchmark decision and regression record | `40-delivery/benchmarks/findings.md`, `40-delivery/benchmarks/evaluation-criteria.md` | Corresponding experiment protocol |

All paths in this table are relative to `docs/`. A slice should load related documents only when touching their interface. Shared concepts reference [data contracts](../30-app/data-contracts-and-cache.md) rather than repeating schema in every file.

## Evidence/dependency ordering (for future planning only)

- Media/track inventory + safe publish + job tracking enable metadata scans and basic file workflows.
- Subtitle parsing + structured per-event provenance enable independent source selection, light synchronization, ASS composition and review.
- Full ASR/alignment → semantic correspondence → reliable per-track time mappings → omission/translation changes → readability/layout → generated output.
- Quality audit and human review can be developed with fixture data independently of final model selection.
- Series glossaries may be built from parsed subtitle text ahead of full ASR.
- OCR and experimental background speech can be independent later slices.

Do not interpret this as permission to implement everything before benchmark gates. The final implementation plan may reorder slices based on validation results.
