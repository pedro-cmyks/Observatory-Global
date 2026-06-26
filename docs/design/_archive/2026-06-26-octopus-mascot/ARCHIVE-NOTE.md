# ARCHIVED — Octopus Mascot exploration (2026-06-26)

**Status: PARKED. Not active work. Do not wire into the app.**

## Why archived

Decision (Pedro, 2026-06-26): the mascot is **not the right focus for Atlas
right now** — the current aesthetic is already good and simple, and pushing the
mascot further is spending time/resources better used elsewhere. The exploration
reached a solid result and is preserved here to **resume later** if/when it's
worth iterating.

## What's here

- `octopus_portrait.py` — parametric generator (Python; venv deps `shapely`,
  `numpy`). CLI: `--mode portrait|companion --size <px> --out <file> [--preview]`.
- `octopus-portrait-v16.svg` / `.png` / `-head.png` — the locked base character
  (filled biological engraving, *Octopus vulgaris* ref, ancestral eyes,
  papillae skin), duotone Atlas (navy + emerald/cream).
- `assets/octopus-portrait.svg`, `assets/octopus-companion.svg` — SVGO-optimized
  exports (were briefly under `frontend-v2/src/assets/mascot/`, removed from live
  source on archive).
- `octopus-mascot-design.md` — design spec (rationale, two modes, rejected
  directions, motion).
- `octopus-mascot-implementation.md` — implementation spec; T1–T3 done
  (generator hardened, companion mode, export+SVGO), T4–T6 (React component,
  Brief loader, docs) NOT done.

## How to resume

```bash
# render loop used during design (from a venv with shapely+numpy; resvg installed via brew)
python octopus_portrait.py --mode portrait --preview --size 900 --out /tmp/p.svg
resvg /tmp/p.svg /tmp/p.png -w 900
```

## Decisions worth keeping (so we don't re-litigate)

- Treatment = **filled vector engraving** (v16). Line-art was tried and REJECTED
  as a regression.
- Palette = duotone Atlas tokens only; never the data-viz/typed-node octopus,
  never costumes, never the cute-pet style.
- Two intended modes: **portrait** (loader/brand/favicon) + **companion**
  (ghosted, woven among editorial text — the "lives among the letters" idea).
- Idea floated but not built: a **code-rain loading panel** (tiny box of text/
  characters; characters dim/shift as the octopus passes over them).

GitHub #106 stays open/parked; not updated as part of this archive.
