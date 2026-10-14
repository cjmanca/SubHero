# SubHero — second code review and Qwen remediation handoff

**Review target:** `cjmanca/SubHero`, branch `main`, commit `bdb937fc4a0d846920a2072724975cb88feecc49` (2026-10-14).  
**Comparison baseline:** `06f8ae660f4dbe397214fef3baa3257460ff9d6a`.  
**Review type:** Source-level review of the changes and benchmark contracts. Not a full execution of the repository test suite. I separately reproduced the FFmpeg audio-map failure using a one-stream WAV, and checked the committed S03 case's breakpoint timestamps arithmetically. The project's `STATUS.md` records **151 passing tests** and clean Ruff checks; these are project-reported, not independently rerun here.

## Overall disposition

**Changes substantially address the first audit, but G0/G1 real-media readiness is not yet established.** In particular, the existing source-selection tests prove that the selected audio was decoded, but miss that the targeted validator tries to select the same multi-audio stream *again* from the already single-stream WAV. There are also benchmark scoring, language-routing, reproducibility, and privacy edge cases that can lead to misleading results or accidentally tracked private data.

Fix the blocking items **before** using E01/E02 for benchmark conclusions. Do not implement B2–B5 or the production application as part of this handoff. Continue preserving `PLAN.md` immutability and leave G0/G1 explicitly unverified until real-media runs.

## Blocking findings (P1)

### F01 — Selected second audio stream breaks targeted ASR

