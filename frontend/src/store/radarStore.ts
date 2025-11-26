import { create } from 'zustand';

export interface NodeData {
    id: string;
    name: string;
    lat: number;
    lon: number;
    intensity: number;
    sentiment: number;
    themes: string[];
    sourceCount: number;
    sourceDiversity: number;
    topSources: string[];
    keyActors: Array<{ name: string; count: number }>;
    topThemes: Array<{ label: string; count: number }>;
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
    searchQuery: string;

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
    setSearchQuery: (query: string) => void;
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
        { id: 'US', name: 'United States', lat: 37.0902, lon: -95.7129, intensity: 0.9, sentiment: -0.2, themes: ['Politics', 'Economy'], sourceCount: 150, sourceDiversity: 0.8, topSources: ['cnn.com', 'nytimes.com', 'foxnews.com'], keyActors: [{ name: 'Joe Biden', count: 45 }, { name: 'Congress', count: 30 }], topThemes: [{ label: 'Politics', count: 120 }, { label: 'Economy', count: 95 }] },
        { id: 'CN', name: 'China', lat: 35.8617, lon: 104.1954, intensity: 0.8, sentiment: 0.1, themes: ['Trade', 'Technology'], sourceCount: 120, sourceDiversity: 0.6, topSources: ['xinhuanet.com', 'chinadaily.com.cn'], keyActors: [{ name: 'Xi Jinping', count: 40 }, { name: 'Huawei', count: 25 }], topThemes: [{ label: 'Trade', count: 110 }, { label: 'Technology', count: 90 }] },
        { id: 'RU', name: 'Russia', lat: 61.5240, lon: 105.3188, intensity: 0.7, sentiment: -0.5, themes: ['Conflict', 'Energy'], sourceCount: 90, sourceDiversity: 0.5, topSources: ['rt.com', 'tass.com'], keyActors: [{ name: 'Vladimir Putin', count: 50 }, { name: 'Gazprom', count: 20 }], topThemes: [{ label: 'Conflict', count: 130 }, { label: 'Energy', count: 80 }] },
        { id: 'IN', name: 'India', lat: 20.5937, lon: 78.9629, intensity: 0.75, sentiment: 0.2, themes: ['Economy', 'Technology'], sourceCount: 110, sourceDiversity: 0.7, topSources: ['timesofindia.indiatimes.com', 'thehindu.com'], keyActors: [{ name: 'Narendra Modi', count: 35 }, { name: 'Tata Group', count: 15 }], topThemes: [{ label: 'Economy', count: 100 }, { label: 'Technology', count: 85 }] },
        { id: 'DE', name: 'Germany', lat: 51.1657, lon: 10.4515, intensity: 0.6, sentiment: 0.2, themes: ['EU', 'Industry'], sourceCount: 80, sourceDiversity: 0.75, topSources: ['dw.com', 'spiegel.de'], keyActors: [{ name: 'Olaf Scholz', count: 25 }, { name: 'Volkswagen', count: 15 }], topThemes: [{ label: 'EU', count: 90 }, { label: 'Industry', count: 70 }] },
        { id: 'GB', name: 'United Kingdom', lat: 55.3781, lon: -3.4360, intensity: 0.65, sentiment: 0.1, themes: ['Brexit', 'Politics'], sourceCount: 85, sourceDiversity: 0.8, topSources: ['bbc.co.uk', 'theguardian.com'], keyActors: [{ name: 'Rishi Sunak', count: 30 }, { name: 'Parliament', count: 20 }], topThemes: [{ label: 'Politics', count: 95 }, { label: 'Brexit', count: 60 }] },
        { id: 'FR', name: 'France', lat: 46.2276, lon: 2.2137, intensity: 0.55, sentiment: 0.0, themes: ['EU', 'Culture'], sourceCount: 70, sourceDiversity: 0.7, topSources: ['france24.com', 'lemonde.fr'], keyActors: [{ name: 'Emmanuel Macron', count: 35 }, { name: 'EU', count: 20 }], topThemes: [{ label: 'EU', count: 80 }, { label: 'Culture', count: 50 }] },
        { id: 'JP', name: 'Japan', lat: 36.2048, lon: 138.2529, intensity: 0.6, sentiment: -0.1, themes: ['Technology', 'Trade'], sourceCount: 75, sourceDiversity: 0.65, topSources: ['japantimes.co.jp', 'nhk.or.jp'], keyActors: [{ name: 'Fumio Kishida', count: 20 }, { name: 'Toyota', count: 15 }], topThemes: [{ label: 'Technology', count: 85 }, { label: 'Trade', count: 60 }] },
        { id: 'BR', name: 'Brazil', lat: -14.2350, lon: -51.9253, intensity: 0.5, sentiment: 0.3, themes: ['Environment', 'Agriculture'], sourceCount: 60, sourceDiversity: 0.6, topSources: ['globo.com', 'folha.uol.com.br'], keyActors: [{ name: 'Lula da Silva', count: 30 }, { name: 'Petrobras', count: 15 }], topThemes: [{ label: 'Environment', count: 90 }, { label: 'Agriculture', count: 70 }] },
        { id: 'CA', name: 'Canada', lat: 56.1304, lon: -106.3468, intensity: 0.5, sentiment: 0.1, themes: ['Environment', 'Politics'], sourceCount: 50, sourceDiversity: 0.7, topSources: ['cbc.ca', 'ctvnews.ca'], keyActors: [{ name: 'Justin Trudeau', count: 25 }, { name: 'Parliament', count: 15 }], topThemes: [{ label: 'Politics', count: 70 }, { label: 'Environment', count: 60 }] },
        { id: 'IT', name: 'Italy', lat: 41.8719, lon: 12.5674, intensity: 0.5, sentiment: -0.05, themes: ['EU', 'Economy'], sourceCount: 55, sourceDiversity: 0.65, topSources: ['ansa.it', 'corriere.it'], keyActors: [{ name: 'Giorgia Meloni', count: 25 }, { name: 'EU', count: 15 }], topThemes: [{ label: 'EU', count: 75 }, { label: 'Economy', count: 60 }] },
        { id: 'KR', name: 'South Korea', lat: 35.9078, lon: 127.7669, intensity: 0.55, sentiment: 0.1, themes: ['Technology', 'Security'], sourceCount: 65, sourceDiversity: 0.6, topSources: ['yonhapnews.co.kr', 'koreaherald.com'], keyActors: [{ name: 'Yoon Suk-yeol', count: 20 }, { name: 'Samsung', count: 25 }], topThemes: [{ label: 'Technology', count: 80 }, { label: 'Security', count: 65 }] },
        { id: 'MX', name: 'Mexico', lat: 23.6345, lon: -102.5528, intensity: 0.45, sentiment: -0.1, themes: ['Migration', 'Economy'], sourceCount: 45, sourceDiversity: 0.55, topSources: ['eluniversal.com.mx', 'milenio.com'], keyActors: [{ name: 'AMLO', count: 30 }, { name: 'Pemex', count: 15 }], topThemes: [{ label: 'Migration', count: 85 }, { label: 'Economy', count: 60 }] },
        { id: 'ES', name: 'Spain', lat: 40.4637, lon: -3.7492, intensity: 0.45, sentiment: 0.05, themes: ['Tourism', 'Politics'], sourceCount: 50, sourceDiversity: 0.65, topSources: ['elpais.com', 'elmundo.es'], keyActors: [{ name: 'Pedro Sanchez', count: 20 }, { name: 'EU', count: 15 }], topThemes: [{ label: 'Politics', count: 70 }, { label: 'Tourism', count: 60 }] },
        { id: 'AU', name: 'Australia', lat: -25.2744, lon: 133.7751, intensity: 0.4, sentiment: 0.15, themes: ['Climate', 'Trade'], sourceCount: 40, sourceDiversity: 0.7, topSources: ['abc.net.au', 'smh.com.au'], keyActors: [{ name: 'Anthony Albanese', count: 20 }, { name: 'Parliament', count: 15 }], topThemes: [{ label: 'Climate', count: 75 }, { label: 'Trade', count: 60 }] },
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
    // const activeNodeIds = new Set(nodes.map(n => n.id));

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
    searchQuery: '', // Added
    data: { nodes: [], flows: [], heatmapPoints: [] },
    isLoading: false,

