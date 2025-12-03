# Observatory Global - Project Status

**Last Updated**: December 3, 2025

## Current State: MVP Complete ✅

### Working Features

| Feature | Status | Details |
|---------|--------|---------|
| Map visualization | ✅ | 52+ countries with correct coordinates |
| Country sidebar | ✅ | Signals, sentiment, themes, sources |
| Theme flows | ✅ | Jaccard similarity-based connections |
| Theme drill-down | ✅ | Rich context with related themes, sources, persons |
| Search | ✅ | Themes, countries, sources |
| Briefing | ✅ | Daily summary dashboard |
| Time filters | ✅ | 1H, 6H, 12H, 24H, 2D, 1W |
| Ingestion | ✅ | Auto-running every 15 minutes |

### Recent Major Fixes

| Fix | Date | Impact |
|-----|------|--------|
| Theme context enrichment | Dec 3 | Theme detail now shows related topics, sources, persons |
| Flows endpoint Decimal error | Dec 3 | Fixed serialization of flow strength values |
| Country coordinate overwrite bug | Dec 2 | Prevented ingestion from corrupting manual fixes |
| GDELT source limits | Dec 2 | Removed arbitrary caps on API responses |

### Data Statistics (Recent)

- Total signals: ~45,000+
- Countries: 214 (in DB), ~52 active
- Sources: 4,800+
- Themes: 1,000+ active
- Date range: Nov 26 - Dec 3, 2025

### Architecture Decisions

1. **No Docker for development**: Hot-reload requires native processes
2. **PostgreSQL only in Docker**: Database persistence across restarts
3. **Deck.gl over Mapbox**: No API key required, GPU-accelerated
4. **TimescaleDB**: Optimized for time-series queries
5. **Theme-based flows**: Jaccard similarity instead of arbitrary connections

### File Structure
```
ObservatorioGlobal/
├── backend/
│   ├── app/
│   │   ├── main_v2.py              # FastAPI application
│   │   └── services/
│   │       ├── ingest_v2.py        # GDELT ingestion
│   │       └── theme_context.py    # Theme enrichment
│   └── requirements.txt
├── frontend-v2/
│   ├── src/
│   │   ├── App.tsx                 # Main application
│   │   ├── components/
│   │   │   ├── Briefing.tsx        # Morning briefing
│   │   │   ├── SearchBar.tsx       # Search functionality
│   │   │   └── ThemeDetail.tsx     # Theme drill-down modal
│   │   └── lib/
│   │       └── themeLabels.ts      # Theme code → label mapping
│   └── package.json
├── infra/
│   ├── auto_ingest_v2.sh           # Ingestion runner
│   └── docker-compose.yml
└── docs/
    ├── ARCHITECTURE.md
    └── HANDOFF-*.md
```

## Next Steps

### Immediate (Next Session)
1. Monitor theme drill-down performance with new context
2. Verify ingestion continues running smoothly
3. Consider adding article titles if available in GDELT data

### Short-term (This Week)
1. Improve theme label coverage (currently ~200 labels)
2. Add loading states for theme detail modal
3. Implement error handling for failed API calls

### Medium-term (This Month)
1. Integrate additional data sources (NewsAPI, RSS)
2. Add AI-generated theme summaries (using Claude/GPT)
3. Implement user preferences and saved searches
4. Add time-lapse animation for narrative evolution

## Known Issues

See docs/ISSUES.md for detailed bug tracking and enhancement proposals.
