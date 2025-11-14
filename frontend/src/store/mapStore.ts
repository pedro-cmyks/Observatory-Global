import { create } from 'zustand'
import { FlowsResponse, TimeWindow, CountryHotspot, HexmapResponse, ViewMode } from '../lib/mapTypes'
import api from '../lib/api'

interface MapState {
  // Data
  flowsData: FlowsResponse | null
  hexmapData: HexmapResponse | null
  loading: boolean
  error: string | null
  lastUpdate: Date | null

  // Filters
  timeWindow: TimeWindow
  selectedCountries: string[]
  autoRefresh: boolean
  refreshInterval: number

  // View Mode
  viewMode: ViewMode
  mapZoom: number

  // UI State
  selectedHotspot: CountryHotspot | null
  hoveredFlow: string | null // "FROM_TO" format

  // Actions
  setViewMode: (mode: ViewMode) => void
  setMapZoom: (zoom: number) => void
  setTimeWindow: (window: TimeWindow) => void
  setSelectedCountries: (countries: string[]) => void
  toggleCountry: (country: string) => void
  setAutoRefresh: (enabled: boolean) => void
  setRefreshInterval: (interval: number) => void
  setSelectedHotspot: (hotspot: CountryHotspot | null) => void
  setHoveredFlow: (flow: string | null) => void
  fetchFlowsData: () => Promise<void>
  fetchHexmapData: () => Promise<void>
  clearError: () => void
}

export const useMapStore = create<MapState>((set, get) => ({
  // Initial state
  flowsData: null,
  hexmapData: null,
  loading: false,
  error: null,
  lastUpdate: null,

  timeWindow: '24h',
  selectedCountries: [],
  autoRefresh: true,
  refreshInterval: 5 * 60 * 1000, // 5 minutes

  viewMode: 'classic',
  mapZoom: 2,

  selectedHotspot: null,
  hoveredFlow: null,

  // Actions
  setViewMode: (mode) => {
    set({ viewMode: mode })
    // Fetch appropriate data for the mode
    if (mode === 'heatmap') {
      get().fetchHexmapData()
    } else {
      get().fetchFlowsData()
    }
  },

  setMapZoom: (zoom) => {
    set({ mapZoom: zoom })
    // Refetch hexmap with new resolution if in heatmap mode
    if (get().viewMode === 'heatmap') {
      get().fetchHexmapData()
    }
  },

  setTimeWindow: (window) => {
    set({ timeWindow: window })
    if (get().viewMode === 'heatmap') {
      get().fetchHexmapData()
    } else {
      get().fetchFlowsData()
    }
  },

  setSelectedCountries: (countries) => {
    set({ selectedCountries: countries })
  },

  toggleCountry: (country) => {
    const { selectedCountries } = get()
    const newSelection = selectedCountries.includes(country)
      ? selectedCountries.filter((c) => c !== country)
      : [...selectedCountries, country]
    set({ selectedCountries: newSelection })
  },

  setAutoRefresh: (enabled) => {
    set({ autoRefresh: enabled })
  },

  setRefreshInterval: (interval) => {
    set({ refreshInterval: interval })
  },

  setSelectedHotspot: (hotspot) => {
    set({ selectedHotspot: hotspot })
  },

  setHoveredFlow: (flow) => {
    set({ hoveredFlow: flow })
  },

  fetchFlowsData: async () => {
    set({ loading: true, error: null })

    try {
      // Fetch real data from backend API
      const response = await api.get('/v1/flows', {
        params: {
          time_window: get().timeWindow,
          threshold: 0.5
        }
      })
      const data = response.data

      set({
        flowsData: data,
        loading: false,
        lastUpdate: new Date(),
      })
    } catch (err: any) {
      console.error('Error fetching flows data:', err)
      set({
        error: err.message || 'Failed to fetch map data',
        loading: false,
      })
    }
  },

  fetchHexmapData: async () => {
    set({ loading: true, error: null })

    try {
      const { mapZoom, timeWindow, selectedCountries } = get()

      // Fetch hexmap data from backend API
      const params: any = {
        zoom: mapZoom,
        k_ring: 2, // Use k=2 for blob effect
        time_window: timeWindow,
        cache: true,
      }

      // Add country filter if specific countries selected
      if (selectedCountries.length > 0) {
        params.countries = selectedCountries.join(',')
      }

      const response = await api.get('/v1/hexmap', { params })
      const data = response.data

      set({
        hexmapData: data,
        loading: false,
        lastUpdate: new Date(),
      })
    } catch (err: any) {
      console.error('Error fetching hexmap data:', err)
      set({
        error: err.message || 'Failed to fetch hexmap data',
        loading: false,
      })
    }
  },

  clearError: () => {
    set({ error: null })
  },
}))
