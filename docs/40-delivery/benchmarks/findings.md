# Benchmark findings and algorithm decision records

**Status: harness executed on synthetic plumbing fixtures; no real-media experiments yet.** This page is an index of actual evidence and decisions, not a prediction of winners. Source requirements remain in their owning feature documents; unresolved items remain in [the experiments register](../open-questions-and-experiments.md).

## Experiment status

| ID | Purpose | Current state | Evidence/decision |
| --- | --- | --- | --- |
| B0 | Corpus, labels, minimal runner | **in_progress** — runner + synthetic fixture complete; scoring/measurement validity corrected 2026-10-14 (third-review remediation: 269 focused tests) | `benchmarks/` CLI implemented; offline runs on `Fx00` fixture produced machine-readable proposals/scores; real-media clean controls (G0) **pending** user episodes E01/E02 |
| B1 | ffsubsync / ALASS / targeted ASR validation | **in_progress** — arms executable, canonical Fx00 matrix re-run under third-review remediation (old pre-remediation runs invalidated by the binding contracts) | ffsubsync 0.5.1 global + `--split-penalty` executed; ALASS absent → arm records `unsupported`; `b1-va` → `not_run` (no local ASR/semantic-verifier endpoints configured). No algorithm selection; G1 **blocked** pending real media |
| B2 | Full source-language ASR + forced alignment | **Not started** | None |
| B3 | Cross-language utterance/cue matching | **Not started** | None |
| B4 | Translation correction | **Not started** | None |
| B5 | Source consolidation and ASS/SRT integrity | **Not started** | None |
| B6+ | Metadata, glossary, quality, OCR, Plex, Unraid | **Not started** | None |

Mark `not_run`, `blocked`, `in_progress`, `completed` or `invalidated` explicitly. Never change a row to completed solely because a runner produced output files: a finished experiment must have inspected evidence and a conclusion.

## Observed B0/B1 infrastructure evidence (2026-10-14, offline synthetic only)

- Environment: Python 3.14.0; `ffsubsync 0.5.1` (installed; `--split-penalty`, framerate flags verified against installed version); `ffmpeg`/`ffprobe` present; **ALASS not installed**; no ASR model endpoint configured.
- Harness behavior verified on the redistributable `Fx00` synthetic fixture (tone bursts filling dialogue windows — plumbing validation only):
  - Deterministic corruption generators S00–S04/S06 with recorded per-cue injected deltas and exact inverse maps; repeated same-seed preparation produces byte-identical output; invalid timestamp injections (negative starts) raise `InvalidTime` and are rejected, never clamped.
  - Clean S00 controls produced zero harmful accepted corrections for global arms (`b1-fg`, `b1-px-fg`); piecewise arms introduced small 6–44 ms tails on controls on the tone fixture.
  - Signs-only tracks: proxy arms record `abstain_no_speech_anchors` and leave timing unchanged; direct arms produced harmful accepted corrections (3.6 s median residual), i.e. the negative control exposes exactly the false-anchor hazard the proxy design targets.
  - Tool-absent states recorded as `unsupported` (ALASS) and `not_run` (targeted-ASR without endpoint); `not_run`/`unsupported`/`abstain`/mapping-failure states recorded honestly, with no synthetic zero-scores fabricated.
  - 49 focused offline tests pass; `ruff check`/`ruff format --check` clean.
  - Independent read-only adversarial review conducted; accepted findings fixed and locked with regression tests: central scratch-root write guards on manifests/reports/subtitle saves/proxy outputs/tool outputs/validator logs (CLI-refused `report --out` outside scratch roots), fingerprint verification before every `run`/`score` (aborts with SOURCE CHECK FAILED on tamper), full-track tool-output mapping by preserved file order (unsorted-event regression test), S02 zero-injection guard (drift scales that quantize away are rejected), validated arm relabeled as `b1-va` in scores, end-boundary timing errors scored alongside onsets, abstention-status exactness, breakpoint detection computed in the original timeline domain, and repo-root-relative paths in committed case manifests.
- Sample machine-readable + human report: `benchmarks/reports/Fx00-plumbing-report.md` (synthetic denominators: 1 fixture episode; all variants correlated).
- **Conclusion so far:** the harness can execute the B1 matrix and score it honestly; **no candidate is adopted**, and the G1 gate has no real-media evidence. Real-episode registration procedure and stream-selection requirements are documented in `benchmarks/README.md`.


## Corrected-harness B0/B1 re-run (2026-10-14, genuine executed measurements, synthetic fixture only)

