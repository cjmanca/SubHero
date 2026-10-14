# Inference model roles, backends, escalation and GPU use

**Owner:** model adapter/resource scheduler · **Related:** [ASR](../20-subtitles/asr-and-forced-alignment.md), [translation](../20-subtitles/matching-and-translation.md), [queue](workflows-and-queue.md).

## Per-role inference configuration

- Configurable model, endpoint, credentials, capabilities, version and default/escalation path **independently for**: audio language identification, text language classification, ASR, forced alignment, utterance/semantic matching, translation, source-grounded translation verification, optional diarization/separation, optional OCR, terminology ranking, and optional JEV classification.
- Support models **in the application container** where practical (especially small ASR/forced alignment) and **external services** for every role when an appropriate adapter exists; another LAN computer and paid cloud provider are different trust/cost domains. Never require external/cloud usage for ordinary operation.
- Support configurable model residency vs unload/swap to conserve VRAM, job concurrency and resource limits, batching, GPU assignment, out-of-memory recovery and warmup when supported. CPU fallback is desirable if simple; not mandatory if it substantially complicates the app.
- Default/escalation model selection at each suitable stage; optionally repeat a difficult section with a more accurate model or alternate ASR for independent verification. An LLM's confidence score isn't automatically a calibrated probability.

## Initial candidates, not mandated bindings

| Role | Candidate / experiment |
| --- | --- |
| ASR | Qwen3-ASR-1.7B (alternatives e.g. Whisper-family) |
| Forced alignment | Qwen3-ForcedAligner-0.6B where language supported |
| Translation | Hy-MT2-1.8B; compare 7B where needed |
| Cross-language matching | LaBSE/SONAR-family embeddings vs translation-first vs hybrid |
| Timing | ffsubsync (including experimental piecewise); ALASS comparator; deterministic verified mappings |
| Classification | Deterministic rules/small classifiers; optional JEV `POST /v1/decision` for text candidate scoring |
| OCR/diarization/separation | To benchmark; not fixed |

Qwen3-ASR supports more languages than its forced aligner. Document **default full-pipeline support** as the 11-language intersection in [ASR](../20-subtitles/asr-and-forced-alignment.md), further restricted by selected translation target support. Metadata classification may support additional languages. Dynamic model capability negotiation is a goal.

## Budgets, privacy and caches

- User-configurable limits: number of escalation calls, time/resource usage, GPU memory caps, optional monetary budget; if exhausted, leave finding unresolved in review instead of inventing certainty.
- Off-host third-party cloud audio/video/text transfer must be opt-in by policy; credential handling secure; no implicit provider fallback to cloud.
- Store immutable model IDs/hashes/versions, prompts/configuration, segmentation settings and provider details with output so future upgrades can invalidate specific stages without unnecessary full re-ASR.
- Chunk processing and residue cleanup should be bounded and restartable; extracted audio deleted by default.
