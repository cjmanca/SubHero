# Job lifecycle, automation and processing coordination

**Owner:** orchestrator · **Related:** [profiles](../00-foundation/processing-profiles.md), [discovery](../10-media/discovery-and-stability.md), [storage](../10-media/safe-media-writes.md).

## One persistent shared queue

Web UI, raw API, MCP, directory watches, periodic library scans and webhooks enqueue the **same job representation** and use the same authorization, deduplication and persistence rules. A submission names media file(s) and job type(s); default unit of processing is a **whole media item** with all relevant tracks, not one subtitle stream. Allow one submission containing metadata + enhancement, or individual audit/light/full/OCR/series-preparation jobs.

Expected lifecycle: `discovered → waiting-for-stability → queued → preparing → running stages → privately-staged → pending-review (where needed) → validating → committing → completed`, with `blocked`, `retryable-failure`, `failed`, `canceled`, `superseded` and `requeued` states as appropriate. **Private staged** does not mean Plex-visible: publication to watched directories follows approval/automatic authorization and validation; see [output](../20-subtitles/output-and-provenance.md). Exact storage/worker framework TBD.

## Scheduling and reliability

- Persist requests, source versions, stage receipts/cache keys, settings, current stage, progress, review outcomes, errors and commit results across container recreation/restarts.
- Support job priorities, cancellation, safe retry/resume, configurable concurrency/resource pools, duplicate coalescing, reprocessing under changed settings, and explicit re-run of individual stages when dependencies permit.
- Avoid competing file mutations: lock/serialize commits per source; UI/read-only analysis may run concurrently with other work if safe.
- When source changes during processing, **cancel and requeue** after stability backoff; prevent output based on stale stream identity from reaching commit. Preserve stage artifacts only if their inputs are still valid.
- Stage boundaries (discovery, extraction, ASR, align, match, translate, synchronize, optimize, render-check, publish) should be independently observable and cacheable. Failed late stages should not rerun expensive earlier stages by default.
- Manual scan and automatic discovery respect filters per root/series, ignore staging files and prevent self-triggered loops.

## Job options and policy

- Choose metadata only, quality audit, lightweight enhancement, full enhancement, bitmap OCR, series preparation, and/or safe publication.
- Select target language, audio/source track overrides, output format and destination, action thresholds, review policy, model providers/default+escalation, inference/privacy budget, whether direct original timing modification is permitted.
- Allow users to configure which triggers run which operations (e.g., watch new files → metadata audit/correct + quality scoring; full enhancement only on demand, by approval, or optional high-opportunity automation).
- Report why work stopped or escalated: source not stable, insufficient classification evidence, unsupported format, mismatched streams, inference budget exhausted, review required, or commit not atomic.

## Distributed execution assumptions

Separate API/UI from long-running workers conceptually; a worker may call internal or remote model services. The queue must not assume a permanently loaded GPU model or one specific hardware topology. Limit GPU work independently of CPU/I/O work.
