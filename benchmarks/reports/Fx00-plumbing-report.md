# Benchmark comparison report

**Caveat:** synthetic-timing recovery measures recovery of injected errors only. It is not evidence
about real-speech synchronization, and it is not a production threshold. See denominators.
**Score-number provenance:** comparative rows are admitted only from a directory whose run.json passes the proposal-byte check; the row bullets' recorded input fingerprint and proposal hash are the audit anchors. Numbers fabricated *inside* a score.json that pairs with an admitted, byte-verified run record render as recorded — regenerate score.json with `score` rather than editing it.

dropped unbound score rows: 0 (scores with no fingerprint-matching run.json, current rows missing a proposal hash pair, structurally incomplete rows, and planted numbers are never rendered)
dropped stale-generation rows: 0 (schema-4 scores bound to a run.json whose recorded fingerprint differs from the current case generation are never rendered)
legacy schema-3 rows rendered separately: 0 (schema 3 drove the aggregate safety counters from onset errors only and counted every proposed region as an accepted region for unvalidated arms — sixth-review M1/M2 changed both semantics; kept in a labeled non-comparative section, never mixed into schema-4 comparisons)
legacy schema-2 rows rendered separately: 0 (schema 2 counted unguarded proposals as 'accepted' — pre-F06 semantics; kept in a labeled non-comparative section, never mixed into current comparisons)
dropped obsolete-acceptance rows: 0 (b1-va scores whose validated base run/proposal no longer matches the current base artifacts are never rendered; re-run the base arm and re-validate)
dropped tampered/removed proposal rows: 0 (run.json proposal_sha256 no longer matches proposal.json bytes on disk at report time; the run/score pair is never rendered comparably; re-run the arm)
unreadable artifacts skipped: 0 (run/score JSON that cannot be parsed, and score.json files with no pairing admitted run.json in the same directory, are reported here, never rendered as a number, and do not abort the rest of the report)
## Tool/model versions

- `ffsubsync`: ffsubsync 0.5.1

## Case `Fx00-S00` (scenario S00)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 4):** aggregate safety counts are WHOLE-CUE (sixth-review M1): `Repaired` requires BOTH boundaries within tolerance; `Worsened`/`Harmful`/denominator altered/unaltered fire on EITHER boundary; `Harmful` compares each boundary against its corrupted baseline. Onset-only and end-only detail (`repaired_onset/end_*`, `harmful_onset/end_*`, `severe_onset/end_*`, `*_unaltered_onset/end_*` flags and the `timing_errors_*_end_us` distribution) stays in score.json for independent analysis; the median/P90/P95 column is the ONSET axis by label. `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

| b1-fg | 1:1-order-preserving | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 0 ms / 0 ms | 0/0/0 (0) | 0/0 | 24/0/24 |
| b1-fp | 1:1-order-preserving | 24 | — | 24 | —/0 | —/0 | 0/0/— | 17 ms / 41 ms / 44 ms | 0/0/0 (0) | 0/0 | 24/0/24 |
| b1-n | noop | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 0 ms / 0 ms | 0/0/0 (0) | 0/0 | 24/0/24 |
| b1-px-fg | 1:1-order-preserving | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 0 ms / 0 ms | 0/0/0 (0) | 0/0 | 24/0/24 |
| b1-px-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/0 | 0/0/— | 6 ms / 38 ms / 41 ms | 0/0/0 (2) | 0/0 | 24/0/24 |
| b1-pxo-fg | 1:1-order-preserving | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 0 ms / 0 ms | 0/0/0 (0) | 0/0 | 24/0/24 |
| b1-pxo-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/0 | 0/0/— | 6 ms / 38 ms / 41 ms | 0/0/0 (2) | 0/0 | 24/0/24 |
| b1-va | not_run | 0 | 0 | — | 0/— | 0/— | 0/—/0 | 0 ms / 0 ms / 0 ms | 0/0/0 (0) | 0/0 | 24/0/24 |