After the reviewer-directed correction milestones (private-data protection, source-stream selection, scoring validity, gold-label leakage removal, cross-language ASR validation, output-mapping/filesystem safety), the canonical Fx00 matrix was re-executed in the repository with the corrected harness (real `ffsubsync 0.5.1`; Python 3.14.0; ALASS absent; ASR/semantic-verifier endpoints unconfigured). Case regeneration reproduced all 7 committed manifests **byte-identically** (determinism preserved through all harness changes). `benchmarks/reports/Fx00-plumbing-report.md` is the committed report from this executed run.

Observed on the corrected harness (denominator: 1 synthetic fixture, correlated variants — plumbing/validity evidence only, never production thresholds):

- **No-op arm receives zero breakpoint-detection credit** on discontinuity cases (S03/S04: candidate-implied breakpoints 0, matched 0, false-positive 0) while the separate unresolved-discontinuity metric correctly reports the injected discontinuities as unresolved (1/1, 3/3-class behavior). The pre-correction residual-domain scorer granted the no-op free detection credit; that artifact is gone.
- **Offset-recovery sign is pinned:** on S01 (+1.9 s injected constant offset), global arms report applied shift −1900 ms, recovered +1900 ms, **residual 0 ms**; no-op reports applied 0, residual 1900 ms. Direction verified against the corruption generator (`corrupted = original + offset`).
- **Gold-label leakage boundary measured live:** default proxy arms classify anchors with heuristics only; oracle-assisted diagnostic arms (`b1-pxo-*`, explicitly excluded from `--all`, marker present in proposal notes and reports) show the gold-label path; on the signs-only fixture, both agree the track is all non-speech → `abstain_no_speech_anchors`; direct full-track piecewise arms on signs-only tracks still produce harmful accepted corrections (≈3.6 s median residual) — negative control intact.
- **Real ffsubsync rewrites event structure in some flows, and the correspondence guard catches it:** S03/S04 full-track arms returned `mapping_failure_ambiguous_text` (equal 24-event counts, normalized text re-attached at shifted positions) and SGN01 full-track global returned `mapping_failure_count_mismatch` (5 inputs → 1 output). Pre-correction positional mapping would have guessed correspondences from these outputs; the corrected harness abstains visibly, and no score in this re-run derives from guessed identity. Consequence for B1 planning: full-track ffsubsync arms must be interpreted through correspondence-preserving flows on real media (proxy/dialogue arms mapped 1:1 on the same cases).
- **`b1-va` cross-language validation posture:** without configured ASR/semantic-verifier endpoints it records `not_run` with original timing retained (all 7 cases). The lexical-era systematic false-reject of valid translations is removed in code (cross-language pairs are decided only by the translation-tolerant verifier boundary; mocked-endpoint tests cover translations→accept, contradictions→reject, absent-verifier→abstain, injection-steered responses→unknown, never false accept). Real b1-va behavior remains **EXTERNAL/UNVERIFIED** until local endpoints are configured.
- Automated verification: 151 focused offline tests pass (`python -m pytest benchmarks\tests -q`); `ruff check`/`ruff format --check` clean; independent read-only review of the full correction diff: no P0/P1; acceptance-blocking P2s (report-destination guard ordering, transliterated-transcript false rejects, verifier prompt-injection steering) fixed with regression tests; P3 hardening (Windows reserved ids, rights enumeration/home coherence, zero-audio refusal, fresh-clone test hermeticity) folded in. Full ledger: `STATUS.md`.
- **Not claimed:** G0 (known-good real-episode clean controls) and G1 (sync algorithm decision) remain **blocked** — they require user-supplied E01/E02 real episodes. No candidate is adopted. No threshold is calibrated from synthetic data.

## Second code review remediation (2026-10-14, executed measurements, synthetic fixture only)

A second independent source-level review of the corrected harness identified eight findings (F01–F04 P1, F06–F08 P2, F05 P1); all were fixed, each with targeted regression tests, and the canonical Fx00 matrix was re-executed under the remediated harness (same environment; real `ffsubsync 0.5.1`; ALASS absent; ASR/semantic endpoints unconfigured → `b1-va not_run`). Commits `c65d3ef..414ae3f`; full ledger in `STATUS.md`.

Measured outcomes (denominator: 1 synthetic fixture, correlated variants — validity/plumbing evidence only):

