# Sonda ciega — usuario frío en prod (2026-08-12)

**Protocolo**: agente sin CONTEXTO ALGUNO (ni el nombre del producto), solo el
URL. Prohibido leer repo/docs/web — solo lo que el sitio muestra. ≥15-20
interacciones reales, incluyendo pase móvil a 375px.

**Confounds conocidos (leer antes de juzgar la sección BROKE):**
1. La sonda corrió MIENTRAS la cadena nocturna de recuperación (corrida manual
   post-incidente +x) saturaba Supabase — parte de la tormenta 429/502/503 es
   de esa hora, no del steady-state. La clase de falla es real igual (el
   council la vio en días quietos), pero la severidad de hoy está inflada.
2. El "Workbench 3/4 pinned" que vio en frío era contaminación DEL TEST: el
   agente del Frank-test había dejado su investigación en el MISMO perfil de
   browser compartido. No es estado del producto.
3. "Country editions dead" (DE/NG "could not assemble"): transitorio de la
   misma saturación — verificado sirviendo 0.9-2s con slot_guard minutos
   después. El hallazgo de diseño que SÍ queda: bajo carga, el orden
   artefacto-fresco→build-vivo→artefacto-viejo cuelga al lector en el paso 2;
   debería servir el artefacto viejo YA y refrescar en background.

**El reporte, verbatim y sin editar:**

---
I've explored thoroughly. Here's my cold read.

---

# Cold read: observatory-global.vercel.app ("ATLAS")

## 1. FIRST 60 SECONDS

Before clicking: a serif wordmark, "ATLAS.", "The news of the world, **measured**," on cream paper with a faint constellation. Two buttons: *Read the Brief* / *Open the console*. Three numbers under the fold: 855k signals indexed, 126 countries of voice, "live · ingesting every ~15 min."

My guess was: **a data-journalism side project or research demo — a pretty dashboard that counts news articles and colors a map.** I assumed the word "measured" was marketing, that "Open the console" led to a chart page, and that the whole thing was one person's portfolio piece.

Half right. It *is* one person's project (the footer quietly says `Source: atlas-api-pedro /api/v2`, and there's a Ko‑fi tip jar instead of a pricing page). But I badly underestimated the depth. There are four distinct products behind that door, and the word "measured" turned out to be load-bearing — it's an actual editorial doctrine that shows up in the UI dozens of times, including in places where it costs the product something.

---

## 2. WHAT IT ACTUALLY IS

Atlas ingests global news wire + RSS + a few attention feeds (Google Trends, Wikipedia pageviews) and a commentary lane (Bluesky/Lemmy), embeds every headline multilingually, clusters them into **"narrative threads,"** and then measures the *coverage* of each thread rather than reporting the news itself.

The core claim it makes, and it's a narrow one on purpose: *"This many outlets, from these countries, in these languages, published about this — and here are the headlines."* It explicitly refuses to say what's important or true.

Four layers, and they really are different products:

- **L0 Landing** — the pitch, with live numbers.
- **L1 Brief** (`/brief`) — a newspaper front page for the last 24 h. Lead story + desk, each with clickable "receipts" (real headlines, real domains, source-language excerpts, outlet-origin flags). Three tabs: *The World*, *Under the Radar*, *Culture, Sport & Life*.
- **L2 Console** (`/app`) — a dense analyst terminal: equal-area heat globe with co-occurrence flow arcs, a live signal stream (~6/min), a ranked narrative-thread rail with sparklines, a semantic "universe" orbital view, and a bottom dock (Anomaly / Source Integrity / Under the Radar / Markets).
- **L3 Workbench** — pin evidence into investigations; pins freeze a snapshot so your dossier "doesn't drift under you." Stored in your browser, not the server.

**Who it's for:** it says so plainly — journalist, OSINT researcher, newsroom desk, policy analyst. I agree with its own assessment. This is not a consumer news app; a normal reader would bounce off L2 in ten seconds.

**What I'd use it for:** two things, specifically. (a) *"Who is actually covering X, and who isn't?"* — the self-voice / foreign-voice split. (b) *"What has real coverage volume but zero verified reporting?"* — the coverage-gap panels. Both are questions a news site structurally cannot answer about itself, and Google can't answer at all.

