import React from 'react';
import Map from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import { MapViewState } from '@deck.gl/core';
import { useRadarStore } from '../../store/radarStore';
import { ScatterplotLayer, ArcLayer } from '@deck.gl/layers';
import { HeatmapLayer } from '@deck.gl/aggregation-layers';

// Mapbox Token (should be in env, but using hardcoded for now as per previous context if needed, 
// but better to assume it's in the environment or passed down. 
// I'll check if there's a common config file, but for now I'll assume import.meta.env.VITE_MAPBOX_TOKEN)
const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN || 'pk.eyJ1IjoicHZpbGxlZyIsImEiOiJjbWh3Nnptb28wNDB2Mm9weTFqdXZqM3VyIn0.ZnybOXNNDKL1HJFuklpyGg';

const INITIAL_VIEW_STATE: MapViewState = {
    longitude: 0,
    latitude: 20,
    zoom: 1.5,
    pitch: 0,
    bearing: 0
};

const RadarMap: React.FC = () => {
    const { data, activeLayers } = useRadarStore();

    console.log('RadarMap rendering with:', {
        nodesCount: data.nodes.length,
        flowsCount: data.flows.length,
        heatmapPointsCount: data.heatmapPoints.length,
        activeLayers
    });

    const layers = [
        // Heatmap Layer (uses dispersed points for regional field effect)
        activeLayers.heatmap && new HeatmapLayer({
            id: 'heatmap-layer',
            data: data.heatmapPoints,
            getPosition: (d: any) => d.position,
            getWeight: (d: any) => d.weight,
            radiusPixels: 180,  // Very large radius for persistent regional blobs even at close zoom
            intensity: 1.0,
            threshold: 0.02,
            opacity: 0.7,
            colorRange: [
                [0, 0, 255, 25],      // Deep blue (cool/low)
                [0, 255, 255, 50],    // Cyan
                [0, 255, 0, 100],     // Green
                [255, 255, 0, 150],   // Yellow
                [255, 128, 0, 200],   // Orange
                [255, 0, 0, 255]      // Red (hot/high)
            ],
            pickable: false  // Heatmap shouldn't intercept clicks
        }),

        // Flows Layer
        activeLayers.flows && new ArcLayer({
            id: 'arc-layer',
            data: data.flows,
            getSourcePosition: (d: any) => {
                const node = data.nodes.find(n => n.id === d.source);
                return node ? [node.lon, node.lat] : [0, 0];
            },
            getTargetPosition: (d: any) => {
                const node = data.nodes.find(n => n.id === d.target);
                return node ? [node.lon, node.lat] : [0, 0];
            },
            getSourceColor: [0, 255, 255, 180], // Cyan
            getTargetColor: [255, 0, 255, 180], // Magenta
            getWidth: 2,
            pickable: false  // Flows shouldn't intercept node clicks
        }),

        // Nodes Layer (must be last to be on top for clicks)
        activeLayers.nodes && new ScatterplotLayer({
            id: 'node-layer',
            data: data.nodes,
            getPosition: (d: any) => [d.lon, d.lat],
            getFillColor: (d: any) => d.sentiment > 0 ? [0, 255, 100, 150] : [255, 50, 50, 150],
            getRadius: (d: any) => 300000 * d.intensity, // Further reduced
            radiusMinPixels: 4,   // Smaller minimum
            radiusMaxPixels: 14,  // Much smaller maximum
            pickable: true,
            onClick: (info, event) => {
                console.log('🔴 NODE CLICK EVENT FIRED:', info.object);
                if (info.object) {
                    const store = useRadarStore.getState();
                    console.log('🔴 Calling selectNode with:', info.object);
                    store.selectNode(info.object);
                    console.log('🔴 Store selectedNode after click:', store.selectedNode);
                }
            },
            autoHighlight: true,
            highlightColor: [255, 255, 255, 200],
        })
    ].filter(Boolean);

    return (
        <DeckGL
            initialViewState={INITIAL_VIEW_STATE}
            controller={true}
            getTooltip={({ object }) => object && {
                html: `
          <div style="background: rgba(0,0,0,0.8); color: white; padding: 8px; border-radius: 4px; font-size: 12px;">
            <div style="font-weight: bold; margin-bottom: 4px;">${object.name || object.source}</div>
            ${object.intensity ? `<div>Intensity: ${(object.intensity * 100).toFixed(0)}%</div>` : ''}
            ${object.sentiment ? `<div>Sentiment: ${object.sentiment}</div>` : ''}
            ${object.value ? `<div>Flow: ${object.value}</div>` : ''}
          </div>
        `,
                style: {
                    backgroundColor: 'transparent',
                    fontSize: '0.8em'
                }
            }}
            layers={layers}
            style={{ width: '100%', height: '100%' }}
        >
            <Map
                mapboxAccessToken={MAPBOX_TOKEN}
                mapStyle="mapbox://styles/mapbox/dark-v11"
                reuseMaps
                preventStyleDiffing={true}
                projection={{ name: 'mercator' }}
            />
        </DeckGL>
    );
};

export default RadarMap;
