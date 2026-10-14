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

- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · input a84e2df85cc5b52d… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · input e9f7024ead4ff072… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.6s
- `b1-fp`: 1:1-order-preserving · input 76748ab42cd36c7f… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.3s
- `b1-n`: noop · input 9d454e62208bb91a… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input b91f664dbaf394b0… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.2s
- `b1-px-fp`: 1:1-order-preserving · input 92dd3dd5cea61087… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.1s
- `b1-pxo-fg`: 1:1-order-preserving · input cbd7491e1a8b553f… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.8s
- `b1-pxo-fp`: 1:1-order-preserving · input 3d4a4ba0c8873a03… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.9s
- `b1-va`: not_run · input 1e71efcf53c334b1… · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

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

- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 17 (matched 0 of 0 true, false-positive 17, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 17 (matched 0 of 0 true, false-positive 17, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 17 (matched 0 of 0 true, false-positive 17, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 17 (matched 0 of 0 true, false-positive 17, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 17 (matched 0 of 0 true, false-positive 17, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fg` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-fp` offset recovery: true 1900 ms, applied shift -1882 ms, recovered 1882 ms, residual 18 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-n` offset recovery: true 1900 ms, applied shift 0 ms, recovered 0 ms, residual 1900 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-px-fg` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-px-fp` offset recovery: true 1900 ms, applied shift -1881 ms, recovered 1881 ms, residual 19 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-pxo-fg` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-pxo-fp` offset recovery: true 1900 ms, applied shift -1881 ms, recovered 1881 ms, residual 19 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-va` offset recovery: true 1900 ms, applied shift -1900 ms, recovered 1900 ms, residual 0 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-al`: unsupported · input 4bba075c094cd29d… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · input a0307552c9b90fd6… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.2s
- `b1-fp`: 1:1-order-preserving · input 15dc34d3b93e2196… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.5s
- `b1-n`: noop · input 5bc90d0d3f268287… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 0128b0eb67af5066… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.2s
- `b1-px-fp`: 1:1-order-preserving · input a960eb716b61a80c… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.2s
- `b1-pxo-fg`: 1:1-order-preserving · input 4d48a289f56a37be… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.8s
- `b1-pxo-fp`: 1:1-order-preserving · input f59d30bb8e258905… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.9s
- `b1-va`: not_run · input d8e59147b84eef3a… · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

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

- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · input b3ec25a9cd5680fa… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · input 8a76b4962fcb6385… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.2s
- `b1-fp`: 1:1-order-preserving · input bb0fd2867d39d40e… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 2.1s
- `b1-n`: noop · input 5e6068688cd263f4… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 19dce278e36a6039… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.4s
- `b1-px-fp`: 1:1-order-preserving · input b1ab8c08de911672… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.4s
- `b1-pxo-fg`: 1:1-order-preserving · input d66b3d0c1d8564cc… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.8s
- `b1-pxo-fp`: 1:1-order-preserving · input 98e4339db49f7af2… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.9s
- `b1-va`: not_run · input 4803229e423448d8… · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S03` (scenario S03)

| Candidate | Status | Proposals | Accepted | Repaired | Worsened | Harmful prop/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b1-n | noop | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 8340 ms / 8340 ms | 0/0/0 | 1/1 | 24/5/19 |
| b1-px-fg | 1:1-order-preserving | 15 | 15 | 0 | 4 | 4/4 | 40 ms / 8281 ms / 8340 ms | 0/0/0 | 1/1 | 24/5/19 |
| b1-px-fp | 1:1-order-preserving | 15 | 15 | 0 | 1 | 1/1 | 30 ms / 8291 ms / 8340 ms | 0/0/0 | 1/1 | 24/5/19 |
| b1-pxo-fg | 1:1-order-preserving | 15 | 15 | 0 | 4 | 4/4 | 40 ms / 8281 ms / 8340 ms | 0/0/0 | 1/1 | 24/5/19 |
| b1-pxo-fp | 1:1-order-preserving | 15 | 15 | 0 | 1 | 1/1 | 30 ms / 8291 ms / 8340 ms | 0/0/0 | 1/1 | 24/5/19 |
| b1-va | not_run | 15 | 0 | 0 | 0 | 4/0 | 0 ms / 8340 ms / 8340 ms | 0/0/0 | 1/1 | 24/5/19 |

- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 1 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 1 of 1 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · input 59ab2b9303885d7c… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: mapping_failure_ambiguous_text · input b7a8e64495c8c73d… · reason: tool rewrote events: normalized text mismatch at position 16 (cue e0016): input 'That is the third time today.' vs output 'I will make fresh leaves.'; 24 outputs vs 24 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 1.2s
- `b1-fp`: mapping_failure_ambiguous_text · input cc1ca0c447d15e6c… · reason: tool rewrote events: normalized text mismatch at position 16 (cue e0016): input 'That is the third time today.' vs output 'I will make fresh leaves.'; 24 outputs vs 24 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 1.5s
- `b1-n`: noop · input f6ce09f0c1761176… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input eda4f279e1a05826… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.4s
- `b1-px-fp`: 1:1-order-preserving · input 36c2a7d1e52bd10d… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.8s
- `b1-pxo-fg`: 1:1-order-preserving · input 2d8c1424713aa8f7… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.9s
- `b1-pxo-fp`: 1:1-order-preserving · input e52c114745610896… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.2s
- `b1-va`: not_run · input e127cfeb03a23e04… · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-S04` (scenario S04)

| Candidate | Status | Proposals | Accepted | Repaired | Worsened | Harmful prop/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b1-n | noop | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 3540 ms / 4420 ms | 0/0/0 | 0/0 | 24/5/19 |
| b1-px-fg | 1:1-order-preserving | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 3540 ms / 4420 ms | 0/0/0 | 0/0 | 24/5/19 |
| b1-px-fp | 1:1-order-preserving | 15 | 15 | 0 | 2 | 2/2 | 22 ms / 3540 ms / 4420 ms | 0/0/0 | 0/0 | 24/5/19 |
| b1-pxo-fg | 1:1-order-preserving | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 3540 ms / 4420 ms | 0/0/0 | 0/0 | 24/5/19 |
| b1-pxo-fp | 1:1-order-preserving | 15 | 15 | 0 | 2 | 2/2 | 22 ms / 3540 ms / 4420 ms | 0/0/0 | 0/0 | 24/5/19 |
| b1-va | not_run | 0 | 0 | 0 | 0 | 0/0 | 0 ms / 3540 ms / 4420 ms | 0/0/0 | 0/0 | 24/5/19 |

- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · input 0b0732df8b0d7f32… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: mapping_failure_ambiguous_text · input 471551bf433a5f3c… · reason: tool rewrote events: normalized text mismatch at position 4 (cue e0004): input 'I heard that too.' vs output 'Singing loud'; 24 outputs vs 24 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 5.0s
- `b1-fp`: mapping_failure_ambiguous_text · input c04938ff8315ab3a… · reason: tool rewrote events: normalized text mismatch at position 4 (cue e0004): input 'I heard that too.' vs output 'Singing loud'; 24 outputs vs 24 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 1.3s
- `b1-n`: noop · input 8d17e9fce5db49ef… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input 793bdf2cf834fb4e… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.4s
- `b1-px-fp`: 1:1-order-preserving · input c32d46326e44f540… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 2.2s
- `b1-pxo-fg`: 1:1-order-preserving · input 830e1309f5354104… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.9s
- `b1-pxo-fp`: 1:1-order-preserving · input 10b13eddcc95beb4… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 1.0s
- `b1-va`: not_run · input 83e8de7e6dcd8e35… · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

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

- `b1-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-px-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fg` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-pxo-fp` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-al`: unsupported · input 50faeae8f8b7cb9a… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: 1:1-order-preserving · input bc5e8f496314ee3c… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 3.8s
- `b1-fp`: 1:1-order-preserving · input aaaefa6ee0626681… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 3.3s
- `b1-n`: noop · input aa89db4dfa8f6708… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: 1:1-order-preserving · input c3177717eef9bb19… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 1.1s
- `b1-px-fp`: 1:1-order-preserving · input cde2dd329fda78f5… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 5.3s
- `b1-pxo-fg`: 1:1-order-preserving · input f3689a877355ce71… · reason: ffsubsync fg; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.8s
- `b1-pxo-fp`: 1:1-order-preserving · input fd8d45f6306a0aa4… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals); oracle-assisted diagnostic arm (uses gold cue labels; excluded from --all; not a default candidate) · preprocess 0.0s · candidate 0.9s
- `b1-va`: not_run · input 6837ae0d41b91c25… · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Case `Fx00-SGN01` (scenario S01)

| Candidate | Status | Proposals | Accepted | Repaired | Worsened | Harmful prop/acc | Median/P90/P95 final onset err | Breaks implied/matched/false+ | Breaks unresolved/true | Denominator (cues: total/altered/unaltered) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b1-fp | 1:1-order-preserving | 5 | 5 | 0 | 0 | 5/5 | 3636 ms / 4703 ms / 4703 ms | 4/0/4 | 0/0 | 5/5/0 |
| b1-n | noop | 0 | 0 | 0 | 0 | 0/0 | 1490 ms / 1490 ms / 1490 ms | 0/0/0 | 0/0 | 5/5/0 |
| b1-va | not_run | 0 | 0 | 0 | 0 | 0/0 | 1490 ms / 1490 ms / 1490 ms | 0/0/0 | 0/0 | 5/5/0 |

- `b1-fp` discontinuities: candidate-implied breakpoints 4 (matched 0 of 0 true, false-positive 4, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-n` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-va` discontinuities: candidate-implied breakpoints 0 (matched 0 of 0 true, false-positive 0, ambiguous 0, jump threshold 250 ms); final timeline still discontinuous at 0 of 0 true breakpoints (0 without a straddling cue pair)
- `b1-fp` offset recovery: true 1490 ms, applied shift -5126 ms, recovered 5126 ms, residual 3636 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-n` offset recovery: true 1490 ms, applied shift 0 ms, recovered 0 ms, residual 1490 ms (applied shift is what the candidate moved the subtitles; exact recovery means applied_shift == -true_offset)
- `b1-al`: unsupported · input 41440e0665ccc660… · reason: alass executable not available · preprocess 0.0s · candidate 0.0s
- `b1-fg`: mapping_failure_count_mismatch · input 038efc0c0a010984… · reason: tool output has 1 entries vs 5 inputs; refusing to guess correspondence · preprocess 0.0s · candidate 0.9s
- `b1-fp`: 1:1-order-preserving · input 4e71612e717fb15f… · reason: ffsubsync fp; full-track flattened timing proposals only (formatting never applied to originals) · preprocess 0.0s · candidate 0.9s
- `b1-n`: noop · input 5e3e9d47fb2a78f8… · reason: no changes proposed · preprocess 0.0s · candidate 0.0s
- `b1-px-fg`: abstain_no_speech_anchors · input 47a1471ce517a36e… · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-px-fp`: abstain_no_speech_anchors · input 0e3bd20fa8e8a61e… · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-pxo-fg`: abstain_no_speech_anchors · input ec60b7c58b600ee7… · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-pxo-fp`: abstain_no_speech_anchors · input 979d084d513f38b2… · reason: no speech-like cues in track; signs-only/anchorless tracks stay unmapped · preprocess 0.0s · candidate 0.0s
- `b1-va`: not_run · input 348655f140b324ba… · reason: no local ASR endpoint configured (BENCH_ASR_BASE_URL/BENCH_ASR_MODEL); validation not run; original timing retained

## Tolerances used
- good ±50 ms, severe >±250 ms, breakpoint match ±500 ms (declared evaluation tolerance for this run only; not a production threshold)
