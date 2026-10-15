# Benchmark comparison report

**Caveat:** synthetic-timing recovery measures recovery of injected errors only. It is not evidence
about real-speech synchronization, and it is not a production threshold. See denominators.
**Score-number provenance:** comparative rows are admitted only from a directory whose run.json passes the proposal-byte check; the row bullets' recorded input fingerprint and proposal hash are the audit anchors. Numbers fabricated *inside* a score.json that pairs with an admitted, byte-verified run record render as recorded — regenerate score.json with `score` rather than editing it.

dropped unbound score rows: 0 (scores with no fingerprint-matching run.json, schema-3 rows missing a proposal hash pair, structurally incomplete rows, and planted numbers are never rendered)
dropped stale-generation rows: 0 (schema-3 scores bound to a run.json whose recorded fingerprint differs from the current case generation are never rendered)
legacy schema-2 rows rendered separately: 0 (schema 2 counted unguarded proposals as 'accepted' — pre-F06 semantics; kept in a labeled non-comparative section, never mixed into schema-3 comparisons)
dropped obsolete-acceptance rows: 0 (b1-va scores whose validated base run/proposal no longer matches the current base artifacts are never rendered; re-run the base arm and re-validate)
dropped tampered/removed proposal rows: 0 (run.json proposal_sha256 no longer matches proposal.json bytes on disk at report time; the run/score pair is never rendered comparably; re-run the arm)
unreadable artifacts skipped: 0 (run/score JSON that cannot be parsed, and score.json files with no pairing admitted run.json in the same directory, are reported here, never rendered as a number, and do not abort the rest of the report)
## Tool/model versions

- `ffsubsync`: ffsubsync 0.5.1

## Case `Fx00-S00` (scenario S00)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 3):** `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

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
- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 2 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 2 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · input 16dcbe538d0e9a05… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · input 488f16f456539af5… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.1s
- `b1-fp`: 1:1-order-preserving · input 630ebd878242b5a3… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-n`: noop · input c0724d4ff5ec6db3… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 4f6a21896d324d63… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.8s
- `b1-px-fp`: 1:1-order-preserving · input ea697de44e86cd13… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-pxo-fg`: 1:1-order-preserving · input 308f76d86e8bbeac… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.9s
- `b1-pxo-fp`: 1:1-order-preserving · input d244382589e48ec8… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.0s
- `b1-va`: not_run · input 6509e3f8b9087bf0… · validated base b1-px-fg @ run Fx00-S00-b1-px-fg-1792028070 fp 4f6a21896d324d63… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S01` (scenario S01)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 3):** `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

| b1-fg | 1:1-order-preserving | 24 | — | 24 | —/24 | —/0 | 0/0/— | 0 ms / 0 ms / 0 ms | 0/0/0 (0) | 0/0 | 24/24/0 |
| b1-fp | 1:1-order-preserving | 24 | — | 24 | —/24 | —/0 | 0/0/— | 18 ms / 43 ms / 46 ms | 0/0/0 (0) | 0/0 | 24/24/0 |
| b1-n | noop | 0 | — | 0 | —/0 | —/0 | 0/0/— | 1900 ms / 1900 ms / 1900 ms | 0/0/0 (0) | 0/0 | 24/24/0 |
| b1-px-fg | 1:1-order-preserving | 15 | — | 15 | —/15 | —/0 | 0/0/— | 0 ms / 1900 ms / 1900 ms | 0/0/0 (14) | 0/0 | 24/24/0 |
| b1-px-fp | 1:1-order-preserving | 15 | — | 15 | —/15 | —/0 | 0/0/— | 37 ms / 1900 ms / 1900 ms | 11/0/11 (3) | 0/0 | 24/24/0 |
| b1-pxo-fg | 1:1-order-preserving | 15 | — | 15 | —/15 | —/0 | 0/0/— | 0 ms / 1900 ms / 1900 ms | 0/0/0 (14) | 0/0 | 24/24/0 |
| b1-pxo-fp | 1:1-order-preserving | 15 | — | 15 | —/15 | —/0 | 0/0/— | 37 ms / 1900 ms / 1900 ms | 11/0/11 (3) | 0/0 | 24/24/0 |
| b1-va | not_run | 15 | 0 | — | 0/— | 0/— | 0/—/0 | 1900 ms / 1900 ms / 1900 ms | 0/0/0 (14) | 0/0 | 24/24/0 |

