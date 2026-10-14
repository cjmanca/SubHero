# Primary technical references and verification boundaries

These are **reference links, not fixed dependencies**. The requirements are drawn from project decisions; cited documents support specific tool/platform capabilities. Verify installed versions again when implementing. Snapshot reviewed: 2026-10-13.

| Topic | Primary source | Relevant note |
| --- | --- | --- |
| Plex audio/subtitle selection | https://support.plex.tv/articles/204985278-account-audio-subtitle-language-settings/ | MKV default flags ignored; forced/language semantics; unknown language handling |
| Plex local subtitle naming | https://support.plex.tv/articles/200471133-adding-local-subtitles-to-your-media/ | External `en`, `forced`, `sdh`, `cc` naming and subtitle directories |
| Plex subtitle configuration | https://support.plex.tv/articles/200471113-configuring-subtitle-support/ | Forced behavior depends on account subtitle mode |
| Plex API | https://developer.plex.tv/pms/ | Targeted `PUT /library/metadata/{ids}/analyze` |
| Plex commentary flag report | https://forums.plex.tv/t/plex-media-scanner-crashes-on-tracks-with-flagcommentary-1/938513 | 2026 Linux scanner regression report; **test installed versions**, not proof of universal/current failure |
| MKV headers | https://mkvtoolnix.download/doc/mkvpropedit.html | Edit track language/name/flags without a full remux |
| Matroska spec | https://www.rfc-editor.org/rfc/rfc9559.html | Track flags/languages/container concepts (check supported version details) |
| ffsubsync | https://github.com/smacke/ffsubsync | Experimental `--split-penalty` piecewise; optional multi-segment/quality controls |
| ALASS | https://github.com/kaegi/alass | Language-agnostic subtitle sync baseline |
| Qwen3-ASR/ForcedAligner | https://github.com/QwenLM/Qwen3-ASR | Language capabilities, ASR + forced alignment, model/runtime limits |
| Qwen aligner toolkit code | https://github.com/QwenLM/Qwen3-ASR/blob/main/qwen_asr/inference/utils.py | Some runtime guards are narrower than high-level README descriptions |
| Hy-MT2 | https://github.com/Tencent-Hunyuan/Hy-MT2 | Candidate target-language translation models |
| SONAR multilingual embeddings | https://github.com/facebookresearch/SONAR/blob/main/LICENSE.md | Code license differs from some pretrained model licenses (notably text encoder); check weights and intended use before adoption |
| ASS tags | https://aegisub.org/docs/latest/ass_tags/ | Relative animation timing, positioning, clipping, style conventions |
| Python filesystem | https://docs.python.org/3/library/os.html#os.replace | Replace semantics; confirm same-filesystem behavior of mounted paths |
| Unraid shares | https://docs.unraid.net/go/shares/ | `/mnt/user` logical shares span disks/pools; test FUSE commit behavior |

## Not established by the links above

- Universal Plex **external-over-embedded** selection, Plex commentary-flag suppression, or audio-channel precedence on every client.
- Atomic rename guarantees across every `/mnt/user` backing disk/pool combination.
- That any given model is sufficiently accurate on particular anime/TV dialogue, or that a model confidence percentage is calibrated.
- Consistent arbitrary external `.en.<release-group>.ass` naming support and player-visible descriptions.

Those are explicitly experimental items in [`open-questions-and-experiments.md`](open-questions-and-experiments.md).
