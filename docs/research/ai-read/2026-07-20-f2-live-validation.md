# F2 AI-read + F2.5 Leads — live validation (2026-07-20)

Spec: `docs/specs/2026-07-20-workbench-article-enrichment.md` §5/§5b.
All runs against PROD (Fly `atlas-api-pedro`), real articles, real threads.

## Quote gate (decision 3) — holds

- Romanian article (ziare.com, 157 words): 3 claims, **all with verbatim
  Romanian quotes, 0 dropped**; assertion-vs-attribution separated
  ("componenta militară" claim correctly `attributed` to Nicușor Dan).
- Long Romanian article (534 words): initial FAIL — DeepSeek truncated the
  JSON at max_tokens 1400 → read returned None. Fixed: budget 2400 + ask 6
  claims + truncation repair (parse back to the last complete claim; the
  cut tail is lost, never invented). After fix: 6 claims, 0 dropped.
- English Kyiv-attack articles (news.cn 245w, cyprus-mail 317w): 11 claims
  total, attribution chips PER UKRAINIAN AUTHORITIES / PER STATE SERVICE
  FOR EMERGENCIES / ASSERTED — each with its verbatim quote.

## Leads lane (the flywheel) — works, with two live lessons

Case: pin `dynamic-topic-5245` "Russian Attack on Kyiv", 2 fetched bodies.

Result (prod `/api/v2/research/leads`):
- **Vitali Klitschko** (person · Kyiv Mayor, from the BODY — no pinned
  headline names him) → 1 thread: `dynamic-topic-5157` Russia-Ukraine War
  Escalation, with his quote-context from the article.
- **Volodymyr Zelenskiy** (body spelling) → matched pool entities
  `volodymyr zelenskyy`/`volodymyr zelensky` → 2 threads: Russia-Ukraine
  War Escalation + Israel-Lebanon Framework Agreement (real cross-thread
  reach).
- Pinned dt-5245 correctly EXCLUDED from every lead.
- UI: pinning the Klitschko lead created the pin with
  `retrievalLane: 'body-lead'` — the galaxy grew a ring.

Live lessons fixed during validation:
1. **Diacritics/transliteration**: "Nicușor"/"Zelenski" vs pool ASCII →
   fold + surname-prefix rule (≥6 common chars; first names ≥3). A shared
   common WORD ("actor", "ministry") never glues two names (caught by a
   test that initially glued "Rare Actor"↔"Common Actor").
2. **Honest zero**: the Romanian regional case yields 0 leads — its actors
   genuinely aren't in the current top-40 pool. Served as honest empty,
   correct behavior.

Known cosmetic residue: outlet-orgs can surface as leads ("Xinhua" → a
thread carrying its syndication). Honest (1 thread, labeled org) but an
outlet-org filter is a cheap F2.6 candidate.

## Cross-read — honest paths verified

- Two same-story Romanian articles: `findings: []` — the model refused to
  invent overlap between claims about different moments (desecretization
  statement vs Kiev visit). Honest empty, correct.
- Validator drops: unknown claim ids, self-pairs, same-article pairs,
  invented kinds (frozen by tests).
- UI failure honesty: a 429 (paid bucket) initially rendered NOTHING —
  fixed to an explicit "Cross-read unavailable right now" state.

## NATO-Ankara acceptance (decision 5) — deferred to Pedro's frozen pins

The marquee's dt-390/2044/56 ids were RE-FOUNDED by the engine (dt-390
today = a Romania story); the original URLs live only in the frozen pins
in Pedro's localStorage. The by-the-book replay (AI-read vs the manual 4/4
corroboration) runs the first time Pedro opens the NATO-Ankara
investigation and presses AI READ / Cross-read — the dossier backfill
fetches his frozen URLs automatically. Until that run, F2's acceptance
rests on the live validation above.

## Rate-limit note

read/crossread/leads share the per-IP `paid` bucket (20/5min) — heavy dev
smoke testing 429s quickly; honest error states render.