- **Targeted-ASR audio plumbing (F01):** the validator now extracts windows only from the already-decoded single-stream `reference.wav`; a real-ffmpeg integration test proves the windows are the SELECTED second audio stream (byte-equal full decode, dominant-frequency/correlation identity vs the 880 Hz selected stream, anti-correlation vs the unselected 440 Hz stream). Selected-audio provenance is recorded in `run.json`.
- **Gap-aware breakpoint scoring (F02):** detection credit moved from a sub-tolerance time match to one-to-one **bracketing intervals** between adjacent cue anchors (sub-divided by candidate-proposed boundaries), with localization reported as bracket width and ≥2-breakpoint intervals counted explicitly as ambiguous with no credit. The committed `Fx00-S03` case (true breakpoint 45.12 s inside a 2.88 s subtitle-free gap) scores 1/1 matched, 0 false positives under a perfect inverse repair; no-op zero-credit, extra-jump false-positive +1, and harmful/worsened controls preserved. Junk proposed edges cannot farm credit (verified: matched ≤ true breakpoints; junk edges add false positives).
- **Language-identity routing (F03):** cross-language routing is decided by verified spoken/target language identity (ISO 639-2/B↔639-1 normalized; registry-captured MKV tags + declared sidecar hints), with broad script detection (Hangul, Cyrillic, Greek, Arabic, Devanagari) as fallback only. Korean/Russian/French/Japanese/Mandarin/romanized transcripts against English subtitles never take the lexical-reject path: verifier-only when identities differ, abstain when identity is unknown and no verifier is configured. Verified same-language contradiction rejects preserved. A same-stem sidecar collision resolves to identity-unknown abstain, never a wrong-identity reject.
- **Provenance invalidation (F04 + review P1-1/P1-2/residual):** proposals, acceptances, scores, run metadata, the reference-audio cache, and every report row are bound to a versioned fingerprint of the current case generation + selected audio + candidate/tool configuration. Seed regeneration, audio re-registration, tampered proposals/acceptances/scores, stale generations, and legacy artifacts are refused (rc 6) with stale-score deletion; a genuine re-run restores scoring. Cache reuse requires the recorded WAV byte hash. The regenerated plumbing report shows `dropped unbound score rows: 0` / `dropped stale-generation rows: 0` on fresh data, with stale-score deletions observed live on non-scoreable arms.
- **Private-data homes (F05):** in-repo `private-local` registrations are allowed only under Git-ignored private homes (fixtures reserved for declared synthetic references); in-repo custom `--root`s must be the canonical root or proven Git-ignored (fail-closed, verified in disposable `git init` checkouts including a `git add -A` dry-run safety test and junction/subst attacks).
- **Mapping identity (F06), reliability gate (F07), path stability (F08):** duplicate-normalized-text cue groups map only with non-decreasing output onset order (event swaps abstain per-cue; multiset rewrites refused); automatic acceptance in every language path requires a usable ASR reliability signal (missing-sentinel/low/uninterpretable → abstain, verifier `no_match` reject unchanged, evidence counters separated); registration persists canonical absolute sidecar/gold paths in the ignored registry while committed manifests stay root-relative redacted (byte-identical regeneration of all 7 committed manifests re-proven).
- **Review loop:** independent read-only adversarial review round 1 found two P1 provenance gaps (unbound acceptance.json; unbound score/report rows) — fixed with binding + 12 regression tests; round 2 verdicts: F01/F02/F03/F05/F06/F07/F08 PASS, P1s RESOLVED, one narrow P2 (proposal-missing stale score + report generation binding) fixed with 4 further tests. Automated verification progression: 151 → **222 passed** (`python -m pytest benchmarks\tests -q`, 0 skips), `ruff check`/`ruff format --check` clean throughout; reviewer independently re-ran the suite and probe scripts.
- **Not claimed:** G0/G1 remain **blocked** (E01/E02 real episodes not supplied); no candidate adopted; no thresholds calibrated. `b1-va` real-endpoint behavior remains EXTERNAL/UNVERIFIED. Transliterated transcript with language hint `und`/`en` against Latin subtitles abstains safely (documented residual).

## Third code review remediation (2026-10-14, executed measurements, synthetic fixture only)

A third independent review (PLAN.md "Third review and bounded Qwen remediation handoff") found seven harness-validity findings — F01–F04 (P1), F05–F07 (P2) — all fixed with focused regression tests, then closed through four adversarial review rounds. Commits land on top of the reviewed `d4da5d6`; full ledger in `STATUS.md`. Environment unchanged: Python 3.14.0, `ffsubsync 0.5.1`, ALASS absent, ASR/semantic-verifier endpoints unconfigured.

Fixes (mechanisms now enforced by code, each locked by tests):