- `b1-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-n` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-va` final timeline = accepted_output
- `b1-fg` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-n` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-px-fg` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-px-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-pxo-fg` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-pxo-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-va` regions: 1 proposed (0 with proposed changes); validated acceptance: 0 accepted / 0 rejected / 0 abstained (from the bound AcceptanceRecord)
- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 2 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 2 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · input 3beaf02482824d23… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · input 87a231f6fc8ed19b… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-fp`: 1:1-order-preserving · input 0a0bd04dc87dc23b… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.6s
- `b1-n`: noop · input e2e859cccff5f795… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 970ddfca157ad366… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-px-fp`: 1:1-order-preserving · input b4d89bd0ce0ce161… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.3s
- `b1-pxo-fg`: 1:1-order-preserving · input 62ce933e7fa988a8… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.2s
- `b1-pxo-fp`: 1:1-order-preserving · input b54d5418204dc14b… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.8s
- `b1-va`: not_run · input a27dfa926e03bf99… · validated base b1-px-fg @ run Fx00-S00-b1-px-fg-1792045048 fp 970ddfca157ad366… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S01` (scenario S01)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 4):** aggregate safety counts are WHOLE-CUE (sixth-review M1): `Repaired` requires BOTH boundaries within tolerance; `Worsened`/`Harmful`/denominator altered/unaltered fire on EITHER boundary; `Harmful` compares each boundary against its corrupted baseline. Onset-only and end-only detail (`repaired_onset/end_*`, `harmful_onset/end_*`, `severe_onset/end_*`, `*_unaltered_onset/end_*` flags and the `timing_errors_*_end_us` distribution) stays in score.json for independent analysis; the median/P90/P95 column is the ONSET axis by label. `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

| b1-fg | 1:1-order-preserving | 24 | — | 24 | —/24 | —/0 | 0/0/— | 0 ms / 0 ms / 0 ms | 0/0/0 (0) | 0/0 | 24/24/0 |
| b1-fp | 1:1-order-preserving | 24 | — | 24 | —/24 | —/0 | 0/0/— | 18 ms / 43 ms / 46 ms | 0/0/0 (0) | 0/0 | 24/24/0 |
| b1-n | noop | 0 | — | 0 | —/0 | —/0 | 0/0/— | 1900 ms / 1900 ms / 1900 ms | 0/0/0 (0) | 0/0 | 24/24/0 |
| b1-px-fg | 1:1-order-preserving | 15 | — | 15 | —/15 | —/0 | 0/0/— | 0 ms / 1900 ms / 1900 ms | 1/0/0 (14) | 0/0 | 24/24/0 |
| b1-px-fp | 1:1-order-preserving | 15 | — | 15 | —/15 | —/0 | 0/0/— | 37 ms / 1900 ms / 1900 ms | 11/0/10 (3) | 0/0 | 24/24/0 |
| b1-pxo-fg | 1:1-order-preserving | 15 | — | 15 | —/15 | —/0 | 0/0/— | 0 ms / 1900 ms / 1900 ms | 1/0/0 (14) | 0/0 | 24/24/0 |
| b1-pxo-fp | 1:1-order-preserving | 15 | — | 15 | —/15 | —/0 | 0/0/— | 37 ms / 1900 ms / 1900 ms | 11/0/10 (3) | 0/0 | 24/24/0 |
| b1-va | not_run | 15 | 0 | — | 0/— | 0/— | 0/—/0 | 1900 ms / 1900 ms / 1900 ms | 1/0/0 (14) | 0/0 | 24/24/0 |

- `b1-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-n` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-va` final timeline = accepted_output
- `b1-fg` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-n` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-px-fg` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-px-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-pxo-fg` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-pxo-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-va` regions: 1 proposed (1 with proposed changes); validated acceptance: 0 accepted / 0 rejected / 0 abstained (from the bound AcceptanceRecord)
- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 1 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 14 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 1 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 11 (matched 0 of 0 true, false-positive 10, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 1 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 1 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 14 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 1 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 11 (matched 0 of 0 true, false-positive 10, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 1 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-va` discontinuities: candidate-implied breakpoints 1 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 14 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 1 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-fg` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-fp` offset recovery: true 1900 ms, applied shift -1882 ms, recovered 1882 ms, residual 18 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-n` offset recovery: true 1900 ms, applied shift 0 ms, recovered 0 ms, residual 1900 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-px-fg` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-px-fp` offset recovery: true 1900 ms, applied shift -1881 ms, recovered 1881 ms, residual 19 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-pxo-fg` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-pxo-fp` offset recovery: true 1900 ms, applied shift -1881 ms, recovered 1881 ms, residual 19 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-va` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-al`: unsupported · input 2efc886e23496c42… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · input 852db217f8067c31… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.5s
- `b1-fp`: 1:1-order-preserving · input 33a9f643abed1780… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.3s
- `b1-n`: noop · input 08813765451d78a5… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 2452afe5f2524cbe… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.1s
- `b1-px-fp`: 1:1-order-preserving · input 59bc727ffafa4774… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.3s
- `b1-pxo-fg`: 1:1-order-preserving · input cd5a98f3b2114461… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.6s
- `b1-pxo-fp`: 1:1-order-preserving · input 02a0c201fe3d3751… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.3s
- `b1-va`: not_run · input da86c9d357fa41d6… · validated base b1-px-fg @ run Fx00-S01-b1-px-fg-1792045088 fp 2452afe5f2524cbe… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S02` (scenario S02)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 4):** aggregate safety counts are WHOLE-CUE (sixth-review M1): `Repaired` requires BOTH boundaries within tolerance; `Worsened`/`Harmful`/denominator altered/unaltered fire on EITHER boundary; `Harmful` compares each boundary against its corrupted baseline. Onset-only and end-only detail (`repaired_onset/end_*`, `harmful_onset/end_*`, `severe_onset/end_*`, `*_unaltered_onset/end_*` flags and the `timing_errors_*_end_us` distribution) stays in score.json for independent analysis; the median/P90/P95 column is the ONSET axis by label. `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

| b1-fg | 1:1-order-preserving | 24 | — | 24 | —/2 | —/0 | 0/0/— | 20 ms / 40 ms / 50 ms | 0/0/0 (0) | 0/0 | 24/2/22 |
| b1-fp | 1:1-order-preserving | 24 | — | 24 | —/2 | —/0 | 0/0/— | 3 ms / 5 ms / 5 ms | 0/0/0 (0) | 0/0 | 24/2/22 |
| b1-n | noop | 0 | — | 0 | —/0 | —/0 | 0/0/— | 30 ms / 50 ms / 50 ms | 0/0/0 (0) | 0/0 | 24/2/22 |
| b1-px-fg | 1:1-order-preserving | 15 | — | 15 | —/1 | —/0 | 0/0/— | 4 ms / 40 ms / 50 ms | 0/0/0 (3) | 0/0 | 24/2/22 |
| b1-px-fp | 1:1-order-preserving | 15 | — | 15 | —/1 | —/0 | 0/0/— | 11 ms / 40 ms / 50 ms | 0/0/0 (3) | 0/0 | 24/2/22 |
| b1-pxo-fg | 1:1-order-preserving | 15 | — | 15 | —/1 | —/0 | 0/0/— | 4 ms / 40 ms / 50 ms | 0/0/0 (3) | 0/0 | 24/2/22 |
| b1-pxo-fp | 1:1-order-preserving | 15 | — | 15 | —/1 | —/0 | 0/0/— | 11 ms / 40 ms / 50 ms | 0/0/0 (3) | 0/0 | 24/2/22 |
| b1-va | not_run | 15 | 0 | — | 0/— | 0/— | 0/—/0 | 30 ms / 50 ms / 50 ms | 0/0/0 (3) | 0/0 | 24/2/22 |

- `b1-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-n` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-va` final timeline = accepted_output
- `b1-fg` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-n` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-px-fg` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-px-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-pxo-fg` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-pxo-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-va` regions: 1 proposed (1 with proposed changes); validated acceptance: 0 accepted / 0 rejected / 0 abstained (from the bound AcceptanceRecord)
- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-al`: unsupported · input 4ad0cfa90ef2a6dc… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · input 5b27359fbac4c7b1… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-fp`: 1:1-order-preserving · input 8c6001416731cbfd… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.2s
- `b1-n`: noop · input 0e0aa33e52b22996… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 846df3c79754d16f… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-px-fp`: 1:1-order-preserving · input 8f2b6b2a6480f7a3… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.8s
- `b1-pxo-fg`: 1:1-order-preserving · input 8f8f4cd67bcc38d9… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.7s
- `b1-pxo-fp`: 1:1-order-preserving · input 88640c65e03edc0a… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.0s
- `b1-va`: not_run · input 976b4b4779f0b79e… · validated base b1-px-fg @ run Fx00-S02-b1-px-fg-1792045128 fp 846df3c79754d16f… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S03` (scenario S03)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 4):** aggregate safety counts are WHOLE-CUE (sixth-review M1): `Repaired` requires BOTH boundaries within tolerance; `Worsened`/`Harmful`/denominator altered/unaltered fire on EITHER boundary; `Harmful` compares each boundary against its corrupted baseline. Onset-only and end-only detail (`repaired_onset/end_*`, `harmful_onset/end_*`, `severe_onset/end_*`, `*_unaltered_onset/end_*` flags and the `timing_errors_*_end_us` distribution) stays in score.json for independent analysis; the median/P90/P95 column is the ONSET axis by label. `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

| b1-n | noop | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 8340 ms / 8340 ms | 0/0/0 (0) | 1/1 | 24/5/19 |
| b1-px-fg | 1:1-order-preserving | 15 | — | 15 | —/0 | —/5 | 5/5/— | 40 ms / 8281 ms / 8340 ms | 0/0/0 (3) | 1/1 | 24/5/19 |
| b1-px-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/2 | 2/2/— | 30 ms / 8291 ms / 8340 ms | 0/0/0 (3) | 1/1 | 24/5/19 |
| b1-pxo-fg | 1:1-order-preserving | 15 | — | 15 | —/0 | —/5 | 5/5/— | 40 ms / 8281 ms / 8340 ms | 0/0/0 (3) | 1/1 | 24/5/19 |
| b1-pxo-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/2 | 2/2/— | 30 ms / 8291 ms / 8340 ms | 0/0/0 (3) | 1/1 | 24/5/19 |
| b1-va | not_run | 15 | 0 | — | 0/— | 0/— | 5/—/0 | 0 ms / 8340 ms / 8340 ms | 0/0/0 (3) | 1/1 | 24/5/19 |

- `b1-n` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-va` final timeline = accepted_output
- `b1-n` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-px-fg` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-px-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-pxo-fg` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-pxo-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-va` regions: 1 proposed (1 with proposed changes); validated acceptance: 0 accepted / 0 rejected / 0 abstained (from the bound AcceptanceRecord)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-al`: unsupported · input a89236132b73a361… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: mapping_failure_ambiguous_text · input 9a7666aa23caeb83… · reason: tool rewrote events: normalized text mismatch at position 16 (cue e0016): input 'That is the third time today.' vs output 'I will make fresh leaves.'; 24 outputs vs 24 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 0.9s
- `b1-fp`: mapping_failure_ambiguous_text · input 382c84f6c2fc6e89… · reason: tool rewrote events: normalized text mismatch at position 16 (cue e0016): input 'That is the third time today.' vs output 'I will make fresh leaves.'; 24 outputs vs 24 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 0.9s
- `b1-n`: noop · input 127181785a8fd09d… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 60176e669e1cc126… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-px-fp`: 1:1-order-preserving · input 0d1ceed097fc717d… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 165.1s
- `b1-pxo-fg`: 1:1-order-preserving · input 8378f797b5f88f47… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.3s
- `b1-pxo-fp`: 1:1-order-preserving · input e5ad16b43155d06e… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.1s
- `b1-va`: not_run · input 1bd6bf4e779c030e… · validated base b1-px-fg @ run Fx00-S03-b1-px-fg-1792045144 fp 60176e669e1cc126… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S04` (scenario S04)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 4):** aggregate safety counts are WHOLE-CUE (sixth-review M1): `Repaired` requires BOTH boundaries within tolerance; `Worsened`/`Harmful`/denominator altered/unaltered fire on EITHER boundary; `Harmful` compares each boundary against its corrupted baseline. Onset-only and end-only detail (`repaired_onset/end_*`, `harmful_onset/end_*`, `severe_onset/end_*`, `*_unaltered_onset/end_*` flags and the `timing_errors_*_end_us` distribution) stays in score.json for independent analysis; the median/P90/P95 column is the ONSET axis by label. `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

| b1-n | noop | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 3540 ms / 4420 ms | 0/0/0 (0) | 0/0 | 24/5/19 |
| b1-px-fg | 1:1-order-preserving | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 3540 ms / 4420 ms | 0/0/0 (0) | 0/0 | 24/5/19 |
| b1-px-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/3 | 3/3/— | 22 ms / 3540 ms / 4420 ms | 0/0/0 (3) | 0/0 | 24/5/19 |
| b1-pxo-fg | 1:1-order-preserving | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 3540 ms / 4420 ms | 0/0/0 (0) | 0/0 | 24/5/19 |
| b1-pxo-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/3 | 3/3/— | 22 ms / 3540 ms / 4420 ms | 0/0/0 (3) | 0/0 | 24/5/19 |
| b1-va | not_run | 0 | 0 | — | 0/— | 0/— | 0/—/0 | 0 ms / 3540 ms / 4420 ms | 0/0/0 (0) | 0/0 | 24/5/19 |

- `b1-n` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-va` final timeline = accepted_output
- `b1-n` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-px-fg` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-px-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-pxo-fg` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-pxo-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-va` regions: 1 proposed (0 with proposed changes); validated acceptance: 0 accepted / 0 rejected / 0 abstained (from the bound AcceptanceRecord)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · input 78e2716369a7cb5f… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: mapping_failure_ambiguous_text · input ef0fa4a558cfb34a… · reason: tool rewrote events: normalized text mismatch at position 4 (cue e0004): input 'I heard that too.' vs output 'Singing loud'; 24 outputs vs 24 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 1.1s
- `b1-fp`: mapping_failure_ambiguous_text · input b40469902e7e8dc3… · reason: tool rewrote events: normalized text mismatch at position 4 (cue e0004): input 'I heard that too.' vs output 'Singing loud'; 24 outputs vs 24 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 1.7s
- `b1-n`: noop · input b50c33dee2b0b6c5… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 36a0344cf43ce5ca… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.2s
- `b1-px-fp`: 1:1-order-preserving · input 0eabb920fcab663d… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.4s
- `b1-pxo-fg`: 1:1-order-preserving · input 991429501492384e… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.5s
- `b1-pxo-fp`: 1:1-order-preserving · input 821c087419798ddf… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.6s
- `b1-va`: not_run · input e58086641b7b2960… · validated base b1-px-fg @ run Fx00-S04-b1-px-fg-1792045329 fp 36a0344cf43ce5ca… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S06` (scenario S06)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 4):** aggregate safety counts are WHOLE-CUE (sixth-review M1): `Repaired` requires BOTH boundaries within tolerance; `Worsened`/`Harmful`/denominator altered/unaltered fire on EITHER boundary; `Harmful` compares each boundary against its corrupted baseline. Onset-only and end-only detail (`repaired_onset/end_*`, `harmful_onset/end_*`, `severe_onset/end_*`, `*_unaltered_onset/end_*` flags and the `timing_errors_*_end_us` distribution) stays in score.json for independent analysis; the median/P90/P95 column is the ONSET axis by label. `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

| b1-fg | 1:1-order-preserving | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 0 ms / 0 ms | 0/0/0 (0) | 0/0 | 24/0/24 |
| b1-fp | 1:1-order-preserving | 24 | — | 24 | —/0 | —/0 | 0/0/— | 17 ms / 41 ms / 44 ms | 0/0/0 (0) | 0/0 | 24/0/24 |
| b1-n | noop | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 0 ms / 0 ms | 0/0/0 (0) | 0/0 | 24/0/24 |
| b1-px-fg | 1:1-order-preserving | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 0 ms / 0 ms | 0/0/0 (0) | 0/0 | 24/0/24 |
| b1-px-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/0 | 0/0/— | 6 ms / 38 ms / 41 ms | 0/0/0 (2) | 0/0 | 24/0/24 |
| b1-pxo-fg | 1:1-order-preserving | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 0 ms / 0 ms | 0/0/0 (0) | 0/0 | 24/0/24 |
| b1-pxo-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/0 | 0/0/— | 6 ms / 38 ms / 41 ms | 0/0/0 (2) | 0/0 | 24/0/24 |
| b1-va | not_run | 0 | 0 | — | 0/— | 0/— | 0/—/0 | 0 ms / 0 ms / 0 ms | 0/0/0 (0) | 0/0 | 24/0/24 |

- `b1-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-n` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-va` final timeline = accepted_output
- `b1-fg` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-n` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-px-fg` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-px-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-pxo-fg` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-pxo-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-va` regions: 1 proposed (0 with proposed changes); validated acceptance: 0 accepted / 0 rejected / 0 abstained (from the bound AcceptanceRecord)
- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 2 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 2 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities); 1 track-boundary one-cue correction(s) (isolated edge adjustment vs release-boundary offset ambiguity: claims kept for localization, cues never auto-counted as local, unmatched edge claims 0 recorded explicitly instead of auto-declared false release discontinuities — descriptors in score.json, never silent)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · input 4898cfc7d6ff9770… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · input 5476ce6530b546b8… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 13.3s
- `b1-fp`: 1:1-order-preserving · input e102e256c965a947… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-n`: noop · input 4fd414795fd031dd… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input f812169e578122ae… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.1s
- `b1-px-fp`: 1:1-order-preserving · input b705e0f2a2650b8e… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.8s
- `b1-pxo-fg`: 1:1-order-preserving · input ca604f287a80f3b0… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.8s
- `b1-pxo-fp`: 1:1-order-preserving · input ba41941f9bb6a38d… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.8s
- `b1-va`: not_run · input f595bfccc843651c… · validated base b1-px-fg @ run Fx00-S06-b1-px-fg-1792045360 fp f812169e578122ae… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-SGN01` (scenario S01)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 4):** aggregate safety counts are WHOLE-CUE (sixth-review M1): `Repaired` requires BOTH boundaries within tolerance; `Worsened`/`Harmful`/denominator altered/unaltered fire on EITHER boundary; `Harmful` compares each boundary against its corrupted baseline. Onset-only and end-only detail (`repaired_onset/end_*`, `harmful_onset/end_*`, `severe_onset/end_*`, `*_unaltered_onset/end_*` flags and the `timing_errors_*_end_us` distribution) stays in score.json for independent analysis; the median/P90/P95 column is the ONSET axis by label. `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

| b1-fp | 1:1-order-preserving | 5 | — | 5 | —/0 | —/0 | 5/5/— | 3636 ms / 4703 ms / 4703 ms | 4/0/4 (0) | 0/0 | 5/5/0 |
| b1-n | noop | 0 | — | 0 | —/0 | —/0 | 0/0/— | 1490 ms / 1490 ms / 1490 ms | 0/0/0 (0) | 0/0 | 5/5/0 |
| b1-va | not_run | 0 | 0 | — | 0/— | 0/— | 0/—/0 | 1490 ms / 1490 ms / 1490 ms | 0/0/0 (0) | 0/0 | 5/5/0 |

- `b1-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-n` final timeline = unguarded_proposal_if_blindly_applied
- `b1-va` final timeline = accepted_output
- `b1-fp` regions: 1 proposed (1 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-n` regions: 1 proposed (0 with proposed changes); NO validated acceptance — accepted regions 0 (tool-only arm: proposals are not acceptances)
- `b1-fp` discontinuities: candidate-implied breakpoints 4 (matched 0 of 0 true, false-positive 4, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` offset recovery: true 1490 ms, applied shift -5126 ms, recovered 5126 ms, residual 3636 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-n` offset recovery: true 1490 ms, applied shift 0 ms, recovered 0 ms, residual 1490 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-al`: unsupported · input eec2d17cfc2cc762… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: mapping_failure_count_mismatch · input 9fb4c0a57e5d00c0… · reason: tool output has 1 entries vs 5 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 0.9s
- `b1-fp`: 1:1-order-preserving · input 1691fcf36b4109ad… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-n`: noop · input 58a98c9277165887… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: abstain_no_speech_anchors · input 96c8ffb18a793331… · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-px-fp`: abstain_no_speech_anchors · input 0b54e2e23085328e… · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-pxo-fg`: abstain_no_speech_anchors · input 4bdb8825b8e4b9ab… · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-pxo-fp`: abstain_no_speech_anchors · input 7be775e9cb2364c1… · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-va`: not_run · input fc9b019bd4a601a1… · validated base b1-px-fg @ run Fx00-SGN01-b1-px-fg-1792045374 fp 96c8ffb18a793331… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Tolerances used
- good ±50 ms, severe >±250 ms, breakpoint match ±500 ms (declared evaluation tolerance for this run only; not a production threshold)
