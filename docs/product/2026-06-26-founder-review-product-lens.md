# Founder Review — Atlas (product-lens, Mode 2)

Date: 2026-06-26 · Lens: founder / YC-office-hours. Diagnosis, not a roadmap.

## What is this trying to be?
An **open-signal narrative-intelligence product** — "news weather-radar": sees how
narratives move across countries / sources / languages / public attention, and is
**honest about its own coverage** (gated-vs-raw, voice-mix bias, press-vs-public,
forums-in-the-inference, semantic connections, frozen-pin dossiers).

The moat is real and rare: **most tools give answers; Atlas gives a narrative +
the receipts on what it knows and whose voice is missing.** That is hard to copy.

## PMF signals (0–10, honest)
| Signal | Score | Why |
|---|---|---|
| **Usage growth** | **1** | No product analytics. Can't see if anyone uses it. A waitlist exists (demand capture), but no active-user trajectory. |
| **Retention** | **0–1** | No accounts, no saved state across devices (workbench is per-browser localStorage), no return-user signal. Nothing to retain *to*. |
| **Revenue** | **0** | No billing / pricing / checkout anywhere. |
| **Moat / differentiation** | **8** | The self-auditing honesty layer + multi-source/multilingual pipeline + the search→pin→report loop. Genuinely defensible. |
| **Build velocity** | **9** | 175 commits / 14 days, solo. Supply side is screaming fast. |

**Diagnosis: a supply-rich, demand-blind product.** Enormous, defensible
capability; zero validated demand. We are building the *machine*, not yet proving
the *market*.

## The ONE thing that would 10x this
Not another surface. **Pick ONE user and ONE job, instrument time-to-value, and
get 5 real people doing that job weekly.**

Today Atlas is a brilliant *console* for an undefined analyst. The 10x move is to
collapse it to a sharp wedge, e.g. *"a regional risk analyst / journalist who needs
the real story + sources behind a specific event in under 2 minutes, honestly
caveated."* Everything we shipped (truncated threads, forums-in-inference,
dossier) **serves that job** — but no one is doing the job yet because there's no
user, no account, no measurement.

## What we're building that may not matter (yet)
- **More console depth without a user.** The depth is excellent and the moat —
  but past a point it's supply with no demand feedback. We have no signal on which
  of the 4 map layers / 4 tabs anyone actually uses.
- **Polishing the analyst surface before there's an analyst.** Phase 3 dossier is
  great; it has zero users today.
- *(Not on this list: the processing pipeline #240/#241. That IS load-bearing —
  the moat is the honesty/connectedness, which the pipeline delivers. Fix it.)*

## Go / no-go
**GO — but pivot the next two weeks from supply to demand.** The product is real
and differentiated. The risk is building a perfect machine no one is using.

## Next steps (specific)
1. **Instrument time-to-value.** Add lightweight analytics (one event: "user got a
   first useful answer" — opened a thread's evidence / generated a dossier).
   Without this we're flying blind. *(1 day.)*
2. **Define the wedge user + job** in one sentence; write it at the top of
   CLAUDE.md and the Landing. Kill features that don't serve it. *(½ day.)*
3. **Minimal return loop**: accounts + one saved watch + one alert (the
   persist→deliver→alert loop already named in the product-gap doc). Converts a
   browse tool into a product someone comes back to. *(the real next build.)*
4. **5 users doing the job weekly** before adding more console depth. Recruit from
   the waitlist. Measure: do they return?
5. **Keep fixing the pipeline (#240/#241)** — it's the moat's delivery, not a
   distraction.

## Anti-goal
Do NOT add a 5th map layer, a 6th source family, or a new surface until #1–#4
above produce a usage signal. More capability without a measured user is the trap.
