# B1 — Lightweight synchronization and targeted-ASR validation

**Status: pending. First algorithm benchmark after B0.** **Requirements owner:** [subtitle timing](../../20-subtitles/lightweight-and-full-synchronization.md). **Shared scoring:** [criteria](evaluation-criteria.md); inputs: [fixtures](corpus-and-fixtures.md).

## Hypotheses to test

1. Global **ffsubsync** accurately fixes ordinary offsets at low cost; its experimental `--split-penalty` and **ALASS** may also handle release discontinuities.
2. A **temporary dialogue-only synchronization proxy** reduces false alignments from signs, karaoke and SDH events without damaging source ASS data.
3. **Targeted ASR with cross-language semantic checking** can reject bad timing proposals that a VAD overlap score alone would accept.
4. If no safe alignment exists, **no-op/abstain** is preferable to forcing a shift; a custom mapper is justified only by demonstrated failures of cheaper candidates.

## Controlled candidate matrix

| Arm | Candidate | Important controls |
| --- | --- | --- |
| B1-N | No change | Cost, no regression, known errors left unresolved |
| B1-FG | ffsubsync global (audio/VAD reference) | Exact version, flags, framerate behavior |
| B1-FP | ffsubsync piecewise with `--split-penalty` | Split cost/penalty, false breakpoint rate |
| B1-AL | ALASS | Same audio track/input windows where supported |
| B1-PX | Dialogue-only proxy applied to applicable arms | Event classifier quality; original ASS event IDs retained |
| B1-VA | Same best proposal **with** targeted ASR + semantic validation | Same proposed changes as unvalidated arm, to isolate validator value |

First test untouched S00, global ± S01, drift S02, jumps S03, isolated cue errors S04 and sign-heavy S06. Add **actual edited footage**, not merely a timestamp jump, before claiming release-edit support. Vary perturbation size and number of jumps; include portions that were already correctly timed. No algorithm is allowed to mutate the reference subtitle track.

## Candidate extraction and application

Generate a temporary speech-like subtitle proxy, excluding sign/written-text, song/karaoke, accessibility sound descriptions and non-speech events as audio anchors. Do not assume all ordinary dialogue is monophonic or clean. Keep an ID map between proxy events and original track events; test whether a candidate tool's output can reliably produce **global/region-level mapping** for originals. If a candidate emits only a rewritten SRT and lacks a reliable split/mapping interface, record this adapter limitation. Do **not** ship/score its flattened ASS output as the final subtitle.

Represent each source subtitle track with **its own** inferred mapping to the common media timeline. A signs-only track with no speech anchors may receive a validated sibling-track mapping only if related release evidence exists; otherwise abstain and preserve original timing. Apply mapped offsets rigidly to animated events; do not stretch duration-relative movement or karaoke without proof of safety. A discontinuity must not silently propagate across unmapped scenes.

## ASR validation experiment

Select verification regions at the **beginning/middle/end**, **before and after each inferred split**, low-evidence regions, unusually large timing changes, and independently distributed random controls. Compare fixed sample counts against adaptive sampling. A valid match requires **correspondence of the specific spoken utterance to the candidate subtitle**, not merely speech activity at its timestamp. **B1 can use a small fixed targeted-ASR/translation verifier without implementing the later B2 full-episode ASR and B3 matcher**; human gold labels are reserved for scoring, not fed into this validator as answers. Native-language subtitles can provide extra evidence, but only when their source and alignment are credible. Use bounded, source-language targeted ASR; translate/check semantics selectively. Isolate validation cost from candidate generation cost.

Escalate to more sampling or full ASR **only when policy permits**; when uncertainty persists, reject the affected change and retain the original timing. Do not let validation on one region justify unrelated offsets or a jump's other side.

## Required report and decision

For every arm/scenario report median/P90/P95 cue timing errors, recovered offset/drift, number/position of true and false splits, **already-correct cues made worse**, accepted harmful corrections, abstention, edit coverage, runtime, ASR seconds/calls and reasons for rejected regions. Report real edit-release/unmatched sections distinctly.

Decision after G1: accept an existing guarded candidate, identify a case-specific fallback, or justify **precisely which failure requires** a custom synchronizer. Do not select ffsubsync/ALASS merely because a score is high. Upstream candidate docs: [ffsubsync](https://github.com/smacke/ffsubsync), [ALASS](https://github.com/kaegi/alass).
