# Series glossary, context and retroactive terminology fixes

**Owner:** series-level semantic knowledge · **Related:** [translation](matching-and-translation.md), [data](../30-app/data-contracts-and-cache.md), [review](../30-app/web-ui-and-review.md).

## Knowledge represented

- Original-language terms, preferred target translations, aliases, transliteration, names, titles/honorifics, character identities, references/relationships, translation-style preferences, scope (library, series, season, episode), source evidence, confidence and provenance.
- Explicitly distinguish **user-confirmed**, **automatically inferred** and **contradictory/pending review** entries. User edits and confirmed glossary terms outrank model popularity and release-group weights. Evidence may be provisional rather than a hard constraint.
- Pronouns/relationships may be uncertain; character voice does not prove the identity or gender of the person being mentioned. Do not convert speculative background knowledge into fact.

## Automated discovery and ranking

- Support an explicit **Prepare Series** operation: scan subtitle text across *all available as-yet-unprocessed episodes*, identify recurring terms/names and competing translations, and collect provisional evidence. Avoid mandatory whole-series ASR; begin with available source-language and translated text, escalating to targeted ASR/model checks for disputed high-impact terms.
- **Automatic preflight for queued series work:** before applying newly inferred terminology to a batch of unprocessed episodes, perform a bounded cross-episode discovery pass rather than processing the first episode as if its terminology were authoritative. If new disputed terminology appears while multiple accessible episodes remain unprocessed, re-evaluate relevant occurrences across those episodes **before applying the new choice**. A manual Prepare Series command is not a prerequisite for this behavior.
- Reuse cached scans and restrict re-preflight to affected terms/episodes to prevent repeated whole-series work. If the needed cross-episode evidence cannot be acquired within policy/budget, leave the inferred choice provisional or in review rather than silently making inconsistent changes. User-confirmed terms remain authoritative and do not wait for automatic ranking.
- Rank proposed terms using multiple evidence signals: recurrence **across episodes**, independent source count (discount retimes/copies), source-language correspondence, contextual LLM assessment, track-specific translation quality, and user-maintained **known-good release-group** weights. No single popularity vote is automatically correct.
- Infer candidates automatically where useful; contradictions across episodes go to glossary review. Different scenes/episodes may need scoped exceptions.
- For lightweight glossary application: confirmed, clearly identified occurrences can be deterministic. An inferred entry may be auto-applied **only when configured threshold and context evidence justify it**; ambiguous occurrence may use source-language subs and targeted ASR. A changed translation can require new line breaks/readability/timing checks.

## Retroactive application

- Web UI permits viewing/editing/approving glossary entries, choosing preferred variants and scopes, and proposing retroactive changes to existing **generated** tracks; never overwrite original translation text to impose glossary policy.
- On user-confirmed better term, optionally find affected prior episodes, propose changes, preserve prior approved decisions, rerun local text layout/scheduling as needed, and batch review. Text-length changes may affect flow, timing and placement; **do not blindly string-replace existing output**.
- Store source term-to-cue correspondence after enhancement so applying a confirmed change usually needs no repeat full ASR; invalidate only dependent translation/readability artifacts.
- Optionally reevaluate prior episodes when new context resolves an ambiguity; changes must be transparent and reversible.
