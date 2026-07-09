# Atlas narrative-intelligence vision (Pedro, 2026-07-08)

The north star, in Pedro's words, captured verbatim-in-intent. Everything below
is GATED on the substrate fix (embedding throughput + attribution) — without
signals threaded + actors/geo attributed correctly, none of this is trustworthy.

## The layer model (roles)
- **L1 Brief** = the day as a **data table / data visualization**. What happened,
  at a glance.
- **L2 Console** = **exploration per thread**. Enter a narrative thread ("Colombia
  presidential elections") and SEE: the thread + its **sub-threads by actor**
  (De la Espriella, Cepeda, controversies), **volume + tone**, **which media
  cover it**, and the **edge = which countries of the world talk about the same
  topic**. This is where who-says-what + tone + geo-spread live.
- **L3 Workbench/dossier** = **"data about the data"** — the exposition. You pin
  threads, combine several, and the report exposes the deeper relations.

## The pin should carry the WHOLE thread (key correction)
When you pin a NARRATIVE THREAD (not just a topic) into the Workbench, it should
carry **everything the thread holds**: all its surface data, **all connected
threads**, **all people/entities it links to**. Today a pin carries only a frozen
snapshot (evidence headlines + summary); the connections are computed only at
REPORT time, over the pinned topics — they are NOT pulled in with the pin, and
the constellation is not visible incrementally as you build. GAP.

## "Actor" = ANY entity (broad)
An actor is not only a person. It is **any typed entity**: person, institution,
company, place, natural phenomenon, object, or system. The subject-typing must
span all of these (today it types person/org/group/place/event — extend to
phenomena/objects/systems). Favorability, stance, and who-says-what all key on
this broad actor set.

## The Workbench REPORT answers the 5 W's + H
The report ("brief del Workbench") targets the journalist's questions —
**who / what / when / where / how / why** — grounded in the pinned evidence.
Honest capability map per question:
- **Quién (who)** = the actors/subjects (broad set above). ← attribution must be good.
- **Qué (what)** = the event / narrative thread itself. ✓ (a thread IS the "what").
- **Cuándo (when)** = timeline + firstSeen + the temporal-propagation layer. ◐→✗.
- **Dónde (where)** = subject-geography + the countries-of-conversation edge. ◐.
- **Cómo (how)** = tone + voice (who tells it) + framing/stance. ◐ (framing missing).
- **Por qué (why)** = THE HARD ONE (Pedro: "no sé si alcance"). Atlas must NOT
  assert causation. Honest stance: surface the **causal MATERIAL** — what preceded
  what in time, which threads/actors connect, what triggered the spike — and let
  the analyst (or the brief's LLM, the one allowed AI surface) INFER the why,
  labeled as inference, never as measured fact. The propagation/origin layer is
  what makes even a partial "why" possible.

## The three deep capabilities (what "should be seen")
1. **Who says what, and HOW they say it** — the starting principle. Volume + tone
   per actor, sliced by voice (origin-country / language / press-vs-public).
   Stance/framing (who is favored, who is victim vs aggressor) is the harder layer
   on top of document tone. PARTIAL (tone+voice exist; stance missing).
2. **How the story travels in TIME** — when did it START, **after which person/
   outlet talked about it**, did everyone start **at once (coordinated)** or did
   it **propagate** one→another, and **where does more info about this topic come
   from** (the origin/source of the narrative). MOSTLY MISSING — Atlas has the raw
   material (per-signal timestamp + origin-country + source + actor) but does NOT
   assemble the propagation/origin story yet. This is the deepest layer.
3. **Coverage gaps / who is silent** — already partially built (the "what is
   missing" box). Complements 1 + 2.

## Honest map: exists / partial / missing
- ✓ L2 thread detail: volume, tone, countries, sources, key subjects, timeline,
  "active since".
- ✓ Who-says-what (press vs public) + voice-mix (self-voice by ownership).
- ◐ Sub-threads by actor (umbrella→children exists; not surfaced as per-actor
  sub-threads richly).
- ◐ The "edge" — which countries talk about the same topic (heat/flow exist; not
  a clean per-thread country-of-conversation view).
- ✗ Pin carries connected threads + entities (only a snapshot today).
- ✗ Constellation visible incrementally in the Workbench (only at report time).
- ✗ Stance/framing (who is favored) — needs a target-level layer, not doc tone.
- ✗ **Temporal propagation + origin** (who started it, coordinated vs organic,
  where the narrative comes from) — the raw material exists; the assembly doesn't.

## Sequence
1. **Substrate** (in flight): embedding throughput (task_3720e7f5) + geo/actor
   attribution (task_1b44cea1). Nothing above is trustworthy until this lands.
2. **Re-measure coverage**, then clustering recall/promotion.
3. THEN, in order of leverage: pin-carries-full-context + incremental
   constellation (Workbench) → stance/framing layer → temporal-propagation/origin.

The propagation/origin view (2) is the signature capability — "who started the
narrative, how it spread, who's silent" — the thing no black-box AI summary gives.
