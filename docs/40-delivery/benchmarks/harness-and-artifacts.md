# Minimal benchmark harness and reproducible artifacts

**Status:** runner is **not implemented**. **Owner:** standalone benchmark CLI and recorded artifacts. Related: [corpus](corpus-and-fixtures.md), [metrics](evaluation-criteria.md), [findings](findings.md).

## Boundaries

Implement a small **Python CLI**, not production infrastructure. It may use direct subprocess adapters for ffsubsync/ALASS/FFmpeg and thin replaceable calls to candidate models. Do **not** build a job queue, persistent service, web UI, MCP/API, plugin platform, or large testing framework just to benchmark. The harness should make the same cases and scoring data available to competing candidates.

Keep input media **read-only**; derive test subtitle files, true-edit media variants, extracted audio, caches and reports in a designated scratch tree outside Plex-watched folders. Avoid reading from/writing to BitTorrent paths except read-only inputs. Remove temporary decoded/extracted audio at end of runs by default; retain optional versioned ASR transcripts and match records for comparison.

Illustrative eventual code layout (a **design sketch, not commands that currently work**):

```text
benchmarks/
  README.md               # actual usage once the CLI exists
  cases/                  # reproducible, non-media manifests
  gold/                   # shareable annotations where rights allow
  scripts/prepare.py      # copies and perturbs only scratch variants
  scripts/run.py          # candidate execution
  scripts/score.py        # shared scoring
  results/                # ignored machine-produced artifacts
```

## Minimal case/run contracts

Use machine-readable JSON (or equivalent explicitly versioned schema) with the following stable concepts, not a production data model:

| Artifact | Required fields |
| --- | --- |
| Source manifest | `source_id`, media hash and access path reference, input rights status, stream IDs/languages, subtitle format, annotation version |
| Case manifest | `case_id`, `source_id`, `scenario`, seed, transformation parameters, expected inverse timeline (where applicable), gold/reference version |
| Candidate manifest | algorithm/model identifier, exact version/commit/weight revision/checksum, runtime/library versions, flags, prompts/decoding settings, local/remote execution class |
| Candidate output | stable original cue IDs; original/proposed media times; proposed mapping **per region**; untouched/rejected/uncertain regions and reasons; semantic candidate/link IDs as appropriate |
| Result record | `run_id`, case/candidate IDs, success/failure reason, run times, relevant raw/cached artifact fingerprints, scored metrics, resources, exceptions and sample coverage |

Represent time on a documented **common episode timeline** (prefer integer microseconds or a rational timebase; no implicit float equality). Distinguish source subtitle time from final media time, clip-local time and subtitle display time. Preserve per-event IDs when producing dialogue-only SRT proxies; when a tool outputs only rewritten timestamps, map those back to the originals **only where matching is unambiguous**. Failed mapping is a measured failure/abstention, not a reason to guess.

## Reproducibility and cost

- Pin candidates at a version/commit, including ffsubsync flags (piecewise is experimental), ffmpeg/ffprobe builds, VAD model, Qwen model revisions and Hy-MT2 weights/prompt. Capture CPU/GPU specifications and relevant inference settings.
- Save time taken, throughput per hour of input media, peak VRAM/RAM, model loading count, approximate disk I/O and actual remote usage/cost when known. Compare **cold and warm** runs separately, including and excluding shared preprocessing costs; don't unfairly exclude ASR/translation setup from one method.
- Fail gracefully on unavailable tools, unsupported languages/formats, license-incompatible models or unavailable GPU. Record `not_run`/`unsupported`, not a synthetic score of zero.
- Freeze cached upstream inputs when comparing downstream matchers/translators. Cache keys include source audio identity, track selection, model/version, settings, text/segmentation inputs and processing-stage version.
- Never log unredacted credentials or upload media/audio/text to a cloud endpoint without explicit permission. Model usage licenses (including **SONAR model** vs code licenses) must be checked for intended use.

`findings.md` records conclusions; **generated result files should remain separate from the human-readable decision record**. A benchmark rerun should be auditable without needing the eventual production database.
