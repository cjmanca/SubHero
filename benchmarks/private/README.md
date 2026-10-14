# benchmarks/private — repository-local home for private benchmark data

This directory is the supported repository-local home for the real reference episodes
(E01 — Japanese anime, E02 — Mandarin drama) and everything derived from them.

- **Everything under `benchmarks/private/` is git-ignored except this README stub.**
  Never commit episodes, sidecar subtitle tracks, extracted audio, transcripts,
  annotations/gold files, private case manifests, logs, model outputs, or results.
- Put each episode in its own subdirectory, for example
  `benchmarks/private/E01/episode.mkv` with sidecars like
  `benchmarks/private/E01/episode.ass`.
- Case manifests for sources whose rights are not `redistributable-synthetic-fixture`
  are written automatically by `case prepare` under `benchmarks/private/cases/`;
  the committed `benchmarks/cases/` directory is only for redistributable synthetic
  fixtures.
- The CLI refuses to register media, sidecar subtitles, or gold annotations that live
  inside the repository outside `benchmarks/private/` and the synthetic
  `benchmarks/fixtures/` home. Private media may also live **outside the repository**
  on read-only mounts, which is allowed and recommended.
- Keep every registered source read-only; the harness never writes inside source roots.
