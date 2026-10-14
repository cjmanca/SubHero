# B3 — Cross-language utterance-to-subtitle correspondence

**Status: pending.** **Requirements owner:** [matching and translation](../../20-subtitles/matching-and-translation.md), [sources/ancestry](../../20-subtitles/source-selection-and-ancestry.md). **Shared scoring:** [criteria](evaluation-criteria.md).

## Question

Which approach most accurately maps **timed source-language utterances** to each existing target-language subtitle track, despite alternative phrasing, release timing differences, subtitles merged/split across sentences, omitted dialogue and independent or copied translations?

**Matching is not translation verification.** Two sentences can embed closely despite negation differences. A high correspondence score means only that they probably refer to the same utterance, not that the subtitle represents its meaning faithfully.

## Fair comparison

Freeze a verified source-language transcript and utterance segmentation, a fixed subtitle event set, and known gold links. Compare:

1. **Direct cross-lingual embeddings** (e.g. LaBSE; SONAR only if its selected **model weights** are compatible with intended licensing) to retrieve candidate cue/group links.
2. **Translation-first:** translate source utterances with pinned Hy-MT2 candidate settings, then candidate retrieval using target-language text/semantics.
3. **Hybrid:** direct embeddings for candidate generation, targeted translation or multilingual LLM adjudication when ambiguous; apply the same global constrained sequence solver as other arms where possible.
4. **No-semantic baseline:** order/weak-time + structural constraints to establish benefit attributable to semantic representation.

Keep candidate generation and sequence alignment stages **separately scored**. Holding candidate lists fixed isolates whether dynamic programming/gap/merge rules help. When measuring complete pipelines, include translation/embedding model costs and failures.

## Stress cases

- 1:1, **one utterance→multiple cues**, **multiple utterances→one cue**; intentional condensed repetition, deleted subtitle, unrecoverable ASR line and unrelated inserted cue.
- Major global and piecewise timing differences; **do not make initial timestamps the primary retrieval constraint**. Validate per-track timeline mapping after confidence-filtered anchors, including true missing scenes and unmatched spans.
- Very short or generic repeated dialogue ("Yes", "Wait", "What?") that could lead to many plausible but incorrect matches.
- Song lyrics, signs, on-screen text, SDH captions and commentary: classify and exclude from ordinary speech anchors, not silently force-match.
- Two English tracks with common translation ancestry, one independent candidate, native-language subtitles, dub-matched sources; **do not count copied translations as independent votes**.
- Incorrect source transcription as a second pass *after* fixed-transcript comparison, to quantify propagated ASR errors.

## Scoring and decision

Gold correspondence is a **set of linked cue/utterance groups with explicit unmatched elements**, not an assumption of one-to-one sentences. Report group precision/recall and wrong forced links; retrieval candidate recall@K separately from final accepted link precision; abstention and false missing-dialogue claims; monotonic/gap/breakpoint errors; cost per accepted reliable link; variation across languages/release types.

At G3 choose the **least costly reliable** candidate generator/solver and an escalation rule. If ambiguous repeated phrases remain uncertain, leave them **unmatched/reviewed** rather than contaminating a timing map or inventing dialogue. [SONAR upstream](https://github.com/facebookresearch/SONAR) (code and pretrained-weight licenses differ); [Hy-MT2 upstream](https://github.com/Tencent-Hunyuan/Hy-MT2).
