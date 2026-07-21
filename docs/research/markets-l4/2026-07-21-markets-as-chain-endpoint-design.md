# Markets as a chain ENDPOINT — design route (2026-07-21)

> **⚠ SUPERSEDED (2026-07-21) by
> [`2026-07-21-markets-relational-axis-design.md`](2026-07-21-markets-relational-axis-design.md).**
> Pedro corrected the core framing: a market is NOT a one-way chain SINK with a
> hand-mapped relation. It is a **bidirectional, DISCOVERED co-movement axis over all of
> Atlas** (news-change ⇄ market-variance, measured not assumed; market as an entry, not a
> dead end). This doc is kept for the honest-tier / instrument-map-as-prior reasoning it
> seeded; read the master doc for the current route.

**Status:** design / brainstorm only. NOT a build. Blocked on the #226 gate for the
causal tier (see §7). The descriptive tier is design-ready but is #151 product
territory, not L4.

**Purpose.** The 2026-07-21 multi-hop "walked constellation" work (journey map
`docs/state/2026-07-21-analyst-journey-map.md`; forthcoming spec under
`docs/superpowers/specs/`) walks topic→topic edges out from the analyst's pins,
labeling hops **hermano** (direct measured edge) vs **primo** (indirect walk,
degree = hops) with a weight-product decay brake. Pedro's motivating example ended
at **"oil price"** — but Atlas stores no market data. The chain can currently only
reach a NEWS thread *about* price variance, never the price series itself. This doc
routes how a market series becomes a reachable, pinnable chain **terminus** when
that data enters, without ever letting measured price blend into the
news-narrative graph.

**References.** #226 (L4 M0 event study, gate = STOP — `markets/m0_event_study.py`,
`docs/research/markets-l4/2026-07-06-m0-event-study.md`); L4 markets layer doc
(`docs/research/2026-06-12-atlas-markets-layer-l4.md`); the connection/edge model
(`backend/app/routers/dossier.py`); #151 (product-side market overlay); #219 (Kalman
movement feed). Wedge = narrative analyst; math-first; no employer IP;
evidence-gated; not investment advice.

---

## 1. The core problem: a market node is a DIFFERENT KIND of thing

Every existing graph node is a `dynamic_topic` with an **e5 centroid**, and every
existing edge basis reduces to that embedding or to shared entities:

| edge basis (today) | how measured | source |
|---|---|---|
| semantic | whitened e5 centroid cosine, tau 0.50 | `dossier.py:57-65` |
| shared_country | top-4 country overlap | `dossier.py:66` |
| shared_person | rarity-weighted distinctive-actor overlap | `dossier.py:13-15,631-633` |

