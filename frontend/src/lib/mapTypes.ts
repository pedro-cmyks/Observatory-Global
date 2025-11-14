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

export interface MapFilters {
  timeWindow: TimeWindow
  countries: string[]
  autoRefresh: boolean
  refreshInterval: number // milliseconds
}

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

export type ViewMode = 'classic' | 'heatmap'
