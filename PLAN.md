# Assignment: Correct Three Remaining Benchmark Issues

**Repository:** `cjmanca/SubHero`
**Reviewed commit:** `4c7fe16697244847e5b8cb762e930f2769c18819`

## Objective

Correct three benchmark-validity problems identified during the fourth independent code review.

The previous remediation is substantially complete. Preserve those corrections.

**Do not expand into B2–B5 or build production application infrastructure.**

Follow `AGENTS.md` and the applicable orchestration policies. Keep approved `PLAN.md` versions immutable during execution. Only the main orchestrator manages `STATUS.md`.

Read the relevant benchmark specifications and safety invariants before implementation.

---

## Milestone 1 — Preserve Subtitle-Track Identity

**Priority: P1**

### Problem

In `benchmarks/bench/corrupt.py`, `prepare_case()` currently assigns:

`CaseManifest.track_id = source_track_path.stem`

However, the source registry identifies subtitle tracks using the user-supplied identifier.

For example:

```text
Registered:
  main=sidecar:episode.ass

Requested:
  --track-id main

Stored in case manifest:
  track_id = episode
```

This creates inconsistencies between the source registry and case manifests.

Consequences include incorrect subtitle-language resolution, incorrect source-track lookup, and incomplete fingerprint protection.

The existing basename-alias workaround doesn't fully resolve the underlying issue.

### Required changes

1. Pass the explicitly registered track ID to `prepare_case()`.
2. Preserve that identifier throughout the benchmark pipeline.
3. Use it consistently for subtitle-language lookup, source fingerprints, gold annotations, and candidate identity.
4. Remove unnecessary basename aliases.
5. Handle existing case manifests deliberately rather than silently reinterpreting their identities.

### Required regression tests

Register two subtitle tracks with different IDs but identical filenames in different directories.

Verify that their case manifests preserve the correct IDs and their source identities remain distinct.

Also test changing a registered subtitle source while retaining the same media and audio. Previously generated candidate results must be invalidated rather than silently reused.

### Acceptance

Every prepared case unambiguously identifies the subtitle track selected during registration.

---

## Milestone 2 — Correct Cross-Language Timing Ambiguity

**Priority: P1**

### Problem

The previous timing-validation correction introduced a distinction between matching speech inside the proposed subtitle interval and matching speech in surrounding padding.

The same-language validator checks for matching dialogue in both locations and abstains when the occurrence is ambiguous.

**The cross-language path doesn't perform the equivalent ambiguity check.**

In `benchmarks/bench/validator.py`, the cross-language branch sends the overlapping segment text to the semantic verifier.

If the verifier returns `match`, the validator treats the timing correspondence as verified.

However, the same utterance might also appear in the surrounding padding.

### Example

English subtitle:

> I will protect this city.

Japanese dialogue:

* 00:10 — `この街は私が守る`
* 00:12 — `この街は私が守る`

The subtitle is proposed for the first occurrence.

If both occurrences appear in the sampled window, the validator must recognize that the repeated dialogue creates ambiguity rather than assuming the first match establishes the intended correspondence.

### Required changes

1. Evaluate whether matching original-language dialogue occurs both inside the proposed interval and in the padding.
2. Use bounded additional semantic verification when necessary.
3. Abstain when multiple occurrences cannot be distinguished.
4. Preserve automatic acceptance for genuinely unambiguous matches.
5. Do not reject valid translations merely because their words differ from the source-language transcript.

Also review cases where an ASR segment spans both the proposed interval and its padding.

A broad segment containing several utterances must not automatically establish the precise timing of one particular utterance.

### Required regression tests

Cover correctly positioned translated dialogue, matching dialogue only in padding, repeated matching dialogue both inside and outside the proposed interval, unrelated dialogue in padding, and an overly broad ASR segment crossing the interval boundary.

### Acceptance

Cross-language timing validation requires unambiguous evidence that the matching utterance occurred at the proposed time.

---

## Milestone 3 — Distinguish Local Repairs from Reversible Release Offsets

**Priority: P1**

### Problem

The previous discontinuity-scoring correction identifies local cue adjustments by detecting offset sequences of the form:

```text
A → B → A
```

This works when a single subtitle has an incorrect timestamp.

However, the implementation does not adequately distinguish a short isolated correction from a genuine release-specific offset region.

For example:

```text
Cues 001–030:    Offset  0s
Cues 031–230:    Offset -2s
Cues 231–260:    Offset  0s
```

This represents two potentially genuine release discontinuities affecting a 200-cue region.

The current scoring logic can classify the entire middle section as a local adjustment because its offset eventually returns to the original value.

Both genuine discontinuities are then excluded from detection scoring.

### Required changes

1. Distinguish short local corrections from sustained offset regions.
2. Consider cue count, temporal duration, and supporting neighboring anchors.
3. Do not classify a region as local solely because its offset eventually returns to a previous value.
4. Preserve the existing gap-aware breakpoint matching behavior.
5. Represent inherently ambiguous short regions conservatively.
6. Continue measuring actual timing recovery independently from inferred release-breakpoint classification.

Ground-truth annotations may be used by the scorer to evaluate correctness, but must never leak into ordinary algorithm candidates.

### Required regression tests

**Test A — Isolated error:** One cue incorrectly shifted and perfectly repaired. Expected: local adjustment, no false release discontinuities.

**Test B — Genuine reversible offset:** A long middle section with a different offset and two real release discontinuities. Expected: both discontinuities recognized.

**Test C — Spurious regional shift:** A candidate introduces a sustained A→B→A shift into previously correct subtitles. Expected: harmful correction appropriately penalized.

**Test D — Sparse dialogue:** Preserve the previously corrected gap-aware scoring behavior.

### Acceptance

A perfectly repaired long release-specific region must not lose discontinuity-detection credit merely because its offset eventually returns to the original value.

---

## Final Verification

After implementation:

1. Run focused regression tests for each finding.
2. Run the existing benchmark test suite and configured Ruff checks.
3. Inspect the complete diff.
4. Perform a distinct read-only adversarial review.
5. Revalidate candidate fingerprints and regenerate affected synthetic benchmark artifacts where necessary.
6. Update benchmark findings using only genuinely executed measurements.

Keep testing proportional to the affected behavior. Avoid adding unnecessary infrastructure or large numbers of redundant tests.

### Safety requirements

Original media must remain read-only.

All private episodes, subtitle files, extracted audio, transcripts, annotations, generated cases, and benchmark results must remain Git-ignored.

Preserve the existing `benchmarks/private/` protection.

Do not push, publish, deploy, or begin production-media modification.

### Completion requirements

Report the changed files, actual test commands and results, remaining limitations, and the final review findings.

Do not claim G0/G1 success without real-media validation.

**After these corrections, the next milestone should be G0/G1 real-episode synchronization benchmarking using known-good Japanese and Mandarin episodes.**
