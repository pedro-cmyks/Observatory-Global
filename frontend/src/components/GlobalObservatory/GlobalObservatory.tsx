import React, { useState, useMemo, useEffect } from 'react'
import Map, { NavigationControl, useMap } from 'react-map-gl'
import DeckGL from '@deck.gl/react'
import { MapViewState } from '@deck.gl/core'
import 'mapbox-gl/dist/mapbox-gl.css'

import ControlPanel from './ControlPanel'
import { getLayers } from './MapLayerManager'
import { useMapStore } from '../../store/mapStore'
import { TimeWindow } from '../../lib/mapTypes'

// Types
export interface LayerState {
    heatmap: boolean
    flows: boolean
    markers: boolean
}

const MAPBOX_TOKEN = 'pk.eyJ1IjoicHZpbGxlZyIsImEiOiJjbWh3Nnptb28wNDB2Mm9weTFqdXZqM3VyIn0.ZnybOXNNDKL1HJFuklpyGg'

const INITIAL_VIEW_STATE: MapViewState = {
    longitude: 0,
    latitude: 20,
    zoom: 1.5,
    pitch: 0,
    bearing: 0
}

const GlobalObservatory: React.FC = () => {
    // Store State
    const {
        timeWindow,
        setTimeWindow,
        fetchFlowsData,
        flowsData,
        loading
    } = useMapStore()

    // UI State
    const [activeLayers, setActiveLayers] = useState<LayerState>({
        heatmap: true,
        flows: true,
        markers: true
    })

    // Map View State - shared between Mapbox and DeckGL
    const [viewState, setViewState] = useState<MapViewState>(INITIAL_VIEW_STATE)

    // Initial Data Fetch
    useEffect(() => {
        fetchFlowsData()
    }, [])

    // Layers - now with zoom information
    const layers = useMemo(() => {
        console.log('[GlobalObservatory] Generating layers. Data:', flowsData ? `Hotspots: ${flowsData.hotspots.length}` : 'null', 'Zoom:', viewState.zoom)
        return getLayers({
            activeLayers,
            timeWindow,
            data: flowsData,
            zoom: viewState.zoom  // Pass zoom for scaling
        })
    }, [activeLayers, timeWindow, flowsData, viewState.zoom])

    const handleTimeWindowChange = (newWindow: TimeWindow) => {
        setTimeWindow(newWindow)
        // fetchFlowsData is called automatically by the store setter?
        // Checking mapStore.ts: setTimeWindow calls fetchFlowsData. Correct.
    }

    const handleLayerToggle = (layer: keyof LayerState) => {
        setActiveLayers(prev => ({
            ...prev,
            [layer]: !prev[layer]
        }))
    }

    return (
        <div style={{ width: '100vw', height: '100vh', position: 'relative', overflow: 'hidden', background: '#000' }}>
            <DeckGL
                viewState={viewState}
                onViewStateChange={({ viewState: newViewState }) => setViewState(newViewState as MapViewState)}
                controller={true}
                layers={layers}
                style={{ position: 'absolute', width: '100%', height: '100%' }}
                parameters={{
                    // Enable depth testing for proper 3D rendering
                    depthTest: true,
                    depthMask: true,
                }}
            >
                <Map
                    mapboxAccessToken={MAPBOX_TOKEN}
                    mapStyle="mapbox://styles/mapbox/dark-v11"
                    style={{ width: '100%', height: '100%' }}
                >
                    <NavigationControl position="top-right" />
                </Map>
            </DeckGL>

            {/* UI Overlays */}
            <ControlPanel
                activeLayers={activeLayers}
                onToggleLayer={handleLayerToggle}
                timeWindow={timeWindow}
                onTimeWindowChange={handleTimeWindowChange}
            />

            {/* Title Overlay */}
            <div style={{
                position: 'absolute',
                top: 20,
                left: 20,
                zIndex: 10,
                pointerEvents: 'none'
            }}>
                <h1 style={{
                    color: 'white',
                    margin: 0,
                    fontSize: '24px',
                    fontWeight: 600,
                    textShadow: '0 2px 4px rgba(0,0,0,0.5)'
                }}>
                    Global Observatory
                </h1>
                <p style={{
                    color: 'rgba(255,255,255,0.7)',
                    margin: '4px 0 0 0',
                    fontSize: '14px'
                }}>
                    Real-time Narrative Tracking
                </p>
            </div>

        </div>
    )
}

export default GlobalObservatory
