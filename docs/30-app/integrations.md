# Integration with Plex, Tdarr, Bazarr and library workflows

**Owner:** external system adapters · **Related:** [media discovery](../10-media/discovery-and-stability.md), [Plex/sidecars](../10-media/plex-and-sidecars.md), [safe writes](../10-media/safe-media-writes.md).

## Plex

- Goal: correct primary audio/subtitle language and forced behavior so Plex selects the right tracks, without replacing Plex's library manager.
- Configure server/token/library identity; map media path to Plex item; after successful changes optionally call **targeted analyze** rather than relying only on filesystem scan (same name/size header changes can be missed).
- Account for user language/forced preferences and previously manually selected streams. Test external-over-embedded auto-selection and ASS font/rendering on actual clients; don't equate correct metadata with guaranteed preferred playback.
- Minimize Plex churn: never expose half-written or missing media while staging/replacing; stream-copy remux rather than transcode where feasible. Cross-extension migrations (`.mp4` to `.mkv`) need **explicit Plex identity/refresh and sidecar handling**: even if the new file is published completely, two paths can briefly coexist or Plex can register a new item. Do not promise no duplicate/new-item churn without validation; apply the [migration safety policy](../10-media/safe-media-writes.md).

## Tdarr / other writers

- A prior media file may be remuxed, transcoded, renamed, replaced or have track titles/tags stripped. Reassociate by known stream/content evidence, sanity-check prior corrected metadata; rerun language detection only where needed.
- Detect in-flight writes and any source modification during a job; cancel and **requeue after backoff**. Never overwrite newer output from another application with old staging.
- Avoid treatment of an earlier generated track as an independent human translation; use layered provenance and approximate cue fingerprints when embedded title/tag is lost.

## Bazarr / ARR ecosystem

- Do not rebuild subtitle download/search/index functions already handled by existing tools. Operate on locally present subtitle tracks/files and optionally accept integration events/webhooks.
- Avoid blindly renaming/removing sidecars owned/managed by other tools. Detect naming collisions, preserve distinct releases, and offer configurable output locations/naming subject to Plex recognition.

## File workflow

Expected download → hardlink import into final library → metadata scan → optional subtitle audit/light/full enhancement; utility normally operates on the **library side**, never on the torrent download tree. Publication must break hardlink safely if editing library media. Unraid `/mnt/user` is expected accessible path; portability remains a requirement.
