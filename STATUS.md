# STATUS — execution ledger (Qwen second-remediation assignment)

**Plan:** `PLAN.md` (Second code review and Qwen remediation handoff, 2026-10-14)
**Approved PLAN.md SHA-256:** `10977f0327a8287493c2594075c2382f92b04eed356cf3e9a5cea265dfbd2f33` — recorded 2026-10-14 at ledger initialization for this plan version. `PLAN.md` is immutable during execution; progress is recorded only here. (Plan lines 3–4 contain author Markdown hard-breaks flagged by `git diff --check`; left untouched as authored plan content.)
**Branch/HEAD at init:** `main` @ `bdb937fc4a0d846920a2072724975cb88feecc49` (the reviewed commit; prior B0/B1 correction work landed there). Working tree at init contained user-authored uncommitted `PLAN.md` (new assignment version replacing the B0+B1 plan) and an emptied `STATUS.md`; ledger reinitialized by the orchestrator for this assignment.
**Ledger initialized:** 2026-10-14 by top-level orchestrator implementing the authorized remediation brief (Milestones M1–M4 per plan).

## Baseline (observed 2026-10-14, this session, at `bdb937f`)

- `python -m pytest benchmarks\tests -q` → **151 passed** (independently rerun at init, not just inherited)
- `ruff check .` → clean; `ruff format --check .` → 82 files already formatted
- Tools: Python 3.14.0, ffmpeg 2023-02-22-git-d5cc7acff1 full build (gyan.dev) present. No ASR/semantic endpoint configured → `b1-va` integration boundary only.

## Milestones

| Slice | State | Evidence |
| --- | --- | --- |
| M1 Validity before real runs (F01 audio-map, F02 gap-aware scoring, F03 language routing, F04 provenance invalidation) | **in progress** | F01–F03 accepted (see records); F04 pending |
| M2 Data-safety holes (F05 private registration + custom-root ignores) | **pending** | — |
| M3 Harden ambiguities (F06 duplicate-text identity, F07 verifier ASR gate, F08 path resolution) | **pending** | — |
| M4 Verify (targeted+full suite, lint, adversarial review, findings/ledger evidence) | **pending** | — |

## M1 progress records

- **F01 accepted (2026-10-14, delegated implement + orchestrator re-verify):** `validate_proposal` no longer accepts a source-container stream map; windows extract stream 0 of the already-decoded `reference.wav` (validator.py docstring contract; passing `audio_stream` is now TypeError). `cmd_run` b1-va `run.json` records selected-audio provenance (`audio_stream` + source `media_sha256`). Renamed test `test_validate_proposal_windows_use_reference_wav_stream_zero` (old mocked `0:a:1` threading assertion removed); new real-ffmpeg integration test `test_targeted_asr_windows_decode_selected_audio_real_ffmpeg`: 2-audio MKV registered `--audio index:1`, `reference.wav` byte-equals direct `0:a:1` decode, all `asr_<cid>.wav` non-empty with no `asr_errors.log`, windows correlate >0.99 with 880 Hz selected-stream decodes and <0.2 with 440 Hz unselected; ≥5 overlapping windows checked. Test-side note (P3, accepted): byte-exact MKV-window vs pre-resampled WAV-window equality is mechanically impossible (ffmpeg seekpoint/packet framing; measured 24-sample lag) — identity proven via full-decode byte equality + window dominant-frequency/correlation. Orchestrator-observed: `pytest benchmarks\tests\test_stream_selection.py -q` → 13 passed; full suite **152 passed**; `ruff check` clean; `ruff format --check` clean (82 files); diff inspected line-by-line.
- **F02 accepted (2026-10-14, delegated implement + orchestrator re-verify):** scoring.py module docstring + matching rewritten: implied break from cue-anchor step (a,b] credits via bracketing interval `(onset(a), onset(b)]`, sub-divided by candidate-proposed region boundaries strictly inside the gap (no trailing claim past last proposed boundary); 1 tb inside → matched with `bracket_start_us`/`bracket_end_us`/`bracket_width_us` localization + secondary `precise_residual_us`/`precise_within_tol` (coexists, does not gate); 0 → false positive; ≥2 → ambiguous (`ambiguous_breakpoints`/`ambiguous_true_breakpoints`, no auto-credit, never silent). One-to-one holds structurally (disjoint left-open/right-closed partition). Additive fields, schema stays v2, no renames; report renders localization line + ambiguous count. Perfect inverse of **committed** Fx00-S03 (tb 45.12 s, gap to 48.00 s) → 1/1 matched, 0 FP (bracket 45.00–48.00, precise_within_tol False) — no longer penalized for the 2.88 s gap; multi-jump 2/2 one-to-one; sparse 39 s bracket credited; ambiguous interval test (0 matched, 0 FP, amb 1/true 2); no-op zero-credit + extra-jump FP + harmful/worsened assertions untouched. Orchestrator-observed: focused `-k "scor"` → 22 passed; full suite **157 passed**; ruff clean ×2; diff inspected.

- **F03 accepted (2026-10-14, delegated implement + orchestrator re-verify):** routing now identity-authoritative. `validator.py`: broad script classes (Hangul, Cyrillic, Greek, Arabic, Devanagari, Kana/Han/Latin), `normalize_language` (ISO 639-2/B↔639-1, und/mul sentinels→None), `is_cross_language(sub, tr, language, subtitle_language)` — known pair ⇒ cross exactly when identities differ; unknown ⇒ script-contrast/transliteration fallback (script never sole gate). `validate_proposal(subtitle_language="und")`: known+equal → lexical accept/contradiction-reject (reject reachable only via verified same-language lexical or verifier `no_match`); known+differ → verifier-only (match/no_match/unknown→accept/reject/abstain); unknown+low overlap → verifier if configured else **abstain, never reject** (`identity_unknown_abstentions` note counter); verifier receives resolved hints (never hardcoded "und"). `cli.py`: `source add --subtitle-language track=<lang>` + MKV ffprobe tag auto-capture → additive registry field `subtitle_languages` (sidecar stem alias); `run --subtitle-language` + audio fallback to `audio_selected.language`; both identities threaded to validator. `asr.py` MockSemanticVerifier records hints (test instrumentation). Tests: ko/ru→en param (match accept/no_match reject/no-verifier abstain-not-reject), fr→en both-Latin never lexical-rejects, unverified-identity zero-reject guard, ja/zh + romanized preserved, en/en accept + en/en verified contradiction reject, real-hint assertion; registration capture tests. Orchestrator-observed: full suite **171 passed** (157+14); `test_semantic_verification.py` 37 passed; ruff clean ×2; `git diff --check` clean; diff inspected. Residuals accepted (P3): transliterated transcript with language und/en handled safely via abstain path (documented); sidecar stem aliasing ambiguity (benchmark-registry scope note for eventual app contracts).

## Standing constraints

- No B2–B5 work; no production application infrastructure.
- `PLAN.md` immutable; no Git pushes/publishing/production/media-library writes without explicit authorization; local commits by orchestrator after accepted slices.
- G0/G1 remain **unverified/pending** — real known-good episodes E01/E02 not supplied; no gate claims; findings updated only with genuinely executed measurements.
- Read-only reference media; corruptions only in designated scratch space; no private data tracked.

## Next action

M1 slice F04 (case/run provenance fingerprint staleness): bind proposal/run/acceptance/scoring/cache to a versioned fingerprint of the actual input case + selected source audio + candidate/tool config; refuse stale reuse on `score`/`b1-va` paths; verify `reference.wav` integrity against recorded checksum; acceptance = seed-change, audio-selection-change, and tampered-WAV refusal tests.
