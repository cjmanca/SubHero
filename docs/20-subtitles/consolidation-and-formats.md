# Combining subtitle tracks without damaging ASS/SSA formatting

**Owner:** enhancement compositor · **Related:** [sources](source-selection-and-ancestry.md), [sync](lightweight-and-full-synchronization.md), [readability](readability-and-accessibility.md).

## Merge semantics

- Merge **semantic events**, not whole files. Align each source independently to the common media timeline first. Deduplicate semantically equivalent dialogue/sign/song cues; select best content using evidence and preserve base-track translation style.
- A full track should contain its signs/songs; borrowing an excellent positioned sign from a reduced forced track can replace an inferior top/bottom sign in the base. Do not display both if they express the same information.
- Preserve deliberate overlaps from **one** source track. Overlap newly introduced by combining tracks or moving cues must be detected; resolve by safe repositioning/scaling within limits, scheduling adjustments, merging spoken lines, or review. Never blindly flatten/concatenate entire tracks.
- For standard dialogue borrowed from other tracks, use the **base track's style**; import foreign track styles **only when needed** for positioned signs, karaoke and other meaningful graphic effects.

## ASS/SSA-specific invariants

- Treat events as structured graphical/timed objects, not plain strings. Preserve event IDs, style definitions, fonts/attachments where possible, margins, colors, layers, alignment, and existing override tags. Preserve unrelated **ASS script-info fields, custom metadata, style/event ordering, and comments** when round-tripping or importing content.
- Preserve original **raw subtitle bytes and encoding evidence** (encoding/BOM, newline convention, invalid-sequence diagnostics, and Unicode text). Timing-only or metadata-only processing must not silently transcode character data, normalize Unicode, replace undecodable bytes or rewrite line endings. If an input is not safely decodable/round-trippable, flag it rather than performing a lossy write. New generated outputs may use a documented target encoding (e.g. UTF-8) while retaining the untouched source representation.
- When importing between scripts with different `PlayResX`/`PlayResY`, transform coordinate systems consistently for positions, movement, origins, clipping and vector drawings. Account for aspect/scaled border behavior; test real renderer output.
- Avoid collisions in style names, font dependencies, layers and multi-event animation groups. `\pos`, `\move`, `\org`, `\clip`, `\t`, karaoke tags and relative animation times require aware handling; never rewrite these as plain text.
- Preserve animations/effects as-is except validated rigid timing shifts when necessary. A duration change can retime movement when animation spans the cue duration; default to **not stretching complex animated events** without proof of preservation.
- Off-screen positioning is NOT necessarily an error: a scrolling sign may intentionally enter/exit the frame. Optional **procedural** rendering validation must understand animated trajectories and not flag all offscreen frames. AI-vision rendering inspection is unnecessary/undesired for the primary quality gate.

## Three configurable output-format policies

1. **Allow ASS generation/promotion:** if *any selected output event* requires ASS-specific styling/positioning/animation (e.g. imported positioned sign or karaoke), produce **ASS** even with an SRT base. Import needed styles/dependencies and transform coordinates rather than flattening the event; ASS may also be chosen for separate background dialogue.
2. **Keep source format class:** determine the output class from the selected **base/main-dialogue track**: ASS base → ASS; SRT base → SRT. With an SRT base and selected ASS-only alternate content, preserve text where representable in SRT, but do **not** silently import unsupported positioning/animation or drop important events. Expose the conflict/loss in review with a choice to accept a safe flattened alternative, omit genuinely nonessential content explicitly, or change to ASS-permitted mode. Do not override this user-selected format restriction merely because an alternate track uses ASS.
3. **Force SRT:** output SRT regardless of inputs; attempt complete text preservation first, then prioritize essential dialogue and relevant signs when simultaneous layers cannot be made readable. Surface format/animation/positioning loss, omitted events and any needed approval; never claim ASS graphics or karaoke animation survive.

**Precedence:** intentional source-event preservation governs selection *within* the chosen output mode, but explicit format restrictions override automatic ASS promotion. Lossy conversions must be explained and reviewed as configured; important semantic content must not disappear silently. Exact mixed-source quality thresholds/preview UX remain subject to validation (see [E16](../40-delivery/open-questions-and-experiments.md)).

Because multi-track combination can introduce new dependencies, generated track needs format-aware validity checks and group-level review. External ASS font behavior with Plex clients must be tested; embedding is available when needed.
