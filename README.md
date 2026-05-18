# Atlas

> Public narrative intelligence for seeing how information moves across countries, sources, languages, and public attention.

Atlas is not a news aggregator. It is an open-signal intelligence product: it ingests media, public-attention, humanitarian, social, and provenance signals, then turns them into maps, briefs, narrative threads, country context, and investigation workspaces.

## Product Flow

Atlas is organized as a three-step experience:

1. **Landing** — explains what Atlas is, who it is for, and which data layers power it.
2. **Brief** — a readable daily orientation layer for what is moving now.
3. **App Console** — the analyst surface: map, signal stream, narrative threads, source integrity, public attention, country briefs, and workspace.

The current design keeps **Brief** as the live orientation page. Future publication outputs such as **Atlas Daily** or a Workspace-generated investigation newspaper should be built as generated/shareable artifacts, not by renaming the live Brief.

## Current Capabilities

- **Live signal stream** — open media and event signals, updated continuously.
- **Global narrative map** — country-level activity and attention patterns.
- **Narrative threads** — themes ranked by volume, spread, velocity, sentiment, and public-attention matches.
- **Country Brief** — country-level context, source diversity, people, themes, sentiment, and evidence links.
- **Public Attention** — Google Trends and Wikipedia attention signals where available.
- **Source Integrity** — source diversity, source concentration, and coverage-quality indicators.
- **Investigation Workspace** — pin countries, themes, people, sources, public-attention topics, and signals into an investigation graph.
- **Dossier export** — export workspace evidence and notes for research handoff.
- **NLP enrichment** — sentiment, named entities, framing, provenance, source family, language, and confidence fields. Multilingual scoring is being hardened before it is treated as fully reliable.

## Data Sources

Atlas is moving from a GDELT-first system into a multi-source intelligence layer.

| Source | Role |
| --- | --- |
| GDELT GKG 2.0 | Global media narratives, themes, people, sentiment, locations |
| GDELT Events | Actor/action geopolitical event stream using CAMEO codes |
| Curated RSS / ReliefWeb | Humanitarian and regional context with stronger source provenance |
| NewsData.io | Multilingual media coverage expansion |
| MediaStack | Country-specific media expansion, especially LatAm coverage |
| NewsAPI.org | Targeted crisis-query coverage |
| Reddit public feeds | Social/commentary layer for early narrative movement |
| Google Trends | Search-demand attention signal |
| Wikipedia Pageviews | Reference-seeking public attention signal |

Atlas should not rank the world by raw article count alone. The analytical model is designed around baselines, source diversity, language/source mix, country normalization, deduplication, and cluster-level scoring.

## Architecture

| Layer | Technology |
| --- | --- |
| Frontend | React 19 + TypeScript + Vite (`frontend-v2/`) |
| Backend | Python 3.11 + FastAPI (`backend/`) |
| Database | PostgreSQL / Supabase |
| Cache | Redis / Upstash |
| Backend hosting | Fly.io |
| Frontend hosting | Vercel |
| Maps/visualization | MapLibre GL JS, Deck.gl, React Force Graph |

Production work happens on `v3-intel-layer`. The old `frontend/` directory is deprecated; use `frontend-v2/`.

## Running Locally

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main_v2:app --reload --port 8000

# Frontend
cd frontend-v2
npm install
npm run dev
```

Copy `.env.example` to `.env` and set local database/cache values. Production secrets belong in Fly.io, Vercel, Supabase, and Upstash dashboards, not in git.

## Documentation

- Product docs: `/docs` in the web app.
- Roadmap: `docs/roadmap/2026-05-16-productization-roadmap.md`.
- Multisource hardening plan: `docs/superpowers/plans/2026-05-18-multisource-intelligence-hardening.md`.
- Backend docs: `backend/README.md`.
- Repository guidelines: `AGENTS.md`.

## Security Notes

- `.env`, `.env.*`, private keys, local MCP configs, virtual environments, checkpoints, logs, and runtime scratch files are ignored.
- API keys must be stored as provider secrets, not committed.
- The repository intentionally tracks `.env.example` files only.

## Status

Atlas is in active development. Current focus: data quality, multilingual NLP validation, source diversification, country heat methodology, workspace dossiers, and clearer product documentation.

Built with open data and public infrastructure: GDELT, Wikimedia, Google Trends, FastAPI, Supabase, Fly.io, Vercel, and React.