---

## 3. WHAT WORKED — things I couldn't get elsewhere

**East Timor at 12σ.** In the Anomaly dock, a ranked list of countries whose coverage departed from *their own* baseline: East Timor 12.4σ, Bhutan 3.7σ, Zimbabwe 2.8σ. I clicked East Timor. The map flew there, every panel re-scoped, and I got: *47 signals · Source Mix 10 · **100% foreign** · Narrative Threads 0*, plus a plain-language summary ("led by US Politics, Environment, and Leadership… most-covered figures: anthony albanese and sue lines"). That's a real finding delivered in one click: East Timor spiked, and **nobody in East Timor wrote any of it.** No news site tells you that. This is the product's actual thesis working.

**Clicking Australia on the globe.** Flow arcs fanned out from Australia (width = co-occurrence strength), the thread rail re-ranked to Australian threads (NSW ICAC Liberal Corruption, Cost of Living Crisis, Avian Flu Outbreak, Sydney Airport Near Miss), and the dock filled with **GAPS IN AUSTRALIA**: gang control 49 raw / 0 verified, telecom shutdown 48/0, energy grid instability 22/0, trade restriction 12/0. Every panel obeyed one focus. That "click a thing, the whole instrument re-points" behavior is genuinely good and I didn't expect it to work.

**The "Narrative Biography · 14 weeks" on a thread.** Opening *Ebola Outbreak Congo* gave a stitched timeline of that story's ancestry across 14 weeks of archived clusters — with the stitching parameters printed underneath (`8 topic-era 0.882 · 8 era-era 0.862 · stitch min 0.90`). Watching a story's identity persist and mutate across months is not something I can assemble by hand.

**Semantic search that actually crossed languages.** I searched "water crisis." It returned Johannesburg's water crisis, UN warnings on Palestinian water shortages, Italy's rice-belt drought, and a tanker shortage in Vizag — four continents, verified, at 0.86 similarity. That's a genuinely useful sweep.

**Press vs. public, side by side.** The dock shows Google Trends *global* — Roblox, Spider-Man, Zendaya, Tom Holland, "Deaths in 2026" — directly beside a press rail reading Ebola, Syria bases, Thailand school shooting. The gap between those two columns *is* the insight, and it's rendered without commentary.

**Honest failure as a first-class output.** When my "water crisis" query's thread lane timed out, it didn't fake a result. It printed: `GAP — Thread lane unavailable (TimeoutError); coverage unknown`, then `No coherent thread currently covers the 'water' axis…`, then a reconciling ledger: *478 candidates evaluated · 2 primary · 480 low confidence · partial ledger · lane degradation disclosed.* I have never seen a dashboard show me its own downranking ledger. Same discipline on the landing page ("Live voice-mix unavailable — showing the dated baseline… rather than pretending it is current") and in the empty states ("Nothing under the radar in East Timor: no category reached the 8-signal floor with zero verified coverage").

**Receipts are real.** Every headline links to a specific article URL, tagged with outlet, tier (MAJOR / LOCAL / **STATE**), origin country, and where fetched — including `via Wayback Machine` when the live page was dead. `arabic.rt.com` and `russian.rt.com` were marked STATE without me asking. That's the trust move.

---

## 4. WHAT CONFUSED ME

**The clustering is visibly wrong in places, and the honest labels don't fully rescue it.**
- *"US Bombards Iran Over Ormuz Attack"* (88 raw signals) contains, under a "Syria" subheading, two articles about the **IMF praising Syrian economic growth**. Unrelated to bombing anything. It's flagged AWAITING VERIFICATION / medium confidence — but the headline is still a dramatic assertion of a war act sitting on top of economic-outlook stories.
- *"Motorcycle and Vehicle Crashes"* has receipts from Iowa City, South Dakota, and Northern Ireland but is tagged `IN COVERAGE: Canada, United Kingdom`. There's a footnote explaining coverage-country ≠ subject-country, but as a reader my eye reads it as an error every time.
- Inside the *Ebola Outbreak Congo* thread, the Bluesky lane attached a Brazilian police-assault post at **89%** and a Greek unemployment stat at **80%**. Labeled UNVERIFIED, but the scores make noise look like signal.

