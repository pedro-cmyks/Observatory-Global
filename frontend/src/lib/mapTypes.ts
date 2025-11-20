export interface CountryHotspot {
  country_code: string
  country_name: string
  latitude: number
  longitude: number
  topic_count: number
  intensity: number // 0-1 scale
  confidence: number
  top_topics: Array<{
    label: string
    count: number
  }>
  // Sentiment and theme fields (added in Priority 3)
  dominant_sentiment?: string // "very_negative" | "negative" | "neutral" | "positive" | "very_positive"
  avg_sentiment_score?: number // -100 to +100
  theme_distribution?: { [theme: string]: number } // e.g., {"Economic Inflation": 156, "Protests": 120}
  signals?: Array<{
    signal_id: string
    timestamp: string
    themes: string[]
    theme_labels: string[]
    theme_counts: { [theme: string]: number }
    sentiment_label: string
    sentiment_score: number
  }>
}

export interface Flow {
  from_country: string
  to_country: string
  heat: number // 0-1 scale
  similarity: number // 0-1 scale
  time_delta_minutes: number
  shared_topics: string[]
  from_coords: [number, number] // [lng, lat]
  to_coords: [number, number] // [lng, lat]
}

export interface FlowsResponse {
  time_window: string
  generated_at: string
  hotspots: CountryHotspot[]
  flows: Flow[]
}

export type TimeWindow = '1h' | '6h' | '12h' | '24h'

export type ViewMode = 'classic' | 'heatmap'

export interface HexCell {
  h3_index: string
  intensity: number // 0-1 scale
}

export interface HexmapMetadata {
  resolution: number
  k_ring: number
  hex_count: number
  countries_analyzed: string[]
  cache_hit: boolean
  time_window: string
}

export interface HexmapResponse {
  hexes: HexCell[]
  metadata: HexmapMetadata
  generated_at: string
}

export interface MapFilters {
  timeWindow: TimeWindow
  countries: string[]
  autoRefresh: boolean
  refreshInterval: number // milliseconds
}
