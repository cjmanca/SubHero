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
# Multi-audio media REQUIRE --audio (see "Stream selection" below); Fx00 has one audio
# stream and registers with the persisted default selection (sidx:0).
python benchmarks\run_bench.py source add --path benchmarks\fixtures\Fx00\reference.wav `
  --source-id Fx00 `
  --subtitle "main=sidecar:benchmarks/fixtures/Fx00/episode.ass" `
  --subtitle "signs=sidecar:benchmarks/fixtures/Fx00/signs.ass" `
  --gold "main=benchmarks/fixtures/Fx00/gold_episode.json" `
  --gold "signs=benchmarks/fixtures/Fx00/gold_signs.json" `
  --rights redistributable-synthetic-fixture

# Example with explicit selection (dual-audio episode with commentary):
python benchmarks\run_bench.py source add --path benchmarks\private\E01\episode.mkv `
  --source-id E01 --audio lang:jpn --subtitle "main=mkv:lang:eng"

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
genuine executed offline run. The synthetic fixture's audio consists of tone bursts
filling the dialogue windows (silence outside them): it validates harness plumbing
only, **not** speech-synchronization quality, and no thresholds are calibrated from it.

## Stream selection (reference audio + embedded subtitle tracks)

`source add --audio index:<n>|sidx:<n>|lang:<code>` fixes which audio stream the
harness decodes for dual-audio/commentary episodes:

- `index:<n>` — the ffprobe **global** stream index (what `source inspect` lists);
  the stream must exist and be an audio stream.
- `sidx:<n>` — the ffmpeg **audio-relative** index used in `-map 0:a:<n>`
  (`0 <= n <` audio stream count).
- `lang:<code>` — must match **exactly one** audio stream's ffprobe language tag;
  zero or multiple matches refuse registration with a message listing the audio streams.

Registration validates the spec against ffprobe and persists the resolved identity
in `cases/sources.json`: `audio_selected: {index, sidx, language, codec_name}` plus
`audio_spec` (the spec as given). A multi-audio source registered **without**
`--audio` is refused (exit 2, listing each stream's index/sidx/language and
instructing `--audio`); a single-audio source defaults to `sidx:0` and persists the
same structure. `run` decodes the full reference audio **and** the targeted-ASR
windows (`b1-va`) from the persisted selection: `_get_reference_audio` resolves
`0:a:<sidx>` and `cmd_run` threads that string into `validate_proposal` →
`extract_audio_window`. A registry record with >1 audio stream and no persisted
selection **fails closed** (clear refusal, non-zero rc); legacy single-audio records
without the field fall back to `0:a:0`. Sources registered before this change
(real registries) must re-register sources to record their selection. A scratch
`reference.wav` is reused only when `preprocess.json` records the current
`audio_stream` and source `media_sha256`; after a re-registration with a
different `--audio`, or with missing/corrupt metadata, the harness re-extracts
and rewrites `preprocess.json` — audio decoded under a stale selection is
never reused.

Embedded MKV subtitle specs are unambiguous — `track_id=mkv:sidx:<n>`
(ffmpeg subtitle-relative index for `-map 0:s:<n>`), `track_id=mkv:index:<n>`
(ffprobe global index; must be a subtitle stream), `track_id=mkv:lang:<code>`
(exactly one match). Sidecar specs are unchanged. Each MKV spec is validated
against ffprobe at registration, the per-track normalized identity is persisted as
`subtitle_selected`, and `subtitle_specs` stores the canonical `mkv:sidx:<n>` form
from which `case prepare` derives `-map 0:s:<sidx>`. A legacy bare `mkv:<digits>`
spec is **refused**: ffmpeg `-map 0:s:<n>` counts subtitle streams while
`source inspect` shows ffprobe global indices, so the bare number is ambiguous.

## Arms

| ID | Candidate | Notes |
| --- | --- | --- |
| `b1-n` | No-op baseline | cost/no-regression reference |
| `b1-fg` | ffsubsync global | timing proposals extracted from tool output only |
| `b1-fp` | ffsubsync piecewise | passes `--split-penalty 5`; capability probed from installed version |
| `b1-al` | ALASS | positional CLI; `unsupported` when binary absent |
| `b1-px-fg` / `b1-px-fp` | dialogue-only proxy + ffsubsync | **heuristic-only anchor classification** (karaoke/music/style/brackets); gold cue labels are never supplied to these arms; cue-ID map recorded; anchorless tracks abstain |
| `b1-pxo-fg` / `b1-pxo-fp` | **Oracle-assisted DIAGNOSTIC**: dialogue proxy using **GOLD cue labels** + ffsubsync | upper-bound reference only: anchor selection comes from the benchmark's own gold annotations; every proposal/run record carries an explicit `oracle-assisted diagnostic arm` marker; **excluded from `--all`** and from default candidates; select explicitly (`--candidate b1-pxo-fg`) |
| `b1-va` | targeted-ASR validation | validates a base arm's proposals; `not_run` without a configured local ASR endpoint (and cross-language samples abstain — `not_run` if that is the only evidence — without a configured `BENCH_SEM_VERIFY_*` semantic verifier; lexical score never decides cross-language pairs) |

### Gold-label leakage boundary

Gold cue-classification files are **reference evaluation data**. Default
candidates must never derive anchor choices from them, and the harness
enforces this at two boundaries: `run` passes the gold path **only** to the
oracle diagnostic arms, and `run_candidate` independently ignores any gold
path supplied for every default candidate (including the default proxy
arms). Consequences: `--all` runs exactly the six default arms
(`b1-n`, `b1-fg`, `b1-fp`, `b1-al`, `b1-px-fg`, `b1-px-fp`) plus the
special-cased `b1-va`; oracle arms appear only when named explicitly and
are labeled in proposal notes, `run.json` reasons, and scoring. Scoring
itself never consumes gold files (gold labels play no role in timing,
breakpoint, or offset metrics); case manifests keep
`gold_classification_path` solely as evaluation metadata.

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

### Translation-assisted semantic verification boundary (`BENCH_SEM_VERIFY_*`)

Lexical comparison is meaningless across languages: Japanese/Chinese audio transcripts
against English subtitles have ~zero lexical overlap, so a cross-language lexical score is
**never accept-support and never reject evidence**. Cross-language samples are decided only
by an explicitly configured, **translation-tolerant semantic verifier** — an
OpenAI-compatible `/chat/completions` endpoint judged by the env var pair, fully
**independent** of the ASR env vars:

```
$env:BENCH_SEM_VERIFY_BASE_URL = "http://127.0.0.1:8100/v1"
$env:BENCH_SEM_VERIFY_MODEL = "<model>"
$env:BENCH_SEM_VERIFY_API_KEY = "<optional>"
```

Subtitles/transcript text leave the machine only to that endpoint; confirm it is local and
permitted before configuring it. Verifier posture: `match` → accept, `no_match` → reject,
`unknown`/call-failure → abstain (logged). **Unconfigured verifier**: every cross-language
sample abstains with the reason that cross-language lexical differences are not evidence,
and if no usable evidence exists at all the record is `not_run` with original timing
retained — valid translations are never systematically false-rejected. Same-script pairs
keep the lexical Dice decision (agreement is meaningful within one language). Mock
semantic verifiers exist for tests only, stamp `asr_notes.log`, region reasons, and record
notes with a `test-only` marker, and the CLI wires only
`get_semantic_verifier()` (env-configured) — never mocks.

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

Private-data home and CLI protection (enforced, not just policy):

- The supported repository-local home for real episodes is **`benchmarks/private/`**
  (see its README stub). Each episode goes in its own subdirectory, e.g.
  `benchmarks/private/E01/episode.mkv` with sidecars beside it. Everything under
  `benchmarks/private/` — media, sidecar subtitles, extracted audio, transcripts,
  annotations/gold files, private case manifests, logs, model outputs, results — is
  git-ignored and **never committed**; only `benchmarks/private/README.md` is committed.
- `source add` **refuses** to register any media, sidecar subtitle, or gold annotation
  path that resolves inside the repository outside `benchmarks/private/` and the
  synthetic `benchmarks/fixtures/` home (exit 2, nothing registered, no partial writes).
  Paths outside the repository (e.g. read-only mounts) are allowed and recommended.
- Case manifests are routed by rights: only `redistributable-synthetic-fixture` sources
  write `.case.json` manifests into the committed `benchmarks/cases/` directory; all
  other sources (e.g. `private-local`) write under `benchmarks/private/cases/`.
  `case list`, `run`, `score`, and `report` find manifests in both locations.

## Safety invariants enforced by this harness

- Sources opened read-only; fingerprints recorded at registration; `run` and `score`
  recompute registered media/sidecar fingerprints plus the case input fingerprint before
  any execution or scoring and abort (rc 3, `SOURCE CHECK FAILED`) on any mismatch.
- Corruptions and all generated artifacts (manifests, reports, proxies, excerpts, logs)
  are written only under scratch roots; every write path passes through
  `paths.ensure_scratch_path`, which refuses source roots and `--forbidden-root` trees.
  `prepare_case` refuses to overwrite the original.
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

Current observed state: 120 tests pass; `ruff check` clean; `ruff format --check` clean.

## Scope boundaries

Out of scope (by design): production app, Docker service, web UI, job queue, API/MCP,
Plex/Tdarr/Bazarr, metadata rewriting, cloud inference, full-episode ASR (B2), general
semantic matchers (B3), translation correction (B4), multi-source consolidation (B5).
Actual edited-footage fixtures (true release differences) are a separate fixture type to be
added after this baseline — a synthetic timestamp jump is not evidence about real edits.

Findings and decisions: [`docs/40-delivery/benchmarks/findings.md`](../docs/40-delivery/benchmarks/findings.md).
