# Telemetry weekly read — 2026-07-04

(Cadence debt from T5.1: "read weekly — the wedge anti-goal is ungoverned
without the reading." Last read 2026-07-01.)

## This week (06-27 → 07-04)

| event | n | sessions |
|---|---|---|
| app_open | 405 | 18 |
| thread_open | 111 | 9 |
| **first_value_moment** | **42** | **9** |
| brief_open | 29 | 8 |
| search_query | 13 | 3 |
| search_story_open (NEW 07-04) | 2 | 1 |
| brief_thread_open | 1 | 1 |

Weekly trend: value moments **3 (wk of 06-22) → 42 (wk of 06-29)**; app_opens
42 → 404; brief_opens 0 → 29 (the brief_open event only landed 07-01).

## Honest reading

1. **Value moments are no longer near-zero** — the 07-01 alarm ("only 3, none
   since 06-28") is resolved. 9 distinct sessions reached a value moment.
2. **Caveat: dev-noise inflates this.** Preview/browser-driving during build
   sessions emits real events (today's search_story_open ×2 = the build's own
   verification). No dev-session flag exists — numbers are an UPPER bound on
   organic use. Follow-up: tag dev sessions (localStorage flag or UA filter).
3. Search is still thin (13 queries / 3 sessions) — the new story panel's
   adoption question ("do people FIND?") now has instrumentation
   (search_story_open + search_query zero-flag); next week's read answers it.
4. brief_thread_open = 1: the Brief is read (29 opens) but threads are opened
   from the console, not the Brief — consistent with Brief=front-page,
   console=depth.

## Actions

- Next read: 2026-07-11. Watch: search_story_open (adoption), value-moment
  kinds split, brief_thread_open.
- Debt: dev-session tagging so organic vs build-verification separates.
