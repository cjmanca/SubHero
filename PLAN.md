# Assignment: Correct SubHero B0/B1 Benchmark Issues

Repository: `cjmanca/SubHero`

Reviewed commit: `06f8ae660f4dbe397214fef3baa3257460ff9d6a`

Implement the corrections identified in the accompanying `SubHero_Qwen_B0_B1_Review_Handoff_2026-10-14.md`.

## Scope

Correct benchmark validity, source-media safety, stream selection, and experimental reproducibility.

Do not proceed with the B2–B5 milestones or build production application infrastructure.

Follow the existing `AGENTS.md` and `ORCHESTRATION.md`.

Preserve `PLAN.md` as immutable. Record verified progress in `STATUS.md`. Do not push changes without authorization.

## Milestone 1 — Private Benchmark Data Protection

Update `.gitignore` and the benchmark artifact paths.

Establish `benchmarks/private/` as the supported repository-local directory for real reference episodes.

Ensure that all private episode media, subtitle files, extracted audio, transcripts, annotations, generated cases, logs, model outputs, and benchmark results are excluded from Git.

Keep the existing redistributable `Fx00` synthetic fixtures committed.

Introduce a separate ignored location for private case manifests rather than placing them alongside committed synthetic cases.

Validate Git exclusions using `git check-ignore`, `git status`, and `git ls-files`.

Add safeguards preventing the CLI from registering private in-repository media under non-ignored directories.

**Acceptance:** No file related to E01/E02 can accidentally appear in a normal Git commit.

## Milestone 2 — Correct Source-Stream Selection

Support explicitly selecting the source audio track during episode registration.

Persist and validate the selection.

Ensure that both synchronization and targeted ASR use the selected audio stream.

Correct embedded subtitle extraction so stream identifiers have unambiguous semantics.

Add focused tests using synthetic media containing multiple audio and subtitle tracks.

**Acceptance:** The harness consistently processes the intended original-language audio and selected subtitle track.

## Milestone 3 — Correct Benchmark Scoring

Fix discontinuity detection scoring.

Detected breakpoints must be derived from proposed timing corrections, not residual timing errors.

Distinguish candidate breakpoint detection from unresolved discontinuities.

Correct the sign convention for reported offset recovery.

Add tests proving that:

* An unchanged candidate does not receive credit for detecting a correction.
* A perfect piecewise repair receives appropriate credit.
* Incorrect additional breakpoints count as false positives.
* Correctly synchronized regions remain protected.

**Acceptance:** Scoring correctly distinguishes successful corrections, unsuccessful corrections, and regressions.

## Milestone 4 — Remove Ground-Truth Leakage

Do not pass gold cue-classification labels to ordinary synchronization candidates.

Retain gold labels exclusively for evaluation.

If desired, create a separately identified oracle-assisted candidate for diagnostic comparisons.

**Acceptance:** Default candidates cannot obtain answers from the benchmark's reference annotations.

## Milestone 5 — Correct Targeted ASR Validation

Replace cross-language lexical matching with a genuinely multilingual semantic comparison or translation-assisted verification.

Keep transcription and semantic verification independently configurable.

If the required model is unavailable, abstain and report `not_run` or insufficient evidence.

Never interpret lexical differences between Japanese/Chinese audio transcripts and English subtitles as proof of incorrect alignment.

Add focused examples covering valid translations and actual semantic contradictions.

**Acceptance:** Cross-language validation does not produce systematic false rejections.

## Milestone 6 — Harden Output Mapping and Filesystem Safety

Verify cue correspondence after external synchronization tools rewrite subtitle events.

Matching event counts alone must not establish event identity.

Reject ambiguous correspondence rather than guessing.

Validate all user-controlled IDs and destination paths before creating directories or writing output.

Test path traversal, reordered ASS events, and rejected writes outside scratch roots.

**Acceptance:** Sources remain unchanged and all generated data stays within permitted directories.

## Final Verification

Run the existing automated tests and relevant lint/static checks.

Add targeted regression tests for each corrected defect.

Perform a separate read-only review of the actual changes.

Update benchmark findings only with measurements genuinely executed.

Do not claim that G0/G1 passed: those gates still require known-good real episodes.

Provide an evidence-based handoff identifying completed corrections, test results, remaining problems, and readiness for real-media benchmarking.
