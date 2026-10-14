# Media Metadata & Subtitle Utility

**Status:** Requirements specification (October 2026). The application described here is **planned, not yet implemented or available for installation**. Model choices, compatibility behaviors, and performance targets remain subject to testing.

A local-first utility for keeping media track metadata accurate and improving existing subtitles without discarding good translations or formatting. It is intended to run in Docker, with an initial focus on Unraid and Plex, while remaining usable on other platforms.

The project has two independent purposes: **library-wide metadata maintenance** and **on-demand subtitle repair or enhancement**. Both will use the same queue, web interface, API, and MCP interface.

## What it will do

### Media metadata maintenance

- Identify the actual primary spoken language of each audio track using samples taken from different parts of a file.
- Identify subtitle languages from their content, including tracks containing some text in a second language.
- Correct embedded language metadata, classify forced/signs-and-songs subtitles, and identify commentary tracks so they are less likely to be selected unintentionally.
- Correct languages of **external subtitles by renaming their files** according to supported player naming conventions.
- Optionally adjust track ordering when metadata alone cannot produce the desired playback selection, with review for uncertain classifications.
- Scan existing libraries, watch for new files, respond to webhooks, or process individual files on request.

### Subtitle repair and enhancement

- Repair global timing shifts, gradual drift, release-specific discontinuities, and individual timing errors.
- Compare multiple subtitle tracks and original-language audio to detect missing dialogue, mistranslations, and incomplete signs/songs coverage.
- Improve readability, including display durations, line breaks, and overly dense subtitles, while preserving meaning.
- Select useful material from different subtitle tracks without blindly combining or duplicating events.
- Preserve ASS/SSA positioning, styling, karaoke, and animation where possible; support SRT output with clearly documented tradeoffs.
- Use configurable, series-specific glossaries for names, recurring terminology, and translation preferences.
- Optionally produce new translated subtitles when no suitable target-language track exists, using source-language subtitles as additional evidence where available.
- Convert bitmap subtitles (such as PGS and VobSub) into editable text subtitles through a separate OCR operation.

Existing subtitle **text** remains available: normal enhancement creates a separately identifiable, AI-generated track. Changing the timing of an original track is an explicit option, not the default. A later enhancement can replace the previous generated version without losing its revision history.

## Processing choices

| Mode | Intended use | Result |
| --- | --- | --- |
| **Audit** | Inspect tracks and assess subtitle quality without changing media | Reports and recommended actions |
| **Lightweight enhancement** | Apply conservative timing, glossary, and readability improvements | A new generated subtitle track |
| **Full enhancement** | Analyze original audio, compare subtitle sources, and investigate missing or incorrect dialogue | A more comprehensively enhanced track, subject to review policy |
| **Metadata correction** | Fix languages, forced/commentary classification, and applicable track properties | Updated media metadata or external subtitle names |
| **Subtitle OCR** | Convert image-based subtitle tracks to text | Additional text subtitle output |

Automatic actions, confidence thresholds, and escalation to more expensive analysis will be configurable separately for different types of correction. Uncertain proposals can be held for review instead of being applied automatically.

## Review and quality dashboard

The planned web interface will provide a persistent processing queue, playback-oriented review of proposed changes, before-and-after comparisons, manual text/timing edits, and bulk approval or rejection of compatible changes.

Quality assessment will distinguish timing, readability, completeness, formatting, and translation evidence. A file's subtitle quality reflects its **best individually usable full track**, not an imaginary combination of tracks that a player cannot display at once. A separate **enhancement opportunity score** will estimate the potential improvement from merging or repairing sources; the difference from the existing best score can help prioritize review. Scores will disclose assessment coverage and uncertainty.

## Media safety and playback

- Prefer generating **external subtitles** for inexpensive iteration and review; embedding into MKV remains an option, particularly for complex ASS content.
- Keep unapproved outputs out of Plex-watched library paths unless an explicit preview action is requested.
- Avoid re-encoding video when remuxing will suffice. When converting other media containers, prefer stream-copy remuxing to MKV where compatible.
- Support staged writes and atomic publication so media servers do not see incomplete or briefly missing media. Protect torrent-linked originals by staging or copy-on-write when appropriate.
- Detect media replaced during processing and requeue rather than commit changes derived from an outdated file.
- Optionally ask Plex to reanalyze modified media; account for Tdarr remuxing or transcoding and preserve generated-subtitle provenance as reliably as possible.

## Deployment and model flexibility

The planned application is written in **Python** and deployed through **Docker**. It will support local model execution or independently configured remote inference backends for suitable processing stages, including optional escalation models. External cloud use will require explicit permission and configurable budgets. Initial media targets include Chinese-language shows, Japanese anime, and Korean television; supported languages for each feature will depend on validated model capabilities.

The project complements existing media tools rather than replacing subtitle discovery services such as Bazarr.

## Requirements and development status

This repository currently records the agreed behavior and the experiments still needed before selecting final algorithms. For more detail:

- [Project scope and boundaries](docs/00-foundation/scope.md)
- [Processing modes and policies](docs/00-foundation/processing-profiles.md)
- [Media discovery and track handling](docs/10-media/discovery-and-stability.md)
- [Subtitle sources and consolidation](docs/20-subtitles/source-selection-and-ancestry.md)
- [Subtitle output and provenance](docs/20-subtitles/output-and-provenance.md)
- [Review interface](docs/30-app/web-ui-and-review.md)
- [Quality scoring and prioritization](docs/30-app/quality-and-triage.md)
- [Benchmarks and evaluation goals](docs/40-delivery/evaluation-and-benchmarks.md)
- [Planned benchmarking methods](docs/40-delivery/benchmarks/README.md)
- [Unresolved technical questions](docs/40-delivery/open-questions-and-experiments.md)

No installation commands are provided yet because there is no released application to install.
