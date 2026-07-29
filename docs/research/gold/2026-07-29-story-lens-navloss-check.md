# Story Lens — Task 11 gate: browser walkthrough + NAV-LOSS re-run

**Date:** 2026-07-29 (run) · **Branch:** `eclipse-dramatic-moment` · **HEAD at run start:** `f35c0c6d`
**Configuration:** dev frontend (`localhost:3000`, vite) against the **PROD Fly API**
(`atlas-api-pedro.fly.dev`). The lens frontend is not on Vercel; this is the correct gate
configuration.

> **HEAD moved mid-run.** A parallel session landed `5e940d0c` (docs) and `c2d955b6`
> *"active-child umbrella resolution; graph cached with the matrix; empty scan never cached"*
> while this walkthrough was in progress. Both are **backend-only** (`story.py`,
> `story_siblings.py`, tests); `git diff f35c0c6d..HEAD -- frontend-v2/` is **empty**.
> Consequences for this artifact, stated precisely:
> - **L1, the CRIT defect and the basis of the NO-GO, is frontend** (`NarrativeThreads.tsx`)
>   and is **untouched** by these commits. The ship verdict stands unchanged.
> - The **sibling payloads** recorded in Part 2 were served by the **deployed** Fly build,
>   which predates `c2d955b6`. Umbrella resolution and the empty-scan cache rule may shift
>   which siblings are returned once that build deploys. The `promised ∩ delivered` figures
>   should be **re-measured after deploy**; the 0-of-107-renderable structural result should
>   not change, because it does not depend on which siblings come back.
> - Story suites re-run at the new HEAD: **20 passed** (was 18 — `c2d955b6` adds 2).
**Rubric:** `docs/research/gold/rubric-v2-ui.md`, dimension **N1 (NAV-LOSS)** — rendered
pixels only. A field present in the payload but absent from the screen scores as absent.
**Baseline:** `docs/research/gold/2026-07-30-ui-eval-v2-run.md` — NAV-LOSS **20/20**,
answered 14.3 %, informed 71.4 %, honesty 0.83.
**Pre-registered ship criterion (plan Task 11 / spec §13):** *NAV-LOSS falls on the re-run set.*

> ## ⛔ SHIP VERDICT: **NO-GO**
> NAV-LOSS **held on 6 of 6** pre-registered queries. It fell on none.
> The lens's primary mechanism — the `◈ Measured neighborhood` group in the threads panel —
> **cannot render on the current field**: measured across every live anchor, **0 of 107
> walked siblings are present in the panel's fetched thread pool** (0/18 anchors). The lens
> ships a banner with a count; the neighborhood it counts is not on screen anywhere except
> inside a pinned dossier.
>
> The honesty rails, the exit/entry/deep-link/pin machinery and the degraded path are
> **sound and should be kept**. This is a NO-GO on the gate, not a verdict on the build.

---

## Step 1 — Suites

| suite | result |
|---|---|
| `pytest tests/test_story_siblings.py tests/test_story_router_contract.py` @ `f35c0c6d` | **18 passed** in 0.60s |
| same, re-run @ `c2d955b6` (HEAD moved mid-run) | **20 passed** in 0.36s |
| Frontend build / vitest | **not re-run this session** — no frontend source was modified; the walkthrough ran against the live dev server. Honest gap in this artifact. |

---

## Part 1 — The walkthrough

Anchors used: **`dynamic-topic-8080`** *Spain Wildfires Force Evacuations Near Madrid, Valencia*
(the GQ-01 witness) and **`dynamic-topic-466`** *Berlin Pride Attack: Suspect Profile and
Manhunt* (the GQ-02/18 flagship).

