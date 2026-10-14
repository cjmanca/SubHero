# Safe writes, hardlinks, remux and atomic commit

**Owner:** storage and mutation engine · **Related:** [discovery](discovery-and-stability.md), [provenance](../20-subtitles/output-and-provenance.md), [invariants](../00-foundation/invariants.md).

## Mutability modes

1. **Safe staging (default):** copy or CoW/reflink clone when actually supported; edit the clone; probe and validate full output; check source unchanged; publish atomically. A torrent's hardlinked download inode must never be altered unintentionally.
2. **Fast in-place metadata only (opt-in):** allowed only when hardlink count/ownership and other safety checks pass and user accepts interruption/rollback risk. Suitable for MKV header changes (e.g. `mkvpropedit`), NOT general track edits/remux. Record originals and verify result.
3. **Original timing correction (separate opt-in):** edit an existing embedded or external subtitle track's timestamps only; preserve original text/style and rollback data. Normal glossary/translation changes go to generated tracks instead.

## Atomicity is a hard invariant

- Preserve the existing path and full content until the replacement is **completely prepared**. Never delete old then copy new, copy over a visible target, or expose a half-written video to Plex.
- For media replacement, verify that a final temporary file and destination support an **actual atomic rename/replace**. When needed, first stage from general workspace into a **destination-compatible** commit area and validate before the final rename. If same-filesystem atomicity cannot be established, **stop and report**, not non-atomically fall back.
- A generic fast scratch directory and a final commit staging directory are distinct. Favor hidden/excluded staging outside library scanning roots while compatible with the destination; avoid Plex watching a partially copied file. Use temp names and ignore own staging events. On Linux, consider file/directory sync for power-failure durability separately from atomic visibility.
- Unraid `/mnt/user` is the expected logical FUSE library view and should be used for normal operations. A shared `/mnt/user` path does **not, by itself, prove** renames across underlying disks/pools are atomic. Verify actual rename semantics for chosen source/staging paths; don't redirect to `/mnt/disk*` unsafely or assume a single staging path covers all media.
- Reject stale publish: re-probe/compare source identity immediately before commit; if Tdarr or another writer changed it, cancel and requeue after stability delay.

## Container normalization

- Existing MKVs: edit language/forced/header properties via MKVToolNix where possible without full remux; adding/reordering tracks generally needs a remux. Avoid unnecessary video/audio re-encoding.
- Non-MKV formats: when an operation **modifies the media container**, the desired output is MKV, preserving compatible encoded streams via **stream copy/remux**. An audit-only scan or an operation that only publishes an external sidecar does **not** implicitly convert the video. Inventory/check attachments, chapters, HDR-related info, subtitle streams, timestamps, codec compatibility and tags; never silently drop an unsupported stream. No bulk conversion of otherwise untouched library items is implied.
- `episode.mp4` → `episode.mkv` is a **pathname/container migration**, not an atomic replacement of one existing pathname: a single rename cannot simultaneously replace the old path and introduce the new one. Stage and validate the **complete** MKV first, coordinate destination naming, sidecar association, Plex refresh/identity and possible duplicate or new-item detection, then retire the old file only under an explicit migration/rollback policy. Never remove the original first or copy a partly complete MKV into a scanned library. If no-churn migration cannot be demonstrated, surface the limitation and require configured policy or review rather than claiming atomic same-path semantics.
- Atomic sidecar replacement/rename follows its own small-file commit path, with collision checks.

## Recovery / audit

- Maintain write intent, backup/rollback metadata or version where appropriate, input fingerprints, output validation results and committed generation ID. On interrupted jobs leave original playable and quarantine cleanup-able staging, not a damaged media file.

**References:** [mkvpropedit](https://mkvtoolnix.download/doc/mkvpropedit.html), [Python os.replace](https://docs.python.org/3/library/os.html#os.replace).
