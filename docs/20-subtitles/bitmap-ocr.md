# Bitmap subtitle OCR conversion

**Owner:** independent subtitle conversion · **Related:** [formats](consolidation-and-formats.md), [queue](../30-app/workflows-and-queue.md), [models](../30-app/models-and-resources.md).

## Desired operation

- Handle embedded or external bitmap subtitles such as PGS and VobSub where decoders are available; **convert image-based subtitles to text-based selectable subtitle tracks** (SRT or ASS as output policy allows). The bitmap original remains available.
- OCR is an independently queueable job, **not** required to run the complete ASR/translation/enhancement pipeline. Metadata-only bitmap language classification MAY request bounded OCR as a separately configurable escalation; when OCR is disabled, unsupported or inconclusive, report **language unassessed / needs OCR**, not a guessed correction. OCR output can become an additional source for later matching, classification, consolidation or translation.
- Record image-to-text confidence, source timestamp/bitmap reference, recognized language, bounding/position evidence when available, style reconstruction decisions, model/engine identity and uncertain characters.
- Protect against dropped glyphs, duplicate events, punctuation errors, vertical CJK text, stylized fonts, multi-line signs and overlapping captions. Low-confidence conversions go to review.
- Retain bitmap timing as input evidence; do not claim accurate native positioning, animation, font or effect reconstruction from OCR alone. Output ASS only if justified by recovered layout; SRT fallback with limitations disclosed.

## Distinction

PGS/VobSub are already **soft/selectable subtitles** in many containers; the requested operation is **bitmap-to-text conversion** so the contents can be indexed, edited, translated and improved.

**Priority:** desirable capability after core metadata, sync and text enhancement behavior is established; benchmark OCR against multilingual anime/TV subtitle material before selecting a specific engine.
