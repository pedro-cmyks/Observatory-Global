import { FlowsResponse, CountryHotspot, Flow } from './mapTypes'

/**
 * Mock data generator for development when backend is unavailable
 */
export function generateMockFlowsData(): FlowsResponse {
    const countries = [
        { code: 'US', name: 'United States', lat: 37.0902, lng: -95.7129 },
        { code: 'BR', name: 'Brazil', lat: -14.2350, lng: -51.9253 },
        { code: 'GB', name: 'United Kingdom', lat: 55.3781, lng: -3.4360 },
        { code: 'FR', name: 'France', lat: 46.2276, lng: 2.2137 },
        { code: 'DE', name: 'Germany', lat: 51.1657, lng: 10.4515 },
        { code: 'CN', name: 'China', lat: 35.8617, lng: 104.1954 },
        { code: 'RU', name: 'Russia', lat: 61.5240, lng: 105.3188 },
        { code: 'IN', name: 'India', lat: 20.5937, lng: 78.9629 },
        { code: 'AU', name: 'Australia', lat: -25.2744, lng: 133.7751 },
        { code: 'JP', name: 'Japan', lat: 36.2048, lng: 138.2529 },
        { code: 'MX', name: 'Mexico', lat: 23.6345, lng: -102.5528 },
        { code: 'AR', name: 'Argentina', lat: -38.4161, lng: -63.6167 },
    ]

    // Generate hotspots with realistic intensity distribution
    const hotspots: CountryHotspot[] = countries.map((country, index) => {
        const intensity = 0.2 + Math.random() * 0.7 // 0.2 to 0.9
        const topicCount = Math.floor(5 + Math.random() * 15) // 5-20 topics

        return {
            country_code: country.code,
            country_name: country.name,
            latitude: country.lat,
            longitude: country.lng,
            topic_count: topicCount,
            intensity,
            confidence: 0.8 + Math.random() * 0.2,
            top_topics: [
                { label: 'Economic Policy', count: Math.floor(Math.random() * 100) + 20 },
                { label: 'International Relations', count: Math.floor(Math.random() * 80) + 15 },
                { label: 'Climate Change', count: Math.floor(Math.random() * 60) + 10 },
            ],
            dominant_sentiment: intensity > 0.6 ? 'negative' : intensity > 0.4 ? 'neutral' : 'positive',
            avg_sentiment_score: (intensity - 0.5) * 20, // -10 to +10
            theme_distribution: {
                'Economic Policy': Math.floor(Math.random() * 50) + 30,
                'Healthcare': Math.floor(Math.random() * 40) + 20,
                'Technology': Math.floor(Math.random() * 30) + 10,
            },
            signals: [
                {
                    signal_id: `signal-${country.code}-1`,
                    timestamp: new Date(Date.now() - Math.random() * 86400000).toISOString(),
                    themes: ['ECON_POLICY', 'POLITICS'],
                    theme_labels: ['Economic Policy', 'Politics'],
                    theme_counts: { 'Economic Policy': 45, 'Politics': 32 },
                    sentiment_label: intensity > 0.5 ? 'negative' : 'positive',
                    sentiment_score: (intensity - 0.5) * 20,
                    persons: ['Political Leader A', 'Minister B'],
                    organizations: ['Central Bank', 'Treasury Department'],
                    source_outlet: index % 3 === 0 ? 'reuters.com' : index % 3 === 1 ? 'bbc.com' : 'nytimes.com',
                },
            ],
            source_count: Math.floor(Math.random() * 10) + 3,
            source_diversity: 0.5 + Math.random() * 0.4,
        }
    })

    // Generate flows between countries
    const flows: Flow[] = []
    for (let i = 0; i < countries.length; i++) {
        for (let j = i + 1; j < countries.length; j++) {
            // Only create some flows (not all pairs)
            if (Math.random() > 0.7) {
                const heat = 0.3 + Math.random() * 0.6 // 0.3 to 0.9
                flows.push({
                    from_country: countries[i].code,
                    to_country: countries[j].code,
                    heat,
                    similarity: 0.6 + Math.random() * 0.3,
                    time_delta_minutes: Math.floor(Math.random() * 360) + 30, // 30min to 6h
                    shared_topics: ['Economic Policy', 'Climate Change'],
                    from_coords: [countries[i].lng, countries[i].lat],
                    to_coords: [countries[j].lng, countries[j].lat],
                })
            }
        }
    }

    return {
        time_window: '24h',
        generated_at: new Date().toISOString(),
        hotspots,
        flows,
        metadata: {
            formula: 'heat = similarity × exp(-Δt / 6h)',
            threshold: 0.3,
            time_window_hours: 24,
            total_flows_computed: flows.length * 2,
            flows_returned: flows.length,
            countries_analyzed: countries.map(c => c.code),
            data_source: 'mock_dev',
            data_quality: 'dev_mock',
            placeholder_reason: 'Using mock data for frontend development - backend unavailable',
        },
    }
}
