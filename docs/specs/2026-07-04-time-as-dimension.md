# Time as a dimension, not a filter (2026-07-04 night, Pedro — DESIGN SPEC)

Pedro: *"El tiempo debería estar mostrándose siempre. La pestaña de tiempo
solo debería afectar el globo y el universo. Los hilos se mueven solos por
velocidad y reciencia — pero la persistencia en el tiempo también dice mucho
de una historia. Si una historia tuvo un pico de volumen en el pasado, poder
mirar hacia atrás dice qué estaba pasando. El tiempo podría ser un scroll en
el globo y el universo, como ya lo es en la órbita — una dimensión de cómo
mostramos las cosas."*

## Current state (honest)

- The global time-range dropdown (24h/48h/7d…) WINDOWS THE DATA everywhere:
  threads list counts, theme details, map heat. It was compacted (#152),
  never removed — no prior decision to remove it existed.
- The universe (07-02) and orbital already have TIME SCRUBBERS — Pedro's
  model shipped there: scrub births/decays/trajectories WITHOUT changing the
  data window. The globe has none. Threads are windowed.

## The thesis (adopted as target architecture)

1. **Data is never windowed by a UI tab.** Threads exist on their FULL
   timeline; the ranking moves by velocity + recency naturally (changed_10h
   already does this). A long-lived story's AGE and PERSISTENCE are first-
   class signals, not artifacts to filter out. "Active since June 12" beats
   "started 23h ago" (feeds from the archive warm tier — see flywheel doc).
2. **The time control becomes a SCRUBBER, per visual surface** (globe +
   universe + orbital — one interaction language): scrubbing moves WHAT THE
   VIEW SHOWS (heat at that moment, bodies alive at that moment, positions
   on their trajectories) — never what the system knows.
3. **Looking back is an investigative act**: a story page shows its
   volume-over-life sparkline (full history); clicking a past PEAK answers
   "¿qué estaba pasando ese día?" — the evidence sample of that window
   (archive-backed beyond the hot 7d).
4. Persistence surfaces in ranking honestly: volume(log) + movement +
   coherence stays, but AGE/persistence becomes a visible attribute (chip:
   "3 weeks alive · peaked Jun 12"), not a hidden bias.

## Build slices (post-3-day-route; mostly small-model-executable)

- S1: Globe time scrubber (reuse the universe scrubber pattern; heat/markers
  replay from the daily timeline already served per node). Frontend-only.
- S2: Thread AGE chip + full-life sparkline in ThemeDetail (data: first_seen
  from dynamic_topics + emergent snapshot series; archive extension later).
- S3: Peak drill-down ("click the spike"): theme detail accepts a day param
  and serves that day's evidence window (hot DB ≤7d now; archive warm tier
  extends it — DuckDB endpoint or precomputed per-day slices).
- S4: Demote the global time dropdown to a VIEW control (it drives the
  scrubbers' default window, not the data); threads list stops windowing.
  ⚠ biggest semantic change — needs its own session + Pedro eyeball on
  counts (the #214 count-honesty contract must survive).

## Cross-refs

- Flywheel/history-as-asset doc (the archive powers S2/S3 beyond 7d).
- Crisis-as-dynamics reframe (velocity/surprise = the movement lens; time
  scrubbing = the same 'state over content' philosophy applied to the UI).
- Universe spec §I (decay-not-cliff; the scrubber semantics already agree).
