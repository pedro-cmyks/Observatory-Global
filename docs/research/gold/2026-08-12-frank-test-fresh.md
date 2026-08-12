# Fresh Frank Test — does the dossier FILE as news after corroborate-v2?

**Date:** 2026-08-12 · **Surface:** prod (`observatory-global.vercel.app/app`, API `atlas-api-pedro.fly.dev`)
**Story filed:** *Syria Russia Bases Deal* (`dynamic-topic-12280`) — 33 signals/7d, 56 lifetime,
2 countries (SY 20 / RU 17), 20 sources, active since Aug 9. Chosen because it is a real
multi-country story whose sources include Russian and Syrian state media — the hardest case for
an independence claim.

**Investigation built as an analyst:** thread pinned → sibling thread (*US Bombards Iran Over
Ormuz Attack*, flagged `↔ Syria`) pinned → key subject (`vladimir putin`) pinned → Syria
CountryBrief pinned → REPORT → CORROBORATE → CROSS-READ. The sibling was later dropped
(the report itself measured it as unconnected — see §3).

---

## VERDICT: **DRAFT-ONLY**

Closer than the R4 council's "draft yes, file NO" — the corroboration lane now exists, renders,
and carries clickable receipts. But it does not clear the editor's bar for two reasons that a
red pen cannot fix:

1. **The lane failed 3 of 4 times in the product** (2× HTTP 502, 1× "lane unavailable", 1× success).
2. **When it succeeded, it over-claimed independence.** The report told me "6 independent
   corroborations" for what is, in news terms, **one Syrian Foreign Ministry announcement retold
   by three outlets**. An editor cannot correct that with editing — they would have to redo the
   sourcing analysis themselves, which is the whole reason to use Atlas.

A verdict of PUBLISH-WITH-EDITS would be a courtesy pass: the defect is in the *measurement*, not
the copy.

---

## 1. Does the report STAND ALONE? — **YES (with a background edit)**

A stranger gets the story. Auto-title and lede are real news prose:

> **Syria and Russia reach deal on future of Russian bases**
>
> "Syria and Russia have reached an agreement on the future of Russia's military presence at
> Hmeimim and Tartous, announced Syria's Foreign Ministry on 2026-08-10 [3]. The deal follows 18
> months of negotiations and will restructure Russia's presence along the Syrian coast [3]."
>
> "Under the memorandum of understanding, Syria will begin restructuring Russia's presence along
> the Syrian coast and assume control of civilian facilities, including at Hmeimim Airport and the
> fourth commercial pier at Tartous Port [3]."

`EDITORIAL READINESS — 5W+H` renders WHO/WHAT/WHEN/WHERE/HOW **READY**, WHY **PARTIAL**
("causal explanation not measured") — an honest self-assessment.

