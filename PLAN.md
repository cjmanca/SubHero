# SubHero — Third review and bounded Qwen remediation handoff

**Repository:** https://github.com/cjmanca/SubHero  
**Reviewed branch/HEAD:** `main` / `d4da5d6698497c5f1ecedfa60b1f9f068777b43e` (2026-10-14)  
**Comparison baseline:** `bdb937fc4a0d846920a2072724975cb88feecc49`  
**Review method:** Read-only GitHub source review of the 13 intervening commits, relevant benchmark modules, tests, and project ledger. The reviewer could not clone the repository in the execution environment and **did not run its actual test suite, FFmpeg benchmark matrix, or a live inference endpoint**. The project's ledger reports 222 passing tests and clean Ruff checks; that is project-reported evidence, not an independently executed check. A minimal reproduction of the isolated-cue discontinuity-counting issue was run independently against the code's documented formula.

## Disposition

The previous remediation has substantially addressed its requested fixes: private media have a Git-ignored home, audio streams are explicitly selected, cross-language comparisons are routed to semantic verification, candidate output mapping is more conservative, and the prior gap-at-breakpoint scoring bug has been addressed. **Do not begin evidence-based G1 algorithm selection yet.** Four remaining benchmark-validity defects can distort the results, followed by three narrower reporting/evidence problems. This is a **corrective assignment only**, not authorization to develop B2–B5 or the production application.

Follow `AGENTS.md` and `ORCHESTRATION.md`. Use this as a new, separately approved bounded plan; **do not silently edit the previous frozen `PLAN.md`** or mark work accepted before checks run. Only the main orchestrator owns plan/version approval and `STATUS.md`. Preserve private media and synthetic fixture evidence.

## Blocking findings

### F01 — P1: A B1-VA acceptance is not invalidated when its base proposal changes

**Source:** `benchmarks/bench/cli.py` `_acceptance_binding_problem()` (~446–530), `cmd_run()` (~1020–1105), `cmd_score()` (~1108–1215); `benchmarks/bench/fingerprint.py` (~26–73).

`b1-va/run.json` records `validated_candidate_id` and `base_proposal_sha256`, but `_acceptance_binding_problem()` checks only its own acceptance hash and the *name* of the validated base arm. It does **not** verify the current base-arm proposal's checksum, base run generation/fingerprint, or the verifier/ASR configuration that produced the acceptance. The B1-VA `input_fingerprint` is calculated with `tool_versions={}` and has no dependency on base proposal bytes, CLI sample seed, language hints, model identity, verifier choice, or prompt/settings. As a result:

1. Run a base candidate and B1-VA on a case.
2. Rerun that base candidate with different candidate settings or results, keeping the case unchanged.
3. Score `b1-va` without rerunning the validator. The old acceptance can still pass the own-run hash and identity checks and be scored as if it validated the new proposal.

Similarly, changing `--base-candidate`, `--seed`, `--language`, `--subtitle-language`, or local ASR/semantic models can leave a current-looking yet obsolete acceptance artifact. This defeats the purpose of the previous stale-result remediation.

**Required fix:** Make the accepted-result identity depend on the exact validated base **run and proposal**, including hashes, and on the validation input configuration (sampling seed, resolved language identities, ASR/verifier model IDs/revisions/settings; no credentials). At `score` and `report`, reject or clearly exclude an acceptance that no longer matches the current base. Don't compare only the base candidate *name*. On a base rerun, either proactively invalidate downstream artifacts or enforce the dependency check at read time.

**Focused regressions:** base result A → validate → base result B (same case) → B1-VA `score` refuses; unchanged base continues to score; different validation seed/model/language cannot be mislabeled as the same experiment. A deletion of stale `score.json` must not remove legitimate current results.

### F02 — P1: The input fingerprint omits ground truth and oracle input material

**Source:** `benchmarks/bench/fingerprint.py` `fingerprint_payload()` (~26–59); `benchmarks/bench/cli.py` `cmd_score()` (~1108–1215).

