 🌐 Observatory Global

A real-time global narrative intelligence platform that visualizes worldwide information flows using GDELT (Global Database of Events, Language, and Tone) data.

## What it does

Observatory Global monitors global news in real-time and visualizes:
- **Heatmap**: Geographic intensity of news coverage
- **Flows**: Information connections between countries (who's talking about whom)
- **Nodes**: Country-level aggregations with sentiment analysis

## Features

- 🗺️ Interactive global map with multiple visualization layers
- 📊 Real-time data ingestion from GDELT (every 15 minutes)
- 🔍 Time-window filtering (1h, 6h, 12h, 24h, all)
- 📈 Sentiment analysis per country
- 🌡️ Heatmap showing news activity hotspots

## Tech Stack

- **Frontend**: React, TypeScript, Mapbox GL, Deck.gl
- **Backend**: Python, FastAPI
- **Database**: PostgreSQL
- **Cache**: Redis
- **Infrastructure**: Docker, Docker Compose

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/pedro-cmyks/Observatory-Global.git
cd Observatory-Global
```

2. Start the services:
```bash
cd infra
docker-compose up -d
```

3. Run initial data ingestion:
```bash
docker-compose exec api python -m app.services.gdelt_ingest
docker-compose exec api python -m app.services.aggregator
```

4. Open the application:
- Frontend: http://localhost:5173
- API: http://localhost:8080
- API Docs: http://localhost:8080/docs

### Automatic Data Collection

To continuously collect data every 15 minutes:
```bash
cd infra
nohup bash -c './auto_ingest.sh' > ingestion.log 2>&1 &
disown
```

## Project Structure
```
Observatory-Global/
├── backend/           # Python FastAPI backend
│   ├── app/
│   │   ├── api/v1/    # API endpoints (nodes, flows, heatmap)
│   │   ├── services/  # Business logic (GDELT ingestion, aggregation)
│   │   ├── models/    # Database models
│   │   └── db/        # Database configuration
├── frontend/          # React TypeScript frontend
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── store/       # Zustand state management
│   │   └── lib/         # Utilities
├── infra/             # Docker and infrastructure
│   └── docker-compose.yml
└── docs/              # Documentation
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /v1/nodes?time_window=24h` | Country nodes with intensity and sentiment |
| `GET /v1/flows?time_window=24h` | Information flows between countries |
| `GET /v1/heatmap?time_window=24h` | Geographic heatmap points |
| `GET /v1/health` | API health check |

## Current Limitations

- Data ingestion processes one GDELT file at a time (~15 min of data)
- Country coverage depends on GDELT's geographic tagging
- Heatmap currently uses country centroids (city-level precision in development)

## Roadmap

- [ ] Search functionality (by topic, country, keyword)
- [ ] Anomaly detection (vs historical baseline)
- [ ] City-level heatmap precision
- [ ] Data retention and archival system
- [ ] Multiple data source integration

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting PRs.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [GDELT Project](https://www.gdeltproject.org/) for the global event data
- [Mapbox](https://www.mapbox.com/) for mapping infrastructure
- [Deck.gl](https://deck.gl/) for data visualization layers
