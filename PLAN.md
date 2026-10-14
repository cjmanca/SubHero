# Qwen Handoff — Benchmark Harness (B0 + B1)

## Assignment

Implement the **standalone Python benchmark tool** for the Media Metadata & Subtitle Utility, starting with **B0 (corpus/fixtures/runner/scorer)** and **B1 (lightweight subtitle synchronization comparison and targeted validation)**.

The goal is to measure competing approaches, **not** build the production media-management application or prematurely select a winning algorithm.

This is an authorized, bounded **pre-plan benchmark task**.

Operate as the top-level implementing agent: follow `AGENTS.md` and `ORCHESTRATION.md`.

If you delegate, give subagents self-contained, narrowly scoped briefs; they must not read `ORCHESTRATION.md`, `PLAN.md`, or `STATUS.md`.

Do **not** create `PLAN.md`/`STATUS.md` merely because the orchestration policy describes them. If approved versions already exist, respect their ownership and immutability rules.

## 1. Read the relevant requirements

Start with these repository documents:

* `docs/40-delivery/benchmarks/README.md`
* `docs/40-delivery/benchmarks/corpus-and-fixtures.md`
* `docs/40-delivery/benchmarks/harness-and-artifacts.md`
* `docs/40-delivery/benchmarks/synchronization.md`
* `docs/40-delivery/benchmarks/evaluation-criteria.md`
* `docs/40-delivery/benchmarks/findings.md`
* `docs/20-subtitles/lightweight-and-full-synchronization.md`
* `docs/00-foundation/invariants.md`
* `docs/40-delivery/implementation-slice-map.md`

Read adjacent documents only where a concrete interface requires them.

The existing documentation is authoritative for requirements; this handoff defines the immediate implementation scope.

Inspect the repository before editing and preserve existing work.

---

## 2. B0 — Build the minimal reusable harness

Create a usable CLI under `benchmarks/`, or adapt to the existing repository layout.

Provide equivalent operations for:

1. Registering and inspecting reference media.
2. Preparing deterministic corrupted subtitle cases.
3. Running candidate algorithms against selected cases.
4. Scoring candidate outputs.
5. Producing human-readable comparison reports.

Use simple, versioned JSON manifests and results.

Avoid introducing a production database, service, queue, web UI, API, MCP, elaborate plugin system, or unnecessarily complex testing infrastructure.

### Source media safety

Source episodes and their original subtitle tracks must be **read-only**.

The user will provide known-good episodes later.

Support pointing to them through configurable local paths, preferably read-only mounts.

Keep derived subtitle cases, extracted audio, logs, and run artifacts in explicit scratch/results directories **outside Plex-watched libraries**.

Do not commit licensed/private media, private transcripts, identifying paths, model weights, or credentials.

### Required data representations

Represent at least:

* Source identifier and source fingerprint.
* Case identifier and deterministic seed.
* Selected audio and subtitle stream IDs.
* Original cue identifiers.
* Subtitle format.
* Transformation parameters.
* Expected inverse timing transformation.
* Candidate algorithm, version, and settings.
* Run status and failure reasons.
* Timing measurements.
* Scoring results and evaluation coverage.
* Output artifact references.

Use a documented common timeline, preferably integer microseconds or rational time units.

Distinguish source subtitle timestamps, media timestamps, and actual speech timestamps.

Do not assume subtitle display duration must equal spoken-dialogue duration.

---

## 3. Generate controlled benchmark cases

Implement deterministic transformations of known-good subtitles.

### Initial scenarios

| Case | Description                                                                  |
| ---- | ---------------------------------------------------------------------------- |
| S00  | Untouched control, including intentional overlapping ASS events              |
| S01  | Small and large positive/negative global offsets                             |
| S02  | Linear drift and frame-rate-like time scaling                                |
| S03  | One or more abrupt piecewise timing discontinuities                          |
| S04  | Isolated mistimed dialogue cues surrounded by correct cues                   |
| S06  | Mixed dialogue, signs, karaoke, SDH/non-speech events, and signs-only tracks |

For every case:

* Retain original event identity.
* Record exactly which changes were introduced.
* Preserve the original subtitle separately.
* Generate the expected inverse timing transformation.
* Ensure repeated runs with the same seed produce identical results.
* Detect invalid timestamps rather than silently modifying the ground truth.

