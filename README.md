# Atlas

> See how information travels the world.

![Atlas screenshot showing global narrative map with signal stream and narrative threads](https://raw.githubusercontent.com/pedro-cmyks/ObservatorioGlobal/main/docs/screenshot.png)

## What is Atlas?

Atlas is a real-time global narrative intelligence platform. It shows how information moves geographically — which countries are talking about the same topics, how stories travel between regions, and how the same event gets framed differently across the world.

It is not a news aggregator. It has no editorial bias. It is a tool for curious people who want to understand the world without relying on an algorithm to decide what matters.

## What it does

- **Live signal stream** — real-time news signals from 50+ countries via GDELT, updated every 15 minutes
- **Global narrative map** — countries glow with signal intensity. Click any country to see what it's talking about
- **Narrative threads** — track how topics spread geographically over time. When did it start? Which countries picked it up? Is it accelerating or fading?
- **Correlation matrix** — which countries are discussing the same topics right now? Country-by-country and theme-by-theme views
- **Framing analysis** — the same topic covered differently by different countries
- **Anomaly detection** — countries with unusual activity spikes vs their 7-day baseline
- **Source integrity** — how diverse and concentrated are the information sources for any country or topic?
- **Live aircraft tracking** — real-time flight positions via OpenSky Network. Toggle the PLANE layer on the globe

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL (Supabase in production) |
| Cache | Redis |
| Frontend | React 19 + TypeScript + Vite |
| Map | MapLibre GL JS + Deck.gl |
| Data | GDELT Project (free, global, 15-min updates) |
| Hosting | Fly.io (backend) + Vercel (frontend) |

## Running locally

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### Setup

```bash
# 1. Start PostgreSQL and Redis
cd infra
docker compose up -d
cd ..

# 2. Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main_v2:app --host 0.0.0.0 --port 8000 --reload

# 3. Frontend (new terminal)
cd frontend-v2
npm install
npm run dev

# 4. Start data ingestion (new terminal)
./infra/auto_ingest_v2.sh
```

Frontend runs at `http://localhost:3000`, backend at `http://localhost:8000`.

### Environment variables

Copy `.env.example` to `.env`, then set at minimum:

```
DATABASE_URL=postgresql://observatory:changeme@localhost:5432/observatory
REDIS_URL=redis://localhost:6379
```

## Project status

Active development. The six-panel narrative intelligence terminal is live. Current work: 3D globe visualization, additional data source layers, and drift detection algorithms.

## Inspiration

Built out of curiosity during a period of global uncertainty — too much information, too many conflicting narratives, no clear view of how stories actually travel across the world.

The question was simple: can you build something that lets you *see* how information moves, without anyone telling you what to think about it?

---

Built with [GDELT](https://www.gdeltproject.org/) · [MapLibre](https://maplibre.org/) · [Deck.gl](https://deck.gl/) · [FastAPI](https://fastapi.tiangolo.com/)
