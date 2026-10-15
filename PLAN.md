# SubHero — Sixth Review Remediation

**Repository:** `cjmanca/SubHero`
**Reviewed commit:** `26d81a4bd5c3af77b5f7e87ab4cc2de53b334c7d`

## Objective

Correct two benchmark-scoring issues before using real-episode measurements to select
synchronization algorithms.

The fifth-review remediation is accepted in its targeted areas. Preserve the existing
functionality and safety protections.

Do not expand the application architecture or implement unrelated B2–B5 functionality.

Follow `AGENTS.md`, `ORCHESTRATION.md`, and the approved plan/ledger procedures.

## Milestone 1 — Correct End-Boundary Safety Metrics

**Priority: P1**

### Problem

`benchmarks/bench/scoring.py` records both subtitle onset and end errors but uses onset
errors exclusively for several aggregate counters.

Affected concepts: altered vs unaltered cues; successfully repaired cues; previously
correct cues made worse; harmful proposed corrections; harmful accepted corrections;
severe final timing errors. End-only defects are therefore underrepresented in the
primary safety metrics.

### Required correction

Maintain separate measurements for onset and end accuracy. Define whole-cue safety using
both boundaries. A cue should be considered:

* **Altered:** when either original boundary was corrupted beyond the declared tolerance.
* **Fully repaired:** when both boundaries have been restored within their applicable
  tolerances.
* **Worsened:** when a previously correct boundary becomes incorrect beyond tolerance.
* **Harmfully corrected:** when the proposed or accepted result makes either boundary
  materially worse than its corrupted baseline.
* **Severely mistimed:** when either boundary exceeds the declared severe-error tolerance.

Preserve detailed onset-only and end-only measurements so the two can still be analyzed
independently.

Do not change the existing release-discontinuity detector to infer release jumps from
isolated changes to subtitle display duration. Release-offset classification and
cue-boundary safety are separate measurements.

### Evaluation semantics

Preserve the distinction between: (1) proposed changes, (2) hypothetical blind
application, (3) validated automatically accepted changes.

For synthetic corruptions, compare against the recorded inverse timing transformation.

For future human-annotated reference cases, respect acceptable subtitle display intervals
rather than assuming that every subtitle should end exactly when speech ends.

### Required tests

**Test A — Clean subtitle, damaged end.** Original: 10–12 seconds. Proposal: 10–15
seconds. Expected: onset error remains zero; end error is three seconds; the proposal is
counted as harmful; the previously correct cue is counted as worsened; severe-error
accounting recognizes the damaged end boundary.

**Test B — End-only corruption repaired.** Original: 10–12 seconds. Corrupted: 10–15
seconds. Proposal: 10–12 seconds. Expected: cue counted as altered; cue counted as fully
repaired; no harmful correction.

**Test C — Partial repair.** Original: 10–12 seconds. Corrupted: 11–15 seconds. Proposal:
10–15 seconds. Expected: onset repaired; end remains incorrect; cue is not counted as
fully repaired.

**Test D — Existing behavior.** Verify ordinary global-offset recovery, unchanged S00
controls, and correctly repaired S03 discontinuities retain their intended measurements.

### Compatibility

Because this changes scoring semantics:

* Explicitly version the affected score definitions.
* Prevent old and new incompatible scores from appearing in the same comparative table.
* Regenerate affected scores and the committed synthetic report.
* Avoid rerunning expensive candidate algorithms if their existing proposal/run artifacts
  remain valid and only the scorer changed.

Do not introduce a new persistence framework.

---

## Milestone 2 — Correct Acceptance-Region Accounting

**Priority: P2**

### Problem

In `score_case()`, tool-only candidates can populate `counts.accepted_regions` despite
having no acceptance record.

### Required correction

Reserve acceptance terminology for validated decisions.

For an unvalidated candidate, report: number of proposed regions; number of regions with
proposed changes; no validated acceptance.

For B1-VA, report actual accepted, rejected, and abstained regions from its
`AcceptanceRecord`.

Use zero or an explicitly not-applicable value for accepted regions when no validation
occurred. Do not silently treat every proposed region as accepted.

Update report rendering only where the new distinction is relevant.

### Required tests

Verify that:

1. A tool-only synchronization candidate never claims validated acceptance.
2. A genuinely validated B1-VA result reports the actual accepted-region count.
3. A rejected or abstained B1-VA proposal reports no falsely accepted regions.

---

## Milestone 3 — Verification

Run focused tests for the two corrections. Then run:

```bash
python -m pytest -q
ruff check benchmarks
ruff format --check benchmarks
git diff --check
```

Inspect the changed code and perform one bounded read-only review of the affected scoring
contracts.

Regenerate the canonical Fx00 scoring report using genuinely executed calculations.

Record the changes in `docs/40-delivery/benchmarks/findings.md`.

Do not claim that synthetic tone-burst results establish actual synchronization quality.

Avoid expanding the test framework or introducing unrelated abstractions.

---

## Milestone 4 — Transition to G0 Real-Media Benchmarking

Once the scoring fixes pass, the next development phase is **G0: real-reference
validation**, followed by **G1: synchronization algorithm evaluation**.

Do not require another speculative hardening cycle before G0.

### Corpus locations

Use the existing ignored directory:

```text
benchmarks/
└── private/
    ├── E01/
    │   ├── episode.mkv
    │   └── reference.ass
    ├── E02/
    │   ├── episode.mkv
    │   └── reference.srt
    └── cases/
```

E01 should contain known-good Japanese anime with original Japanese audio and preferably
positioned ASS signs/karaoke. E02 should contain known-good Mandarin-language content with
English subtitles and preferably native-language subtitles. The user supplies the actual
media. Do not commit or upload any episode-related data.

### G0 work

When the episodes are available:

1. Register them with explicit source-audio and subtitle-track selection.
2. Verify the selected audio is the original language rather than a dub.
3. Verify reference subtitle timing manually at representative locations.
4. Identify dialogue, signs, karaoke, and non-speech events.
5. Prepare deterministic S00–S04/S06 variants.
6. Verify input files remain unchanged.
7. Preserve an independent episode or series as a future holdout.

### G1 work

Run the existing candidate matrix against real audio: no-op baseline; ffsubsync global;
ffsubsync piecewise; ALASS where available; dialogue-only proxy variants; targeted
ASR/semantic verification when local models are configured.

Compare the same cases and audio streams across candidates.

Report timing error distributions, harmful changes, clean-track regressions, false
discontinuities, unmapped regions, abstentions, and processing costs.

Do not use oracle-assisted diagnostic arms when ranking production candidates. Do not
declare an algorithm winner without real-media evidence.

### Expected handoff

Provide the verified test results and a concise statement of real-media readiness.

If E01/E02 are unavailable, stop at the external-input blocker rather than building
additional infrastructure merely to occupy the next milestone.

## Safety

All source media remain read-only. All private media, sidecars, derived audio,
annotations, transcripts, case manifests, and result artifacts must remain Git-ignored.
Do not place generated outputs in Plex-watched directories. No production-media writes or
remote publication without authorization.

## Completion

Provide: changed paths; exact test commands and results; evidence each reported defect is
corrected; unresolved findings; confirmation source files remain immutable; one concrete
next action.

**The next meaningful milestone is real-media G0/G1 evaluation, not another synthetic
infrastructure expansion.**