Preserve original ASS/SRT text and style semantics when generating variants.

### Important distinction

An artificial timestamp discontinuity does not prove the algorithm can handle a genuine release difference involving inserted or deleted video footage.

Actual media edits must be represented as a separate fixture type with their own verified media-to-source timeline mapping.

That experiment can be added after the initial synchronization baseline.

### B0 tests

Provide focused tests for:

* Deterministic transformations and inverses.
* Unmodified control cases.
* Preservation of cue identity.
* Invalid timestamps.
* Correct scoring calculations.
* Source-media immutability.
* Scratch-directory isolation.

Include a small redistributable synthetic fixture for automated testing.

Do not claim this fixture validates actual speech synchronization.

---

## 4. B1 — Compare synchronization candidates

Implement executable adapters, where their dependencies are available, for the following approaches.

| Candidate | Description                                                   |
| --------- | ------------------------------------------------------------- |
| B1-N      | No-op baseline                                                |
| B1-FG     | ffsubsync global synchronization                              |
| B1-FP     | ffsubsync experimental piecewise synchronization              |
| B1-AL     | ALASS synchronization                                         |
| B1-PX     | Dialogue-only proxy variants                                  |
| B1-VA     | Targeted-ASR validation of existing synchronization proposals |

Verify actual command-line arguments and supported capabilities against the installed tool versions.

The piecewise ffsubsync candidate should test `--split-penalty` where supported.

Use subprocess argument arrays, explicit timeouts, captured errors, and clear failure states.

An unavailable executable or model should produce `not_run` or `unsupported`, not a fabricated benchmark result.

Use equivalent inputs and reference audio tracks for fair comparisons.

## 5. Dialogue-only synchronization proxy

Do not blindly feed complete styled ASS subtitle tracks into synchronization tools.

Generate temporary speech-like subtitle representations that exclude inappropriate audio-alignment anchors.

Examples include:

* Signs and written-text translations.
* Karaoke and song lyrics.
* Sound descriptions.
* Other non-speech events.

Retain explicit correspondence between proxy entries and original subtitle cue IDs.

Use candidate tools to generate timing proposals, not authoritative replacements for original subtitles.

### Mapping requirements

Attempt to derive global or region-level timing transformations.

Only project proposed changes back onto original events when correspondence is demonstrably reliable.

If a tool cannot provide sufficiently reliable mapping information, record the limitation or abstain.

Do not invent a mapping.

A signs-only track without reliable correspondence must remain unmapped or unchanged.

Preserve ASS styles, positioning, layers, and event-relative animation semantics.

Rigid shifts are generally safer than stretching animated events.

---

## 6. Targeted ASR validation

Implement a validation stage that evaluates synchronization proposals independently.

The validator should operate on proposals from an existing candidate so its incremental benefit can be measured.

### Sampling strategy

Include samples from:

* Beginning, middle, and end of the episode.
* Both sides of proposed timing discontinuities.
* Regions with weak synchronization evidence.
* Regions with unusually large proposed corrections.
* Distributed random control locations.

Compare fixed sampling strategies against adaptive approaches when practical.

### Validation requirement

The validator must establish **semantic correspondence between the subtitle and the specific spoken utterance**.

Detecting speech at the proposed timestamp is insufficient.

Where models are configured and available, use bounded source-language ASR together with an appropriate semantic comparison method.

Native-language subtitles may provide supplementary evidence when their source and timing are credible.

Do not feed ground-truth correspondence labels into the validator.

Record model versions, settings, inference costs, and uncertainty.

### Unavailable models

If an ASR model or semantic verifier isn't available:

* Implement the minimal runnable integration boundary.
* Mark the affected experiment as not run.
* Explain what is needed to execute it.
* Continue independent benchmark development.

Do not simulate successful verification or automatically accept unverified proposals.

The full-episode ASR pipeline and general semantic matchers belong to later B2/B3 experiments.

---

## 7. Shared scoring and evaluation

For every candidate and case, produce machine-readable results and a concise comparison report.

### Synchronization measurements

Include:

* Median timing error.
* P90 and P95 timing errors.
* Recovered global offsets.
* Drift estimation errors.
* Detected discontinuity positions.
* False-positive discontinuities.
* Correctly repaired cues.
* Previously correct cues made worse.
* Harmful proposed corrections.
* Harmful automatically accepted corrections.