- **F01 acceptance↔base binding:** `b1-va` run.json records the validated base's `base_run_id`, `base_run_sha256`, `base_input_fingerprint`, proposal hash, and the full `validation_config` (seed, language identities, ASR/verifier model IDs, pad/timing tolerance — no credentials). Score and report **re-verify at read time**: re-running the base arm with a new proposal, byte-tampering the base run/proposal, deleting `acceptance.json`, relabeling seed/models/languages, deleting the base directory, or a cross-case-planted acceptance all refuse (rc 6, stale score deleted, report row excluded with a reason). Positive controls: unchanged base scores stay green; a genuine re-validation restores the row.
- **F02 fingerprint v2:** `FINGERPRINT_SCHEMA_VERSION = 2` binds ground-truth fields (`original_times_us`, `injected_cue_deltas`, `expected_inverse`, transform/grid/format), the live gold-classification **content hash** (`GOLD_FILE_MISSING` sentinel) and subtitle-input identity. Editing injected deltas/ground truth, changing the gold file (edit, delete, restore), or swapping the subtitle input invalidates cached proposals/scores in run, score, b1-va deps and report; old-fingerprint rows never mix into comparative tables (stale-generation counts observed live: pre-remediation committed artifacts drop as 39 unpaired/6 obsolete, forcing the re-run below).
- **F03 timing-correspondence:** semantic verification now distinguishes `semantic_content_present_in_window` from `timing_correspondence_verified` using ASR verbose_json segment timestamps with a documented `TIMING_TOLERANCE_US = 500 ms`. Auto-accept requires time-local evidence inside the interval (with tolerance); padding-only matches, ambiguous in-interval+padding windows, and missing timestamps **abstain** (never text-presence-only accepts); the cross-language verifier judges in-interval segment text only.
- **F04 local-cue vs release discontinuities:** an equal-correction run flanked by equal values on **both** sides is transient — its entering/exiting steps are excluded from implied-break/false-positive counts and its cues are reported as `local_cue_adjustments`. Perfect isolated S04 repair: 0 implied, 0 false-positive, 1 local adjustment, 1 repaired (was 2 false positives pre-fix); sustained spurious step keeps its false positive (S00 control); gap-aware bracket credit and one-to-one localization preserved (S03 1/1 matched, 0 FP under perfect inverse); oscillation [0,-2,0,-2,0] → 0 claims, 2 local adjustments (middle untouched cue not counted).
- **F05 fail-closed report:** when the current case manifest or registered source is missing, self-consistent historical rows render **only** in a labeled *Unverified historical results (NOT COMPARABLE)* section; the comparative tables go empty; re-registration restores them.
- **F06 counterfactual labeling:** scores are schema 3: without any AcceptanceRecord every count is named `*_if_blindly_applied` and the row records `final_semantics = unguarded_proposal_if_blindly_applied`; `accepted_*` names exist only for arms with a genuine acceptance record. Report columns read `Acc validated` / `If blind` with the semantics note; legacy schema-2 rows render only in a labeled *NOT COMPARABLE* section.
- **F07 verifier-time attribution:** `semantic_seconds` and `verifier_calls` are recorded separately (AcceptanceRecord, b1-va run.json, report bullets: `asr calls N/Xs · verifier calls M/Ys · inference total Zs`); `asr_seconds` keeps ASR-only meaning; additive defaults keep pre-F07 acceptance.json readable. Proven with fake transcriber at exactly 7.0 s/sample and fake verifier at exactly 3.0 s/call: asr 7·n, semantic 3·c, total 10·n.
- **Review-round closures (adversarial rounds 1–4, read-only reviewers with scratch repros):** acceptance-deletion and report-path proposal-byte bypasses, proposal-hash-key-removal bypass, non-dict/structurally-incomplete artifact crashes, score.json directory-piggyback, copied run/proposal/score triples, cross-directory field grafts, type-tampered hash/number/schema fields, hostile acceptance value types, registry-record key removal (media_path/media_sha256/subtitle_specs) → all closed by directory-pairing admission (a score.json renders only through its own byte-verified run.json; duplicate case+candidate directories excluded), type-safe binding (refusal, never traceback), and read-time re-verification; 17 dedicated regression tests. Round-4 verdict: **CLOSURE VERIFIED — no P0/P1/blocking-P2**, positive controls green (genuine flows render, unchanged-case cacheable, media mutation rc 3 → restore rc 0), zero tracebacks across the attack battery.
- **Documented inherent residual:** fabricated numbers *inside* a score.json that pairs with an admitted, byte-verified run record render as recorded (score bytes are not self-hashed); the report header now states this provenance boundary and directs regeneration via `score` rather than editing. `git diff --check` clean for harness files.

