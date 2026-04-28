import React, { useEffect } from 'react';
import RadarMap from './RadarMap';
import RadarSidebar from './RadarSidebar';
import RadarControls from './RadarControls';
import { SearchBar } from './SearchBar';
import { useRadarStore } from '../../store/radarStore';

export const GlobalRadarPage: React.FC = () => {
    const { fetchData } = useRadarStore();

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 300000); // Refresh every 5m
        return () => clearInterval(interval);
    }, [fetchData]);

    return (
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

            {/* Search Bar */}
            <SearchBar />

            {/* Map Container */}
            <div
                className="absolute inset-0 bg-gray-900"
                style={{
                    zIndex: 0,
                    width: '100%',
                    height: '100%',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    overflow: 'hidden'
                }}
            >
                <RadarMap />
            </div>

            {/* Controls - Using portal-like positioning to ensure visibility */}
            <RadarControls />

            {/* Sidebar - Must be outside map container for proper z-index */}
            <RadarSidebar />
        </div>
    );
};

export default GlobalRadarPage;