### Acceptance and uncertainty

Measure:

* Proposal coverage.
* Accepted corrections.
* Rejected corrections.
* Abstentions.
* Unchanged regions.
* Validation sample coverage.
* Reasons for accepting or rejecting changes.

**Distinguish proposed corrections from automatically accepted corrections.**

Abstention is a valid outcome when evidence is insufficient.

### Resource consumption

Record:

* Wall-clock runtime.
* Preprocessing time.
* Candidate execution time.
* ASR processing time and calls, when applicable.
* Memory and VRAM consumption where measurable.
* Relevant tool/model versions.
* Input and output fingerprints.

Do not compare one method's inference-only time against another method's complete processing time without identifying the difference.

### Ground truth

Score synthetic timing recovery against the recorded injected errors.

Score speech/subtitle correspondence against independently verified annotations when available.

Keep clean controls and unchanged regions within partially corrupted files as negative controls.

Do not assume that a known-good subtitle's original display interval is always the theoretically optimal display interval.

### Statistical safeguards

Report actual denominators and the number of independent source episodes.

Multiple synthetic variants of one episode do not constitute independent validation episodes.

Keep tuning variants from the same source episode together.

Reserve at least one genuinely independent episode or series as a future holdout.

Do not invent numeric acceptance thresholds or declare a production-safe algorithm based on a single episode.

---

## 8. Required deliverables

Produce:

1. A working Python CLI benchmark harness.
2. `benchmarks/README.md` documenting actual installation and usage commands.
3. Versioned source, case, candidate, and result manifest formats.
4. Deterministic subtitle corruption generators.
5. Runnable synchronization candidate adapters.
6. Scoring and comparison reporting.
7. Targeted semantic-ASR validation where practical.
8. Focused automated tests.
9. A sample report from genuinely executed offline tests.
10. An evidence-based implementation handoff with remaining blockers.

Record actual experiments and conditional conclusions in:

`docs/40-delivery/benchmarks/findings.md`

Only update experiment status when sufficient evidence exists.

Leave unperformed experiments explicitly pending.

## 9. Out of scope

Do not implement the main application's:

* Docker service or production deployment.
* Web UI.
* Persistent job queue.
* API or MCP interface.
* Plex/Tdarr/Bazarr integrations.
* Media metadata rewriting.
* Cloud inference infrastructure.
* Full-episode ASR pipeline.
* Translation enhancement engine.
* Multi-source subtitle consolidation.

Do not modify or publish original media, push commits, create remote repositories, or place generated sidecars in Plex-watched folders.

Follow the existing agent and orchestration policies for commits and other permissions.

---

## 10. Work that can proceed without reference episodes

The user has not yet supplied known-good episodes.

Do not block independent implementation unnecessarily.

Complete the benchmark CLI, synthetic transformation logic, candidate integration code where possible, scoring, and meaningful offline tests.

Document exactly how the user can register reference episodes, including:

**E01 — Japanese anime**

Original-language audio, known-good ASS subtitles, ideally with positioned signs, karaoke, and multiple subtitle tracks.

**E02 — Mandarin drama or donghua**

Original-language audio, known-good English subtitles, and preferably Chinese-language subtitles.

Record the requirements for selecting reference audio and subtitle streams.

Until actual reference episodes have been supplied and validated, report **G0/G1 real-media validation as pending or blocked**.

Do not manufacture timing-accuracy results.

Once real samples become available, verify the reference synchronization before generating corruptions and running the candidate matrix.

---

## 11. Final review and handoff

Before completion, inspect the actual code changes and benchmark artifacts.

Perform a distinct read-only review focused on:

* Source-media safety.
* Correctness of synthetic transformations and ground truth.
* Unreliable timestamp mapping.
* False-positive synchronization corrections.
* Incorrect score calculations.
* Misleading claims about completed experiments.
* Unnecessary abstractions and testing infrastructure.

Fix high-impact findings and rerun affected checks.

The final report should include changed paths, exact commands and observed results, unresolved findings, limitations, benchmark conclusions supported by evidence, and **one concrete next action**.

**The objective is a small, reliable, reusable benchmark tool that can objectively establish which synchronization approaches work before we commit to the production subtitle pipeline.**
