# B4 — Translation accuracy, selective correction and glossary context

**Status: pending, requires reliable gold utterance↔subtitle matches.** **Requirements owner:** [matching/translation](../../20-subtitles/matching-and-translation.md) and [glossaries](../../20-subtitles/series-glossary.md). **Shared scoring:** [criteria](evaluation-criteria.md).

## Aim

Show that proposed modifications improve **source-grounded meaning** more often than they harm good human subtitles. Don't measure success by producing smoother English or by how many cues were changed. Source-language speech is authoritative, but **ASR's transcript is fallible**. Existing native-language subtitles, nearby conversations, confirmed glossary and human interpretation may be needed to challenge ASR.

## Candidates and ablations

| Arm | Source-grounded procedure | Key variable |
| --- | --- | --- |
| T-N | Keep base-track text unchanged | No-edit control |
| T-I | Independent Hy-MT2-1.8B translation versus existing cue | Translation-first evidence |
| T-D | Direct multilingual critique of original speech text + existing target cue | Identify actual meaning discrepancy without gratuitous rewrite |
| T-H | Cheap verification, escalate only on disagreements (e.g. Hy-MT2-7B or stronger approved model) | Precision/cost of selective escalation |
| T-X | Above arms with native-language subtitles / confirmed series glossary / independent alternate tracks | Independent contextual evidence |

Pin models, prompts, context windows, generation settings and *translation target language*. Default presentation should lean toward faithful subtitled dialogue and the selected base track's established style—not gratuitous dub-like localization. Include configurable cultural-idiom/honorific preferences as **test profiles**, not as competing definitions of basic semantic correctness.

## Evaluation cases

Use human-verified examples with planted errors: reversed **negation**, numbers/time/quantities, names, dropped clauses, speaker vs **referent** pronouns (Mandarin `tā` ambiguity), idioms, relationships and emotional tone. Pair each with a broad set of **correct original lines and legitimate stylistic paraphrases**. Include code-switching, source ASR mishearings, glossary contradictions, dub-dialogue paraphrases, copied subtitle ancestry and long scenes needing context.

Keep **translation for matching** separate from **final display optimization**: an adequate semantic paraphrase may not meet CPS and line limits; a visually short rewrite may omit essential meaning. Compare change suggestions before readability edits, then measure any degradation caused by condensation or glossary substitutions. If context can't resolve identity or gender, preserve ambiguity or request review—do not reward invented certainty.

## Human judgment and release gate

Human references (preferably reviewer unfamiliar with which model proposed the change) should classify each proposal as *genuine improvement*, *equivalent/stylistic*, *worse*, or *uncertain*, with high-severity error tags. **The candidate translator must not serve as sole judge of its own output.** Measure correction precision/recall on planted and real mistakes, false modifications of good text, semantic severity, preservation, resource cost and reviewer burden; separate automatic accepted changes from all suggestions.

At G4 choose policy/model/escalation only for cases where error precision is demonstrably acceptable, otherwise leave translation unchanged or require manual review. Hy-MT2 1.8B vs 7B is a candidate comparison, not a quality fact. [Hy-MT2 model family](https://github.com/Tencent-Hunyuan/Hy-MT2).