    setTimeWindow: (window: '1h' | '6h' | '12h' | '24h') => {
        set({ timeWindow: window });
        get().fetchData();
    },

    setSearchQuery: (query: string) => {
        set({ searchQuery: query });
        // Debounce fetch could be added here, but for now direct call
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
            const useMockData = false;

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

            const { timeWindow, searchQuery } = get(); // Destructure searchQuery
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8080';

            const params = new URLSearchParams({
                time_window: timeWindow
            });
            if (searchQuery) {
                params.append('query', searchQuery);
            }

            const response = await fetch(`${apiUrl}/v1/flows?${params.toString()}`); // Use params in fetch
            if (!response.ok) throw new Error('Failed to fetch data');

            const data = await response.json();

            const nodes: NodeData[] = (data.hotspots || []).map((h: any) => ({
                id: h.country_code || h.id,
                name: h.country_name || h.name,
                lat: h.latitude || (h.loc ? h.loc[0] : 0),
                lon: h.longitude || (h.loc ? h.loc[1] : 0),
                intensity: Math.min(1.0, (h.intensity || 0.1) * 3), // Boost intensity for visibility
                sentiment: h.sentiment || 0,
                themes: h.themes || [],
                sourceCount: h.source_count || 0,
                sourceDiversity: h.source_diversity || 0,
                topSources: (h.signals || [])
                    .map((s: any) => s.source_outlet)
                    .filter((s: string) => s) // Filter nulls
                    .filter((v: string, i: number, a: string[]) => a.indexOf(v) === i) // Unique
                    .slice(0, 5), // Top 5
                keyActors: (() => {
                    const actors: Record<string, number> = {};
                    (h.signals || []).forEach((s: any) => {
                        (s.persons || []).forEach((p: string) => actors[p] = (actors[p] || 0) + 1);
                        (s.organizations || []).forEach((o: string) => actors[o] = (actors[o] || 0) + 1);
                    });
                    return Object.entries(actors)
                        .sort(([, a], [, b]) => b - a)
                        .slice(0, 5)
                        .map(([name, count]) => ({ name, count }));
                })(),
                topThemes: (() => {
                    // Use theme_distribution from API if available, otherwise aggregate from signals
                    if (h.theme_distribution) {
                        return Object.entries(h.theme_distribution)
                            .sort(([, a], [, b]) => (b as number) - (a as number))
                            .slice(0, 5)
                            .map(([label, count]) => ({ label, count: count as number }));
                    }
                    // Fallback aggregation
                    const themes: Record<string, number> = {};
                    (h.signals || []).forEach((s: any) => {
                        (s.theme_labels || []).forEach((t: string) => themes[t] = (themes[t] || 0) + 1);
                    });
                    return Object.entries(themes)
                        .sort(([, a], [, b]) => b - a)
                        .slice(0, 5)
                        .map(([label, count]) => ({ label, count }));
                })()
            }));

            const flows: FlowData[] = (data.flows || []).map((f: any) => ({
                source: f.from_country, // Fixed: match API field
                target: f.to_country,   // Fixed: match API field
                value: f.weight || (f.heat * 10) || 1
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