- `b1-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-n` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-va` final timeline = accepted_output
- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 14 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 11 (matched 0 of 0 true, false-positive 11, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 14 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 11 (matched 0 of 0 true, false-positive 11, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 14 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-fg` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-fp` offset recovery: true 1900 ms, applied shift -1882 ms, recovered 1882 ms, residual 18 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-n` offset recovery: true 1900 ms, applied shift 0 ms, recovered 0 ms, residual 1900 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-px-fg` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-px-fp` offset recovery: true 1900 ms, applied shift -1881 ms, recovered 1881 ms, residual 19 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-pxo-fg` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-pxo-fp` offset recovery: true 1900 ms, applied shift -1881 ms, recovered 1881 ms, residual 19 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-va` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-al`: unsupported · input aae80bc0f6a4d652… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · input 805a2a946304f2bf… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.8s
- `b1-fp`: 1:1-order-preserving · input 4609d805eff6743f… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-n`: noop · input 33877f3edc51dff7… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 73ad1722b8a52e3a… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.8s
- `b1-px-fp`: 1:1-order-preserving · input 7249d01d08eb5d3b… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.8s
- `b1-pxo-fg`: 1:1-order-preserving · input 9da1400cf4777957… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.9s
- `b1-pxo-fp`: 1:1-order-preserving · input 15bd4ec6e56564ec… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.0s
- `b1-va`: not_run · input 5357781f863c84ec… · validated base b1-px-fg @ run Fx00-S01-b1-px-fg-1792028081 fp 73ad1722b8a52e3a… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S02` (scenario S02)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 3):** `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

| b1-fg | 1:1-order-preserving | 24 | — | 24 | —/1 | —/0 | 0/0/— | 20 ms / 40 ms / 50 ms | 0/0/0 (0) | 0/0 | 24/1/23 |
| b1-fp | 1:1-order-preserving | 24 | — | 24 | —/1 | —/0 | 0/0/— | 3 ms / 5 ms / 5 ms | 0/0/0 (0) | 0/0 | 24/1/23 |
| b1-n | noop | 0 | — | 0 | —/0 | —/0 | 0/0/— | 30 ms / 50 ms / 50 ms | 0/0/0 (0) | 0/0 | 24/1/23 |
| b1-px-fg | 1:1-order-preserving | 15 | — | 15 | —/0 | —/0 | 0/0/— | 4 ms / 40 ms / 50 ms | 0/0/0 (3) | 0/0 | 24/1/23 |
| b1-px-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/0 | 0/0/— | 11 ms / 40 ms / 50 ms | 0/0/0 (3) | 0/0 | 24/1/23 |
| b1-pxo-fg | 1:1-order-preserving | 15 | — | 15 | —/0 | —/0 | 0/0/— | 4 ms / 40 ms / 50 ms | 0/0/0 (3) | 0/0 | 24/1/23 |
| b1-pxo-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/0 | 0/0/— | 11 ms / 40 ms / 50 ms | 0/0/0 (3) | 0/0 | 24/1/23 |
| b1-va | not_run | 15 | 0 | — | 0/— | 0/— | 0/—/0 | 30 ms / 50 ms / 50 ms | 0/0/0 (3) | 0/0 | 24/1/23 |

- `b1-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-n` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-va` final timeline = accepted_output
- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-al`: unsupported · input 16786ae65419cf97… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · input 9d5d569271ccd152… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-fp`: 1:1-order-preserving · input 1d9b0998756f7c95… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.8s
- `b1-n`: noop · input 7c27fa28c412f40c… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 5b80dd7cf05ab6be… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.8s
- `b1-px-fp`: 1:1-order-preserving · input 3f649252bdfb32b3… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-pxo-fg`: 1:1-order-preserving · input 6c68b7c4ab3a560f… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.9s
- `b1-pxo-fp`: 1:1-order-preserving · input 23b0aa1c2c8e241d… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.1s
- `b1-va`: not_run · input c8532acfc1efb49f… · validated base b1-px-fg @ run Fx00-S02-b1-px-fg-1792028093 fp 5b80dd7cf05ab6be… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S03` (scenario S03)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 3):** `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

| b1-n | noop | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 8340 ms / 8340 ms | 0/0/0 (0) | 1/1 | 24/5/19 |
| b1-px-fg | 1:1-order-preserving | 15 | — | 15 | —/0 | —/4 | 4/4/— | 40 ms / 8281 ms / 8340 ms | 0/0/0 (3) | 1/1 | 24/5/19 |
| b1-px-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/1 | 1/1/— | 30 ms / 8291 ms / 8340 ms | 0/0/0 (3) | 1/1 | 24/5/19 |
| b1-pxo-fg | 1:1-order-preserving | 15 | — | 15 | —/0 | —/4 | 4/4/— | 40 ms / 8281 ms / 8340 ms | 0/0/0 (3) | 1/1 | 24/5/19 |
| b1-pxo-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/1 | 1/1/— | 30 ms / 8291 ms / 8340 ms | 0/0/0 (3) | 1/1 | 24/5/19 |
| b1-va | not_run | 15 | 0 | — | 0/— | 0/— | 4/—/0 | 0 ms / 8340 ms / 8340 ms | 0/0/0 (3) | 1/1 | 24/5/19 |

- `b1-n` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-va` final timeline = accepted_output
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-al`: unsupported · input 0a2f95495254dba1… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: mapping_failure_ambiguous_text · input 4a7c14776444f861… · reason: tool rewrote events: normalized text mismatch at position 16 (cue e0016): input 'That is the third time today.' vs output 'I will make fresh leaves.'; 24 outputs vs 24 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 0.8s
- `b1-fp`: mapping_failure_ambiguous_text · input cdddd8c9ddd93fa8… · reason: tool rewrote events: normalized text mismatch at position 16 (cue e0016): input 'That is the third time today.' vs output 'I will make fresh leaves.'; 24 outputs vs 24 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 0.8s
- `b1-n`: noop · input c47de19bb296c823… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 2f667ac25997aaa3… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.8s
- `b1-px-fp`: 1:1-order-preserving · input 8b0dbdafb4305597… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-pxo-fg`: 1:1-order-preserving · input 3c40c53dcf65091f… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.8s
- `b1-pxo-fp`: 1:1-order-preserving · input 1c19500b242ed6b8… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.8s
- `b1-va`: not_run · input 5692a57daa333b0d… · validated base b1-px-fg @ run Fx00-S03-b1-px-fg-1792028104 fp 2f667ac25997aaa3… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S04` (scenario S04)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 3):** `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