The declared fingerprint contract says it binds the injected ground truth to a case generation, but its `case` payload omits `original_times_us`, `injected_cue_deltas`, `expected_inverse`, `transform`, and `grid_us`/format; it also omits oracle gold-classification **content** and subtitle-source identity. These inputs can change the score or oracle anchor selection without changing the fingerprint. For example, edit an original onset in a private `.case.json` but leave the seed/params/subtitle SHA unchanged: the same `input_fingerprint` still matches, while the apparent timing-error result changes. Likewise, changing gold cue labels can change a `b1-pxo-*` candidate's behavior without invalidating its cached proposal.

**Required fix:** Version the fingerprint contract and bind the **canonical semantic case inputs**, actual ground-truth annotation revision/hash, selected subtitle input identity, and any oracle-only labels by content hash. Don't include mutable output locations or secrets. Ensure the binding is checked consistently in `run`, `score`, B1-VA dependencies, and `report`. Historical score rows with old fingerprints must not be silently mixed into new comparisons.

**Focused regressions:** modify a private case's gold timing or injected deltas while keeping its corrupted subtitle bytes unchanged → stale scores rejected; modify the oracle cue classification file → its dependent arm must rerun; a genuine unchanged case remains cacheable.

### F03 — P1: Targeted semantic verification does not prove *where* matching speech occurs

**Source:** `benchmarks/bench/validator.py` `PAD_US` (~51), `validate_proposal()` (~332–570), especially audio extraction (~471–477), and verifier verdict acceptance (~418–464).

The validator extracts the **entire proposed cue interval plus 1.5 s on each side**, transcribes the whole window into one text string, then asks whether the subtitle matches that transcript. There is no word/utterance timestamp, speaker/segment association, or evidence that the matching words occurred **inside the proposed subtitle interval** rather than in the padding. With close adjacent lines or repeated dialogue, a wrongly shifted cue can therefore be accepted because its actual line is *nearby*, even if not spoken when proposed. Multiple matching samples can all share this systematic error. This contradicts the benchmark's requirement to verify the *specific timed utterance*, not just its presence nearby.

**Required fix:** Distinguish `semantic_content_present_in_window` from `timing_correspondence_verified`. Only automatically accept a synchronization region where time-local evidence connects the matching utterance to the proposed interval, with a documented tolerance. Evaluate whether the targeted ASR backend provides usable segment timestamps or whether a bounded aligner can be used; if not, abstain on ambiguous multi-utterance windows rather than promoting a text-only match to timing proof. Keep this a B1-targeted experiment, not an implementation of the full B2 ASR pipeline.

**Focused regressions:** two distinct adjacent dialogue lines; repeat one line in the padding but outside the proposed interval; wrong shift whose padded transcript still contains the subtitle text. The validator must not accept solely because an ASR transcript of the enlarged window contains that text. Include a correctly localized positive control.

### F04 — P1: A perfect isolated-cue repair scores as false *release* discontinuities

**Source:** `benchmarks/bench/scoring.py` `score_case()` (~200–295). **Scenario:** `S04` in `benchmarks/bench/corrupt.py`.

`score_case()` infers every change in adjacent cues' *applied corrections* to be a candidate release discontinuity. For a perfectly corrected S04 case with one isolated cue shifted by +2 s in the corrupted source, the ideal correction deltas are `[0, -2 s, 0]`. This produces **two** inferred breakpoints from the scorer, even though `S04` has **zero** release-edit breakpoints. The scorer records two false-positive discontinuities for a correct local repair. The result is an invalid comparison between local cue repair and global/piecewise timeline mapping. The current tests cover the S04 *no-op* case, not the perfect isolated repair.

**Required fix:** Separate *local isolated cue corrections* from sustained timeline-offset change points in the discontinuity metric. Use stable support on each side, or classify a short transient-and-reversal as a local correction with an explicit `local_cue_adjustments` measure. Preserve proper penalties for real spurious **regional** discontinuities, and retain the prior gap-aware and one-to-one breakpoint credit behavior.

**Focused regressions:** a perfect S04 isolated-cue repair has zero release-break false positives and correct cue-repair credit; a spurious lasting step in S00 has a false-positive release breakpoint; a correct S03 step across a cue-free gap keeps its credit.

## Additional issues to address within this bounded correction

### F05 — P2: `report` can present stale results when current case/source evidence is missing

