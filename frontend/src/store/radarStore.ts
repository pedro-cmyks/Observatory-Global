import { create } from 'zustand';

export interface NodeData {
    id: string;
    name: string;
    lat: number;
    lon: number;
    intensity: number;
    sentiment: number;
    themes: string[];
}

export interface FlowData {
    source: string;
    target: string;
    value: number;
}

interface RadarState {
    // UI State
    timeWindow: '1h' | '6h' | '12h' | '24h';
    activeLayers: {
        heatmap: boolean;
        flows: boolean;
        nodes: boolean;
    };
    selectedNode: NodeData | null;
    hoveredNode: NodeData | null;

    // Data State
    data: {
        nodes: NodeData[];
        flows: FlowData[];
    };
    isLoading: boolean;

    // Actions
    setTimeWindow: (window: '1h' | '6h' | '12h' | '24h') => void;
    toggleLayer: (layer: 'heatmap' | 'flows' | 'nodes') => void;
    selectNode: (node: NodeData | null) => void;
    setHoveredNode: (node: NodeData | null) => void;
    fetchData: () => Promise<void>;
}

// Placeholder data generator
const generatePlaceholderData = () => {
    const nodes: NodeData[] = [
        { id: 'US', name: 'United States', lat: 37.0902, lon: -95.7129, intensity: 0.9, sentiment: -0.2, themes: ['Politics', 'Economy'] },
        { id: 'CN', name: 'China', lat: 35.8617, lon: 104.1954, intensity: 0.8, sentiment: 0.1, themes: ['Trade', 'Technology'] },
        { id: 'RU', name: 'Russia', lat: 61.5240, lon: 105.3188, intensity: 0.7, sentiment: -0.5, themes: ['Conflict', 'Energy'] },
        { id: 'BR', name: 'Brazil', lat: -14.2350, lon: -51.9253, intensity: 0.5, sentiment: 0.3, themes: ['Environment', 'Agriculture'] },
        { id: 'DE', name: 'Germany', lat: 51.1657, lon: 10.4515, intensity: 0.6, sentiment: 0.2, themes: ['EU', 'Industry'] },
    ];

    const flows: FlowData[] = [
        { source: 'US', target: 'CN', value: 10 },
        { source: 'US', target: 'RU', value: 5 },
        { source: 'CN', target: 'RU', value: 8 },
        { source: 'BR', target: 'US', value: 4 },
        { source: 'DE', target: 'US', value: 6 },
    ];

    return { nodes, flows };
};

export const useRadarStore = create<RadarState>((set, get) => ({
    timeWindow: '24h',
    activeLayers: {
        heatmap: true,
        flows: true,
        nodes: true,
    },
    selectedNode: null,
    hoveredNode: null,
    data: { nodes: [], flows: [] },
    isLoading: false,

    setTimeWindow: (window) => {
        set({ timeWindow: window });
        get().fetchData();
    },

    toggleLayer: (layer) => set((state) => ({
        activeLayers: {
            ...state.activeLayers,
            [layer]: !state.activeLayers[layer]
        }
    })),

    selectNode: (node) => set({ selectedNode: node }),

    setHoveredNode: (node) => set({ hoveredNode: node }),

    fetchData: async () => {
        set({ isLoading: true });
        try {
            const { timeWindow } = get();
            // Map timeWindow to backend parameter if needed, or pass directly
            // Assuming backend accepts '1h', '24h' etc or needs conversion.
            // Based on previous knowledge, backend might expect '1h', '24h'.

            const response = await fetch(`http://localhost:8000/v1/flows?time_window=${timeWindow}`);
            if (!response.ok) throw new Error('Failed to fetch data');

            const data = await response.json();

            // Transform backend data to our format if necessary
            // Backend returns { flows: [], hotspots: [] } usually
            // We need to map 'hotspots' to 'nodes'

            const nodes: NodeData[] = (data.hotspots || []).map((h: any) => ({
                id: h.country_code || h.id, // Fallback
                name: h.country_name || h.name,
                lat: h.loc ? h.loc[0] : 0,
                lon: h.loc ? h.loc[1] : 0,
                intensity: h.intensity || 0.5,
                sentiment: h.sentiment || 0,
                themes: h.themes || []
            }));

            const flows: FlowData[] = (data.flows || []).map((f: any) => ({
                source: f.source_country,
                target: f.target_country,
                value: f.weight || 1
            }));

            set({
                data: { nodes, flows },
                isLoading: false
            });
        } catch (error) {
            console.error('Error fetching radar data:', error);
            // Fallback to placeholder on error for now, or just empty
            set({ isLoading: false });
        }
    },
}));