| # | Step | Result | Evidence (quoted from screen) |
|---|---|---|---|
| 1 | Open thread from threads panel → banner + console reconfigures | **PASS** | Banner: `◈ STORY · Spain Wildfires Force Evacuations Near Madrid, Valencia · LABEL UNDER REVIEW · 11 hermanos · 2 countries · ◇ Pin story · ✕`. Court chip renders when flagged (`label_status: partial`) and is correctly **absent** on the Berlin Pride anchor (`entailed`). |
| 1b | Open from search | **PASS** (entry) | `wildfires` → dropdown → click → lens enters. Search input **cleared on select** — D1's root cause is unchanged upstream of the lens. |
| 2 | Anchor under `◈ The story`; siblings under `◈ Measured neighborhood` with `↔` chips | **FAIL** | `◈ The story` renders **only when the anchor happens to be in the top-20 pool** (wildfire anchor: yes; Berlin Pride anchor at 287 signals: **no** — `anchorRows: 0`). `◈ Measured neighborhood` **never rendered in any run**. `sl-row-sibling` count **0**. `↔` reason chips on screen **0**. `⚠ grab-bag` chips on screen **0** — while **all 7** Berlin Pride siblings and **all 11** Hormuz siblings carry `is_blob: true` in the payload. |
| 3 | Stream `STORY \| ALL`, STORY scoped via `topic=` | **PASS w/ residuals** | Request captured verbatim: `/api/v2/signals?limit=50&hours=24&sort=relevance&topic=dynamic-topic-8080,dynamic-topic-407,…,dynamic-topic-4249` — anchor first, 12 ids, exactly `LENS_TOPIC_CAP`. **ALL** restores unscoped. Two residuals below. |
| 4 | Dock re-scoped + `◈ STORY → CC` badge | **PASS** | `◈ STORY → ES` + `PUBLIC ATTENTION · SPAIN` + `CONFLICTS · SPAIN` (wildfires); `◈ STORY → EG` + `PUBLIC ATTENTION · EGYPT` (Berlin Pride). Residual below. |
| 5 | Kill the siblings request → honest degraded, console never blanks | **PASS (honesty)** | Banner: `◈ STORY · Narrative Thread · ⚠ Neighborhood lookup failed — not a measured absence · ✕`. Console fully intact (18 thread rows, map, stream, dock). No `Pin story` offered — correct, nothing to freeze. Copy correctly separates *lookup failure* from *measured absence*. Two defects below. |
| 6 | Pin story → `◆ pinned`, Workbench, Dossier, export, re-click no-op | **PASS** | Banner flips `◇ Pin story` → `◆ pinned`; the button element is **consumed** (re-click impossible). Workbench: `FROZEN JUL 28 · COUNTS AS PINNED`. DossierView renders `MEASURED NEIGHBORHOOD (FROZEN)` with all 8 frozen siblings, e.g. `France Heatwave Alerts ↔ whitened_cos 0.81 · ⚠ grab-bag`, `Orés Wildfire Update ↔ whitened_cos 0.82 via Fontainebleau Forest Fire`. Honest: `METADATA ONLY — NO FROZEN EVIDENCE` + `GAPS & UNCERTAINTY: 1 of 1 pins captured without frozen evidence`. Export block at `lib/dossier.ts:139-145`, test-frozen `lib/dossier.test.ts:166,175`. Pin re-open payload: `?theme=dynamic-topic-8080&lens=story` — **deep-links back into the lens**. |
| 7 | `✕` exits clean · no resurrection · Escape · fresh-tab deep link | **PASS** | `✕` → banner gone, `body.className` empty, section labels gone, 18 rows intact, `?theme` cleared. Country click after exit → `COUNTRY Iran ×`, **no lens resurrection**. Escape closes detail + lens. Fresh tab `?lens=story&theme=dynamic-topic-8080` → full lens. Residual below. |
| 8 | Eclipse co-active | **NOT LIVE-VERIFIABLE** | `/api/v2/attention/eclipse` → **HTTP 503** `{"reason":"db_busy"}`. Verified by inspection only: `storyLens.css:10` `body.story-lensed{padding-top:28px}`; `:15` `body.eclipsed.story-lensed{padding-top:56px}` (specificity 0,0,2,0 beats 0,0,1,0); `:16` `body.eclipsed.story-lensed .sl-banner{top:28px}` — banner stacks below the ribbon. Colour separation not verified. |
| + | Sibling re-anchor (click a `◈ Measured neighborhood` row) | **BLOCKED** | Untestable — no sibling row exists to click on any anchor. |
| + | Atlas thread (`slug--cc`) opens WITHOUT lens | **PASS** | `isLensAnchor()` (`lib/storyLens.ts:51`) gates on `dynamic-topic-` so no fetch fires; backend agrees — `GET /story/armed-conflict-escalation--US/siblings` → `{"anchor":null,"siblings":[],"notes":["unsupported_anchor_type"]}`. |
| + | Mobile 375 px | **PARTIAL** | Banner visible top, wraps to 2 lines, `✕` reachable; bottom tab bar (`Map/Threads/Stream/Pulse`) **not clipped**. But the banner overlaps the panel's own controls — defect **L5**. |

### Walkthrough tally
**7 PASS · 1 FAIL (step 2, the core mechanism) · 1 not live-verifiable · 1 blocked · 1 partial.**

---