| b1-n | noop | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 3540 ms / 4420 ms | 0/0/0 (0) | 0/0 | 24/5/19 |
| b1-px-fg | 1:1-order-preserving | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 3540 ms / 4420 ms | 0/0/0 (0) | 0/0 | 24/5/19 |
| b1-px-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/2 | 2/2/— | 22 ms / 3540 ms / 4420 ms | 0/0/0 (3) | 0/0 | 24/5/19 |
| b1-pxo-fg | 1:1-order-preserving | 0 | — | 0 | —/0 | —/0 | 0/0/— | 0 ms / 3540 ms / 4420 ms | 0/0/0 (0) | 0/0 | 24/5/19 |
| b1-pxo-fp | 1:1-order-preserving | 15 | — | 15 | —/0 | —/2 | 2/2/— | 22 ms / 3540 ms / 4420 ms | 0/0/0 (3) | 0/0 | 24/5/19 |
| b1-va | not_run | 0 | 0 | — | 0/— | 0/— | 0/—/0 | 0 ms / 3540 ms / 4420 ms | 0/0/0 (0) | 0/0 | 24/5/19 |

- `b1-n` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-px-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fg` final timeline = unguarded_proposal_if_blindly_applied
- `b1-pxo-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-va` final timeline = accepted_output
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 3 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · input 39f0c5bf49e2b2cc… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: mapping_failure_ambiguous_text · input 18e315fb1b2dea54… · reason: tool rewrote events: normalized text mismatch at position 4 (cue e0004): input 'I heard that too.' vs output 'Singing loud'; 24 outputs vs 24 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 0.8s
- `b1-fp`: mapping_failure_ambiguous_text · input 3b3d5a0dc7df9e3d… · reason: tool rewrote events: normalized text mismatch at position 4 (cue e0004): input 'I heard that too.' vs output 'Singing loud'; 24 outputs vs 24 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 0.8s
- `b1-n`: noop · input 6fa1ff2b2bbf51df… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input d9fbb5c5d572e3eb… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.8s
- `b1-px-fp`: 1:1-order-preserving · input d986a10ba520af96… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.1s
- `b1-pxo-fg`: 1:1-order-preserving · input 9fcd3a706497db80… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.7s
- `b1-pxo-fp`: 1:1-order-preserving · input 6c9324bff7cf8487… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.9s
- `b1-va`: not_run · input 0b2678bbb9c1b216… · validated base b1-px-fg @ run Fx00-S04-b1-px-fg-1792028115 fp d9fbb5c5d572e3eb… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S06` (scenario S06)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 3):** `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

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
- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 2 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair); 2 local cue adjustments (transient isolated-cue corrections, counted separately, not release discontinuities)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · input 1dfc13d4aef826bd… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · input dad0a35123c77b7d… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-fp`: 1:1-order-preserving · input 62cd2d6338e96a93… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-n`: noop · input b74da6b280a70542… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 6f466d14bcd13db3… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.1s
- `b1-px-fp`: 1:1-order-preserving · input 54f94100685744c0… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-pxo-fg`: 1:1-order-preserving · input 7b3018326218ba5f… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.9s
- `b1-pxo-fp`: 1:1-order-preserving · input 5f1e4672417ea0aa… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.2s
- `b1-va`: not_run · input 585a571a33545691… · validated base b1-px-fg @ run Fx00-S06-b1-px-fg-1792028128 fp 6f466d14bcd13db3… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-SGN01` (scenario S01)

| Candidate | Status | Proposals | Acc validated | If blind | Repaired acc/blind | Worsened acc/blind | Harmful prop/blind/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ (local adj) | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
**Column semantics (schema 3):** `Acc validated` = automatically accepted nonzero cues from a real AcceptanceRecord (b1-va only); `If blind` = unguarded proposal nonzero (counterfactual: what blind application would have changed — no validator ran); `repaired/worsened` show accepted-side / blindly-applied-side counts (`—` where that side does not apply); `final onset err` statistics use the arm's final semantics per row below.

| b1-fp | 1:1-order-preserving | 5 | — | 5 | —/0 | —/0 | 5/5/— | 3636 ms / 4703 ms / 4703 ms | 4/0/4 (0) | 0/0 | 5/5/0 |
| b1-n | noop | 0 | — | 0 | —/0 | —/0 | 0/0/— | 1490 ms / 1490 ms / 1490 ms | 0/0/0 (0) | 0/0 | 5/5/0 |
| b1-va | not_run | 0 | 0 | — | 0/— | 0/— | 0/—/0 | 1490 ms / 1490 ms / 1490 ms | 0/0/0 (0) | 0/0 | 5/5/0 |

- `b1-fp` final timeline = unguarded_proposal_if_blindly_applied
- `b1-n` final timeline = unguarded_proposal_if_blindly_applied
- `b1-va` final timeline = accepted_output
- `b1-fp` discontinuities: candidate-implied breakpoints 4 (matched 0 of 0 true, false-positive 4, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` offset recovery: true 1490 ms, applied shift -5126 ms, recovered 5126 ms, residual 3636 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-n` offset recovery: true 1490 ms, applied shift 0 ms, recovered 0 ms, residual 1490 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-al`: unsupported · input eec2d17cfc2cc762… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: mapping_failure_count_mismatch · input 9fb4c0a57e5d00c0… · reason: tool output has 1 entries vs 5 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 1.0s
- `b1-fp`: 1:1-order-preserving · input 1691fcf36b4109ad… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-n`: noop · input 58a98c9277165887… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: abstain_no_speech_anchors · input 96c8ffb18a793331… · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-px-fp`: abstain_no_speech_anchors · input 0b54e2e23085328e… · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-pxo-fg`: abstain_no_speech_anchors · input 4bdb8825b8e4b9ab… · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-pxo-fp`: abstain_no_speech_anchors · input 7be775e9cb2364c1… · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-va`: not_run · input fc9b019bd4a601a1… · validated base b1-px-fg @ run Fx00-SGN01-b1-px-fg-1792028139 fp 96c8ffb18a793331… · validation seed 1 langs und/und asr=None verifier=None pad 1500000 ms ratio 0.45 tol 500000 ms · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Tolerances used
- good ±50 ms, severe >±250 ms, breakpoint match ±500 ms (declared evaluation tolerance for this run only; not a production threshold)
