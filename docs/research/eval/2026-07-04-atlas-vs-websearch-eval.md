# Atlas vs. plain web search — a real analyst task (2026-07-04)

**Purpose.** Stop polishing; USE Atlas on a real question the way a narrative
analyst would, document the path, then run the same question on plain web search
and compare. Honest verdict: is Atlas an *axis* (eje) or just nice-looking
(bacano)? Driven visually in the live preview (frontend-l11 :3210, prod DB).

## The path (visual, screenshotted)

1. Landed on Atlas. Universe field + a thread open in the stream. First honest
   finding: the open thread was **"Portugal Beats Croatia 2-1"** — a beach-soccer
   score presented as a narrative thread (noise class leading; see Weaknesses).
   But the right rail carried real threads: Food price stress, Heat & public
   health, Gang control, **Election legitimacy dispute (1.4k, accelerating)**,
   Flood & landslide disaster.
2. Picked **Election legitimacy dispute** — the best test of Atlas's unique
   claim (a narrative that is inherently cross-country). Clicked it.
3. Atlas detail delivered, in one view:
   - **1,269 assigned signals · 15 countries · avg tone −0.37.**
   - **Drill-down (R3 spine) into 2 concrete stories:** "Peru Election Results
     Proclamation" (19 sig) + "Gombe LG Election Results" (Nigeria, 29 sig).
   - **Per-country volume + tone map:** US 207/−0.6 · **India 143/−1.5** ·
     Russia 46/−1.2 · Brazil 41/−0.5 · **Greece 41/−1.6** · Nigeria 39/−0.6 ·
     Spain 37/−0.2 · **Moldova 33/−1.8** · UK · Australia.

The **insight Atlas handed me for free**: election-legitimacy is a *simultaneously
global* narrative right now — volume-led by the US & India, but framed most
negatively in Moldova, Greece, India, Russia — and it grounds out in two concrete
disputes I was not tracking (Peru's proclamation; Nigeria's Gombe locals).

## The plain-web comparison

**Query 1 — same as the analyst would type:** *"election legitimacy dispute 2026
Peru … Nigeria Gombe"*. Web returned deep, authoritative coverage of the ONE
story it recognised — **Peru** (Wikipedia, Al Jazeera, Bloomberg, Crisis Group,
Britannica): Fujimori vs Sánchez, first-round fraud claims by López Aliaga, the
foreign-vote dispute, proclamation due July 3. **But it returned nothing on
Nigeria's Gombe election** — a story Atlas had co-clustered into the same
narrative.

**Query 2 — the critical test:** was Atlas's India signal (143 sig, −1.5) TRUE,
or gate-noise? *"India election legitimacy dispute June 2026"* →
**confirmed real and major**: Mamata Banerjee refusing to recognise results, the
Modi government's "SIR" roll purge deleting ~9M voters (disproportionately
Muslims), the ongoing "vote chor" movement, a TMC faction dispute, ECI under
scrutiny (Democracy Now!, Democratic Erosion, Legal Service India).

**So Atlas's cross-country tone map pointed me at India — a genuine, high-intensity
election-legitimacy crisis — that I would NEVER have reached starting from a
"Peru election" web search.** The aggregation discovered the pattern before I
knew to ask.

## Verdict: Atlas is an eje — for DISCOVERY, not for the ANSWER

| | Atlas | Plain web search |
|---|---|---|
| **Discovery / where to look** | **Wins.** Named 15 countries + tone in one view; surfaced India & Nigeria unprompted | Requires you to already know the country/event to search |
| **Cross-country pattern** | **Wins.** "Election-legitimacy is hot in PE+IN+NG+MD+GR+RU simultaneously" is the product | No notion of the global shape; one story per query |
| **Under-covered stories** | **Wins.** Gombe (NG) surfaced; web has ~nothing | Ranks the already-loud (Peru), misses the quiet |
| **Depth on a specific event** | **Loses.** Gate kept 1/1,269 → all UNVERIFIED candidate material | **Wins.** Banerjee/SIR/vote-chor specifics, verified, sourced |
| **Tone / framing quantified** | **Wins** (−1.5 India vs −0.2 Spain) | Manual reading only |

**Atlas = the radar (where / what-tone / what-co-occurs / what's-under-covered).
Web = the answer (what exactly happened).** They're complementary, and the radar
role is *exactly* the product wedge — "honest situational awareness on who is
saying what across countries." On this task Atlas earned the eje label for the
first-mile job. The moment it points you somewhere, you still leave for the web
to verify — until the gate-recall gap closes.

## Weaknesses this task exposed (live, honest)

1. **Gate recall is the #1 blocker to Atlas being an answer-tool, not just a
   radar.** The election-legitimacy slice kept **1 of 1,269** signals → the whole
   cross-country map is served as UNVERIFIED "candidate material." The signal is
   real (India confirmed) but Atlas can't *stand behind* it. Maps to #204
   taxonomy / gate-recall + #229 clustering recall (the inventory doc's measured
   #1 lever). This is the thing to fix next if Atlas is to be trusted, not just
   suggestive.
2. **Noise classes still lead surfaces.** The open thread was a beach-soccer score
   ("Portugal Beats Croatia"); global PUBLIC ATTENTION was Mbappé / Harry Kane;
   FORUM DISCUSSION was Lemmy craft posts ("Little wolf girl I made my daughter").
   → #248 noise classes; lifestyle/sport damp exists but public-attention & forum
   lanes aren't damped.
3. **Label bug (already captured as a task):** the map key + stream header showed
   `dynamic-topic-821` instead of the thread's name.

## So what next (this eval's recommendation)

The eje is real for **discovery/situational awareness** — that's shippable value
today and matches the wedge. To convert "suggestive radar" → "trustworthy desk",
the single highest-leverage move is **gate/clustering recall** (#229 + #204): it
turns 1-of-1,269 UNVERIFIED into a coverage map an analyst can cite. Everything
else (more viz, F4 cutover, attention roles) sits behind that. Concurs with the
alignment doc's next-3-moves.
