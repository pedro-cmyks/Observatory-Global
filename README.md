# Observatory Global 🌐

Real-time global narrative intelligence platform. Visualize what the world is talking about.

## Features

- **Global Heatmap**: 52+ countries with real-time news activity
- **Sentiment Analysis**: Color-coded mood (red=negative, yellow=neutral, green=positive)
- **Information Flows**: Connections between countries discussing similar themes
- **Theme Drill-down**: Explore what's being said about specific topics
- **Morning Briefing**: Daily summary of global narratives
- **Search**: Find themes, countries, and sources

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Python 3.10+

### Setup

```bash
# Clone repository
git clone https://github.com/pedro-cmyk/ObservatorioGlobal.git
cd ObservatorioGlobal

# Start database
docker-compose up -d observatory-db

# Backend (in one terminal)
cd backend
pip install -r requirements.txt
uvicorn app.main_v2:app --host 0.0.0.0 --port 8000 --reload

# Frontend (in another terminal)
cd frontend-v2
npm install
npm run dev

# Start ingestion (in another terminal)
./infra/auto_ingest_v2.sh
```

Open http://localhost:3000

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   GDELT     │────▶│  Ingestion  │────▶│ PostgreSQL  │
│   GKG API   │     │  (Python)   │     │ TimescaleDB │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐     ┌──────▼──────┐
                    │   React     │◀────│   FastAPI   │
                    │   Deck.gl   │     │   Backend   │
                    └─────────────┘     └─────────────┘
```

## Data Source

- **GDELT GKG** (Global Knowledge Graph): Real-time news from 200+ sources
- Updates every 15 minutes
- Coverage: 100+ languages, 190+ countries

## Known Limitations

| Feature | Status | Notes |
|---------|--------|-------|
| Country-level data | ✅ 100% | All signals have country code |
| Themes | ✅ 100% | Full GDELT taxonomy |
| Sentiment | ✅ 100% | GDELT tone analysis |
| Precise coordinates | ⚠️ 0.02% | Most signals lack lat/lon |
| Person names | ⚠️ 4.9% | GDELT limitation |

## Roadmap

### Phase 1: MVP ✅
- [x] Real-time ingestion
- [x] Country visualization
- [x] Theme-based flows
- [x] Search functionality
- [x] Briefing dashboard

### Phase 2: Enhanced Context
- [ ] Article titles/summaries
- [ ] AI-generated theme summaries
- [ ] Additional data sources (NewsAPI, RSS)

### Phase 3: Advanced Features
- [ ] Time-lapse animation
- [ ] Custom alerts
- [ ] User accounts
- [ ] API access

## Contributing

Pull requests welcome. For major changes, open an issue first.

## License

MIT
