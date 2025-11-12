import { create } from 'zustand'
import { FlowsResponse, TimeWindow, CountryHotspot } from '../lib/mapTypes'
import { mockFlowsData } from '../lib/mockMapData'

interface MapState {
  // Data
  flowsData: FlowsResponse | null
  loading: boolean
  error: string | null
  lastUpdate: Date | null

  // Filters
  timeWindow: TimeWindow
  selectedCountries: string[]
  autoRefresh: boolean
  refreshInterval: number

  // UI State
  selectedHotspot: CountryHotspot | null
  hoveredFlow: string | null // "FROM_TO" format

  // Actions
  setTimeWindow: (window: TimeWindow) => void
  setSelectedCountries: (countries: string[]) => void
  toggleCountry: (country: string) => void
  setAutoRefresh: (enabled: boolean) => void
  setRefreshInterval: (interval: number) => void
  setSelectedHotspot: (hotspot: CountryHotspot | null) => void
  setHoveredFlow: (flow: string | null) => void
  fetchFlowsData: () => Promise<void>
  clearError: () => void
}

export const useMapStore = create<MapState>((set, get) => ({
  // Initial state
  flowsData: null,
  loading: false,
  error: null,
  lastUpdate: null,

  timeWindow: '24h',
  selectedCountries: [],
  autoRefresh: true,
  refreshInterval: 5 * 60 * 1000, // 5 minutes

  selectedHotspot: null,
  hoveredFlow: null,

  // Actions
  setTimeWindow: (window) => {
    set({ timeWindow: window })
    get().fetchFlowsData()
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
      // TODO: Replace with real API call when backend is ready
      // const response = await api.get('/v1/flows', {
      //   params: { window: get().timeWindow }
      // })
      // const data = response.data

      // Simulate API delay
      await new Promise((resolve) => setTimeout(resolve, 500))

      // Use mock data for now
      const data = mockFlowsData

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

  clearError: () => {
    set({ error: null })
  },
}))