**Location:** [`benchmarks/bench/cli.py` lines 545–601 and 641–719](https://github.com/cjmanca/SubHero/blob/bdb937fc4a0d846920a2072724975cb88feecc49/benchmarks/bench/cli.py#L545-L601); [`benchmarks/bench/validator.py` lines 237–244](https://github.com/cjmanca/SubHero/blob/bdb937fc4a0d846920a2072724975cb88feecc49/benchmarks/bench/validator.py#L237-L244).

`_get_reference_audio()` extracts the selected `0:a:<sidx>` into `reference.wav` (which has **only audio stream 0**), then `cmd_run()` passes that same stream selection along with `reference.wav` to `validate_proposal()`. The validator calls `extract_audio_window(reference.wav, ..., audio_stream="0:a:1")` when the registered original stream is `sidx:1`, and FFmpeg fails because the WAV has no second audio stream. ASR window failures are caught and turned into abstentions, so the benchmark may misleadingly report uncertain validation instead of explaining that the input-map plumbing is broken. A local one-stream-WAV check confirmed `-map 0:a:1` fails with “Stream map matches no streams.”

**Fix:** Adopt one clear contract: either (preferred) extract ASR windows from the **already selected** `reference.wav` using `0:a:0`/no map, or extract directly from the original container using the persisted selected stream. Do not mix these paths. Preserve source-audio identity in preprocessing/run metadata.

**Acceptance:** Integration test using a two-audio-stream MKV, with nonfirst (`sidx:1`) selected, invokes a *real FFmpeg extraction* on the exact validator input; confirms the expected selected audio and successful window extraction. Update the existing test that currently only asserts a mocked function received `audio_stream="0:a:1"` — that test was affirming the bug.

### F02 — A perfectly repaired breakpoint can be scored as missed and false-positive

**Location:** [`benchmarks/bench/scoring.py` lines 180–209](https://github.com/cjmanca/SubHero/blob/bdb937fc4a0d846920a2072724975cb88feecc49/benchmarks/bench/scoring.py#L180-L209); committed [`benchmarks/cases/Fx00-S03.case.json`](https://github.com/cjmanca/SubHero/blob/bdb937fc4a0d846920a2072724975cb88feecc49/benchmarks/cases/Fx00-S03.case.json).

The scoring rule places each detected correction step at the **next cue's original start**, then requires it to be within `--tol-break-us` (default 0.5 seconds) of the exact injected breakpoint. However, an injected breakpoint may be in a silent or subtitle-free gap. The committed S03 case has a true breakpoint at **45.12 s**, while its first post-breakpoint cue (`e0019`) begins at **48.00 s**, a **2.88 s** gap. Even an *exactly correct* repair that changes offsets at that cue is reported as an unmatched breakpoint and a false positive under the default tolerance. The existing hand-built perfect-repair tests put breakpoints *exactly* on cue onsets, so they do not cover this.

**Fix:** Score a breakpoint's identifiable **bracketing interval** between adjacent cue anchors, separately from any precise time-localization estimate. Credit a correct correction discontinuity when the known breakpoint is inside the uniquely matched interval; report localization uncertainty rather than inventing precision in speech-free spans. Enforce one-to-one matching so one proposed jump cannot receive multiple true-breakpoint credits. Retain a separate metric for unresolved residual discontinuities.

**Acceptance:** Add a test with a *perfect inverse repair of the committed* `Fx00-S03` case; detection must not be labeled false/missed solely because the injected boundary falls in a 2.88-second gap. Preserve no-op zero-detection credit and explicit additional-jump false positives. Exercise multiple jumps and sparse dialogue.

### F03 — Cross-language routing still rejects Korean/Russian and different Latin-script languages

**Location:** [`benchmarks/bench/validator.py` lines 31–95 and 262–297](https://github.com/cjmanca/SubHero/blob/bdb937fc4a0d846920a2072724975cb88feecc49/benchmarks/bench/validator.py#L31-L95).

The fix recognizes CJK ideographs/kana versus Latin and treats `ja`/`zh` source-language hints as a reason to use the multilingual verifier. It does **not** recognize Hangul or Cyrillic, or distinguish languages that share Latin script. Example: a Korean transcript `안녕하세요` against the English subtitle `Hello` has neither a Latin-majority nor a recognized `ja/zh` language rule; `is_cross_language(..., "ko")` returns false. With usable ASR confidence and little lexical overlap, the code **rejects** the timing proposal rather than invoking the configured semantic verifier/abstaining. Russian→English, French→English, and romanized source languages can fail similarly.

**Fix:** Route by **verified source and target language identity**, not primarily by script. Record/resolve the target subtitle language separately from the audio language; use the multilingual verifier when they differ. If language identity is unknown or the text is mixed, low lexical overlap is **not sufficient negative evidence**; verify semantically or abstain. Script detection can be a fallback signal, never the sole cross-language gate. Provide real language hints to the verifier instead of hardcoding subtitle language `"und"`.

**Acceptance:** Tests for Korean→English, Russian→English, French→English (both Latin), Japanese/Mandarin→English, romanized source-language outputs, and genuinely same-language cases; missing verifier must not turn correct translated subtitles into `no_match` rejects. Do not equate an LLM model-reported confidence with calibrated correctness.

### F04 — Stale candidate results are silently reusable against a different case

**Location:** [`benchmarks/bench/cli.py` lines 674–735, 741–790](https://github.com/cjmanca/SubHero/blob/bdb937fc4a0d846920a2072724975cb88feecc49/benchmarks/bench/cli.py#L674-L790).

`run` records `input_sha256` in `run.json`, but `score` does not check it. `score` reads an existing `<case>/<candidate>/proposal.json` regardless of whether it came from the **current generation of that case**. Regenerating the same `case_id` using a different seed or changing the selected source-audio configuration can therefore lead to scoring an old proposal against the new case without a warning. `b1-va` likewise reads any existing base proposal and does not establish that its run identity matches the current case/selected audio/model settings.

**Fix:** Bind proposal, run, acceptance, scoring, audio-selection, and cache identities to a versioned fingerprint of the *actual input case* and the *selected source media/audio stream* (and candidate/tool configuration where it matters). Refuse or explicitly mark stale results; do not quietly reuse them. Save/verifiably check output artifact checksums where useful. Ensure reference-audio cache is not reused solely on JSON metadata when the WAV file itself is corrupt or replaced.

**Acceptance:** Prepare/run case ID X with seed A; prepare X again with seed B; scoring or validator reuse **must refuse** until the candidate is rerun. Repeat with changed audio selection and tampered `reference.wav`. The expected outcomes are clear invalidation or re-extraction, not numerical scores on stale data.

### F05 — Private-data policy has two non-ignored in-repository escape paths

**Location:** [`.gitignore` benchmark rules](https://github.com/cjmanca/SubHero/blob/bdb937fc4a0d846920a2072724975cb88feecc49/.gitignore); [`benchmarks/bench/cli.py` lines 182–213, 295–334, 920–945](https://github.com/cjmanca/SubHero/blob/bdb937fc4a0d846920a2072724975cb88feecc49/benchmarks/bench/cli.py#L182-L213).

1. `source add --rights private-local` is currently allowed to register a file inside `benchmarks/fixtures/` — an intentionally **tracked/unignored** home. The rights check restricts *synthetic* rights to fixtures, but does not prevent *private* rights there. Private episode files placed there would be eligible for a normal `git add`.
2. A custom in-repository `--root` such as `benchmarks/custom-root/` is allowed. The CLI writes `custom-root/cases/sources.json`, `custom-root/private/`, `_scratch/`, and `results/`, but the `.gitignore` only protects corresponding directories under the **default** root. Custom-root private media and paths/manifests/results may become untracked, committable files.

**Fix:** For private registrations, permit only the canonical **ignored** `benchmarks/private/` path or paths outside the Git repository, not the tracked synthetic fixture home. Disallow a custom repository-local `--root` unless it is under a proven Git-ignored safe home, or enforce a correspondingly safe `.gitignore`/`git check-ignore` policy for every generated location. `benchmarks/fixtures/` should remain available only for explicitly declared, redistributable synthetic references. Maintain the existing `benchmarks/private/README.md` exception and avoid broad ignores that hide redistributable fixture code.

**Acceptance:** In a disposable git checkout, private-local registration from `benchmarks/fixtures/E01.mkv` is refused; `--root benchmarks/custom-root` either fails safely or its generated files are proven ignored with `git check-ignore -v` and absent from ordinary `git status`/`git add -A` candidates. Confirm normal `benchmarks/private/E01/` registration and committed Fx00 fixture workflows still work.

## Additional correctness findings (P2)

### F06 — Duplicate subtitle text can still bypass positional identity protection

**Location:** [`benchmarks/bench/adapters.py` lines 137–210](https://github.com/cjmanca/SubHero/blob/bdb937fc4a0d846920a2072724975cb88feecc49/benchmarks/bench/adapters.py#L137-L210).

The new identity check matches event count and **text at each position**, which detects many reorderings. But if two cues have identical normalized text (common for repeated anime dialogue), an external tool can swap their events/timestamps without any per-position text mismatch. The mapper then assigns the other's timing to each cue. Candidate tools already demonstrated event reordering on synthetic cases, making this a realistic ambiguity.

**Fix:** Require stable identity evidence for duplicate-normalized-text groups; where unavailable, mark those cues/regions unmapped rather than guessing. Consider mapping unique text first with verified order/monotonic constraints, but avoid an elaborate general matcher solely for this issue. Test a simulated sync tool swapping two identical-text cues: they must not both be accepted as correctly mapped without additional evidence.

### F07 — Cross-language verifier bypasses ASR reliability threshold

**Location:** [`benchmarks/bench/validator.py` lines 253–297](https://github.com/cjmanca/SubHero/blob/bdb937fc4a0d846920a2072724975cb88feecc49/benchmarks/bench/validator.py#L253-L297).

The same-language path checks `result.confidence >= MIN_CONFIDENCE`, but cross-language `sv.verdict == "match"` accepts even when the ASR transcript has low or missing confidence (`-1.0` is used as a fallback by the HTTP transcriber). A semantically matching model judgment over a hallucinated or unreliable transcript is not reliable timing evidence.

**Fix:** Use one consistent evidence/quality gate before automatic acceptance in all language paths. Missing diagnostics need not make every backend unusable: support model-specific *available* reliability signals, unknown/abstain when evidence is insufficient, and targeted additional sampling. Record ASR and semantic verifier evidence separately. Add a low-confidence-transcription + verifier-`match` regression test requiring abstention or further verification, not acceptance.

### F08 — Registered relative sidecar/gold paths depend on the later working directory

**Location:** [`benchmarks/bench/cli.py` lines 171–180, 353–375, 437–510](https://github.com/cjmanca/SubHero/blob/bdb937fc4a0d846920a2072724975cb88feecc49/benchmarks/bench/cli.py#L171-L180).

Registration checks user-given relative paths against the current working directory, but then stores `sidecar:benchmarks/...` and gold paths as relative strings. A later `run`, `case prepare`, or `score` invoked from a different working directory resolves them differently. This undermines the intended reproducibility and can lead to missing-input failures.

**Fix:** At registration, persist the canonical absolute path in the **ignored local registry**, or a clearly defined path relative to a stable root; never rely on the invoking shell's later CWD. Continue writing only redacted/relative identifiers into committed, redistributable manifests. Test registration from repo root followed by execution from a different CWD.

## Bounded remediation sequence for Qwen

1. **M1 — Protect validity before real runs:** F01 (validator audio map), F02 (gap-aware breakpoint scoring), F03 (language-aware semantic routing), F04 (case/run provenance invalidation). Give each one directly targeted regression tests. No broad new testing framework.
2. **M2 — Close data-safety holes:** F05, including a disposable-checkout `git add -A` safety test. Preserve the canonical private directory and legitimate synthetic fixtures.
3. **M3 — Harden ambiguities:** F06–F08. Keep abstention as the fallback when evidence is insufficient.
4. **M4 — Verify:** Run targeted tests, relevant existing full suite, lint/format checks, and a distinct read-only adversarial review. Report exact commands/outcomes, actual file changes, remaining findings, and one next action. Update `STATUS.md` and benchmark `findings.md` with only observed evidence; do not edit an approved frozen `PLAN.md` to report progress. Follow the project's existing orchestration/commit permissions.

## Completion gates

- G0 and G1 remain **pending** until real, manually verified episodes are supplied and the candidates are actually measured on them.
- No silent acceptance or scoring of stale, mis-mapped, or unverified results.
- No cross-language lexical-only rejection when the spoken and subtitle languages differ or cannot be proven equal.
- No private real-episode data is normally stageable from supported repository-local media/artifact paths; the default `benchmarks/private/` area remains safe.
- No original media file is edited. No publishing, pushing, remote repository mutation, or production integration without explicit authorization.

**After successful remediation:** Register and verify E01 Japanese ASS and E02 Mandarin references under `benchmarks/private/` (or outside the repository on read-only mounts), perform G0 reference checks, and then execute the controlled G1 synchronization matrix. Preserve an independent holdout episode/series; synthetic variants of one episode are not independent evidence.