**"Coverage gap" categories don't match their examples.** *Telecom or internet shutdown* — 246 raw, 0 verified — sampled: an Atif Aslam story about fans using VPNs, and a bill about Trump's social media posts. *Mining and resource safety crisis* sampled an aluminium stock move. The gaps are the most interesting idea on the site and the examples undercut them.

**Search matches on the wrong word.** "water crisis" surfaced *FIFA Leadership Crisis* and *FIFA crisis: Confederations…* as top live threads. Honestly tagged PARTIAL MATCH, but it's matching "crisis."

**Numbers disagree with each other on the same screen.**
- Germany's country card: **4,840** signals / 24 h. The signal-density list twelve inches below: Germany **3,836**.
- Console header: **175 countries · 100,587 signals**. Console dock, same view: **218 countries · 109,632**. Brief: **218 / 109,632**.
- East Timor is "▲12σ above 7-day baseline" in the alert row and "z: 71.2" in its own Trust Indicators.
- East Timor scores **Source Diversity 98** while 7 of its 10 signals come from one domain — and **Source Quality 30** right beneath it. I can't reconcile those.
- The date chip read `FROM 9 AUG 2026` on desktop and `FROM 5 AUG 2026` on mobile.

**The market deltas look alarming until you dig.** The Brief shows `LAST CLOSE` and `WTI ▲ +20.10%`, `SAP ▲ +36.06%` — which read as one-day moves. Only after clicking through to the full chart did I find the tiny `· 30d`. On the summary card that's genuinely misleading.

**Jargon and internals leak.** "gated," "seal attempt likely in progress," "composite rank," "candidate stitch," "UNVERIFIED · EXTENDED (~75% MODEL)," and — in Source Integrity — the literal string **"SOURCE HEALTH: Dynamic Topic 12157."** A raw database id, shown to the user.

**I never figured out why Slovenia.** The Markets dock and the Public Attention panel both scoped themselves to Slovenia at one point with no action from me ("SLOVENIA · OWN INSTRUMENTS", "PUBLIC ATTENTION · SLOVENIA — No attention data"). Nothing explained the choice.

**"Workbench 3/4 pinned" on a cold visit.** My very first console load showed a pre-existing investigation ("Syria Russia Bases", 4 pinned, chips for Putin/Syria) that I never created. Either seeded demo state or someone else's leftover — either way it undermines "your pins live in your browser."

---

## 5. WHAT BROKE

- **Thread detail 502'd repeatedly.** Clicking *Open thread →* from the Brief for the lead story landed in the console and returned a bare `Error: HTTP 502` in the panel. Clicking the same thread again in the rail: 502 again. A different thread eventually loaded — after ~20 seconds.
- **Country editions are dead.** Searching *Nigeria* returned `SIGNALS 1,169 / THREADS 6` and then, immediately below, *"Atlas could not assemble this country's edition right now."* Same for *Germany* (4,840 signals / 6 threads → could not assemble). The panel asserts the threads exist and then can't render them. Two for two.
- **Universe view failed, then worked on manual retry.** "Universe data unavailable. The field endpoint did not answer (already retried once)." One click of ↻ RETRY and it rendered fine.
- **The console cold-load takes 20–30 seconds** on a plain loading screen. Twice I thought it had hung.
- **The console layout shattered on viewport resize** — panels collapsed into small boxes floating in whitespace. Fixed only by a full reload.
- **Multiple mobile controls are inert.** At 375 px the bottom nav's **Lens** and **Live** tabs, the **WORKBENCH** button, and the "Expand the investigation frame" handle all did nothing but select their own label text. The mobile Brief itself is good; the mobile console is a read-only poster.
- **Mobile stat strip is clipped** — `SOURCES / 43,49…` cut off at the edge.
- **The console error log explains all of it:** a wall of **429 (rate limited), 502, and 503** responses. The backend is under-provisioned or aggressively throttled, and every "unavailable" state I hit traces back there.
- **One internal contradiction I'd call a bug, not a degradation:** the Brief lists *"Russian Air Defense Shoots Down Ukrainian Drones — 116 SIGNALS · **0 sources**"* with no receipts at all. 116 signals from zero sources is not a possible state.

