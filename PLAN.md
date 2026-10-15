# SubHero — Fifth Review Remediation

**Repository:** `cjmanca/SubHero`
**Reviewed commit:** `99798019487b045b66962fa9a2131991dbc527b8`

## Assignment

Correct the remaining benchmark-report verification and discontinuity-classification defects.

This is a bounded remediation assignment. Do not expand into additional application functionality, B2–B5 benchmarks, or speculative infrastructure.

The previous remediation is substantially complete. Preserve existing fixes, safety controls, and benchmark behavior.

Follow `AGENTS.md` and `ORCHESTRATION.md`. Respect the approved plan's immutability and the orchestrator's ownership of the execution ledger.

## Milestone 1 — Verify Actual Input Files Before Reporting Results

**Severity: P1**

### Problem

Relevant code:

* `benchmarks/bench/cli.py`
* `_case_evidence_missing()`
* `cmd_report()`
* `_verify_sources()`

The harness correctly verifies media, subtitle, and generated case fingerprints before running or scoring candidates.

However, report generation does not perform the equivalent verification.

`_case_evidence_missing()` checks that the case manifest and registered source record exist and have coherent metadata. It does not verify that the referenced files still exist or match their recorded hashes.

`cmd_report()` then calculates the current generation fingerprint using stored registry metadata.

This allows an existing run/score pair to remain apparently current even when its underlying source files have changed.

### Reproduction

1. Register the synthetic Fx00 source.
2. Prepare an S00 case.
3. Run and score the no-op candidate.
4. Generate a report confirming the candidate appears in the comparative results.
5. Modify or remove the generated corrupted subtitle file without updating its manifest.
6. Generate the report again.

The previously scored result can still appear in the comparative section because report generation does not perform the source-integrity checks used by `run` and `score`.

Repeat using a modified or missing registered media file or subtitle sidecar.

### Required correction

Reuse the existing source-integrity verification rather than introducing another validation framework.

Before including a case in current comparative results, verify:

* The registered media file exists and matches its recorded fingerprint.
* Registered sidecars still match their fingerprints.
* The generated case input matches the case manifest.
* Case and registered-track identities remain coherent.

When verification fails, exclude the affected results from current comparative tables.

Historical results may remain accessible under the existing explicitly unverified historical-results section.

Avoid repeatedly hashing the same full episode unnecessarily within one report generation.

### Acceptance criteria

* A valid unchanged case continues to report normally.
* Modified source media invalidates current comparative results.
* Missing source media invalidates current comparative results.
* Modified sidecars invalidate current comparative results.
* Modified generated case inputs invalidate current comparative results.
* Restoring the original files restores eligibility without requiring unnecessary candidate reruns.
* No original source files are modified by verification.

Implement only the focused tests needed for these behaviors.

---

## Milestone 2 — Correct Discontinuity Classification Around Local Adjustments

**Severity: P1/P2**

Relevant code:

`benchmarks/bench/scoring.py`

The new classification correctly distinguishes ordinary isolated corrections from long reversible release-offset regions.

However, two edge cases remain.

### Finding A — Sustained Region Hidden by Adjacent Transient Runs

**Severity: P1**

Consider these proposed correction offsets:

```text
Cues 001–010:    0s
Cue  011:       -2s
Cue  012:        0s
Cues 013–037:   -2s
```

Assume the reference subtitle was already correctly synchronized.

The first `-2s` correction is isolated. The last `-2s` block is sustained across 25 cues.

The expected evaluation is:

* Detect an isolated local correction.
* Recognize that the final 25-cue region has a sustained offset.
* Penalize the harmful timing changes.
* Count the sustained regional discontinuity as a false-positive release change.

The current algorithm marks the middle short runs as transient.

Its breakpoint loop suppresses a boundary whenever **either adjacent run** is transient:

`if transient[ra] or transient[rb]: continue`

Consequently, the boundary entering the long final region is also suppressed.

The resulting detection count is zero despite the substantial sustained correction.

### Required correction

Change boundary suppression so it applies only to boundaries genuinely attributable to local correction excursions.

A neighboring transient run must not automatically suppress the boundary of a sustained offset region.

Maintain the distinction between:

* Local cue adjustments.
* Ambiguous short offset regions.
* Sustained regional offsets.

Do not use the scenario's ground-truth breakpoint positions to classify candidate corrections. Ground truth remains exclusively for scoring.

### Regression test

Use the exact correction sequence above.

Verify that the sustained final block contributes a release-discontinuity claim and is penalized when the reference track was already correctly synchronized.

Preserve the existing isolated-cue and reversible-region tests.

### Finding B — Isolated Correction at a Track Boundary

**Severity: P2**

Consider an S04 corruption affecting only the first subtitle cue.

A perfect repair might produce correction offsets:

```text
Cue 001:       -2s
Cues 002–021:   0s
```

There is no release discontinuity.

Nevertheless, the scoring algorithm sees an offset step after the first cue.

Because the first run has no preceding flanking region, it cannot satisfy the current transient-classification rule.

It is therefore treated as a sustained release change and can receive a false-positive breakpoint penalty despite perfectly repairing the isolated cue.

The same problem occurs with an isolated correction affecting the final cue.

### Required correction

Handle track-boundary local corrections conservatively.

A one-cue edge adjustment is inherently ambiguous: it may represent an isolated timing error or a release-specific offset affecting the track boundary.

Avoid automatically declaring it a false release discontinuity solely because it lacks a preceding or following anchor.

Record that ambiguity explicitly where necessary.

Continue scoring the actual timing repair and any harm to previously correct cues independently.

### Regression tests

Test an isolated correction affecting:

* The first subtitle cue.
* The final subtitle cue.
* An interior subtitle cue.

Verify that each receives correct timing-repair credit.

An otherwise perfect isolated repair must not receive an unjustified false-release-discontinuity penalty.

Also preserve the existing test where a genuinely sustained erroneous offset begins at the first cue.

---

## Final Verification

After both milestones:

1. Run focused regression tests for each reproduced issue.
2. Run the existing benchmark suite.
3. Run Ruff lint and formatting checks.
4. Inspect the complete diff.
5. Perform one distinct read-only adversarial review.
6. Regenerate affected synthetic results if scoring semantics changed.
7. Update benchmark findings using only observed measurements.

Do not introduce another broad hardening cycle unless review discovers a concrete P0/P1 or acceptance-blocking P2 defect.

Avoid additional speculative abstractions or tests for implementation details unrelated to these failures.

## Safety Requirements

Preserve all existing source-media protections.

The following must remain excluded from Git:

* Private reference episodes and sidecars.
* Gold annotations and transcripts.
* Extracted audio and media derivatives.
* Private case manifests.
* Model outputs and generated benchmark results.

Maintain the existing `benchmarks/private/` protections and the committed redistributable Fx00 fixtures.

Do not modify original media.

Do not push, publish, deploy, or perform production-media writes without explicit authorization.

## Completion

Provide:

* Changed paths.
* Exact test commands and results.
* Evidence that each reported defect is corrected.
* Any unresolved findings.
* Confirmation that source files remain immutable.
* One concrete next action.

Keep G0/G1 marked pending until genuine reference episodes have been verified.

**Next action after successful remediation: Begin G0/G1 real-media synchronization benchmarking using user-provided known-good Japanese and Mandarin episodes.**