Automated verification progression: **222 → 269 passed** (`python -m pytest benchmarks/tests -q`, 0 skips), `ruff check`/`ruff format --check` clean throughout.

**Canonical Fx00 matrix re-run under the remediated harness (required: fingerprint v2 + schema-3 + report pairing invalidate all pre-remediation run/score artifacts; old results were discarded, not mixed).** All 7 committed manifests regenerated **byte-identically** (git-clean `benchmarks/cases` after re-prepare); full arm matrix executed with real ffsubsync 0.5.1 (`b1-al` `unsupported`, `b1-va` `not_run` — no endpoints); `benchmarks/reports/Fx00-plumbing-report.md` replaced by this executed schema-3 run. Header counts observed: `dropped unbound 0 / stale-generation 0 / obsolete-acceptance 0 / tampered-proposal 0 / unreadable artifacts 0 / legacy rows 0` on fresh data. Key rows (denominator: 1 synthetic fixture, correlated variants — plumbing/validity evidence only, never production thresholds):
- S01 offset: `b1-fg`/`b1-px-fg` applied −1900 ms, residual **0 ms**; `b1-fp` residual 18 ms, `b1-px-fp` 19 ms; `b1-n` residual 1900 ms — sign convention intact.
- F04 separation visible in real tool output: `b1-px-fg` on S01 shows **0 implied / 0 false-positive with 14 local cue adjustments** (piecewise jitter no longer farms break credit); `b1-px-fp` shows 11 sustained false positives + 3 local adjustments — sustained vs transient attribution working on genuine tool proposals.
- S03: no-op keeps 0 detection credit with 1/1 true breakpoint reported unresolved; proxy arms 0/0/0 + 3 local; gap-aware behavior preserved.
- SGN01 negative control intact: proxy arms `abstain_no_speech_anchors`; full-track `b1-fp` 5 harmful proposed (5126 ms shift against a 1490 ms truth, median 3636 ms) labeled if-blindly-applied; `b1-fg` count-mismatch mapping failure visible.
- No algorithm selection: G0/G1 remain **blocked** pending user-supplied E01/E02 real episodes; `b1-va` real-endpoint behavior remains **EXTERNAL/UNVERIFIED**; Fx00 remains plumbing evidence only.

## Decision record template



Copy into a **new** decision record under `docs/40-delivery/benchmarks/decisions/` only after running that experiment. Use stable IDs such as `BENCH-SYNC-001.md`. Do not fill sample scores or invent outcomes.

```markdown
# BENCH-<DOMAIN>-<NUMBER>: <Decision title>

- Status: proposed | validated | conditional | rejected | superseded
- Date: YYYY-MM-DD
- Requirements: <links to owning documents>
- Open question IDs: E07, ...
- Corpus: <episode/source IDs, held-out status, annotation version>
- Candidate versions: <exact code/model/weight revisions and settings>
- Run artifacts: <local results path or committed redacted aggregate>

## Hypothesis and controlled comparisons
<conditions, baseline and negative controls; what was held fixed>

## Observations
<metrics with denominators/uncertainty, regression counts, runtime/cost>

## Failure analysis and scope
<important false accepts, language/content limits, unsupported cases>

## Decision
<adopt | adopt conditionally | defer | reject and why>

## Safe fallback and reevaluation triggers
<abstention/escalation when uncertain, upstream changes, new corpus>

## Follow-up documentation changes
<owning requirement document and open-experiments register update>
```

A conditional decision should state **where** it applies (e.g. global offsets only, not sign-heavy piecewise releases). If comparable candidates have insufficient evidence, explicitly record *no selection*, with the smallest additional experiment needed.

## Reporting discipline

- Publish aggregate tables and actionable failure examples **without copying private episode content** into public docs. Track local media paths and private annotations via access-controlled manifests.
- Document each candidate's **unmodified-control regression** rate, acceptance versus abstention, and failures around discontinuities; never show a winner by mean timing error alone.
- Separate measured facts from inference; attach input and command hashes, software/model versions, human-label uncertainty and usable reproduction steps.
- Calibrate automated thresholds only after independent holdouts; record version- and language-specific limitations, and reevaluate decisions after upstream model/tool changes.
- Update the [open-experiments register](../open-questions-and-experiments.md) and one owning requirements document when necessary. Do not silently promote a provisional result into a product requirement.
