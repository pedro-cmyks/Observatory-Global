# Experiment — independent LLM read of the raw corpus vs Atlas's math (2026-07-13)

**Question (Pedro):** the biggest story of the day led the daily brief with only
six citations — is Atlas's mathematical selection + clustering + relation-finding
actually capturing the depth and the connections of what is happening? Process
the raw 24 h corpus as an LLM would, extract the real story of the day and its
connections, and compare against what Atlas produced.

**Method.** Read-only over `signals_v2`: token-frequency to find the raw's
biggest clusters, a 60-headline diverse sample of the top cluster for an
independent LLM (this model) read, and Atlas's own `/threads` + the sealed daily
edition for the comparison. No cherry-picking — the sample is `DISTINCT ON
(headline)` ordered, and the frequencies are whole-corpus counts.

## What the raw corpus says is the story of the day

Whole-corpus headline frequency, last 24 h (`145,520` signals / `115,580`
distinct headlines):

| token | signals |
|---|---:|
| Iran | 3,826 |
| Trump | 3,621 |
| Ukraine | 733 |
| Israel | 672 |
| Wimbledon | 258 |
| Sinner | 135 |
| Cunha | 13 |

An LLM reading the Iran/Trump headlines sees **one massive, densely connected
story**: the **US–Iran war resumed** ("Trump ha comunicato al Congresso la
ripresa della guerra contro l'Iran"; "US Strikes Iran Again"; "Mojtaba Khamenei
is 90% gone"), a **Strait of Hormuz blockade + 20% transit fee** ("Guardian of
the Strait"; Iran's FM Araghchi mocking "20% is too much, we'll be fair"; "Iran
blames US for disrupting Hormuz shipping"), an **Iranian plot to assassinate
Trump**, and the **death of Lindsey Graham** ("Trump whisperer Lindsey Graham
dies at 71: FBI involved as assassination…"). Iran–US–Trump–Hormuz–Graham–
Khamenei are one story, thousands of signals, many languages.

## What Atlas produced

- **Daily brief lead:** "Dino Blocks Cunha Funds" — a Brazilian Supreme Court
  asset freeze, **13 signals in 24 h**. The US–Iran war was not the lead; it was
  not in the edition's visible spine at all.
- **Global top threads** (Atlas `/threads`, 24 h): Ukraine War (71), Senegal
  Political Turmoil (64), **Telstra Outage (AU telco, 41), "Fas Hollanda'yı
  Eledi" (Morocco-Netherlands football, 56), Leuralla Estate Record Sale (AU
  property, 36), Ioane Sa'ula Acting Journey (42), Chris Hemsworth's $2000 Meal
  (37), Suiza Elimina a Colombia (football, 48), Bonnie Tyler Death (43)**. The
  US–Iran war — the largest cluster in the raw — is **absent from the top ten**.
- **Iran-scoped threads:** the one war story is **shattered into six
  disconnected fragments** — "Iran Military Posturing" (41), "Israel Plot to
  Kill Iran Negotiators" (66), "Strait of Hormuz Tensions" (24), "US-Iran Talks
  Continue" (78), "Strait of Hormuz Tanker Attacks" (17), "Yemen Conflict
  Escalation" (24) — with no measured relation reconnecting them (the daily
  `narrative_spine` carried **0 relations**).
- **Stale label:** "US-Iran **Talks Continue**" (78 signals) while the raw of the
  same window says the **war resumed** — the frozen label no longer matches its
  own evidence.

## Measured gaps

1. **Selection.** Volume has zero ranking weight by design (volume≠importance —
   the right instinct against a US-media firehose). Taken this far it is a bug:
   a 3,826-signal war earns no credit and loses the front page to a 37-signal
   celebrity-meal story and a 48-signal football result. An editor leads with the
   war; Atlas led with a 13-signal court filing. The publishable-brief goal fails
   here first.
2. **Fragmentation / no reconnection.** Clustering splits the war into six
   sub-event threads (Hormuz, plot, strikes, talks, tankers, Yemen) and the
   relation layer never rebuilds the umbrella — the exact "more connections than
   six" Pedro expected. The umbrella/event-assembly that exists (R2) is not
   firing for the day's biggest event.
3. **Stale identity.** Thread labels freeze at creation; "Talks Continue"
   survived the pivot to war. Same class as the reliability-matrix label/evidence
   mismatch and the #257 coherence work.
4. **Noise not damped enough.** Football matches, a celebrity's meal, and a
   property sale sit in the global top ten; the lifestyle/sport damp is too weak
   at the ranking layer.

## Interpretation

Atlas's honesty stack (subject geography, grab-bag flags, cited prose) is real
and improving, but this experiment shows the layer underneath — **which story is
the story, and which fragments are one story** — is where the depth is lost. The
math currently answers "what is coherent and verified and moving" and gets a
clean Brazilian court case; it does not answer "what is the world's biggest,
most-connected event today" and so misses a resumed US–Iran war. An LLM reading
the same raw answers the second question immediately.

## Recommended work (throughput / depth)

- **A consequence/importance signal that is not raw volume but is not zero** —
  e.g. cross-language breadth + distinct-actor count + geographic spread, so a
  genuinely global event outranks a national football result without reopening
  the US-firehose bias.
- **Event umbrella for the biggest events** — reconnect Hormuz/plot/strikes/
  talks into one "US–Iran war" story with the fragments as sub-threads (R2
  umbrella must fire here); measure why it did not.
- **Label refresh on pivot** — when a thread's fresh evidence contradicts its
  frozen label ("talks" → "war"), re-label from the current cluster (the daily
  already has edition-scoped current labels; extend to serving threads).
- **Stronger lifestyle/sport/celebrity damp at ranking**, measured against this
  same top-ten as the fixture.

This is the honest depth test behind "publishable as news": a brief that leads
with a celebrity meal over a US–Iran war is not publishable, however well cited.