A market series (Brent front-month, a country ETF, COP=X) has **no headline text,
no e5 centroid, no persons, no country-of-subject** in the news sense. It cannot
enter this graph as another topic. Forcing an embedding onto a price series (e.g.
embedding the instrument's name) would be **exactly the dishonest blend we refuse**
— a fake semantic edge that reads as "this story means the same as this price."

So the market node is a **distinct node kind** joined by a **distinct edge kind**,
built deterministically + measured, never by centroid.

---

## 2. Node kind: `market` (a sink, not a topic)

A new lightweight, Atlas-owned record — NOT a `dynamic_topic`, NOT clustered, NOT
lifecycle-managed.

```
market_series
  symbol         text  PK        -- 'CL=F'
  label          text            -- 'Brent crude, front-month'
  asset_class    text            -- energy | metal | fx | equity-etf | ag | rate
  last_close     numeric
  last_close_at  date
  spark_30d      numeric[]        -- trailing daily closes → the node sparkline
  updated_at     timestamptz
```

Properties that make it honest by construction:

- **It is a SINK in the walk.** The chain may terminate at a market node; it may
  never radiate onward *as a market causal claim* (no market→news "this price moved
  that story", no market→market). Exactly one legitimate reverse hop exists and it
  is co-mapping, not causation (§6).
- **It renders as a different shape + a "MEASURED MARKET DATA" tag**, on an
  asset-class color ramp visibly separate from the news-node palette. It is drawn
  *offset* from the semantic cluster ("lands near"), never inside it.
- **It carries its own provenance:** `source=Yahoo daily close`, `last_close_at`,
  and — critically — the **maturity tier of the edge** that reached it (§4).

Source + cadence: the `markets/` Yahoo puller (already written — `yahoo_daily()` in
`m0_event_study.py`) run as a **nightly off-peak cron** (17:30+, same discipline as
the Atlas crons, §5-guardrail of the L4 doc), writing `market_series`. Daily closes
are the correct grain: the whole L4 method is daily-return event study, and intraday
would invite the leakage/backtest-theater failure the L4 doc warns about. `markets/`
consumes Atlas over its public API and keeps separate credentials; the ONLY thing
that lands inside Atlas's DB is this thin descriptive `market_series` table (a price
+ sparkline the product may show — #151), never a trading signal.

---

## 3. The bridge edge: instrument-map (deterministic) — never centroid

The join is the `INSTRUMENT_MAP` that already exists in `m0_event_study.py:47-57`:
a hand-authored **domain → instrument** map (oil-gas-supply-risk → CL=F/NG=F;
armed-conflict-escalation → CL=F/GC=F/ITA; gang-control-urban-security →
COP=X/MXN=X; …). Promote it from a code constant to a small table so it is
inspectable and the basis is legible:

```
category_instrument_map
  category_slug  text            -- an atlas category slug
  symbol         text            -- references market_series.symbol
  basis          text            -- 'domain-map' (hand-authored, deterministic)
  note           text            -- WHY, e.g. 'Gulf conflict → tanker/Brent risk premium'
```

Edge construction, when a walk reaches a news thread `T`:

1. Resolve `T`'s atlas category `c` (threads already carry category via R3 typing).
2. If `c ∈ category_instrument_map`, emit — for each mapped `symbol` — a **bridge
   edge** `T → market_series[symbol]` of kind `measured-landing`.
3. The edge is **deterministic and cheap** (a map lookup, no embedding, no LLM). It
   is honest about being a *mapping*, not a discovered relation: the edge label is
   the `note` ("Gulf conflict maps to Brent risk premium"), a curated domain link.

This is the **Tier-0 descriptive edge** — available the day `market_series` exists,
because it makes **no causal or lead-lag claim**. It says only: *"the domain of this
news lineage is conventionally priced in this instrument; here is that instrument's
current level."* That is #151 overlay content, honest at n=0 events.

---

## 4. The receipt: measured lead-lag UPGRADES the edge label (gated on #226)

The descriptive edge becomes an **evidence-bearing** edge only when the m0 event
study produces a lead for that (category, symbol) pair. Persist the m0 output:

```
market_leadlag
  category_slug   text
  symbol          text
  lag             int             -- t+1 or t+2 ONLY (t+0 = reaction, never a lead)
  n_events        int
  ratio           numeric         -- mean |move| after spike ÷ baseline |move|
  perm_p          numeric         -- 10k-permutation p
  window          daterange       -- the regime the study covered
  method_version  text            -- leakage-honest protocol version
  passed_gate     bool            -- p<0.10 at t+1/t+2 AND n_events >= threshold
```

Two edge tiers, and the node/chain must show WHICH:

- **Tier 0 — descriptive co-presence** (`market_leadlag` absent or `passed_gate=false`).
  Edge chip: **"mapped domain · descriptive · not a lead-lag claim."** Dashed, low
  weight. This is what ships first and what the #226 STOP verdict permits today.
- **Tier 1 — measured lead-lag** (`passed_gate=true`). Edge chip carries the full
  receipt: **"|move| ×1.5 at t+1 · perm p=0.09 · n=6 events · May–Oct 2026 · NOT
  causal."** Solid, weight = the measured strength.

**The wording is load-bearing.** A chain reaching a market node reads:

> *"this news lineage lands near this measured price move"*

with the lead-lag receipt attached — **never** *"this story caused the price."* The
m0 method itself forbids the stronger claim: it measures |return| (volatility), not
signed direction (no stance model), and t+0 is reaction not lead. The node inherits
that honesty header verbatim.

---

## 5. Chain mechanics: the `measured-landing` hop

The multi-hop walk gains one new hop kind, alongside hermano/primo:

| hop kind | between | weight | can radiate onward? |
|---|---|---|---|
| **hermano** | topic ↔ topic, direct measured edge | semantic/shared weight | yes |
| **primo** | topic ↔ topic, indirect (degree = hops) | weight-product decay | yes |
| **measured-landing** | topic → **market node** | Tier-0 flat-low / Tier-1 receipt | **NO — sink** |

Rules:

- The landing hop **counts against the decay budget** like any hop: a market node
  reached only after 4 primo hops is a **degree-5, heavily-decayed** terminus and
  is labeled that weak. Distance-to-price is honest.
- Tier-0 landing weight is a **flat low co-presence constant** — deliberately small
  so a mere domain mapping never dominates a chain or outranks a real hermano edge.
- Tier-1 landing weight = the measured `ratio`/`perm_p` strength, so a
  gate-passing lead-lag is a genuinely strong terminus.
- The market node **never re-enters** the topic frontier (sink). This prevents the
  reverse causal claim and keeps chains finite/acyclic at the market boundary.
- **Cross-type edges are never mixed into the weight-product with semantic edges**
  for ranking chains against each other — a chain that ends at a market node is
  scored on its news-hop product; the landing is an *annotation on the terminus*,
  not a multiplier that lets a weak news chain look strong because it "reached oil."

---

## 6. The one honest onward turn (optional, keeps the flywheel alive)

A pure sink is a dead end — and the journey map's whole thesis is that dead ends
kill the flywheel (§3 of the journey map). There is exactly **one** honest onward
hop from a market node, and it is **co-mapping, not causation**:

> *"which OTHER news domains map to this same instrument?"* — reverse
> `category_instrument_map` on `symbol`.

From `CL=F` you surface {oil-gas-supply-risk, armed-conflict-escalation,
sanctions-diplomatic-pressure} — the sibling news categories that share the
instrument. This is a legitimate discovery ("this price sits at the confluence of
three of my story families") and makes **no causal claim** — it is set membership
in the same hand-authored map. It hands the analyst back into the NEWS graph (a real
flywheel turn) instead of stranding them on a price. This is the analyst-wedge
payoff: not "trade this," but *"the story I'm tracking sits in a domain the market
prices, and here's what else lives in that domain."*

---

## 7. Gating & rollout (what enters when)

The #226 verdict is **STOP** at n=44 trading days (0 leads; the one near-miss,
sanctions→gold @t+1 ratio 1.51 p=0.117, is exactly the underpowered false-alarm the
gate exists to reject). So:

1. **Now (design-ready, #151 territory):** `market_series` + `category_instrument_map`
   + the **Tier-0 descriptive** landing edge. Ships as a market node the chain can
   terminate at, labeled "descriptive co-presence, not a lead-lag claim," showing a
   live-ish price + 30d sparkline. Zero causal claim → passes the gate trivially
   because it makes no claim the gate governs. This is honest situational awareness:
   *"the domain you're reading is priced here, at this level."*
2. **≈October (re-run the gate, per #226):** the category-day series regenerates
   from the archive as it grows; re-run `m0_event_study.py` at ~150 trading days.
   For any (category, symbol) that clears p<0.10 at t+1/t+2 **with adequate n**,
   write `market_leadlag(passed_gate=true)` → the edge **upgrades to Tier-1** and
   the terminus carries a real lead-lag receipt.
3. **Never:** signed "buy/sell", direction, or "caused". The node is a
   *measurement receipt on a narrative lineage*, aimed at the analyst's question
   ("does my story show up in a market?"), not a trader's.

Nothing here builds trading infrastructure, touches employer IP, or deploys with
Atlas runtime credentials (`markets/` stays a separate consumer; only the thin
descriptive price table lands in Atlas's DB for the product overlay).

---

## 8. Open questions for the creative session

1. **Does the descriptive Tier-0 landing belong in the CHAIN, or only in #151's
   thread-side overlay?** Terminating a *walked chain* at a price with no measured
   lead-lag might over-promise even with the "descriptive" chip. Option: Tier-0 shows
   the market node only as a thread-side badge (#151), and the chain is allowed to
   *reach* a market node **only** at Tier-1 (gate-passed). Cleaner honesty, fewer
   nodes; costs the "oil price" terminus until October.
2. **Instrument-map authorship & drift.** `INSTRUMENT_MAP` is 9 hand-authored
   category→symbol rows. Who curates it, and how do we keep it from silently
   implying relations that were never measured? (Every row carries a `note`; is that
   enough, or does each row need its own gate status?)
3. **How does the market node read on a phone**, where the flywheel already breaks
   (§5 of the journey map)? A sink node with a sparkline + a "3 domains map here"
   onward chip is a plausible phone-native terminus card.
4. **Should the terminus weight ever change chain RANKING**, or stay a pure
   annotation? (§5 argues annotation-only; the session should confirm — letting
   "reached a market" boost a chain is a subtle path back to backtest-theater
   reasoning.)

---

## Return summary

- **Node:** `market_series` — a distinct `market` node kind (price + 30d spark), a
  **sink**, Yahoo daily closes via the existing `markets/` puller, nightly off-peak
  cron. NOT a `dynamic_topic`, no embedding.
- **Edge:** a `measured-landing` bridge from a news thread to its mapped instrument
  via `category_instrument_map` (promoted from `INSTRUMENT_MAP`) — **deterministic
  domain mapping, never a semantic centroid**. Tier-0 = descriptive co-presence
  (ships now, no claim); Tier-1 = measured lead-lag receipt (ratio/perm-p, **gated
  on the #226 re-run ≈October**).
- **Honesty:** distinct shape + "MEASURED MARKET DATA" tag, drawn offset from the
  news cluster; the chain reads *"this news lineage lands near this measured price
  move"* with a lead-lag receipt, **never "caused"**; |move| volatility not signed
  direction; the landing hop counts against decay and never re-radiates as a causal
  claim; one honest onward turn = reverse co-mapping (which other domains price here).
- **Fit:** narrative-analyst wedge (does my story show up in a market?), math-first,
  evidence-gated (#226), no employer IP, not investment advice.
