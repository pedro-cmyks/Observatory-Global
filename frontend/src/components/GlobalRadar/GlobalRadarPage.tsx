import React, { useEffect } from 'react';
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
        <div className="w-screen h-screen bg-black text-white overflow-hidden relative">
            {/* Header */}
            <div className="absolute top-0 left-0 w-full z-50 p-4 pointer-events-none">
                <div className="flex items-center gap-3 pointer-events-auto">
                    <div className="text-2xl font-bold tracking-wider">
                        🌍 OBSERVATORY GLOBAL
                    </div>
                    <div className="text-xs text-gray-400 uppercase tracking-widest border-l border-gray-700 pl-3">
                        Global Narrative Radar
                    </div>
                </div>
            </div>

            {/* Map Container */}
            <div className="absolute inset-0 z-0 bg-gray-900">
                <RadarMap />
            </div>

            {/* Controls */}
            <RadarControls />

            {/* Sidebar */}
            <RadarSidebar />
        </div>
    );
};

export default GlobalRadarPage;
