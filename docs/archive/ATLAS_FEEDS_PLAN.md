# ATLAS External Data Feeds Integration Plan

**Date**: 2026-03-29
**Phase**: 3 — Multi-Source Intelligence Layers
**Status**: Research complete, ready for implementation

---

## Table of Contents

1. [Data Source Evaluation](#1-data-source-evaluation)
2. [Technical Architecture](#2-technical-architecture)
3. [Implementation Sequence](#3-implementation-sequence)
4. [Risk Assessment](#4-risk-assessment)
5. [Effort Estimate](#5-effort-estimate)
6. [Competitive Context](#6-competitive-context)

---

## 1. Data Source Evaluation

### 1.1 Aircraft Tracking (ADS-B)

#### Source Comparison

| Source | Cost | Rate Limit | Real-Time? | Coverage | Auth | Difficulty |
|--------|------|------------|-----------|----------|------|------------|
| **OpenSky Network** | Free (non-commercial) | 400 credits/day (anon), 8,000/day (contributor) | ~5-10s delay | Global (terrestrial only, best in EU/US) | OAuth2 client credentials | 2/5 |
| ADS-B Exchange (RapidAPI) | $10/mo | 10,000 req/mo | ~1-2s delay | Global (unfiltered, includes military) | RapidAPI key | 2/5 |
| FlightAware AeroAPI | $100/mo + per-query | Per-plan | Real-time | Global (best US) | API key | 3/5 |
| AviationStack | Free tier: 100-500 req/mo | 1 req/60s (free) | No positions on free tier | Schedule data only | API key | N/A |

#### Recommendation: OpenSky Network (primary) + ADS-B Exchange (fallback)

**OpenSky Network** is the clear winner for Atlas:
- Free, no payment required
- All necessary fields: lat, lon, altitude, heading, velocity, callsign, origin_country
- Live test returned **11,382 aircraft** in a single global call
- Bounding-box queries reduce payload to ~75 aircraft per visible region
- OAuth2 registration increases daily budget from 400 to 8,000 credits

**API Endpoint Examples:**
```
GET https://opensky-network.org/api/states/all
GET https://opensky-network.org/api/states/all?lamin=45&lomin=5&lamax=48&lomax=10
GET https://opensky-network.org/api/states/all?icao24=3c6752
```

**Data Fields (17 per aircraft):**

| Field | Type | Example |
|-------|------|---------|
| icao24 | string | `"39de4c"` |
| callsign | string | `"TVF3589 "` |
| origin_country | string | `"France"` |
| longitude | float | `8.0833` |
| latitude | float | `46.0515` |
| baro_altitude | float (meters) | `11574.78` |
| on_ground | bool | `false` |
| velocity | float (m/s) | `228.43` |
| true_track | float (degrees) | `279.46` |
| vertical_rate | float (m/s) | `0` |
| geo_altitude | float (meters) | `11650.98` |
| squawk | string | `"1000"` |

**Refresh Rate**: 10-second resolution for anonymous users. Polling every 10-15 seconds with bounding-box filter is sustainable within the 400 credit/day budget (1 call per 30s = 2,880/day on registered account).

**Legal Constraints**: Free for non-commercial/research use. Must credit OpenSky as data source. Commercial use requires written permission. FAA Section 803 (2024 Reauthorization Act) restricts PII from ADS-B but does not apply to crowd-sourced networks.

**Difficulty**: 2/5 — Simple REST API, JSON response, no complex auth (OAuth2 is straightforward).

---

### 1.2 Maritime Vessel Tracking (AIS)

#### Source Comparison

| Source | Cost | Transport | Real-Time? | Coverage | Auth | Difficulty |
|--------|------|-----------|-----------|----------|------|------------|
| **AISStream.io** | Free tier available | WebSocket | Yes (seconds) | Global terrestrial | API key (free) | 2/5 |
| AISHub | Free (must contribute receiver) | REST | 1-2 min | Community stations | API key (membership) | 3/5 |
| Finnish Digitraffic | Free, no auth | REST + MQTT | Real-time | Finland only | None | 1/5 |
| Datalastic | Free: 100 calls/mo | REST | Minutes delay | Global | API key | 2/5 |
| VesselFinder | Paid only ($$$) | REST | ~1 min (sat-AIS) | Global + satellite | API key | 3/5 |
| MarineTraffic | Paid only ($$$) | REST | Seconds | Best global | API key + credits | 3/5 |

#### Recommendation: AISStream.io (primary) + Finnish Digitraffic (prototyping)

**AISStream.io** is the best option for Atlas:
- WebSocket-based real-time push (ideal for live map)
- Free tier with registration
- Supports geographic bounding box filtering
- Clean JSON format matching existing signal pipeline

**WebSocket Connection Example:**
```json
// Connect to: wss://stream.aisstream.io/v0/stream
// Send subscription:
{
  "APIKey": "your-api-key",
  "BoundingBoxes": [[[latMin, lonMin], [latMax, lonMax]]],
  "FilterMessageTypes": ["PositionReport"]
}

// Receive:
{
  "MessageType": "PositionReport",
  "MetaData": {
    "MMSI": 211234567,
    "ShipName": "EVER GIVEN",
    "latitude": 51.89,
    "longitude": 1.28,
    "time_utc": "2024-01-15T12:00:00Z"
  },
  "Message": {
    "PositionReport": {
      "Sog": 12.3,
      "Cog": 245.0,
      "TrueHeading": 243,
      "NavigationalStatus": 0
    }
  }
}
```

**Finnish Digitraffic** for initial prototyping (zero friction):
```
GET https://meri.digitraffic.fi/api/ais/v1/locations
MQTT: wss://meri.digitraffic.fi/mqtt
```

**Vessel Type Classification (built into AIS data):**

| Code | Category | Visual Treatment |
|------|----------|-----------------|
| 30 | Fishing | Green dot |
| 35 | Military | Red triangle (when visible) |
| 60-69 | Passenger/Cruise | Blue dot |
| 70-79 | Cargo/Container | Orange dot |
| 80-89 | Tanker (oil, chemical, LNG) | Yellow dot |
| 50-55 | Service (pilot, SAR, law enforcement) | White dot |

**Important caveat**: Military vessels frequently disable AIS or spoof data. Tankers involved in sanctions evasion also go dark or spoof positions. AIS was designed for safety, not security — no authentication or encryption.

**Difficulty**: 2/5 — WebSocket connection with JSON messages. Slightly more complex than REST polling due to connection management and reconnection logic.

---

### 1.3 Financial Market Data

#### Source Comparison

| Source | Cost | Rate Limit | Real-Time? | Indices | Commodities | Forex | Crypto | WebSocket |
|--------|------|------------|-----------|---------|-------------|-------|--------|-----------|
| **yfinance** | Free | ~950 tickers before 429 | Near real-time* | Yes (all major) | Yes (futures) | Yes | Yes | No |
| **Finnhub** | Free tier | 60 calls/min | Yes (US stocks) | Limited free | No free | Yes | Yes | Yes (50 symbols) |
| **Alpha Vantage** | Free tier | 25 calls/day | 15-min delayed | Yes | Yes (dedicated) | Yes | Yes | No |
| Twelve Data | Free tier | 8 calls/min, 800/day | Real-time (US) | No (paid) | No (paid) | Yes | Yes | Yes (8 symbols) |
| Polygon.io | Free tier | 5 calls/min | End-of-day only | No | No | No | No | No (paid) |
| Marketstack | Free tier | 100 calls/month | End-of-day only | No | No | No | No | No |
| **Frankfurter** | Free, no key | No limit | Daily (ECB) | No | No | Yes (150+ currencies) | No | No |

*yfinance is unofficial and can be blocked unpredictably.

#### Recommendation: Multi-API Strategy

No single free API covers all asset classes. Use a combination:

| Layer | Primary Source | Frequency | What It Covers |
|-------|---------------|-----------|----------------|
| Indices snapshot | yfinance | Every 15 min | S&P 500, DAX, Nikkei, FTSE, Hang Seng, etc. |
| Real-time stream | Finnhub WebSocket | Continuous | Up to 50 US stocks + crypto prices |
| Forex baselines | Frankfurter API | Hourly | 150+ currency pairs from ECB |
| Commodities | Alpha Vantage | Daily | WTI, Brent, gold, natural gas |
| Forex supplement | Finnhub REST | Every 5 min | Real-time major forex pairs |

**Key Instruments for Atlas:**

| Instrument | Ticker (yfinance) | Geographic Anchor |
|-----------|-------------------|-------------------|
| S&P 500 | `^GSPC` | United States |
| DAX | `^GDAXI` | Germany |
| FTSE 100 | `^FTSE` | United Kingdom |
| Nikkei 225 | `^N225` | Japan |
| Hang Seng | `^HSI` | Hong Kong |
| CAC 40 | `^FCHI` | France |
| Euro Stoxx 50 | `^STOXX50E` | EU |
| Crude Oil WTI | `CL=F` | United States |
| Brent Crude | `BZ=F` | North Sea / UK |
| Gold | `GC=F` | London / Zurich |
| Natural Gas | `NG=F` | United States |
| EUR/USD | `EURUSD=X` | EU / US |
| GBP/USD | `GBPUSD=X` | UK / US |
| USD/JPY | `USDJPY=X` | US / Japan |
| USD/CNY | `USDCNY=X` | US / China |
| BTC/USD | `BTC-USD` | Global |

**Finnhub WebSocket Example:**
```
wss://ws.finnhub.io?token=YOUR_KEY
// Subscribe: {"type":"subscribe","symbol":"AAPL"}
// Receive: {"data":[{"p":150.25,"s":"AAPL","t":1672531200000,"v":100}],"type":"trade"}
```

**Display Approach**: Markets should NOT be plotted as dots on the map. Instead:
- **Country polygons**: Choropleth shading by daily index performance (green = up, red = down)
- **Dedicated panel**: Slide-in market panel or bottom bar showing key indices/commodities
- **Correlation layer**: When a country is focused, show its primary index alongside narrative signals

**Difficulty**: 3/5 — Multiple APIs to orchestrate, unreliable free tiers (especially yfinance), backend caching strategy needed to stay within rate limits.

---

## 2. Technical Architecture

### 2.1 Backend: FastAPI Proxy Endpoints

Each external data source gets a FastAPI proxy endpoint that hides API keys, adds caching, and normalizes the response format.

```
/api/v2/feeds/aircraft    → OpenSky Network proxy
/api/v2/feeds/vessels     → AISStream.io proxy (WebSocket relay)
/api/v2/feeds/markets     → yfinance + Finnhub + Alpha Vantage aggregator
```

#### Aircraft Proxy

```python
# GET /api/v2/feeds/aircraft?bbox=minLat,minLon,maxLat,maxLon
@app.get("/api/v2/feeds/aircraft")
async def get_aircraft(bbox: str = Query(None)):
    cache_key = f"aircraft:{bbox or 'global'}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    params = {}
    if bbox:
        parts = bbox.split(",")
        params = {"lamin": parts[0], "lomin": parts[1], "lamax": parts[2], "lomax": parts[3]}

    resp = await http_client.get(
        "https://opensky-network.org/api/states/all",
        params=params,
        headers={"Authorization": f"Bearer {opensky_token}"}
    )
    data = transform_opensky(resp.json())
    await redis.setex(cache_key, 10, json.dumps(data))  # 10s TTL
    return data
```

#### Vessel WebSocket Relay

```python
# WebSocket /api/v2/feeds/vessels/ws
# Backend maintains a single connection to AISStream.io
# and fans out to all connected frontend clients
@app.websocket("/api/v2/feeds/vessels/ws")
async def vessel_ws(websocket: WebSocket):
    await websocket.accept()
    # Subscribe client to the shared AIS stream
    await vessel_broadcaster.subscribe(websocket)
```

#### Markets Aggregator

```python
# GET /api/v2/feeds/markets
# Aggregates from multiple sources, cached 30s
@app.get("/api/v2/feeds/markets")
async def get_markets():
    cached = await redis.get("markets:snapshot")
    if cached:
        return json.loads(cached)

    # Parallel fetch from multiple sources
    indices = await fetch_yfinance_indices()      # ~16 instruments
    forex = await fetch_frankfurter_forex()        # major pairs
    commodities = await fetch_alphavantage_commodities()  # daily

    snapshot = {
        "timestamp": datetime.utcnow().isoformat(),
        "indices": indices,
        "forex": forex,
        "commodities": commodities,
    }
    await redis.setex("markets:snapshot", 30, json.dumps(snapshot))
    return snapshot
```

#### Caching Strategy

| Feed | Redis TTL | Rationale |
|------|-----------|-----------|
| Aircraft positions | 10s | Fast-moving; stale data is misleading |
| Vessel positions | 60s | Slower movement; longer freshness window |
| Market snapshot | 30s | Balances freshness with API rate limits |
| Forex rates (Frankfurter) | 3600s (1h) | Daily ECB rates, no urgency |
| Commodity prices (Alpha Vantage) | 86400s (24h) | Daily data, one fetch per day |
| Static reference (airports, vessel registry) | 86400s | Changes rarely |

#### Rate Limit Handling

```python
# Exponential backoff with jitter for all external APIs
async def fetch_with_retry(url, params, max_retries=3):
    for attempt in range(max_retries):
        resp = await http_client.get(url, params=params)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 2 ** attempt))
            await asyncio.sleep(retry_after + random.uniform(0, 1))
            continue
        resp.raise_for_status()
        return resp.json()
    raise ExternalAPIError(f"Rate limited after {max_retries} retries")
```

### 2.2 Frontend: New Deck.gl Layers

#### Aircraft Layer (IconLayer)

```tsx
import { IconLayer } from '@deck.gl/layers';

const AIRCRAFT_ICON_MAPPING = {
  airborne: { x: 0, y: 0, width: 64, height: 64, mask: true },
  grounded: { x: 64, y: 0, width: 64, height: 64, mask: true },
};

// Color by altitude band
const getAltitudeColor = (alt: number): [number, number, number] => {
  if (alt < 3000) return [0, 200, 255];     // cyan — low
  if (alt < 8000) return [100, 180, 255];    // light blue — mid
  if (alt < 12000) return [200, 160, 60];    // gold — high
  return [255, 100, 50];                      // orange — very high
};

new IconLayer({
  id: 'aircraft-layer',
  data: aircraftPositions,
  iconAtlas: '/sprites/aircraft-icons.png',
  iconMapping: AIRCRAFT_ICON_MAPPING,
  getIcon: d => d.on_ground ? 'grounded' : 'airborne',
  getPosition: d => [d.longitude, d.latitude],
  getSize: 20,
  getAngle: d => 360 - d.true_track,  // rotate by heading
  getColor: d => getAltitudeColor(d.baro_altitude),
  pickable: true,
  visible: layerVisibility.aircraft,
});
```

#### Vessel Layer (ScatterplotLayer)

```tsx
import { ScatterplotLayer } from '@deck.gl/layers';

// Color by vessel type
const getVesselColor = (shipType: number): [number, number, number] => {
  if (shipType === 30) return [40, 180, 80];           // fishing — green
  if (shipType === 35) return [220, 50, 50];           // military — red
  if (shipType >= 60 && shipType < 70) return [60, 130, 240]; // passenger — blue
  if (shipType >= 70 && shipType < 80) return [220, 140, 40]; // cargo — orange
  if (shipType >= 80 && shipType < 90) return [240, 200, 40]; // tanker — yellow
  return [150, 150, 150];                               // other — gray
};

new ScatterplotLayer({
  id: 'vessel-layer',
  data: vesselPositions,
  getPosition: d => [d.longitude, d.latitude],
  getRadius: d => d.sog > 1 ? 800 : 400,  // larger dot if moving
  getFillColor: d => getVesselColor(d.ship_type),
  radiusMinPixels: 2,
  radiusMaxPixels: 8,
  pickable: true,
  visible: layerVisibility.vessels,
});
```

#### Markets — Panel Approach (NOT on the map)

Financial data does not map naturally to point locations. Instead of markers on the globe:

**Option A: Market Status Bar** (recommended)
A slim horizontal bar below the Globe panel showing key indices as colored chips:

```
S&P +0.4%  DAX -0.2%  NIKKEI +1.1%  FTSE +0.3%  |  OIL $72.4  GOLD $2,340  |  EUR 1.082  GBP 1.264
```

Each chip colored green/red by daily change. Clicking a chip could focus the map on the corresponding country.

**Option B: Market Choropleth**
Country polygons shaded by primary index performance. Requires a GeoJSON country boundaries layer on the map — adds complexity but provides powerful geographic context.

**Option C: Slide-in Market Panel**
A dedicated panel (like CountryBrief) that slides in when a "Markets" toggle is activated, showing detailed market data organized by region.

**Recommendation**: Start with Option A (status bar) — lowest effort, highest information density, no map layer complexity. Add Option B as a future enhancement.

### 2.3 Layer Toggle System

Add toggles to the Globe panel header, alongside the existing GLOW/FLOW/NODES toggles:

```
GLOW  FLOW  NODES  |  FLIGHTS  SHIPS  MARKETS
```

Implementation uses the Deck.gl `visible` prop pattern:

```tsx
const [feedToggles, setFeedToggles] = useState({
  flights: false,   // off by default (performance)
  ships: false,     // off by default
  markets: true,    // status bar always visible
});

// In the layers array:
layers={[
  ...existingLayers,
  aircraftLayer,   // visible: feedToggles.flights
  vesselLayer,     // visible: feedToggles.ships
]}
```

**Important**: Use `visible: false` rather than conditional inclusion. This keeps GPU buffers alive for instant toggle response.

### 2.4 Transport Architecture

```
                    +-----------------------+
                    |   External APIs       |
                    |                       |
                    |  OpenSky (REST/10s)   |
                    |  AISStream (WebSocket)|
                    |  yfinance (REST/15m)  |
                    |  Finnhub (WS/realtime)|
                    |  Frankfurter (REST/1h)|
                    |  Alpha Vantage (daily)|
                    +-----------+-----------+
                                |
                    +-----------v-----------+
                    |   FastAPI Backend     |
                    |                       |
                    |  Proxy + Cache (Redis)|
                    |  Rate limit handling  |
                    |  Data normalization   |
                    |  WebSocket relay      |
                    +-----------+-----------+
                                |
                    Single multiplexed WebSocket
                    or SSE + REST hybrid
                                |
                    +-----------v-----------+
                    |   React Frontend      |
                    |                       |
                    |  Web Worker (parsing)  |
                    |  Deck.gl layers       |
                    |  Layer toggle UI      |
                    |  Market status bar    |
                    +-----------------------+
```

**Transport recommendation**: Use **REST polling** for aircraft (every 10-15s) and markets (every 30s), and a **WebSocket relay** for vessel data (AISStream is already WebSocket-native). This avoids the complexity of a full multiplexed WebSocket while still providing push-based updates for the highest-volume data stream.

---

## 3. Implementation Sequence

### Phase 3A: Aircraft Layer (highest visual impact, lowest effort)

**Why first**: Planes moving across the globe is immediately impressive. OpenSky is the simplest API (no auth needed for anonymous, straightforward REST). Users understand aircraft intuitively.

| Step | Description | Deliverable |
|------|-------------|-------------|
| 1 | FastAPI proxy endpoint `/api/v2/feeds/aircraft` | Backend endpoint with Redis caching (10s TTL) |
| 2 | Aircraft icon sprite sheet | 64x64 plane silhouette PNG (airborne + grounded) |
| 3 | Deck.gl IconLayer for aircraft | New layer in App.tsx with altitude coloring + heading rotation |
| 4 | Toggle button in Globe header | FLIGHTS toggle alongside GLOW/FLOW/NODES |
| 5 | Tooltip on hover | Callsign, origin country, altitude, speed |

**Dependencies**: None beyond existing stack.

### Phase 3B: Maritime Layer (second highest impact)

**Why second**: Ships moving through shipping lanes and chokepoints (Suez, Strait of Hormuz, Malacca) tells a powerful geopolitical story. Vessel type classification adds analytical depth.

| Step | Description | Deliverable |
|------|-------------|-------------|
| 1 | AISStream.io account + API key | Free registration |
| 2 | Backend WebSocket relay service | Python service maintaining AISStream connection, fanning out to clients |
| 3 | FastAPI WebSocket endpoint `/api/v2/feeds/vessels/ws` | Client-facing WebSocket with viewport-based filtering |
| 4 | Deck.gl ScatterplotLayer for vessels | Color-coded by vessel type, size by speed |
| 5 | Toggle button | SHIPS toggle in Globe header |
| 6 | Tooltip on hover | Vessel name, type, speed, destination, flag |

**Dependencies**: None beyond existing stack. WebSocket relay is new infrastructure.

### Phase 3C: Financial Markets (most analytical value, medium effort)

**Why third**: Markets are the most complex integration (multiple APIs, panel UI rather than map layer). Best done after the map layers are stable.

| Step | Description | Deliverable |
|------|-------------|-------------|
| 1 | Backend market aggregator endpoint | `/api/v2/feeds/markets` combining yfinance + Frankfurter + Alpha Vantage |
| 2 | Market status bar component | Slim bar below Globe showing index/commodity/forex chips |
| 3 | Polling logic (15-min cycle) | Frontend polls `/api/v2/feeds/markets` |
| 4 | Toggle / expand interaction | Click chip to focus map on country; expand for detail |

**Dependencies**: Phase 3A/3B not required, but the toggle UI pattern established there carries forward.

### Phase 3D: Cross-Layer Intelligence (future)

Once all feeds are running:
- Correlate narrative spikes with vessel traffic anomalies (e.g., tanker re-routing during sanctions)
- Correlate market movements with narrative sentiment (e.g., oil price drop after peace talks narrative)
- Anomaly detection across feeds (unusual aircraft activity + narrative spike = event)

---

## 4. Risk Assessment

### Performance Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Too many moving dots overwhelm GPU | Medium | Viewport-based filtering (only render visible area); ScatterplotLayer handles 1M+ items at 60 FPS; start with `visible: false` by default |
| Multiple polling intervals compete for main thread | Medium | Web Worker for data parsing; stagger update cycles (aircraft at t+0, vessels at t+15s, markets at t+7s) |
| Browser connection limits (6 per domain under HTTP/1.1) | Low | Use single WebSocket for vessels; REST for aircraft/markets shares domain but is infrequent |
| Mobile performance degradation | Medium | Reduce polling frequency on mobile; limit visible items; disable aircraft/vessel layers by default on mobile |

### API Reliability Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| OpenSky rate limit exceeded (429) | Medium | Exponential backoff with jitter; bounding-box queries to reduce calls; registered account (8,000 credits/day) |
| yfinance blocked by Yahoo | High | yfinance is unofficial and Yahoo aggressively blocks scrapers (Nov 2024 tightening); fallback to Finnhub REST for US stocks; 2s delay between requests |
| AISStream.io WebSocket disconnects | Medium | Auto-reconnection with exponential backoff; fallback to Finnish Digitraffic for testing |
| Alpha Vantage 25 calls/day exceeded | Low | Batch all commodity/macro queries in a single daily cycle; cache for 24h |
| Finnhub WebSocket 50-symbol limit | Low | Sufficient for Atlas needs; prioritize key instruments |

### Data Accuracy Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| AIS spoofing (false vessel positions) | Medium | Validate positions: reject coords at (0,0), speed > 50 knots, positions on land, stale timestamps > 1h; flag vessels with suspicious track jumps |
| Aircraft position gaps (no satellite coverage over oceans) | Low | Accept gaps; show data staleness indicator; OpenSky terrestrial network has gaps over open ocean |
| Market data delays (yfinance reports stale prices) | Medium | Display data timestamp alongside values; cross-validate with Finnhub for US instruments |
| GDELT military tagging mixed with AIS military classification | Low | Keep data sources visually distinct; don't auto-correlate without user action |

### Legal/Terms Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| OpenSky non-commercial clause | Medium | Atlas is currently non-commercial/research. If monetized, obtain written permission from OpenSky |
| Aircraft privacy (FAA Section 803) | Low | Does not apply to crowd-sourced networks; no PII displayed (no owner names, just callsigns) |
| yfinance ToS violation | Medium | Yahoo's ToS technically prohibits scraping; use backend proxy to reduce request fingerprint; maintain fallback sources |

---

## 5. Effort Estimate

### Phase 3A: Aircraft Layer

| Component | Effort | Notes |
|-----------|--------|-------|
| Backend: FastAPI proxy + Redis cache | 2h | Simple REST proxy with caching |
| Backend: OpenSky OAuth2 token management | 1h | Token refresh every 30min |
| Frontend: Aircraft IconLayer | 2h | Layer + altitude coloring + heading rotation |
| Frontend: Icon sprite sheet | 0.5h | Single plane silhouette, 2 states |
| Frontend: Toggle button | 0.5h | Extend existing toggle pattern |
| Frontend: Tooltip | 1h | Hover card with aircraft details |
| Testing + polish | 1h | Edge cases, loading states, error states |
| **Total** | **8h** | **~2 sessions** |

### Phase 3B: Maritime Layer

| Component | Effort | Notes |
|-----------|--------|-------|
| Backend: AISStream WebSocket client | 3h | Persistent connection, reconnection logic |
| Backend: WebSocket relay endpoint | 2h | Fan-out to frontend clients, viewport filtering |
| Backend: AIS data validation | 1h | Position validation, stale data filtering |
| Frontend: Vessel ScatterplotLayer | 2h | Type-based coloring, speed-based sizing |
| Frontend: Toggle button | 0.5h | Extend toggle pattern |
| Frontend: Tooltip | 1h | Vessel name, type, speed, destination |
| Testing + polish | 1.5h | WebSocket reconnection, edge cases |
| **Total** | **11h** | **~3 sessions** |

### Phase 3C: Financial Markets

| Component | Effort | Notes |
|-----------|--------|-------|
| Backend: yfinance integration | 2h | Batch fetch + error handling for blocks |
| Backend: Finnhub WebSocket client | 2h | Subscribe to 50 symbols, relay prices |
| Backend: Frankfurter + Alpha Vantage | 1h | Simple REST clients, long TTL cache |
| Backend: Aggregator endpoint | 2h | Combine all sources into unified snapshot |
| Frontend: Market status bar component | 3h | Colored chips, click-to-focus interaction |
| Frontend: Polling logic | 1h | 15-min refresh cycle |
| Testing + polish | 2h | Multiple API failure modes, stale data display |
| **Total** | **13h** | **~3-4 sessions** |

### Summary

| Phase | Hours | Sessions | Visual Impact | Effort |
|-------|-------|----------|---------------|--------|
| 3A: Aircraft | 8h | ~2 | Very High | Low |
| 3B: Maritime | 11h | ~3 | High | Medium |
| 3C: Markets | 13h | ~3-4 | Medium | Medium-High |
| **Total** | **32h** | **~8-9 sessions** | | |

---

## 6. Competitive Context

### What Already Exists

| Product | Type | Data Layers | Cost | Open Source |
|---------|------|-------------|------|------------|
| **World Monitor** | Multi-layer global dashboard | 45+ layers (conflicts, flights, ships, bases, infrastructure) | Free | Yes |
| **ShadowBroker** | OSINT dashboard | ADS-B, AIS, satellites, GDELT, earthquakes, GPS jamming, CCTV | Free | Yes |
| **FlightRadar24** | Flight tracker | Aircraft positions (30K+ ADS-B receivers) | Freemium | No |
| **MarineTraffic** | Vessel tracker | AIS positions (market leader) | Freemium | No |
| **Recorded Future** | Threat intelligence | Social media, news, dark web | $50K+/year | No |
| **Palantir** | Intelligence platform | Custom data fusion | $1M+/year | No |
| **Dataminr** | Event detection | 1M+ sources, multi-modal AI | Enterprise | No |
| **ACLED** | Conflict data | Political violence, protests, 200+ countries | Free (research) | Data only |

### Where Atlas Fits — The Unoccupied Niche

Atlas is not trying to be FlightRadar24 or MarineTraffic. Adding aircraft and vessel layers serves a different purpose: **contextualizing narrative intelligence with physical-world signals**.

What no competitor does:

1. **Narrative propagation on a map** — No one visualizes HOW a story mutates as it crosses borders
2. **Cross-source narrative normalization** — GDELT + Google Trends + Wikipedia unified into a single signal
3. **Sentiment trajectory by geography** — Temporal-geographic sentiment flow is unique to Atlas
4. **Framing mutation detection** — "protest" vs "riot" vs "uprising" across media ecosystems
5. **Democratized narrative intelligence** — Enterprise platforms cost $50K-$1M+. Atlas is free.

Adding ADS-B/AIS/markets data transforms Atlas from a "narrative dashboard" into a **narrative + physical reality correlation engine**:
- Tanker re-routing visible alongside sanctions narrative spikes
- Military aircraft activity correlated with conflict narrative acceleration
- Market reactions visible alongside narrative sentiment shifts

The closest open-source analog is **World Monitor** (45+ layers, 2M+ users), but it aggregates raw feeds without any narrative analysis. Atlas's GDELT-powered intelligence layer is the differentiator.

**The "Windy.com for narratives" metaphor**: earth.nullschool.net beautifully shows wind currents. No equivalent exists for information currents. With physical data layers added, Atlas becomes the first open dashboard where you can see both the narrative weather and the physical reality on the same globe.

---

## Appendix A: API Documentation Links

| Source | Documentation |
|--------|--------------|
| OpenSky Network REST API | https://openskynetwork.github.io/opensky-api/rest.html |
| OpenSky Network Terms | https://opensky-network.org/about/terms-of-use |
| AISStream.io Documentation | https://aisstream.io/documentation |
| Finnish Digitraffic Marine | https://meri.digitraffic.fi/ |
| yfinance (Python) | https://github.com/ranaroussi/yfinance |
| Finnhub API | https://finnhub.io/docs/api |
| Alpha Vantage | https://www.alphavantage.co/documentation/ |
| Frankfurter API | https://frankfurter.dev/ |
| Deck.gl IconLayer | https://deck.gl/docs/api-reference/layers/icon-layer |
| Deck.gl ScatterplotLayer | https://deck.gl/docs/api-reference/layers/scatterplot-layer |
| Deck.gl Performance Guide | https://deck.gl/docs/developer-guide/performance |

## Appendix B: Existing Open-Source Implementations

| Project | Stack | Data Source | URL |
|---------|-------|-------------|-----|
| Aeris (3D flight radar) | React + Deck.gl 9 | OpenSky / adsb.lol | github.com/kewonit/aeris |
| Flight Spotter | React + TypeScript + MapBox | OpenSky | github.com/janhartmann/flight-spotter |
| OpenSkyFlightTracker | ASP.NET + MapLibre GL JS | OpenSky | github.com/bytefish/OpenSkyFlightTracker |
| FlightAirMap | PHP + Leaflet | Multiple ADS-B sources | github.com/Ysurac/FlightAirMap |
| Globe.gl | Three.js | Custom data | github.com/vasturiano/globe.gl |
| Kepler.gl | React + Deck.gl + MapLibre | Custom data | github.com/keplergl/kepler.gl |
