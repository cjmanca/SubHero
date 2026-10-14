# Benchmark comparison report

**Caveat:** synthetic-timing recovery measures recovery of injected errors only. It is not evidence
about real-speech synchronization, and it is not a production threshold. See denominators.

## Tool/model versions

- `ffsubsync`: ffsubsync 0.5.1

## Case `Fx00-S00` (scenario S00)

| Candidate | Status | Proposals | Accepted | Repaired | Worsened | Harmful prop/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b1-fg | 1:1-order-preserving | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 0 ms / 0 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-fp | 1:1-order-preserving | 24 | 24 | 0 | 0 | 0/0 | 17 ms / 41 ms / 44 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-n | noop | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 0 ms / 0 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-px-fg | 1:1-order-preserving | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 0 ms / 0 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-px-fp | 1:1-order-preserving | 15 | 15 | 0 | 0 | 0/0 | 6 ms / 38 ms / 41 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-pxo-fg | 1:1-order-preserving | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 0 ms / 0 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-pxo-fp | 1:1-order-preserving | 15 | 15 | 0 | 0 | 0/0 | 6 ms / 38 ms / 41 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-va | not_run | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 0 ms / 0 ms | 0/0/0 | 0/0 | 24/0/24 |

- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.1s
- `b1-n`: noop · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-px-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-pxo-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a d · preprocess 0.0s · candidate 1.4s
- `b1-pxo-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a d · preprocess 0.0s · candidate 1.0s
- `b1-va`: not_run · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S01` (scenario S01)

| Candidate | Status | Proposals | Accepted | Repaired | Worsened | Harmful prop/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b1-fg | 1:1-order-preserving | 24 | 24 | 24 | 0 | 0/0 | 0 ms / 0 ms / 0 ms | 0/0/0 | 0/0 | 24/24/0 |
| b1-fp | 1:1-order-preserving | 24 | 24 | 24 | 0 | 0/0 | 18 ms / 43 ms / 46 ms | 0/0/0 | 0/0 | 24/24/0 |
| b1-n | noop | 0 | 0 | 0 | 0 | 0/0 | 1900 ms / 1900 ms / 1900 ms | 0/0/0 | 0/0 | 24/24/0 |
| b1-px-fg | 1:1-order-preserving | 15 | 15 | 15 | 0 | 0/0 | 0 ms / 1900 ms / 1900 ms | 17/0/17 | 0/0 | 24/24/0 |
| b1-px-fp | 1:1-order-preserving | 15 | 15 | 15 | 0 | 0/0 | 37 ms / 1900 ms / 1900 ms | 17/0/17 | 0/0 | 24/24/0 |
| b1-pxo-fg | 1:1-order-preserving | 15 | 15 | 15 | 0 | 0/0 | 0 ms / 1900 ms / 1900 ms | 17/0/17 | 0/0 | 24/24/0 |
| b1-pxo-fp | 1:1-order-preserving | 15 | 15 | 15 | 0 | 0/0 | 37 ms / 1900 ms / 1900 ms | 17/0/17 | 0/0 | 24/24/0 |
| b1-va | not_run | 15 | 0 | 0 | 0 | 0/0 | 1900 ms / 1900 ms / 1900 ms | 17/0/17 | 0/0 | 24/24/0 |

- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 17 (matched 0 of 0 true, false-positive 17, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 17 (matched 0 of 0 true, false-positive 17, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 17 (matched 0 of 0 true, false-positive 17, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 17 (matched 0 of 0 true, false-positive 17, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 17 (matched 0 of 0 true, false-positive 17, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fg` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-fp` offset recovery: true 1900 ms, applied shift -1882 ms, recovered 1882 ms, residual 18 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-n` offset recovery: true 1900 ms, applied shift 0 ms, recovered 0 ms, residual 1900 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-px-fg` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-px-fp` offset recovery: true 1900 ms, applied shift -1881 ms, recovered 1881 ms, residual 19 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-pxo-fg` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-pxo-fp` offset recovery: true 1900 ms, applied shift -1881 ms, recovered 1881 ms, residual 19 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-va` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-al`: unsupported · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.1s
- `b1-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.7s
- `b1-n`: noop · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 2.2s
- `b1-px-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.1s
- `b1-pxo-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a d · preprocess 0.0s · candidate 0.8s
- `b1-pxo-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a d · preprocess 0.0s · candidate 0.8s
- `b1-va`: not_run · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S02` (scenario S02)

| Candidate | Status | Proposals | Accepted | Repaired | Worsened | Harmful prop/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b1-fg | 1:1-order-preserving | 24 | 24 | 1 | 0 | 0/0 | 20 ms / 40 ms / 50 ms | 0/0/0 | 0/0 | 24/1/23 |
| b1-fp | 1:1-order-preserving | 24 | 24 | 1 | 0 | 0/0 | 3 ms / 5 ms / 5 ms | 0/0/0 | 0/0 | 24/1/23 |
| b1-n | noop | 0 | 0 | 0 | 0 | 0/0 | 30 ms / 50 ms / 50 ms | 0/0/0 | 0/0 | 24/1/23 |
| b1-px-fg | 1:1-order-preserving | 15 | 15 | 0 | 0 | 0/0 | 4 ms / 40 ms / 50 ms | 0/0/0 | 0/0 | 24/1/23 |
| b1-px-fp | 1:1-order-preserving | 15 | 15 | 0 | 0 | 0/0 | 11 ms / 40 ms / 50 ms | 0/0/0 | 0/0 | 24/1/23 |
| b1-pxo-fg | 1:1-order-preserving | 15 | 15 | 0 | 0 | 0/0 | 4 ms / 40 ms / 50 ms | 0/0/0 | 0/0 | 24/1/23 |
| b1-pxo-fp | 1:1-order-preserving | 15 | 15 | 0 | 0 | 0/0 | 11 ms / 40 ms / 50 ms | 0/0/0 | 0/0 | 24/1/23 |
| b1-va | not_run | 15 | 0 | 0 | 0 | 0/0 | 30 ms / 50 ms / 50 ms | 0/0/0 | 0/0 | 24/1/23 |

- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.2s
- `b1-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-n`: noop · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.2s
- `b1-px-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-pxo-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a d · preprocess 0.0s · candidate 1.1s
- `b1-pxo-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a d · preprocess 0.0s · candidate 1.3s
- `b1-va`: not_run · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S03` (scenario S03)

| Candidate | Status | Proposals | Accepted | Repaired | Worsened | Harmful prop/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b1-n | noop | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 8340 ms / 8340 ms | 0/0/0 | 1/1 | 24/5/19 |
| b1-px-fg | 1:1-order-preserving | 15 | 15 | 0 | 4 | 4/4 | 40 ms / 8281 ms / 8340 ms | 0/0/0 | 1/1 | 24/5/19 |
| b1-px-fp | 1:1-order-preserving | 15 | 15 | 0 | 1 | 1/1 | 30 ms / 8291 ms / 8340 ms | 0/0/0 | 1/1 | 24/5/19 |
| b1-pxo-fg | 1:1-order-preserving | 15 | 15 | 0 | 4 | 4/4 | 40 ms / 8281 ms / 8340 ms | 0/0/0 | 1/1 | 24/5/19 |
| b1-pxo-fp | 1:1-order-preserving | 15 | 15 | 0 | 1 | 1/1 | 30 ms / 8291 ms / 8340 ms | 0/0/0 | 1/1 | 24/5/19 |
| b1-va | not_run | 15 | 0 | 0 | 0 | 4/0 | 0 ms / 8340 ms / 8340 ms | 0/0/0 | 1/1 | 24/5/19 |

- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: mapping_failure_ambiguous_text · reason: tool rewrote events: normalized text mismatch at position 16 (cue e0016): input 'That is the third time today.' vs output 'I will make fresh leaves.'; 24 outputs vs 24 inputs; refu · preprocess 0.0s · candidate 0.8s
- `b1-fp`: mapping_failure_ambiguous_text · reason: tool rewrote events: normalized text mismatch at position 16 (cue e0016): input 'That is the third time today.' vs output 'I will make fresh leaves.'; 24 outputs vs 24 inputs; refu · preprocess 0.0s · candidate 1.3s
- `b1-n`: noop · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.8s
- `b1-px-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-pxo-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a d · preprocess 0.0s · candidate 1.4s
- `b1-pxo-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a d · preprocess 0.0s · candidate 3.4s
- `b1-va`: not_run · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S04` (scenario S04)

| Candidate | Status | Proposals | Accepted | Repaired | Worsened | Harmful prop/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b1-n | noop | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 3540 ms / 4420 ms | 0/0/0 | 0/0 | 24/5/19 |
| b1-px-fg | 1:1-order-preserving | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 3540 ms / 4420 ms | 0/0/0 | 0/0 | 24/5/19 |
| b1-px-fp | 1:1-order-preserving | 15 | 15 | 0 | 2 | 2/2 | 22 ms / 3540 ms / 4420 ms | 0/0/0 | 0/0 | 24/5/19 |
| b1-pxo-fg | 1:1-order-preserving | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 3540 ms / 4420 ms | 0/0/0 | 0/0 | 24/5/19 |
| b1-pxo-fp | 1:1-order-preserving | 15 | 15 | 0 | 2 | 2/2 | 22 ms / 3540 ms / 4420 ms | 0/0/0 | 0/0 | 24/5/19 |
| b1-va | not_run | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 3540 ms / 4420 ms | 0/0/0 | 0/0 | 24/5/19 |

- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: mapping_failure_ambiguous_text · reason: tool rewrote events: normalized text mismatch at position 4 (cue e0004): input 'I heard that too.' vs output 'Singing loud'; 24 outputs vs 24 inputs; refusing to guess corresponden · preprocess 0.0s · candidate 1.0s
- `b1-fp`: mapping_failure_ambiguous_text · reason: tool rewrote events: normalized text mismatch at position 4 (cue e0004): input 'I heard that too.' vs output 'Singing loud'; 24 outputs vs 24 inputs; refusing to guess corresponden · preprocess 0.0s · candidate 3.9s
- `b1-n`: noop · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 3.4s
- `b1-px-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-pxo-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a d · preprocess 0.0s · candidate 1.0s
- `b1-pxo-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a d · preprocess 0.0s · candidate 5.2s
- `b1-va`: not_run · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S06` (scenario S06)

| Candidate | Status | Proposals | Accepted | Repaired | Worsened | Harmful prop/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b1-fg | 1:1-order-preserving | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 0 ms / 0 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-fp | 1:1-order-preserving | 24 | 24 | 0 | 0 | 0/0 | 17 ms / 41 ms / 44 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-n | noop | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 0 ms / 0 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-px-fg | 1:1-order-preserving | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 0 ms / 0 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-px-fp | 1:1-order-preserving | 15 | 15 | 0 | 0 | 0/0 | 6 ms / 38 ms / 41 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-pxo-fg | 1:1-order-preserving | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 0 ms / 0 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-pxo-fp | 1:1-order-preserving | 15 | 15 | 0 | 0 | 0/0 | 6 ms / 38 ms / 41 ms | 0/0/0 | 0/0 | 24/0/24 |
| b1-va | not_run | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 0 ms / 0 ms | 0/0/0 | 0/0 | 24/0/24 |

- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.6s
- `b1-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.3s
- `b1-n`: noop · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-px-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.0s
- `b1-pxo-fg`: 1:1-order-preserving · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a d · preprocess 0.0s · candidate 1.3s
- `b1-pxo-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a d · preprocess 0.0s · candidate 1.3s
- `b1-va`: not_run · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-SGN01` (scenario S01)

| Candidate | Status | Proposals | Accepted | Repaired | Worsened | Harmful prop/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b1-fp | 1:1-order-preserving | 5 | 5 | 0 | 0 | 5/5 | 3636 ms / 4703 ms / 4703 ms | 4/0/4 | 0/0 | 5/5/0 |
| b1-n | noop | 0 | 0 | 0 | 0 | 0/0 | 1490 ms / 1490 ms / 1490 ms | 0/0/0 | 0/0 | 5/5/0 |
| b1-va | not_run | 0 | 0 | 0 | 0 | 0/0 | 1490 ms / 1490 ms / 1490 ms | 0/0/0 | 0/0 | 5/5/0 |

- `b1-fp` discontinuities: candidate-implied breakpoints 4 (matched 0 of 0 true, false-positive 4, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` offset recovery: true 1490 ms, applied shift -5126 ms, recovered 5126 ms, residual 3636 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-n` offset recovery: true 1490 ms, applied shift 0 ms, recovered 0 ms, residual 1490 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-al`: unsupported · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: mapping_failure_count_mismatch · reason: tool output has 1 entries vs 5 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 1.0s
- `b1-fp`: 1:1-order-preserving · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.3s
- `b1-n`: noop · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: abstain_no_speech_anchors · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-px-fp`: abstain_no_speech_anchors · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-pxo-fg`: abstain_no_speech_anchors · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-pxo-fp`: abstain_no_speech_anchors · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-va`: not_run · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Tolerances used
- good ±50 ms, severe >±250 ms, breakpoint match ±500 ms (declared evaluation tolerance for this run only; not a production threshold)
