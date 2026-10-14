# Open decisions, assumptions and empirical verification backlog

This document is an **uncertainty register**, not a list of requirements already answered. See [decisions](../00-foundation/decisions.md) for settled product behavior. No item here should silently become implementation policy. The [benchmark protocols](benchmarks/README.md) define tests for selected items; [findings](benchmarks/findings.md) must contain actual measurements before an experiment can be marked resolved.

| ID | Unresolved experiment/decision | Why it matters |
| --- | --- | --- |
| E01 | Plex external sidecar automatic preference across supported server/clients/settings, including manual stream persistence | Whether external generated track can be auto-selected without MKV mutation |
| E02 | External ASS fonts/attachments/styles vs embedded playback | When default sidecar output must instead be embedded |
| E03 | Plex interpretation of commentary/original flags and audio channel layout/order; **version-specific Linux/Unraid regression test for `FlagCommentary=1` scanner stability** (a 2026 Plex forum report, not an established current/universal bug) | When to reorder tracks; whether flagging commentary has a compatibility regression on tested Plex versions/clients |
| E04 | Sidecar filename qualifiers for multiple same-language tracks, release group suffixes and Bazarr compatibility | Collision-safe language renaming and output names |
| E05 | Unraid `/mnt/user` atomic rename behavior for target files across disks/pools and preferred staging placement | Critical no-partial-file invariant |
| E06 | Safe non-MKV → MKV path migration without Plex identity churn and unsupported stream loss | Conversion/publication policy |
| E07 | ffsubsync global and experimental piecewise behavior, VAD/sign proxy quality, targeted ASR sample strategy; ALASS comparator | Trustworthy lightweight timing fixes. Harness + B1 arms executable (2026-10-14, `benchmarks/`); ffsubsync 0.5.1 verified, ALASS absent (`unsupported`), ASR endpoint unconfigured (`not_run`); only synthetic plumbing evidence so far — no candidate selected; real-media matrix pending E01/E02 |
| E08 | Model/binding limits: Qwen aligner input length across versions, actual Chinese/Japanese/Korean ASR+timestamps on TV/anime | Full-episode transcription feasibility |
| E09 | Direct multilingual embeddings vs translated text vs hybrid matching; merge/split/gaps/jumps | Accuracy and inference cost of correspondence |
| E10 | Hy-MT2-1.8B vs 7B vs source-grounded checking; rate of false-positive translation edits | Whether translation correction helps more than harms |
| E11 | Reliable commentary/forced/dub-matched/SDH classification with meaningful calibration | Safe unattended metadata decisions |
| E12 | Cross-track ASS coordinate/styles/attachments, animation-relative time and subtitle overlap compositor robustness | Preservation of positioned signs and karaoke |
| E13 | OCR quality for anime PGS/VobSub and layout recovery | Bitmap conversion engine/phase |
| E14 | Series glossary inference ranking with correlated releases and user trusted-group weights | Avoid widespread wrong terminology |
| E15 | Best-track quality vs opportunity estimation: calibration, weighting, **matched scoring dimensions/coverage and uncertain/no-baseline handling** | Fair review queue sorting without subtracting incomparable scores |
| E16 | Choose default among **three settled ASS/SRT format policies**; benchmark quality/loss thresholds and review UX for mixed SRT-base + formatted ASS alternate content | Non-deceptive output formatting without silently erasing selected ASS events |
| E17 | Automatic vs reviewed publication defaults and threshold values for each operation | Regressions/autonomy balance |
| E18 | How completely generated text from original audio performs without any existing text sources | Full generation quality and verification |
| E19 | Provenance across Tdarr transformations and whether any extra watermarking is worthwhile | Avoid feedback/duplicates after title/tag stripping |
| E20 | Late opt-in background speech separation and layout policy quality | Explicitly defer; do not block core planning |

## Current working hypotheses (not locked decisions)

- ffsubsync + dialogue-only proxy + targeted semantic ASR verification is a good inexpensive entry point; escalate to full-episode ASR if suspect.
- Full enhancement always ASRs selected reference audio and aligns each original subtitle source individually; cross-language match strategy remains a benchmark outcome.
- External generated subtitles are convenient for iteration; Plex may prefer them over embedded equivalents, but behavior is not contractually guaranteed.
- For non-MKV inputs, remux/stream-copy to MKV where feasible; require explicit handling for unsupported codecs/streams and path migration.
- Series glossary pre-analysis can often start with text from all episodes and use targeted ASR, not whole-season transcription.
- File identity across transcoding cannot be reliably established from file path, MKV tag or subtitle watermark alone.

## How to close items

Record tested software/model versions, dataset characteristics, measurements, tradeoffs, and fallback. Change this register to **verified/decision adopted** and update exactly one owning feature document, with compatibility exceptions where appropriate.
