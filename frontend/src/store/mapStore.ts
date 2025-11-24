import { create } from 'zustand'
import { FlowsResponse, TimeWindow, ViewMode, CountryHotspot } from '../lib/mapTypes'
import api from '../lib/api'

interface MapState {
  // Data
  flowsData: FlowsResponse | null
  lastUpdate: Date | null
  loading: boolean
  error: string | null

  // View state
  viewMode: ViewMode

  // Layer visibility toggles
  layersVisible: {
    heatmap: boolean
    flows: boolean
    markers: boolean
  }

  // Filters
  timeWindow: TimeWindow
  selectedCountries: string[]
  selectedHotspot: CountryHotspot | null

  // Auto-refresh
  autoRefresh: boolean
  refreshInterval: number

  // Actions
  fetchFlowsData: () => Promise<void>
  setViewMode: (mode: ViewMode) => void
  setTimeWindow: (timeWindow: TimeWindow) => void
  setSelectedCountries: (countries: string[]) => void
  toggleCountry: (countryCode: string) => void
  setSelectedHotspot: (hotspot: CountryHotspot | null) => void
  setAutoRefresh: (enabled: boolean) => void
  setRefreshInterval: (interval: number) => void
  toggleLayer: (layer: 'heatmap' | 'flows' | 'markers') => void
  clearError: () => void
}

export const useMapStore = create<MapState>((set, get) => ({
  // Initial State
  flowsData: null,
  lastUpdate: null,
  loading: false,
  error: null,
  viewMode: 'classic',

  // Layer visibility - all enabled by default for unified radar view
  layersVisible: {
    heatmap: true,
    flows: true,
    markers: true,
  },

  // Initial Filters
  timeWindow: '24h',
  selectedCountries: [],
  selectedHotspot: null,

  // Auto-refresh
  autoRefresh: true,
  refreshInterval: 5 * 60 * 1000, // 5 minutes

  // Fetch flows data from backend
  fetchFlowsData: async () => {
    const { timeWindow } = get()
    set({ loading: true, error: null })

    try {
      const params = new URLSearchParams({
        time_window: timeWindow,
      })

      const response = await api.get<FlowsResponse>(`/v1/flows?${params}`)

      set({
        flowsData: response.data,
        lastUpdate: new Date(),
        loading: false,
      })
    } catch (error: any) {
      console.error('[mapStore] Failed to fetch flows data:', error)
      console.warn('[mapStore] Falling back to mock data for development')

      // Import mock data dynamically
      const { generateMockFlowsData } = await import('../lib/mockData')
      const mockData = generateMockFlowsData()

      set({
        flowsData: mockData,
        lastUpdate: new Date(),
        loading: false,
        error: 'Using mock data - backend unavailable',
      })
    }
  },

  setViewMode: (mode) => {
    set({ viewMode: mode })
  },

  setTimeWindow: (timeWindow) => {
    set({ timeWindow })
    get().fetchFlowsData()
  },

  setSelectedCountries: (countries) => set({ selectedCountries: countries }),

  toggleCountry: (countryCode) => {
    const { selectedCountries } = get()
    const newSelection = selectedCountries.includes(countryCode)
      ? selectedCountries.filter((c) => c !== countryCode)
      : [...selectedCountries, countryCode]
    set({ selectedCountries: newSelection })
  },

  setSelectedHotspot: (hotspot) => set({ selectedHotspot: hotspot }),

  setAutoRefresh: (enabled) => set({ autoRefresh: enabled }),

  setRefreshInterval: (interval) => set({ refreshInterval: interval }),

  toggleLayer: (layer) => {
    const { layersVisible } = get()
    set({
      layersVisible: {
        ...layersVisible,
        [layer]: !layersVisible[layer],
      },
    })
  },

  clearError: () => set({ error: null }),
}))
