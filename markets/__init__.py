"""L4 markets — personal trading-research layer (separate consumer, own creds).

Consumes Atlas over its public API + Yahoo's public chart API only; never shares
Atlas runtime credentials, never writes Atlas's DB. Nothing here is investment
advice; no employer IP. Every causal/lead-lag claim is gated on the #226 re-run.
See docs/research/markets-l4/2026-07-21-markets-relational-axis-design.md.
"""