**Source:** `benchmarks/bench/cli.py` `cmd_report()` (~1217–1272) and `benchmarks/bench/reporting.py` `build_report()` (~14–100).

`cmd_report` explicitly skips recomputing the current fingerprint when the case manifest or registered source cannot be loaded, and calls `build_report` anyway. A self-consistent old `run.json`/`score.json` pair can consequently appear in `report --case OLD` despite missing present-day evidence. This is a **fail-open** path in a benchmark that otherwise refuses to score unverifiable results.

**Fix/check:** If current case/source identity cannot be established, refuse to render scored rows or explicitly label them unverified historical results in a separate, non-comparative section. Do not silently treat them as current. Test deletion/invalidity of source registry and case manifest after a valid score pair.

### F06 — P2: Proposed corrections are reported as already “accepted” without any validator

**Source:** `benchmarks/bench/scoring.py` (~120–125, ~177–197, output `counts`) and `benchmarks/bench/reporting.py` (~115–151).

When no `AcceptanceRecord` is supplied, `final_times` defaults to the raw proposed times. Hence a tool-only ffsubsync/ALASS result can have `accepted_nonzero` and `harmful_accepted` counts even though no automatic acceptance decision took place. Scoring hypothetical *blind application* is useful, but the label “accepted” implies safety-gated authorization that did not happen.

**Fix/check:** Retain counterfactual raw-proposal/hypothetical-apply comparisons, but display them under explicit names such as `if_blindly_applied` or `unguarded_proposal`, separately from B1-VA verified accepted changes. Document whether `final` means “candidate output” or “actual accepted output” per arm. Add one focused tool-only result test and one B1-VA result test.

### F07 — P2: Semantic-verifier time is charged as ASR time

**Source:** `benchmarks/bench/validator.py` `run_verifier()` (~418–465), specifically `asr_seconds += sv.seconds` (~435); `benchmarks/bench/cli.py` B1-VA `run.json` (~1070–1106).

The validator adds semantic-verifier inference duration into `asr_seconds`, while `asr_calls` still counts only transcription calls. This inflates the reported ASR runtime and prevents fair component-cost comparisons.

**Fix/check:** Record ASR and semantic-verification wall time/call counts separately, and optionally a combined end-to-end inference time. Keep existing result fields backward-readable and label the revised metrics accurately. Test with fake transcriber and verifier returning known distinct durations.

## Bounded remediation and acceptance sequence

1. **Validity/provenance:** F01 and F02 together. Choose one versioned binding contract, not several competing cache mechanisms. Verify real read-time invalidation and clean reruns; avoid a new database.
2. **Temporal verification:** F03. Establish honest `match-at-time` versus `text-found-near-time` evidence. Do not add a full ASR/forced-aligner architecture just for a benchmark. If timing evidence is unavailable, abstention is the correct measured outcome.
3. **Scoring/reporting:** F04–F07. Keep old measurement formats explicitly legacy or migrate them deliberately; do not recompute historical reports silently. Make terminology of candidate proposals versus accepted corrections unambiguous.
4. **Review/verification:** Add **only focused tests** for each reproduced failure; run `python -m pytest benchmarks/tests -q`, `ruff check benchmarks`, `ruff format --check benchmarks`, and `git diff --check`. Independently review the diff for source-media safety, private artifacts, score correctness, and stale-output protection. Keep `Fx00` committed as the redistributable *plumbing* fixture; do not claim real-media efficacy from its tone-burst synthetic audio. Use genuine tool/model runs for measured claims.

### Required final handoff

Report: changed paths; exact checks run and results; a small reproducible before/after example for each blocking finding; any limitations; whether old runs must be discarded/recreated; one next action. Update the existing benchmark findings and experiment registry only with observed evidence. Preserve the previous immutable plan and the orchestrator-owned status policy; no pushes, production media writes, or private episode publication.

**G0/G1 remain pending real known-good episodes.** After these fixes, register E01 Japanese ASS and E02 Mandarin with the selected original-language audio from `benchmarks/private/` (ignored except its README) or outside the repo via read-only mounts, verify the clean timing controls, and then execute the measured synchronization matrix. No production thresholds or algorithm winner should be declared before that.
