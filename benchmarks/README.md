# Benchmark harness — B0 corpus/runner/scorer + B1 synchronization comparison

Standalone Python CLI that measures competing subtitle-synchronization approaches.
It is **not** the production application: no queue, service, UI, API/MCP, Plex/Tdarr
integration, or media mutation. Source episodes are registered **read-only**; all
derived files live under `benchmarks/_scratch/` and `benchmarks/results/`, which are
git-ignored and never written into source roots or (via `--forbidden-root`) Plex-watched trees.

## Install

```
python -m pip install ffsubsync pysubs2 numpy pytest ruff
```

Requirements observed in development: Python 3.14, `ffmpeg`/`ffprobe` on PATH,
`ffsubsync` 0.5.1 (advertises `--split-penalty`). ALASS is not installed in this
environment, so the `b1-al` arm reports `unsupported` (an honest state, never a fabricated score).

Run from the repository root:

```
python benchmarks\run_bench.py --help
```

## Commands (all executed at least once against the synthetic fixture)

```
# Register a read-only reference source; subtitles are sidecars or MKV stream refs.
python benchmarks\run_bench.py source add --path benchmarks\fixtures\Fx00\reference.wav `
  --source-id Fx00 `
  --subtitle "main=sidecar:benchmarks/fixtures/Fx00/episode.ass" `
  --subtitle "signs=sidecar:benchmarks/fixtures/Fx00/signs.ass" `
  --gold "main=benchmarks/fixtures/Fx00/gold_episode.json" `
  --gold "signs=benchmarks/fixtures/Fx00/gold_signs.json" `
  --rights redistributable-synthetic-fixture

python benchmarks\run_bench.py source list
python benchmarks\run_bench.py source inspect --source-id Fx00

# Deterministic corrupted cases (S00..S04,S06; same seed => identical bytes).
python benchmarks\run_bench.py case prepare --source-id Fx00 --track-id main --scenario S01 --seed 12 --case-id Fx00-S01

# Run candidate arms (sequential; proposals only — originals are never mutated).
python benchmarks\run_bench.py run --case Fx00-S01 --all
python benchmarks\run_bench.py run --case Fx00-S01 --candidate b1-fg --candidate b1-px-fg

# Score against injected ground truth + comparison report.
python benchmarks\run_bench.py score --case Fx00-S01 --all
python benchmarks\run_bench.py report --case Fx00-S01 --out benchmarks\results\report.md
```

`benchmarks\reports\Fx00-plumbing-report.md` is the committed sample report from a
genuine executed offline run. The synthetic fixture has tone-burst "audio" at
dialogue midpoints: it validates harness plumbing only, **not** speech-synchronization
quality, and no thresholds are calibrated from it.

## Arms

| ID | Candidate | Notes |
| --- | --- | --- |
| `b1-n` | No-op baseline | cost/no-regression reference |
| `b1-fg` | ffsubsync global | timing proposals extracted from tool output only |
| `b1-fp` | ffsubsync piecewise | passes `--split-penalty 5`; capability probed from installed version |
| `b1-al` | ALASS | positional CLI; `unsupported` when binary absent |
| `b1-px-fg` / `b1-px-fp` | dialogue-only proxy + ffsubsync | gold/heuristic classification excludes signs/karaoke/SDH anchors; cue-ID map recorded; anchorless tracks abstain |
| `b1-va` | targeted-ASR validation | validates a base arm's proposals; `not_run` without a configured local endpoint |

## Targeted ASR boundary (`b1-va`)

No cloud inference is ever contacted. To run validation, set a **local** OpenAI-compatible endpoint:

```
$env:BENCH_ASR_BASE_URL = "http://127.0.0.1:8000/v1"
$env:BENCH_ASR_MODEL = "<model>"
$env:BENCH_ASR_API_KEY = "<optional>"
python benchmarks\run_bench.py run --case Fx00-S01 --all --base-candidate b1-px-fg --language ja
```

Without these, `b1-va` records `not_run` with the requirement text. Semantic correspondence
(subtitle ↔ the specific spoken utterance) is required; speech activity alone never accepts a
proposal. Mock transcribers exist for tests only and are labeled; they force abstention.

## Registering real reference episodes (G0/G1 — pending user media)

Until these are supplied and validated, G0/G1 remain **pending/blocked**; the fixture proves
plumbing only.

- **E01 — Japanese anime:** original-language audio, known-good **ASS** subtitles, ideally
  with positioned signs, karaoke, and multiple subtitle tracks.
- **E02 — Mandarin drama/donghua:** original-language audio, known-good English subtitles,
  preferably plus native-language (Chinese) subtitles.

Selection requirements: mount inputs read-only; verify the audio stream is the original
(non-dub) language; confirm subtitle track language/forced/commentary identity; manually
inspect beginning/middle/end and sign/music-heavy regions and **verify reference
synchronization before generating corruptions**; record chosen stream IDs in the source
manifest (`--notes`); keep at least one independent episode/series untouched as a future
holdout. Copy nothing into the repo: private media, transcripts, identifying paths, model
weights and credentials never get committed. `benchmarks/cases/sources.json` (contains
absolute local paths) and the scratch/results trees are git-ignored.

## Safety invariants enforced by this harness

- Sources opened read-only; fingerprints recorded at registration; mutation of a registered
  source is detected by fingerprint mismatch.
- Corruptions are written only to scratch; `prepare_case` refuses to overwrite the original.
- Injected invalid (negative/unordered) timestamps raise and are reported — never clamped.
- Tool output is used for timing proposals only; flattened tool output is never scored/applied
  as the final subtitle; signs-only tracks remain unmapped/unchanged.
- Tolerances (`--tol-good-us`, `--tol-severe-us`, `--tol-break-us`) are declared evaluation
  parameters, reported with every result; they are not production thresholds.
- Unavailable tools/models record `not_run`/`unsupported`; abstention is a scored outcome.

## Tests

```
python -m pytest benchmarks\tests -q
ruff check benchmarks
ruff format --check benchmarks
```

Current observed state: 42 tests pass; `ruff check` clean; `ruff format --check` clean.

## Scope boundaries

Out of scope (by design): production app, Docker service, web UI, job queue, API/MCP,
Plex/Tdarr/Bazarr, metadata rewriting, cloud inference, full-episode ASR (B2), general
semantic matchers (B3), translation correction (B4), multi-source consolidation (B5).
Actual edited-footage fixtures (true release differences) are a separate fixture type to be
added after this baseline — a synthetic timestamp jump is not evidence about real edits.

Findings and decisions: [`docs/40-delivery/benchmarks/findings.md`](../docs/40-delivery/benchmarks/findings.md).