## Part 2 — NAV-LOSS re-run

**Protocol.** Search → record the N promised threads as rendered in the dropdown → open ONE →
score whether the other N−1 (or measured equivalents) are reachable **from inside the lens,
with receipts**. `promised ∩ delivered` is computed against the sibling payload; **rendered**
is what actually reached the screen.

| # | query | promised (rendered in dropdown) | delivered by the walk | ∩ | **rendered** in lens | verdict |
|---|---|---|---|---|---|---|
| **GQ-01** | *Wildfires FR/ES* — `wildfires` | **6**: Wildfires Worsen Across Spain and France Amid Heatwave **1,528** · Wildfires Threaten Bordeaux, Defense and Nuclear Sites **1,056** · Spain Wildfires Force Evacuations Near Madrid, Valencia **857** · Wildfires Rage in Spain and France, Over 200,000 Evacuated **749** · Wildfires, Plane Emergency, Arrests in Greece **741** · Wildfires Rage Across Spain and France, Mass Evacuations **508** | 11 siblings: France Heatwave Alerts ⚠ · China Shoe Factory Fire · Fontainebleau Forest Fires ⚠ · Violent Storms in France ⚠ · Fontainebleau Forest Fire · Orés Wildfire Update · Waldbrände in Frankreich und Spanien · La Mierla Wildfire · Ávila Wildfire Record · Waldbrandrauch in Toronto und New York · Isla Salamanca Fire Crisis | **0 / 5** | **0 rows** | **HELD** |
| **GQ-02** | *Berlin Pride attack* — `Berlin Pride` | **5**: Berlin Pride Attack: Suspect Profile and Manhunt **287** · Berlin Pride Attack Suspect Killed **36** · Berlin Pride Terror Attack **19** · Berlin Pride Attack Suspect **16** · Berlin Pride Car Attack **16** — *exactly the pre-registered baseline 287/36/19/16/16* | 7 siblings, **all 7 `⚠ grab-bag`**: Austrian Arrested for Fraud 0.853 · **Berlin Pride Attack Suspect 0.794** · Greek News Roundup: Crime, Sports, Lottery 0.696 · US Strikes Iran Sixth Night 0.681 · Italian Goldsmith Kills Robbers 0.676 · China Shoe Factory Fire 0.318 · Funeral of 20-Year-Old Shot by Police 0.310 | **1 / 4** | **0 rows** | **HELD** |
| **GQ-18** | *Who broke Berlin Pride first* | same 5 | same 7 | **1 / 4** | **0 rows** | **HELD** |
| **GQ-19** | *Hormuz → oil* — `Hormuz` | **6**: Strait of Hormuz De-mining **123** · Hormuz Crisis Escalation **104** · Iran Hormuz Strait Tensions **102** · US Control of Strait of Hormuz **89** · Rubio Warns on Iran Hormuz **83** · Iran Warns US on Hormuz **75** | 11 siblings, **all 11 `⚠ grab-bag`**: US Strikes Iran Sixth Night · Iran Attack Kills US Soldiers · US-Iran Conflict Escalation · **Russian Attacks on Ukraine** · US Drone Strike Iran Submarine · Trump Threatens Iran · **US Gas Prices Surge** · **Ukrainian Drone Attacks on Moscow** · EU Sanctions on Russia · US-Iran Conflict Escalates · **European Heatwave Crisis** | **0 / 5** | **0 rows** | **HELD** |
| **GQ-12** | *Caspian ship* — `Caspian` | **0 threads** (12 media signals only) | n/a — no anchor to open | — | — | **HELD (upstream)** |
| **GQ-06** | *US-Iran framing* — `US Iran`, `Iran`, `Iran strike pause`, `Iran US strikes framing` | **0 threads** across 4 phrasings | n/a — no anchor to open | — | — | **HELD (upstream)** |

### The number

| | baseline (2026-07-30) | this re-run |
|---|---|---|
| **NAV-LOSS** | **20 / 20** | **6 / 6 held · 0 fell** |
| queries where the lens rendered ≥1 measured sibling | — | **0 / 6** |
| promised threads recovered by the walk (payload) | — | **1 of 14** |
| promised threads **rendered** to the analyst | — | **0 of 14** |

**Ship criterion: NOT MET.**

### Three findings that decide it

