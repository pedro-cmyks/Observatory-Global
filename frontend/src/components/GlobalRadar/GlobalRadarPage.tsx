import React, { useEffect } from 'react';
import ErrorBoundary from '../ErrorBoundary';
import { useRadarStore } from '../../store/radarStore';
import RadarMap from './RadarMap';
import RadarControls from './RadarControls';
import RadarSidebar from './RadarSidebar';

const GlobalRadarPage: React.FC = () => {
    const fetchData = useRadarStore((state) => state.fetchData);
    const selectedNode = useRadarStore((state) => state.selectedNode);

    console.log('🔵 GlobalRadarPage RENDER - selectedNode:', selectedNode);

    useEffect(() => {
        console.log('🔵 GlobalRadarPage MOUNTED');
        fetchData();
    }, [fetchData]);

    useEffect(() => {
        console.log('🔵 GlobalRadarPage: selectedNode changed to:', selectedNode);
    }, [selectedNode]);

    return (
        <ErrorBoundary>
            <div className="w-screen h-screen bg-black text-white overflow-hidden relative" style={{ isolation: 'isolate' }}>
                {/* Header */}
                <div className="absolute top-6 left-8 pointer-events-none" style={{ zIndex: 100 }}>
                    <div className="flex flex-col pointer-events-auto">
                        <div className="text-2xl font-bold tracking-wider text-white drop-shadow-md">
                            🌍 OBSERVATORY GLOBAL
                        </div>
                        <div className="text-xs text-blue-400 uppercase tracking-[0.2em] mt-1 font-medium">
                            Live Narrative Radar
                        </div>
                    </div>
                </div>

                {/* Map Container */}
                <div className="absolute inset-0 bg-gray-900" style={{ zIndex: 0 }}>
                    <RadarMap />
                </div>

                {/* Controls - Using portal-like positioning to ensure visibility */}
                <RadarControls />

                {/* Sidebar - Must be outside map container for proper z-index */}
                <RadarSidebar />
            </div>
        </ErrorBoundary>
    );
};

export default GlobalRadarPage;
