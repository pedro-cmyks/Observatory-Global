# Public Attention Investigation Panel QA

Date: 2026-05-07
Issue: #78

## Scenario

`Anomaly Alert -> Public Attention` should not dead-end in the search dropdown. Clicking a public-attention topic should open an investigation view in the center panel.

## Manual QA

- Ran the frontend locally against the Fly backend through a local `/api` proxy.
- Clicked `Ted Turner` in `PUBLIC ATTENTION`.
- Confirmed the center panel changed from `SIGNAL STREAM` to `PUBLIC ATTENTION`.
- Confirmed the panel showed:
  - Wikipedia pageview metrics and country count.
  - Wikipedia summary for `Ted Turner`.
  - Countries talking about the topic.
  - Connected themes derived from matching media signals.
  - Recent headlines mentioning the topic.
- Searched for `Ted Turner`, clicked the `WIKI` result, and confirmed it opened the same investigation panel instead of re-running search.

## Notes

- The panel uses existing `/api/v2/search/unified` data for media signals and connected themes.
- The Wikipedia summary is fetched client-side from the public Wikipedia summary API.
- No new backend endpoint was added for this MVP.