**1. The neighborhood is structurally unrenderable, not merely absent today.**
`NarrativeThreads.tsx:419-422` sorts `displayedNarratives` — the panel's **own fetched
`/threads` payload**. `firstLensSiblingIdx = lensRowRoles.indexOf('sibling')` (`:454`) is `-1`
whenever no fetched row *is* a sibling, so the `◈ Measured neighborhood` header at `:572`
never renders. Nothing fetches the siblings as rows. Measured across every live dynamic
anchor in the served pool:

```
=== 0/18 anchors have >=1 sibling visible in the threads panel pool ===
=== total sibling rows renderable: 0 of 107 walked ===
```

This is not a thin-data day. The walk resolves against **stale identities** (`dynamic-topic-407`,
`-1525`, `-3019`, `-3000`, `-4997`…) while the live co-existing fragments the analyst can
see in the same panel (*Incendios Forestales en Europa*, *Waldbrände in Südfrankreich*,
*Wildfires Rage Across Spain and France*) are **not in the neighborhood at all** — the
argmax-dispersion result from the 2026-07-30 measurement arc, now visible in the UI.

**2. Where the walk does resolve, it resolves onto false neighbors — and says so, invisibly.**
On the flagship Berlin Pride anchor the **highest-weighted** sibling is *Austrian Arrested for
Fraud* (0.853); on Hormuz the neighborhood contains *Russian Attacks on Ukraine*, *Ukrainian
Drone Attacks on Moscow* and *European Heatwave Crisis*. **18 of 18 siblings across those two
anchors carry `is_blob: true`.** The lens's own honesty machinery correctly labels its entire
output a grab-bag — and **zero of those `⚠ grab-bag` flags reach the screen**, because the
rows they belong to never render. This is exactly the rubric's D5-pixels failure mode.

**3. Two of the six pre-registered witnesses never reach a lens at all.**
GQ-12 and GQ-06 return **no thread** under any phrasing tried. Their NAV-LOSS is upstream in
the matcher (D10), which the lens is read-only over. The spec anticipated this; it is recorded
here as *held-upstream*, not as a lens regression.

### What the lens genuinely does deliver

