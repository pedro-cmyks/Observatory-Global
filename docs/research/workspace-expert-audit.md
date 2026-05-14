# WorkspaceBoard Expert Analyst Audit

**Date:** 2026-05-14  
**Method:** Synthetic walkthrough — analyst persona applied against known codebase state  
**Topic:** Drug Trafficking (`drug-trafficking` investigative concept → CRIME, ARREST, KILL, TAX_TERROR, ECON_TRADE themes)  
**Persona:** Intelligence analyst with 8+ years experience on financial crime and narco networks; familiar with Palantir, i2 Analyst's Notebook, and open-source OSINT platforms

---

## Phase 1 — Entry (0–2 min)

**Action:** Types "drug trafficking" in SearchBar. Concept card appears under "Concepts" with description and 5 themes. Clicks it.

**What happened:** `setConcept()` fires → `filter.theme` set to CRIME (primary) → Signal Stream, Source Integrity, Anomaly Alert, NarrativeThreads all react. Globe shows heat for CRIME-heavy countries.

**Analyst note:** Entry is fast and correct. The concept card in search is the right affordance — better than searching a raw theme code. Description text confirms scope before committing.

**Block:** After clicking the concept, there is no visible indicator that 5 themes are active, not 1. The console looks identical to a single-theme search. Analyst cannot tell if ARMEDCONFLICT and ECON_TRADE are also being applied or if only CRIME is active.

---

## Phase 2 — Signal Orientation (2–5 min)

**Action:** Reads Signal Stream in NOTABLE mode (default). Scans top 10 headlines. Switches to CRITICAL. Anomaly Alert status bar updates badge to STREAM: CRITICAL.

**What worked:** CRITICAL filter is fast (client-side). Anomaly badge feedback is clear. Stream drops to 4–8 items — the right density for rapid scanning.

**Action:** Clicks a headline about cartel violence in Sinaloa, Mexico. `SignalDetailPanel` opens (right overlay). Reads source, tone, persons mentioned.

**Block:** Persons mentioned in SignalDetailPanel are displayed as plain text pills. No click action. Analyst wants to pivot to the person (cartel figure) — this is a primary workflow in intelligence analysis. Pills are decorative only.

**Action:** Clicks Mexico in the Signal Stream entry's country tag. CountryBrief opens for MX.

**What worked:** Pivot from signal → country is instant. CountryBrief shows top themes, baseline anomaly, top sources.

---

## Phase 3 — Workspace Build (5–12 min)

**Action:** Opens Workspace (button in toolbar). Sees empty Trail tab. Notices "No trail yet" message.

**Analyst note:** Trail is already auto-populated from the last 3 clicks (drug-trafficking concept, Mexico signal, Mexico country brief). The trail list is correct and the numbered sequence is readable.

**Action:** Pins Mexico from trail. Pins the drug-trafficking concept from trail. Both appear in Pinned tab graph.

**What worked:** Pin from trail is one click. Graph builds automatically. Node types (concept vs country) have distinct colors.

**Block:** After pinning concept + country, the graph shows 2 nodes with no connecting edge. Analyst expects a relationship edge between "drug-trafficking" (concept) and "Mexico" (country where signal was found). Edge is missing because the relationship engine only connects nodes that were explicitly interacted with *together* — not inferred from thematic co-occurrence.

**Action:** Clicks on another headline (fentanyl seizure in Sonora). Pivots to Sonora source domain. Pins the source. Graph now has 3 nodes: MX, drug-trafficking, source.

**Block:** Source node is labeled with the domain name (e.g., `eluniversal.com`) but there is no visible indication of the source's geographic alignment or trust score in the graph view. Analyst has to open SourceIntegrityPanel separately to cross-reference.

**Action:** Zooms out graph to see full picture. At 3 nodes, labels are fully readable. Analyst notes that at larger scale (20+ nodes), the compact dot mode kicks in.

**What worked:** Compact dot mode at 20+ nodes is the right behavior. Hover tooltip shows full name. Zoom-to-expand pattern is standard in i2/Maltego.

**Block:** No way to annotate an edge. In Analyst's Notebook, edges carry relationship labels ("is connected to", "supplied by", "operated in"). In Atlas, edge labels are generic (VISITED, PINNED, RELATED) — not analyst-defined.

