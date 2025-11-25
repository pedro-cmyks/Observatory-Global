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

export interface HeatmapPoint {
    position: [number, number];
    weight: number;
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
    topicFilter: string | null; // Future: filter by topic/entity

    // Data State
    data: {
        nodes: NodeData[];
        flows: FlowData[];
        heatmapPoints: HeatmapPoint[];
    };
    isLoading: boolean;

    // Actions
    setTimeWindow: (window: '1h' | '6h' | '12h' | '24h') => void;
    toggleLayer: (layer: 'heatmap' | 'flows' | 'nodes') => void;
    selectNode: (node: NodeData | null) => void;
    setHoveredNode: (node: NodeData | null) => void;
    setTopicFilter: (topic: string | null) => void;
    fetchData: () => Promise<void>;
}

// Major cities per country for realistic distribution (not just centroids)
const MAJOR_CITIES: Record<string, Array<{ name: string; lat: number; lon: number }>> = {
    US: [
        { name: 'New York', lat: 40.7128, lon: -74.0060 },
        { name: 'Los Angeles', lat: 34.0522, lon: -118.2437 },
        { name: 'Washington DC', lat: 38.9072, lon: -77.0369 },
        { name: 'Miami', lat: 25.7617, lon: -80.1918 }
    ],
    CN: [
        { name: 'Beijing', lat: 39.9042, lon: 116.4074 },
        { name: 'Shanghai', lat: 31.2304, lon: 121.4737 },
        { name: 'Hong Kong', lat: 22.3193, lon: 114.1694 }
    ],
    RU: [
        { name: 'Moscow', lat: 55.7558, lon: 37.6173 },
        { name: 'St Petersburg', lat: 59.9311, lon: 30.3609 }
    ],
    IN: [
        { name: 'New Delhi', lat: 28.6139, lon: 77.2090 },
        { name: 'Mumbai', lat: 19.0760, lon: 72.8777 }
    ],
    DE: [
        { name: 'Berlin', lat: 52.5200, lon: 13.4050 },
        { name: 'Munich', lat: 48.1351, lon: 11.5820 }
    ],
    GB: [
        { name: 'London', lat: 51.5074, lon: -0.1278 },
        { name: 'Manchester', lat: 53.4808, lon: -2.2426 }
    ],
    FR: [
        { name: 'Paris', lat: 48.8566, lon: 2.3522 },
        { name: 'Lyon', lat: 45.7640, lon: 4.8357 }
    ],
    JP: [
        { name: 'Tokyo', lat: 35.6762, lon: 139.6503 },
        { name: 'Osaka', lat: 34.6937, lon: 135.5023 }
    ],
    BR: [
        { name: 'Brasilia', lat: -15.8267, lon: -47.9218 },
        { name: 'São Paulo', lat: -23.5505, lon: -46.6333 }
    ]
};

// Generate dispersed heatmap points around cities (not just centroids)
const generateHeatmapPoints = (nodes: NodeData[]): HeatmapPoint[] => {
    const points: HeatmapPoint[] = [];

    nodes.forEach(node => {
        // Get major cities for this country, or use centroid as fallback
        const cities = MAJOR_CITIES[node.id] || [{ name: node.name, lat: node.lat, lon: node.lon }];

        cities.forEach(city => {
            // Points per city scales with node intensity
            const pointsPerCity = Math.floor(15 + node.intensity * 40);
            const cityRadius = 2 + node.intensity * 5; // Degrees around city

            for (let i = 0; i < pointsPerCity; i++) {
                const distanceFactor = Math.pow(Math.random(), 1.8);
                const distance = cityRadius * distanceFactor;
                const angle = Math.random() * 2 * Math.PI;

                const lat = city.lat + distance * Math.cos(angle);
                const lon = city.lon + distance * Math.sin(angle);
                const weight = node.intensity * (1 - distanceFactor * 0.6);

                points.push({
                    position: [lon, lat],
                    weight: Math.max(0.1, weight)
                });
            }
        });
    });

    return points;
};

