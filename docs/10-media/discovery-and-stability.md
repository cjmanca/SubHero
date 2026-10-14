# Media discovery, identity, and readiness

**Owner:** media input and scanner · **Related:** [queue](../30-app/workflows-and-queue.md), [safe writes](safe-media-writes.md), [integrations](../30-app/integrations.md).

## Inputs and trigger paths

- Scan one media file, directory, configured roots, or whole library via web UI, API or MCP.
- Optional **directory watcher**, **periodic scanner**, **incoming webhooks**, and manual rescan. Users select which job types each trigger creates (metadata, audit, light, full, OCR, or combinations). Default unattended focus: metadata + inexpensive quality audit, not automatic full enhancement.
- Include external subtitles adjacent to media and supported `Subs`/`Subtitles` directories; don't treat them as unrelated media. Never confuse `media.en.ass` with another episode.
- Watcher events are hints; periodic reconciliation catches missed events, renames and files altered by Tdarr. Ignore own temporary/staging outputs to prevent loops.
- Scope all sources to explicitly configured library roots and permitted paths.

## Readiness/stability gate

- Newly discovered files must pass backoff: record size, modification time, and any other available file identity; recheck after configurable quiet period; continue until stable.
- Stable size alone is insufficient: consider in-progress writes without size changes and failed probe/structural validation. Use FFprobe/metadata validation and (where available) writer-open or process signals, but do not rely on advisory locking being universal.
- Keep unstable files pending without processing; cap/retry according to policy and surface stale/stuck files.
- Immediately before commit, verify source identity/version again. If changed during analysis **cancel the current job and requeue the changed file**, reentering stability backoff. Retain reusable results only when the relevant streams truly match.

## Identity, duplicates, and recomputation

- Physical path alone is not identity. Track file size/mtime/inode or equivalents, container/stream fingerprints, subtitle content fingerprints, and optional audio/video identity across remux/transcode.
- Distinguish same-path new content, moved/renamed source, hardlinked paths, and transcode replacement. A checksum/fingerprint strategy must balance I/O and collision risk; strong hashes where a destructive action depends on identity.
- Coalesce redundant queued submissions, prevent simultaneous commits against one file, and avoid loops caused by the program's own corrections or Plex/Tdarr updates.
- File-wide scan must inventory all embedded tracks plus linked external subtitle files before planning changes.
