import React, { useEffect } from 'react';
import ErrorBoundary from '../ErrorBoundary';
import { useRadarStore } from '../../store/radarStore';
import RadarMap from './RadarMap';
import RadarControls from './RadarControls';
import RadarSidebar from './RadarSidebar';

const GlobalRadarPage: React.FC = () => {
    const { fetchData } = useRadarStore();

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    return (
        <ErrorBoundary>
            <div className="w-screen h-screen bg-black text-white overflow-hidden relative">
                {/* Header */}
                <div className="absolute top-6 left-8 z-50 pointer-events-none">
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

                {/* Controls */}
                <RadarControls />

                {/* Sidebar */}
                <RadarSidebar />
            </div>
        </ErrorBoundary>
    );
};

export default GlobalRadarPage;