// Placeholder data generator with time window awareness
const generatePlaceholderData = (timeWindow: '1h' | '6h' | '12h' | '24h') => {
    // All possible nodes with base intensity
    const allNodes: NodeData[] = [
        { id: 'US', name: 'United States', lat: 37.0902, lon: -95.7129, intensity: 0.9, sentiment: -0.2, themes: ['Politics', 'Economy'] },
        { id: 'CN', name: 'China', lat: 35.8617, lon: 104.1954, intensity: 0.8, sentiment: 0.1, themes: ['Trade', 'Technology'] },
        { id: 'RU', name: 'Russia', lat: 61.5240, lon: 105.3188, intensity: 0.7, sentiment: -0.5, themes: ['Conflict', 'Energy'] },
        { id: 'IN', name: 'India', lat: 20.5937, lon: 78.9629, intensity: 0.75, sentiment: 0.2, themes: ['Economy', 'Technology'] },
        { id: 'DE', name: 'Germany', lat: 51.1657, lon: 10.4515, intensity: 0.6, sentiment: 0.2, themes: ['EU', 'Industry'] },
        { id: 'GB', name: 'United Kingdom', lat: 55.3781, lon: -3.4360, intensity: 0.65, sentiment: 0.1, themes: ['Brexit', 'Politics'] },
        { id: 'FR', name: 'France', lat: 46.2276, lon: 2.2137, intensity: 0.55, sentiment: 0.0, themes: ['EU', 'Culture'] },
        { id: 'JP', name: 'Japan', lat: 36.2048, lon: 138.2529, intensity: 0.6, sentiment: -0.1, themes: ['Technology', 'Trade'] },
        { id: 'BR', name: 'Brazil', lat: -14.2350, lon: -51.9253, intensity: 0.5, sentiment: 0.3, themes: ['Environment', 'Agriculture'] },
        { id: 'CA', name: 'Canada', lat: 56.1304, lon: -106.3468, intensity: 0.5, sentiment: 0.1, themes: ['Environment', 'Politics'] },
        { id: 'IT', name: 'Italy', lat: 41.8719, lon: 12.5674, intensity: 0.5, sentiment: -0.05, themes: ['EU', 'Economy'] },
        { id: 'KR', name: 'South Korea', lat: 35.9078, lon: 127.7669, intensity: 0.55, sentiment: 0.1, themes: ['Technology', 'Security'] },
        { id: 'MX', name: 'Mexico', lat: 23.6345, lon: -102.5528, intensity: 0.45, sentiment: -0.1, themes: ['Migration', 'Economy'] },
        { id: 'ES', name: 'Spain', lat: 40.4637, lon: -3.7492, intensity: 0.45, sentiment: 0.05, themes: ['Tourism', 'Politics'] },
        { id: 'AU', name: 'Australia', lat: -25.2744, lon: 133.7751, intensity: 0.4, sentiment: 0.15, themes: ['Climate', 'Trade'] },
    ];

    // Time window affects: node count, intensity boost, flow count
    let nodeCount: number;
    let intensityMultiplier: number;

    switch (timeWindow) {
        case '1h':
            nodeCount = 5; // Only top 5 hottest nodes
            intensityMultiplier = 1.3; // Boost intensity (recent surge)
            break;
        case '6h':
            nodeCount = 8;
            intensityMultiplier = 1.15;
            break;
        case '12h':
            nodeCount = 12;
            intensityMultiplier = 1.0;
            break;
        case '24h':
        default:
            nodeCount = 15; // All nodes
            intensityMultiplier = 0.9; // Slightly lower (averaged over time)
            break;
    }

    // Sort by intensity and take top N
    const nodes = allNodes
        .slice(0, nodeCount)
        .map(node => ({
            ...node,
            intensity: Math.min(1.0, node.intensity * intensityMultiplier)
        }));

    // Generate flows based on shared themes (semantic relationships, not random)
    const flows: FlowData[] = [];
    const activeNodeIds = new Set(nodes.map(n => n.id));

    for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
            const nodeA = nodes[i];
            const nodeB = nodes[j];

            // Calculate shared themes (narrative relationship)
            const sharedThemes = nodeA.themes.filter(t => nodeB.themes.includes(t));

            if (sharedThemes.length > 0) {
                // Flow strength based on number of shared themes and combined intensity
                const flowStrength = sharedThemes.length * (nodeA.intensity + nodeB.intensity) / 2;

                // Only create flow if strength is significant (>= 0.5)
                if (flowStrength >= 0.5) {
                    flows.push({
                        source: nodeA.id,
                        target: nodeB.id,
                        value: Math.round(flowStrength * 10)
                    });
                }
            }
        }
    }

    // Generate dispersed heatmap points
    const heatmapPoints = generateHeatmapPoints(nodes);

    return { nodes, flows, heatmapPoints };
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
    topicFilter: null,
    data: { nodes: [], flows: [], heatmapPoints: [] },
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

    selectNode: (node) => {
        console.log('📦 Store.selectNode called with:', node);
        set({ selectedNode: node });
        console.log('📦 Store.selectedNode updated to:', get().selectedNode);
    },

    setHoveredNode: (node) => set({ hoveredNode: node }),

    setTopicFilter: (topic) => {
        console.log('📦 Setting topic filter:', topic);
        set({ topicFilter: topic });
        get().fetchData(); // Refetch with new filter
    },

    fetchData: async () => {
        set({ isLoading: true });
        try {
            // TEMPORARY: Use mock data to ensure UI rendering while backend is fixed
            const useMockData = true;

            if (useMockData) {
                const { timeWindow } = get();
                console.log(`Fetching mock data for time window: ${timeWindow}`);
                const { nodes, flows, heatmapPoints } = generatePlaceholderData(timeWindow);
                // Simulate network delay
                await new Promise(resolve => setTimeout(resolve, 300));
                set({
                    data: { nodes, flows, heatmapPoints },
                    isLoading: false
                });
                return;
            }

            const { timeWindow } = get();
            const response = await fetch(`http://localhost:8000/v1/flows?time_window=${timeWindow}`);
            if (!response.ok) throw new Error('Failed to fetch data');

            const data = await response.json();

            const nodes: NodeData[] = (data.hotspots || []).map((h: any) => ({
                id: h.country_code || h.id,
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
                data: { nodes, flows, heatmapPoints: generateHeatmapPoints(nodes) },
                isLoading: false
            });
        } catch (error) {
            console.error('Error fetching radar data:', error);
            // Fallback to placeholder on error
            const { timeWindow } = get();
            const { nodes, flows, heatmapPoints } = generatePlaceholderData(timeWindow);
            set({
                data: { nodes, flows, heatmapPoints },
                isLoading: false
            });
        }
    },
}));
