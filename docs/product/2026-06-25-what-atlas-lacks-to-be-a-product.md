# What Atlas lacks to be a product — honest assessment (2026-06-25)

Grounded in the codebase, the open-issue backlog, and the live re-evaluation
done this session (the Brief leading with a syndicated opinion column, geo
mislabeling Australia as France, country chips that omit the actual subject
country, duplicate threads). Those bugs aren't trivia — they ARE the gap.

## What Atlas IS today (be fair)
A genuinely deep narrative-intelligence **engine** with a sophisticated
multi-surface UI: GDELT/RSS/Trends/Wikipedia ingest, dynamic narrative
threads, e5 semantic retrieval, who-says-what, focus propagation, a diversity
program (219 feeds / 126 countries / `voice_entropy` 0.71), a research-plan +
Workbench investigation flow, all deployed (Fly + Vercel). The thesis is real
and differentiated. There's even a waitlist + a Workbench waitlist gate — so
the *intent* to productize already exists.

But it is an **"everything console for one expert user," not yet a product.**
The gap is along five axes, in priority order.

---

## TIER 1 — Trust (table stakes; nothing else matters without it)
An intelligence product dies the first time a user catches it being confidently
wrong. This session caught, on the FRONT PAGE, in one sitting:
- lead story = a 28-signal syndicated AU opinion column over 900-signal real movers;
- "concentrated in France" on Australian outlets;
- Venezuela earthquake chips showing `[BR, MX, CN, US]` / `[RU, RO, UA]` — the
  subject country (VE) absent from both;
- the same event split into two threads by language.

Root cause is structural (**#238**): the system knows **coverage volume, not
the subject** of a story. Plus the entity/subject layer reads `unverified`
because NER throughput can't keep up (**#184** — one 8GB M1, ~6.5% NER'd).
**Until the surface is trustworthy at a glance, Atlas is a demo that
occasionally embarrasses itself, not a product.** Most of this session's work
(lead-story, geo, dedup, count semantics) was paying down exactly this debt —
that's the right instinct, and it's the #1 thing to finish.

## TIER 2 — Who is it for, and the one job (product definition)
Atlas does ten things (map, threads, focus, markets, anomalies, vessels,
workbench…). A product does ONE job 10× better than the alternative for ONE
user. The codebase already leans toward the answer: **the analyst / journalist
/ OSINT user asking "what's the narrative around X, who's saying what, where is
it heading, and what's NOT being covered?"** — the Research Workflow + Workbench
thesis. Productizing means *picking that user and that loop*, and demoting
everything that doesn't serve it from "front and center" to "available."
Right now the cockpit shows everything to everyone, so it reads as impressive
rather than useful.

## TIER 3 — The product loop is missing: persist → deliver → alert
This is the difference between "a thing I look at once" and "a thing I rely on."
- **No accounts.** Waitlist only; no user identity.
- **No durable work.** Workbench investigations live in `localStorage`
  ("per-browser, evictable, NOT durable") — they don't sync across devices,
  survive a cache clear, or get shared with a colleague.
- **No takeaway artifact.** Phase 3 dossier doesn't exist; "export" dumps the
  current view, not a defensible report a user hands to their boss.
- **No alerts.** Atlas is pull-only. The killer feature of an intelligence
  product is *push*: "tell me when this narrative moves / breaks / a new voice
  enters / coverage appears where there was a gap." That's the retention and
  willingness-to-pay engine, and it's entirely absent.

## TIER 4 — Reliability you can actually sell
- **Founder-laptop infra.** NER + topic crons + (until recently) embed run on a
  single 8GB M1 that has frozen during work and can't keep up with ingest.
- **No observability.** Only `/health`; no error tracking, no uptime, no alerting
  on a dead feed (CGTN/Xinhua RSS already died silently).
- **Unmodeled cost.** DeepSeek translation, paid APIs, embedding — no per-user
  cost envelope, which a paid product needs.
A product's pipelines run without the founder's laptop and break **loudly**.

## TIER 5 — Make the differentiation legible, then reach
The real edge (narrative threads + who-says-what + diversity-of-voice + focus
propagation) is buried in a dense console. Make the one differentiated thing
*obvious* in 30 seconds. Then: mobile (**#236**, not scheduled — and most of
this audience checks news on a phone), and the legal/licensing footing for
republishing/translating headlines at scale.

---

## The honest one-liner
**Atlas has the hardest part already — a real, deep, differentiated engine.
What it lacks is product discipline: a trustworthy surface, one sharp user, and
the persist→deliver→alert loop that turns a powerful view into something people
return to and pay for.** None of the missing pieces are research problems; they
are product decisions and finishing work.

## Cheapest high-leverage path from engine → product
1. **Finish trust (Tier 1).** Land #238 subject-geography + close the visible
   data-quality gaps. A front page that's right every time is the precondition.
2. **Name the user and cut to the loop (Tier 2).** Commit to the analyst job;
   make the Brief → investigate → pin → **dossier** path the spine; everything
   else is "advanced."
3. **Ship the loop's two missing halves (Tier 3):** accounts + server-persisted
   investigations, and **one alert type** ("notify me when a thread I follow
   moves > X / a coverage gap I flagged fills"). Even one alert changes the
   product category.
4. **Make it not depend on a laptop (Tier 4):** move the heavy NER/clustering off
   the M1, add basic error tracking + dead-feed alerts.
5. **One obvious differentiator + mobile (Tier 5).**

Items 1–3 are the line between "impressive project" and "product." The engine
is done; this is the productization.
