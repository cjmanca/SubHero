# Web UI, review queue and correction decisions

**Owner:** human-facing workflow · **Related:** [quality](quality-and-triage.md), [data model](data-contracts-and-cache.md), [glossary](../20-subtitles/series-glossary.md).

## Administrative UI

- Browse allowed library roots/files, inspect embedded and external audio/subtitle tracks with language/flags/titles, select source/audio overrides, queue any operation, rescan manually, configure discovery/watch/webhooks and auto-action policies.
- Persistent job dashboard: queued/waiting/running/staged/review/failed/completed with progress per stage, resource/model use, estimates if measurable, priority, retries, errors and relevant diagnostics.
- Per-file and per-track quality dashboard: subtitle quality, metadata health, assessment coverage, combined media-health score, enhancement opportunity, **estimated opportunity delta relative to best present full track**, and uncertainty. Sorting/filtering by potential improvement is important; review queue should expose the delta, not just raw severity.
- Globally configure thresholds/model defaults/escalation, retention, format policy, output destination; series-specific overrides and release-group preferences; edit glossaries and propose retroactive corrections.

## Review experience

- For each proposed correction show **original vs proposed text**, old/new timestamps, subtitle type, audio/source-language transcript, matching source tracks, semantic/style/timing confidence dimensions, model evidence and reason. Jump directly to timestamp in playable audio/video where available.
- Allow *individual* approve/reject, select multiple, filter by type/severity/confidence/source, **select all**, and safe bulk actions. Reviewers may also **edit proposed subtitle text, cue start/end times and eligible layout parameters** before approval, with playback context and neighboring cues visible. Do not restrict the interface to accept/reject decisions.
- Group mutually dependent edits (split/merge, neighbor-timing, multi-layer layout, glossary flow) to prevent inconsistent partial approvals. Revalidate scheduling, semantic dependencies and format constraints after **manual edits** as well as selective/bulk acceptance; report conflicts instead of publishing a broken partial change. Attribute manual revisions to actor, time and prior proposed value.
- Present proposed omissions, contradictions and quality-improvement candidates as review items even when no edit was automatically applied. Distinguish **recommendation** from **actual scored generated output**.
- Previews should render original and proposed subtitle states at the same timecode, optionally side-by-side with video/audio snippets. For ASS, preserve source fonts/styling and warn if preview differs from player behavior. **Pending-review previews are served from private staged artifacts**, not by dropping a discoverable `.en.ass`/`.en.srt` into a Plex-watched library. Any optional live Plex preview must be a separately authorized action with cleanup/restore.
- Provide an audit trail of approved automatic vs human decisions, rejected suggestions, grouped dependencies and final commit. Roll back generated revisions and original timing changes where available.

## Low-confidence routing and playback checks

- Metadata ambiguity, unsafe format transforms, mismatched/overlapping different-source cues, unresolved translation pronouns, unverifiable timing jumps, dub classification uncertainty, questionable glossary updates and final publication decisions can enter targeted review.
- Optional **procedural** ASS rendering checks (not AI-vision review) and structural validation; disable for performance if selected, but keep minimum validity checks before publishing. Treat intentional off-screen/scrolling elements as valid.
- Don't require human review of every simple automated classification or improvement, but ensure decisions are explainable and reversible.