---

## 6. WOULD I RETURN?

**Yes — but for one job, not for news.**

The job: *"Country X is suddenly in the news / suddenly isn't. Who's actually writing it, from where, in what language, and what has volume but no verified reporting?"* For that specific question, nothing else I know of gives me a one-click answer with links. I'd come back before writing anything about a country I don't cover regularly.

I would **not** come back to read the news. The Brief is beautiful, but it's a lagging, noisier version of any wire front page, and its lead story the day I visited was a jalapeño recall.

**The single change that would most raise my odds of returning: make the thread detail reliable.** Everything the product promises — receipts, coverage geography, source mix, the narrative biography — lives behind *Open thread*, and that door returned 502 the first three times I knocked. The honesty framework is already doing heroic work covering for an infrastructure problem; at some point "we say so plainly" stops being a virtue and starts being the whole experience. Fix the 429/502 storm before adding one more feature.

(A close second: **fix or remove the country edition.** "6 threads exist" followed by "could not assemble" is the one place the site tells me something and then fails to honor it — which is precisely the sin the rest of the product is organized around not committing.)

---

## 7. TRUST

**I largely believed it — and the reasons are unusually concrete.**

What earned trust:
- **Falsifiable receipts.** Every claim resolves to a real URL at a real outlet. I checked hrefs: `newsweek.com/taylor-farms-publishes-new-list…`, `medindia.net/news/usda-warns-jalapeño…`. These aren't decorative.
- **It states its own ceilings with numbers.** The docs volunteer that 83.3% of language-known signals are English, that ~half carry no language metadata at all, that its own diversity score is **40.1/100**, that ReliefWeb is wired but produces nothing so it isn't claimed, that "anything before May 2026 does not exist in Atlas." A system that publishes its worst numbers is not optimizing for my credulity.
- **It explains a disagreement instead of hiding it.** There's a whole docs section on why two different source counts appear across surfaces (raw-domain base vs. attributable base, ~6× apart) and an explicit instruction never to compare them.
- **It marks state media unprompted.** RT tagged STATE, not "news."
- **It refuses to claim importance.** "Coverage counts are the volume of press, not a judgement of importance." "What Atlas cannot tell you: whether a story is true, whether it is important, or what will happen next."
- **Empty states have thresholds attached** rather than being blank.
- **The heat map isn't a population map.** They explain that raw volume would leave the US permanently red, so heat is anomaly-vs-own-baseline. Verified in practice: US was not the reddest thing on screen; Tajikistan, Luxembourg, Malta and Côte d'Ivoire topped "Heating Up."

What produced doubt — none of it fatal, but real:
- **The internal numbers don't agree** (Germany 4,840 vs 3,836; 175 vs 218 countries; 12σ vs z=71.2). A product whose entire pitch is "measured" cannot afford two answers to "how many signals did Germany have." This is the single biggest hit to my confidence.
- **116 signals / 0 sources** is a state that shouldn't exist.
- **Composite scores I can't audit.** Diversity 98 on four outlets, one of which holds 40%, sitting next to Quality 30. The docs are transparent about *methodology*; the individual scores are not legible.
- **The honesty framing can be load-bearing in a way that shades toward cover.** "Awaiting verification" is doing a lot of work under a headline like "US Bombards Iran Over Ormuz Attack" that is stitched partly from IMF reports on Syria. Labeling a bad cluster honestly does not make it a good cluster — and a scanner reads the headline, not the badge.

**Net:** I trust the *evidence layer* — the headlines, links, outlet origins, tiers, and language tags — close to fully. I trust the *measurement layer* — the counts, σ-scores, diversity indices — provisionally, and less after seeing the same quantity reported two ways on one screen. I trust the *label layer* — the auto-generated thread names — least, which is exactly what the product itself tells me to do ("Read the sources, not the label"). That alignment between what it warns me about and what I independently found wrong is, ironically, the strongest trust signal on the site.
