# Scope, aims, and boundaries

**Owner:** product requirements · **Related:** [profiles](processing-profiles.md), [invariants](invariants.md).

## Product objective

Build a standalone Python utility packaged for Docker that:

1. Autonomously audits and corrects incorrect **audio and subtitle track languages**, forced-track classification, and detected commentary designation for a media library, including correctly naming external subtitle files.
2. On demand, creates **new enhanced text subtitle tracks** from imperfect subtitles and actual spoken dialogue. Correct timing, missing lines, translation errors, readability, names/terminology, and formatting without replacing good work unnecessarily.
3. Provides repeatable evidence, adjustable automation thresholds, meaningful human review, rollback, and safe application to library files.

Primary content: Chinese-language television/donghua, Japanese anime, Korean television/animation, often originally spoken in non-English languages with translated English subtitles. The target language is configurable. Initial full speech pipeline support follows the intersection of configured ASR/alignment/translation capabilities; metadata detection may be broader.

## Application boundaries

- Media metadata correction and subtitle enhancement are **separate job families** and may run together or individually. Metadata correction is intended for library-wide unattended use; full enhancement usually runs when requested or prioritized by quality auditing.
- Inspect a **whole media file and all relevant tracks**, not only one preselected subtitle stream. Track-level overrides and selective reruns remain possible.
- Allow existing embedded SRT/ASS/SSA, external text tracks, and bitmap tracks where supported. Non-MKV inputs are intended to be remuxed to MKV for final media modifications when safely possible, not re-encoded as the default.
- Python/Docker, open/local first; every appropriate inference role MAY use internal or external model endpoints independently. Avoid reliance on paid services.
- External applications remain responsible for what they already do well: do not create a replacement for Bazarr's subtitle search/retrieval or a generalized media manager. Plex refresh integration and coordination with Tdarr are relevant.

## Prioritization / explicit non-goals

- **Core:** metadata inspection/correction, safe jobs, multiple subtitle sources, lightweight sync with verification, full audio-derived timing/semantic matching, review, provenance.
- **Later / optional:** OCR bitmap-to-text conversion, advanced series context, visual/OCR corroboration, advanced speaker identification.
- **Experimental and low priority:** separate background-dialogue recovery with speech separation and possible future character-aware placement; disabled by default.
- **Not initially promised:** complete SDH generation from normal subs, reliable visual speaker identification, arbitrary ASS animation reconstruction, perfect transcode-surviving watermarking, or error-free inference in any language.
