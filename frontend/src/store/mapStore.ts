import { create } from 'zustand'
import { FlowsResponse, HexmapResponse, TimeWindow, ViewMode, CountryHotspot } from '../lib/mapTypes'
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

  // UI State
  viewMode: ViewMode
  selectedHotspot: CountryHotspot | null
  hoveredFlow: string | null // "FROM_TO" format

  // Actions
  setViewMode: (mode: ViewMode) => void
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
  selectedHotspot: null,
  hoveredFlow: null,

  // Actions
  setViewMode: (mode) => {
    set({ viewMode: mode })
    // Fetch appropriate data for the new mode
    if (mode === 'classic') {
      get().fetchFlowsData()
    } else {
      get().fetchHexmapData()
    }
  },

  setTimeWindow: (window) => {
    set({ timeWindow: window })
    const { viewMode } = get()
    if (viewMode === 'classic') {
      get().fetchFlowsData()
    } else {
      get().fetchHexmapData()
    }
  },

  setSelectedCountries: (countries) => {
    set({ selectedCountries: countries })
    // Refresh data when country selection changes
    const { viewMode } = get()
    if (viewMode === 'classic') {
      get().fetchFlowsData()
    } else {
      get().fetchHexmapData()
    }
  },

  toggleCountry: (country) => {
    const { selectedCountries } = get()
    const newSelection = selectedCountries.includes(country)
      ? selectedCountries.filter((c) => c !== country)
      : [...selectedCountries, country]
    set({ selectedCountries: newSelection })
    // Refresh data when country selection changes
    const { viewMode } = get()
    if (viewMode === 'classic') {
      get().fetchFlowsData()
    } else {
      get().fetchHexmapData()
    }
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
      const { selectedCountries, timeWindow } = get()

      // Build query parameters
      const params: any = {
        time_window: timeWindow,
        threshold: 0.5
      }

      // Only include countries parameter if specific countries are selected
      if (selectedCountries.length > 0) {
        params.countries = selectedCountries.join(',')
      }

      // Fetch real data from backend API
      const response = await api.get('/v1/flows', { params })
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
      const { selectedCountries, timeWindow } = get()

      // Build query parameters
      const params: any = {
        time_window: timeWindow,
        zoom: 2, // Default zoom level
        k_ring: 2 // Default smoothing
      }

      // Only include countries parameter if specific countries are selected
      if (selectedCountries.length > 0) {
        params.countries = selectedCountries.join(',')
      }

      // Fetch hexmap data from backend API
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
