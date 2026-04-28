# ⚠️ DEPRECATED - DO NOT USE THIS FRONTEND ⚠️

This `./frontend` folder is **LEGACY** and should NOT be used.

## Why this is deprecated:
1. **Requires Mapbox API tokens** (paid service with usage limits)
2. **Outdated UI** - does not include latest narrative intelligence features
3. **No longer maintained** - all development happens in `./frontend-v2`

## What to use instead:
Use `./frontend-v2` which:
- Uses **MapLibre + Deck.gl** (free, open-source map stack)
- Contains the latest Observatory Global UI with drill-down, indicators, and executive briefs
- Is actively maintained and documented

## To run the correct frontend:
```bash
cd frontend-v2
npm install
npm run dev
```

Then open http://localhost:3000

---

**If you accidentally started this legacy frontend, stop it and switch to frontend-v2.**
