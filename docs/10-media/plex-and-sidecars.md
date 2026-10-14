# External subtitle names and Plex-specific playback behavior

**Owner:** media metadata/Plex adapter · **Related:** [output](../20-subtitles/output-and-provenance.md), [integrations](../30-app/integrations.md), [safe writes](safe-media-writes.md).

## External subtitle correction

- External subtitle language is usually conveyed to Plex through filename suffixes: `Episode.en.srt`, `Episode.en.forced.ass`, `Episode.en.sdh.srt`; detect written language, forced/SDH purpose and **rename appropriately** without changing cue content during metadata-only jobs.
- Match sidecar to media by safe, documented Plex naming conventions; consider supported `Subs`/`Subtitles` folders. Preserve subtitles of different languages/releases and avoid collisions.
- When two different sidecars both identify as `en`, detect identical/substantially identical duplicates and preserve genuinely different tracks. Try a release-group or alternate identifier only where proven Plex-compatible; otherwise embed, keep safely named with review, or report conflict. Do not silently overwrite/delete different tracks or break Bazarr-managed files.
- External `.en.ass`/`.en.srt` is attractive for generated output but cannot be relied upon to show an arbitrary `[AI Generated]` display title in Plex. Track provenance separately and/or embed to display titles.

## Plex rules vs testable assumptions

- Plex's language preferences use audio/subtitle language; its docs say **MKV default flags are ignored** and **forced subtitle flags are used** subject to Plex subtitle mode. Unknown (`und`) won't match language preference.
- External-over-embedded automatic preference is **observed in some configurations but not guaranteed**; test recent Plex versions, clients, previously chosen user streams, forced/non-forced interactions and audio-language preferences before relying on it.
- Correct commentary/original flags aren't guaranteed to exclude commentary from Plex automatic selection; optional track reorder is a separate remux decision. Audio-channel layout can affect observed client behavior; test rather than assert one universal selection policy.
- After a committed modification, offer Plex targeted **item analysis** (`PUT /library/metadata/{ids}/analyze`) and additional refresh/rescan only if needed. Verify actual new track metadata/selection, including same-name/same-size header edits.

## Optional compatibility workaround

If an external generated English track cannot be auto-selected and the user explicitly enables a Plex-specific mode, MAY set an original embedded full English track's language to `und` and **append** `Original English` to its existing descriptive track title (e.g. `Fansub Group A — Original English`) using MKV header editing. If no title exists, use `Original English`. Make this idempotent: repeated jobs must not duplicate the suffix. Retain the **exact previous title, language, flags and stream identity** for rollback; restore them when the generated output is removed/disabled through the application. Never apply by default, never claim this is semantically correct metadata, and prefer no MKV mutation where external selection works. This workaround affects playback eligibility and must not run on an unpublished draft.

## Fonts / rendering caveat

External ASS may not render identically to ASS embedded in MKV with font attachments. Test client font availability, positioning and rendering; permit embedding when needed. See [format preservation](../20-subtitles/consolidation-and-formats.md).

**Primary references:** [Plex account language behavior](https://support.plex.tv/articles/204985278-account-audio-subtitle-language-settings/), [Plex sidecar naming](https://support.plex.tv/articles/200471133-adding-local-subtitles-to-your-media/), [Plex analysis API](https://developer.plex.tv/pms/).