---

## Phase 4 — NarrativeThreads Drill-Down (12–18 min)

**Action:** Opens NarrativeThreads in left panel. Sees drug-related threads. Clicks "Cartel Violence" thread (ARMEDCONFLICT theme).

**What worked:** Globe flies to Mexico (top country). SourceIntegrity reacts and shows sources for ARMEDCONFLICT. Anomaly Alert shows THREAD: Armed Conflict badge. This is the panel sync from #111 — visible and correct.

**Block:** After clicking the thread, CountryBrief doesn't auto-open for the top country. Analyst has to manually click Mexico on the map. The thread selection implies geography — the panel sync should include CountryBrief.

**Action:** Clicks on Brazil in "Related countries" chip inside the thread row. Nothing happens. Analyst expects this chip to set Brazil as the country focus.

**Block:** Country chips inside NarrativeThreads rows are not interactive. Dead UI that looks interactive.

---

## Phase 5 — ThemeDetail Investigation (18–25 min)

**Action:** Clicks on CRIME theme in CountryBrief for Mexico. ThemeDetail opens. Reads top sources, recent coverage, related topics.

**What worked:** Stale-while-revalidate pattern keeps old data visible during reload. Related Topics section with comparison arrows is useful — analyst can compare CRIME vs CORRUPTION by clicking compare.

**Block:** ThemeDetail shows "AI Insight" block. Analyst reads it. Content is generic ("Crime is a multifaceted issue…") — not specific to Mexico or to the current time window. The insight doesn't use the active country/time filter.

**Block:** Recent Coverage shows 8 articles. Analyst wants to export these as a CSV or copy them to clipboard for a report. No export action available at the article level.

---

## Phase 6 — Workspace Export (25–28 min)

**Action:** Returns to Workspace. Clicks export button. Gets Markdown output.

**What worked:** Export is immediate. Markdown format is readable. Includes pinned nodes and notes.

**Block:** Export doesn't include session trail or the relationship graph topology (which node is connected to which, via what link type). A Palantir-style analyst would want a graph export (JSON adjacency list or Gephi-compatible CSV), not just a node list.

---

## Summary Findings

### What serves real analytical workflows

| Capability | Verdict |
|------------|---------|
| Concept search entry | ✅ Best-in-class entry point |
| Signal Stream pivot (country, theme, person from headline) | ✅ Fast and correct |
| Session Trail auto-build | ✅ No effort from analyst |
| Promote trail → pinned | ✅ One click |
| NarrativeThreads → panel sync (globe, source integrity, anomaly) | ✅ Closed in #111 |
| Compact dot mode at high node count | ✅ Correct behavior |
| ThemeDetail stale-while-revalidate | ✅ No jarring reloads |

### What blocks real analytical workflows

| Gap | Priority | Issue |
|-----|----------|-------|
| Person pills in SignalDetailPanel are not clickable | High | Existing open |
| No concept multi-theme indicator (5 themes active, shows 0) | High | New |
| No analyst-defined edge labels in workspace graph | Medium | New — create |
| Country chips in NarrativeThreads rows not interactive | Medium | New |
| Thread selection doesn't auto-open CountryBrief | Medium | New |
| AI Insight doesn't respect active country/time filter | Medium | Existing |
| No graph topology export (only node list) | Low | New |
| Source trust score not visible in graph node | Low | Enhancement |
| No article-level export from ThemeDetail | Low | Enhancement |

### What is redundant

- **"Show Trail Context" toggle in Pinned tab** — analysts switch to Trail tab directly; the overlay adds noise without clarity. Consider removing or demoting.
- **MARITIME filter in Signal Stream** — surfaced as a top-level tab alongside CRITICAL/NOTABLE, but maritime signals are rare and this tab is almost always empty. Move to secondary filter or collapse.

---

## Recommended Next Issues

Based on this audit, create:

1. **Make country chips in NarrativeThreads rows interactive** (set country focus on click) — 30-min fix
2. **Thread selection → auto-open CountryBrief for top country** — 1h
3. **Concept filter: show active theme count badge** (e.g., "5 themes active") in filter bar — 30-min fix
4. **Graph topology export** (JSON adjacency list alongside markdown) — 2h