**Edits Frank would demand:** no background graf (never says when Assad fell, who al-Sharaa is,
or that Tartous is Russia's only Mediterranean naval facility). And the `HOW` row lists
`language:en` and `bluesky` alongside real outlets (`tass.com`, `sana.sy`, `dw.com`) as if they
were sources — a render defect in a section an editor reads as the sourcing list.

## 2. Is every load-bearing claim backed by a clickable receipt? — **YES**

Best part of the report. Three numbered receipts, each a live link with outlet + date, two
carrying verbatim excerpt plus fetch provenance:

> "Syria says reached deal with Moscow on fate of Russian bases — naharnet.com, Aug 10"
> "*…Syria said that it reached a deal with Russia on the fate of its two bases in the country,
> which Moscow once used to provide military support to ousted leader Bashar al-Assad…*"
> — FROM THE SOURCE · FETCHED 2026-08-11

The cross-read goes further and gives claim-level verbatim quotes attributed to named outlets.
This criterion is genuinely passed.

## 3. Is the independence claim MEASURED and truthful? — **NO. This is the failure.**

### 3a. In-product reliability: 1 success in 4 attempts

| # | Path | Result | Rendered text |
|---|------|--------|---------------|
| 1 | 4 pins (2 with evidence) | **502** | "Corroboration failed — the search lane did not answer. Re-run from the button above." |
| 2 | same, retry | **502** | same |
| 3 | 3 pins (1 with evidence) | 200, no data | "no server-side web-search path answered — GDELT DOC 2.0 unreachable…" → `? UNVERIFIED / web-search lane unavailable — corroboration not measured` |
| 4 | same, retry | **200 OK** | `✓ ESTABLISHED … 34 independent voices` |

Root causes, both measured directly:

* **502 = proxy ceiling, not the math.** `vercel.json` rewrites `/api/:path*` → Fly. Direct to Fly:
  1 evidence pin = **21.7 s / HTTP 200**; 2 evidence pins = **31.4 s / HTTP 200**. The 31 s run
  exceeds the Vercel rewrite ceiling → 502. Same class as the `/api/v2/universe` 502 already in
  the record ("the ceiling is the Fly proxy, not Postgres"). **Two evidence pins is enough to
  break it** — i.e. the endpoint fails on any investigation an analyst would actually build.
* **"lane unavailable" = upstream 429.** GDELT DOC 2.0, probed directly 3×: `429 / 200 / 429`,
  with the body *"Please limit requests to one every 5 seconds."* The handler fires its per-pin
  queries **concurrently** (`asyncio.gather`), which violates that limit by construction. The UI
  copy even admits the rule ("DOC 2.0 permits one query every five seconds") while the code
  ignores it.

The degradation is honest — it never fabricates — but for Frank, honest absence three times out
of four means the corroboration section is not something he can plan a page around.

### 3b. When it worked, the number is not inspectable

> **✓ ESTABLISHED** · Syria Russia Bases Deal
> **34 independent voices (syndicated copies collapsed)**
> · Syria says reached deal with Moscow on fate of Russian bases — hurriyetdailynews.com
> · Syria says deal agreed on future of Russian bases — dw.com
> · Syria , Russia reach deal to reorganize Russian military presence at Khmeimim , Tartus bases — globalsecurity.org
> · Russia says Syria base deal will boost ties , source says some Russian forces will stay — internazionale.it
> · Syria - Russia Deal Ends Moscow Use Of Mediterranean Bases , Straining Its Global African Reach — jp.ibtimes.com

**34 claimed, 5 shown** (`MAX_CITATIONS_PER_PIN`). 29 of the 34 voices are unverifiable by the
reader. And because nothing collapsed on this story (`state_collapsed: 0`), the note shows only
the voices number — the reader cannot distinguish "34 outlets, none collapsed" from "34 voices
distilled from 60 outlets". The v2 phrasing that makes the collapse visible
("*19 independent voices (20 outlets; same-state outlets counted as one voice)*") only appears
when a collapse fires; I saw it fire server-side on the Iran pin, never on the filed story.

### 3c. The claim-level count is inflated — the sharpest finding

> "AI READ · deepseek-chat · **3 of 3 read sources** with quote-backed claims · **6 independent
> corroborations** · verify the quotes"
> …six consecutive blocks reading **"✓ CORROBORATION — 2 INDEPENDENT SOURCES"**

From the raw `crossread` payload (`workbench-cross-read-v1`, `shared_source_findings: 0`):

* All **6** "independent corroborations" are pairs drawn from **3 articles**, and
  **`algemeiner.com` is on side A of all six**.
* One algemeiner claim (`c5`) is counted in **two** different "independent corroborations"
  (paired with `c8` naharnet and `c16` theyeshivaworld) — the same claim double-counted.
* Every pair restates the **same memorandum of understanding announced by Syria's Foreign
  Ministry**. Example pair 3, rendered as two independent sources:
  > "Military facilities would be repurposed as joint training centers, with the transition to be
  > completed within three months" — ALGEMEINER.COM
  > "set a time limit of no more than three months to complete the process" — NAHARNET.COM

  That is one document reaching the reader twice.

**Why corroborate-v2's R2 derivation guard cannot catch it** (`backend/app/services/article_read.py`):
`attributed_outlet()` only fires on *media* attribution ("According to X", "reported by X"), and
`_NON_MEDIA_ATTRIBUTION` explicitly excludes `"ministry"`, `"government"`, `"officials"` as
"normal sourcing, not derivation". `quote_overlap()` needs ≥0.6 near-identical quote text; three
outlets paraphrasing a ministry statement score 0. So the guard is correct for the Haaretz-rewrite
witness it was built for, and **structurally blind to the far more common case: N outlets
rewriting one government press release.** Every claim in the payload carries
`"attribution": "attributed"` and the read step even captures `attributed_to` — but
`attributed_to` is **dropped** when the finding is assembled, so the render can never say
"both sides attribute this to Syria's Foreign Ministry."

### 3d. The v2 features that would have caught this are not wired to the page

`POST /api/v2/corroborate` fully implements corroborate-v2. Probed live on this story:

```json
"verdict": {"status":"corroborated","corroborating":7,"official_corroborating":0,
            "template_matches":5,"aged":0,"window_days":7,
            "note":"corroborated by 7 source(s), none official/wire; 5 template-shaped
                    match(es) set aside (shared casualty boilerplate, no shared event anchor)"}
"source_status": {"doc20":"throttled","atlas_hot":"ok","atlas_archive":"ok"}
```

That is exactly the discipline the brief promises — template matches visible-but-not-counted, a
7-day aged window, an official/wire distinction, an honest `throttled` status. **It has zero
frontend consumers.** `grep "v2/corroborate" frontend-v2/src` returns only a comment in a type
definition; the only fetch in the app is `/api/v2/dossier/corroborate`, whose payload carries
none of `template_matches`, `aged`, `window_days`, or `official_corroborating`. The
`CorroborationVerdict` interface (`dossierCorroboration.ts:63`) is dead code.

## 4. Is anything asserted that isn't backed? — **MOSTLY GOOD, two real breaks**

The "reported (uncorroborated)" discipline and the honesty rails are the strongest non-receipt
part of the report:

> **WHAT WE DON'T KNOW**
> · "Two pins—'vladimir putin' and 'Syria'—were captured without frozen evidence (metadata only),
>   so their content could not be verified or linked to the deal [2][3]."
> · "The exact terms of the deal, including the number of Russian forces staying, are not specified
>   in the evidence; the claim of some forces staying comes from an unnamed source [1]."
> · "No public or forum signal was captured, and the evidence leans toward English-language
>   outlets, so Syrian or Russian domestic perspectives are absent [1][2][3]."

Metadata-only pins are refused loudly rather than padded:
> `METADATA ONLY — NO FROZEN EVIDENCE` · "**'VLADIMIR PUTIN' FROZE METADATA ONLY — NO RECEIPTS TO
> STAND ON.**" [Request snapshot] — and in corroboration: `— NOT APPLICABLE / metadata-only context
> pin — no frozen evidence claim to corroborate`

The measured non-connection is stated rather than implied:
> "**'SYRIA RUSSIA BASES DEAL' CONNECTS TO NOTHING ELSE PINNED.**" [Drop receipt]

**Break 1 — the tension never reaches the prose.** The cross-read found a genuine editorial
discrepancy:
> **⚠ POSSIBLE TENSION** — "c10 asserts Russia has not yet officially commented on the agreement,
> while c1 attributes a statement to Russia's Foreign Ministry about the deal boosting ties."
> *"Russia has yet to officially comment on the agreement."* — NAHARNET.COM
> *"Russia's Foreign Ministry said on Tuesday that a deal … would boost ties"* — ALGEMEINER.COM

…yet the synthesis asserts flatly: *"Russia said the base deal will boost ties, and a source said
some Russian forces will stay [1]."* The report contradicts itself and only the buried section is
right. This is the single most publishable finding in the whole run and the prose drops it.

**Break 2 — the honesty discipline mangles the copy when the lane fails.** On the first run
(corroboration 502), `softenConfirmation` substituted its phrase inline and destroyed the
grammar. Verbatim from the rendered page:

> "…are topically adjacent but **not reported (uncorroborated) connected** to the Syria-Russia
> bases deal; they share no **reported (uncorroborated) actor** with it…"
> "…so their content could not be **reported (uncorroborated) or linked to the reported
> (uncorroborated) deal** [metadata-only]."

So the failure modes compound: the lane fails → the prose becomes ungrammatical. No desk files that.

**Break 3 (cosmetic but disqualifying at a glance) — ⚠ inside dates.** Rendered in the lede:
> "The deal was reported by multiple outlets on **2026⚠-08⚠-10⚠** and **2026⚠-08⚠-12⚠** [2][3][1]."

`isFigureClaim()` (`proseValidator.ts:102`) has no date guard, so each component of an ISO date is
flagged as an unbacked figure. Frank sees warning triangles inside a date and stops trusting the
markers everywhere else.

## 5. Adversarial check — state media and aged receipts

**State media: partially disclosed, never on the receipt.**

* At thread level the flag exists: ThemeDetail shows `tass.com  UNCLASSIFIED ⚑ state`,
  `aa.com.tr STATE ⚑ state`, `egyptindependent.com STATE ⚑ state`. (Note the internal
  contradiction on tass: tier label `UNCLASSIFIED` next to the `⚑ state` flag.)
* In the dossier, state media appears **only as an aggregate**:
  `receipts by tier: unknown 17 · state 3` — the three state receipts are never named.
* The dossier's **evidence receipt list carries no per-receipt tier chip at all** — chips are
  rendered only on *corroboration citations* (`DossierView.tsx:965`). Had one of the three cited
  receipts been `tass.com`, **the report would not have said so.**
* The corroboration-citation path is correct where it fires: `citationTierChip` renders `[STATE]`
  and `citationCollapseNote` adds "· one voice" — and the backend does supply it
  (`news.cn → ownership_group:"state:cn", credibility tier 5 "state"` on the Iran pin, with the
  note *"19 independent voices (20 outlets; same-state outlets counted as one voice)"*).
  **On the story I filed it never fired**, because no state outlet reached the top-5 citations.
  Verified in payload + render code, not visually.
* Credibility tiers are near-useless on this sample: **5/5 citations came back tier 4 `unknown`,
  including `dw.com`** — so no chip renders at all and `citationTierChip` returns null by design.
* The `VOICE` section is the one place the state/ownership question is answered well:
  > "SY — self-voice 5% · dominant outsider RU · state media 6% · top foreign: RU, DE, TR"

**Aged receipts: not flagged in the report.** Citation dates were all in-window
(`seendate` 2026-08-09→08-11, `window 14d`), so nothing should have flagged. But the corroboration
citation render shows **no date at all**, and the `aged` field lives only on the unwired
`/api/v2/corroborate` payload — so an out-of-window receipt in this section would be invisible.
Evidence receipts do carry dates ("— algemeiner.com, Aug 12") and the archive path has its own
"FROM THE ARCHIVE" chip, but neither is the corroborate-v2 aged-window discipline.

---

## What corroborate-v2 visibly changed vs the R4 complaint

R4: *"the blocking lane is independent corroboration with receipts."* Measured today:

| R4 gap | Status | Evidence |
|---|---|---|
| No corroboration section with receipts | **CLOSED (when the lane answers)** | `✓ ESTABLISHED · 34 independent voices` + 5 clickable citations + `measured … · gdelt-doc-2.0 · window 14d` |
| Independence counted in articles | **CLOSED in the math** | `independent_voices` is what status is judged on; `single_source` keys on voices |
| Same-state outlets counted separately | **BUILT, fires server-side** | Iran pin: "19 independent voices (20 outlets; same-state outlets counted as one voice)", `news.cn → state:cn` |
| Nothing said about *why* a receipt didn't count twice | **CLOSED in render code** | `citationCollapseNote` → "· one voice" + tooltip naming the apparatus |
| Claims asserted without backing | **CLOSED** | metadata-only pins refused; `WHAT WE DON'T KNOW`; "CONNECTS TO NOTHING ELSE PINNED" |
| Derivative/attributed coverage counted as corroboration | **NOT CLOSED** | 6 pairs from 3 outlets, one ministry statement, `shared_source_findings: 0` |
| Template/aged/official discipline | **BUILT BUT UNREACHABLE** | full v2 verdict on `/api/v2/corroborate`; zero frontend consumers |

The honest summary: **corroborate-v2 built the right machine and did not finish plugging it in.**

---

## Top 3 remaining gaps, ranked

**1. The independence rollup over-claims on government-announcement stories (credibility risk).**
"6 independent corroborations" for one ministry statement retold by three outlets is the exact
error the feature exists to prevent, and it is the one an editor would be burned by. Fix is small
and specific: carry `attributed_to` into the cross-read finding (it is already captured at read
time and thrown away), and treat two claims attributed to the *same primary actor* — ministry,
police, company, court — as one source, with a new reason like `same_primary_actor`. Keep it
visible, not silent: render "1 primary source (Syria's Foreign Ministry) — retold by 3 outlets".
Also stop counting one claim in two pairs, and label the header
"6 corroborating pairs across 3 sources" rather than "6 independent corroborations".

**2. The lane does not survive a real investigation (delivery, not math).**
Two evidence pins → 31 s → 502 through Vercel. Concurrent queries → GDELT 429 → "lane
unavailable". The endpoint is correct and the product still shows nothing 3 times out of 4. Fix:
make corroboration a job, not a request (kick off + poll, the same split that fixed
`/api/v2/universe`), and serialize the DOC 2.0 queries at ≥5 s spacing with the partial result
returned rather than the whole run lost. Surface `source_status: throttled` in the UI — the
backend already measures it.

**3. The v2 honesty fields never reach the page.**
`template_matches`, `aged`, `window_days`, `official_corroborating` are computed and correct on
`/api/v2/corroborate` and consumed by nobody; `CorroborationVerdict` is dead code. Meanwhile the
dossier names state media only as an aggregate count and puts no tier chip on the evidence
receipts an editor actually cites. Fix: wire the claim verdict into the pin section (or merge the
two endpoints), and render the tier chip on evidence receipts, not just corroboration citations.

*Also worth a chip each, below the top 3:* the `⚠` inside ISO dates (add a date guard to
`isFigureClaim`); the ungrammatical `reported (uncorroborated)` substitution when corroboration is
missing (soften the sentence, don't splice the phrase); the measured cross-read tension not
reaching the synthesis prose; `language:en` and `bluesky` listed as outlets in the 5W+H `HOW` row;
and `tass.com` rendering `UNCLASSIFIED` next to `⚑ state`.

---

## Reproduction

```bash
# lane works direct-to-Fly, breaks through the proxy
curl -m 180 -w '%{http_code} %{time_total}\n' -X POST \
  https://atlas-api-pedro.fly.dev/api/v2/dossier/corroborate \
  -H 'Content-Type: application/json' -d @corrob.json      # 1 pin 21.7s · 2 pins 31.4s · 200
#   → same payload via observatory-global.vercel.app/api/... = 502

# upstream rate limit the handler ignores
for i in 1 2 3; do curl -s -o /dev/null -w "%{http_code}\n" \
  "https://api.gdeltproject.org/api/v2/doc/doc?query=syria%20russia%20bases%20deal&mode=artlist&format=json&timespan=14d"; done
#   → 429 / 200 / 429  ("limit requests to one every 5 seconds")

# the fully-implemented v2 verdict that no frontend calls
curl -X POST https://atlas-api-pedro.fly.dev/api/v2/corroborate \
  -H 'Content-Type: application/json' \
  -d '{"headline":"Syria and Russia reach deal on future of Russian bases at Hmeimim and Tartous","country":"SY","published_date":"2026-08-10"}'
grep -rn "v2/corroborate" frontend-v2/src | grep -v test    # → one comment, zero callers
```