Stated plainly, because the gate verdict should not bury it. The **frozen neighborhood in the
dossier is real, legible and receipt-bearing** — it is the one surface where the measured walk
reaches the analyst, complete with weights, `via` provenance and `⚠ grab-bag` flags. The
degraded copy (*"not a measured absence"*), the honest STORY-empty (*"membership lags ingest by
up to one classifier pass"* — verified true: 0 rows at 24 h, 50 at 168 h), the `topic=` scoping,
the exit/deep-link/pin-freeze machinery and the `unsupported_anchor_type` gate are all correct.
**The renderer is sound; it has nothing to render.**

---

## Defects

Severity: **CRIT** = defeats the feature's stated purpose · **HIGH** = destroys real measured
value · **MED** = degrades trust or usability.

| # | defect | root cause (file:line) | sev |
|---|---|---|---|
| **L1** | **The `◈ Measured neighborhood` section can never render.** The panel re-labels only rows it already fetched; siblings are never fetched as rows. Measured 0/18 anchors, 0 of 107 siblings renderable. Consequence: 0 `↔` receipt chips and 0 `⚠ grab-bag` chips on screen, on every anchor tested. | `NarrativeThreads.tsx:419-422` (sorts `displayedNarratives` only) + `:454` (`indexOf('sibling')` → −1) + `:572` (header gated on that index) | **CRIT** |
| **L2** | **The banner reports every sibling as a `hermano`.** `11 hermanos` where the payload is 5 hermano + 6 primo; `7 hermanos` where it is 5 + 2. The hermano/primo distinction (direct measured edge vs. indirect walk) is the design's honesty core — the banner erases it and overstates measured directness. | `StoryLensBanner.tsx:100` — `{data?.siblings.length ?? 0} hermanos` | **HIGH** |
| **L3** | **The siblings endpoint sits in the `paid` rate-limit bucket — 20 requests / 300 s per IP** — and the lens fires it on **every** thread open, through every door. Walking a fragmented event (the lens's entire purpose) exhausts the budget; every subsequent story then shows `⚠ Neighborhood lookup failed`. Reproduced repeatedly as HTTP 429 during this run. | `backend/app/rate_limit.py:116` (`^/api/v2/story/[^/]+/siblings$` → `paid`); every-door sync from `e3ac5f32` | **HIGH** |
| **L4** | **On the degraded path the banner loses the story's name** — renders `Narrative Thread` although the analyst just clicked a row carrying the full label, which is available locally. A lens banner over a story it cannot name. | `StoryLensBanner` fallback title on error — label not sourced from the clicked row | **MED** |
| **L5** | **Mobile: the lens banner overlaps the ThemeDetail overlay's own header controls.** `body.story-lensed{padding-top:28px}` cannot move a `position: fixed` overlay. Measured at 375 px: banner box `top 0 → bottom 28`; `theme-detail-close` `top 16`, pin button `top 20` — both partly beneath it. Same class as the eclipse-ribbon occlusion already on the record. Controls remain tappable on their lower half. | `storyLens.css:10` + fixed-position mobile ThemeDetail overlay | **MED** |
| **L6** | **Degraded path falls back to a raw-id badge scoped to the wrong country.** `DYNAMIC-TOPIC- → BR`, tooltip *"Re-scoped to the focus's dominant country: Brazil"*, on a **Spain/France** wildfire story (`ES 70 · FR 70 · BR 14`). Pre-existing #234 fallback that the healthy lens badge (`◈ STORY → ES`) masks — the lens is *fixing* this; the degraded path exposes it. | `useFocusRelation` dominant-country fallback; raw-id label leak in `ap-focus-badge` | **MED** |
| **L7** | **A primo's receipt can cite an invisible intermediary.** Hormuz: *"whitened_cos 0.80 **via Turkey S-400 Resale Talks**"* — a parent that appears nowhere in the returned sibling list. The receipt is unverifiable by the reader. | `story_siblings` walk emits `via_parent` for parents dropped by cap/dedup | **MED** |
| **L8** | **Exit leaves a dangling `?lens=story`.** Verified **inert** on reload (no banner, no lens) — cosmetic URL litter only. | lens-param cleanup on exit clears `theme`, not `lens` | **LOW** |
| **L9** | **Duplicate scoped-stream fan-out** — the same `signals?…&topic=` URL fired 3× per lens entry. D17 class, unchanged. | effect double-fire on the stream tab | **LOW** |

---

## Honest residuals & caveats

- **Frontend suite not re-run.** No frontend source was modified in this session, but the
  artifact cannot claim a green vitest run. Backend story suites are green (18/18).
- **My own measurement consumed rate-limit budget.** The 18-anchor intersection sweep and
  repeated sibling probes shared the 20/300 s bucket with the browser. Some degraded banners
  observed mid-run were **my** 429s. L3 is still filed on its merits: the limit is real
  (`rate_limit.py:116`), the per-open call is real, and an analyst walking a shredded event
  will hit it — but the *frequency* seen here is inflated by the harness.
- **Dev-proxy flakiness** produced blanket `Failed to fetch` across every endpoint (vessels,
  correlation, threads, focus) on two loads. Confirmed environmental — the siblings endpoint
  answered HTTP 200 from curl at the same moment. Not counted as a defect. It did, however,
  give an unforced verification of step 5's degraded path.
- **Eclipse co-activation is unverified in the running product** (`/attention/eclipse` 503).
  CSS stacking is verified by source inspection only; colour separation is not verified.
- **Sibling re-anchor and the `⚠ grab-bag` tooltip are untested** — both require a rendered
  sibling row, which L1 makes unreachable. They must be re-gated once L1 is fixed.
- **Dominant country ≠ subject country.** `◈ STORY → EG` on a *Berlin* Pride attack is
  arithmetically correct (Egypt 33 · Germany 17 · Greece 11 by coverage volume) and
  editorially misleading. This is the #238 subject-geography gap, inherited, not introduced.
- **Cross-run stability is real and worth recording.** GQ-02's promised set is byte-identical
  to the baseline three days earlier (287/36/19/16/16), and GQ-01's fragmentation pattern is
  unchanged. The shredding these queries witness is **stable**, not day-noise.

---

## What would change the verdict

L1 is the gate. The lens needs the neighborhood **as rows** — either the panel fetches the
sibling threads it does not already hold, or the banner owns a neighborhood list of its own.
Until then the `↔` receipts and `⚠ grab-bag` flags — both already computed, both already
correct — reach the analyst only through a pinned dossier.

Two things are worth deciding alongside it, because they are visible in the same evidence:
the walk currently resolves onto **stale identities and semantic false neighbors** (18/18
self-flagged grab-bag on the two flagship anchors), so rendering it unchanged would surface a
neighborhood that is honest about being untrustworthy; and **L3's rate budget** is at odds
with the feature's own use case.

*Run configuration: dev frontend + prod API · desktop 1172×1507 and mobile 375×812 ·
6 pre-registered queries · NAV-LOSS 20/20 baseline → 6/6 held, 0 fell · **NO-GO**.*
