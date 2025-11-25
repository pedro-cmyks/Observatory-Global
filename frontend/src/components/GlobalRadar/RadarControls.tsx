import React from 'react';
import { useRadarStore } from '../../store/radarStore';

const RadarControls: React.FC = () => {
    const {
        timeWindow,
        setTimeWindow,
        activeLayers,
        toggleLayer,
        isLoading
    } = useRadarStore();

    return (
        <div className="absolute top-20 left-4 z-40 flex flex-col gap-4">
            {/* Layer Controls */}
            <div className="bg-black/80 backdrop-blur border border-gray-800 p-4 rounded-lg min-w-[200px]">
                <h3 className="text-xs font-bold text-gray-400 uppercase mb-3 flex items-center gap-2">
                    <span>Layers</span>
                    {isLoading && <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>}
                </h3>
                <div className="space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer hover:text-blue-400 transition-colors">
                        <input
                            type="checkbox"
                            checked={activeLayers.heatmap}
                            onChange={() => toggleLayer('heatmap')}
                            className="rounded border-gray-700 bg-gray-900 text-blue-500 focus:ring-blue-500 focus:ring-offset-black"
                        />
                        <span className="text-sm">Radar Heatmap</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer hover:text-blue-400 transition-colors">
                        <input
                            type="checkbox"
                            checked={activeLayers.flows}
                            onChange={() => toggleLayer('flows')}
                            className="rounded border-gray-700 bg-gray-900 text-blue-500 focus:ring-blue-500 focus:ring-offset-black"
                        />
                        <span className="text-sm">Information Flows</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer hover:text-blue-400 transition-colors">
                        <input
                            type="checkbox"
                            checked={activeLayers.nodes}
                            onChange={() => toggleLayer('nodes')}
                            className="rounded border-gray-700 bg-gray-900 text-blue-500 focus:ring-blue-500 focus:ring-offset-black"
                        />
                        <span className="text-sm">Nodes / Centroids</span>
                    </label>
                </div>
            </div>

            {/* Time Window Controls */}
            <div className="bg-black/80 backdrop-blur border border-gray-800 p-4 rounded-lg min-w-[200px]">
                <h3 className="text-xs font-bold text-gray-400 uppercase mb-3">Time Window</h3>
                <div className="grid grid-cols-2 gap-2">
                    {(['1h', '6h', '12h', '24h'] as const).map((window) => (
                        <button
                            key={window}
                            onClick={() => setTimeWindow(window)}
                            className={`
                px-3 py-1.5 text-xs font-medium rounded transition-all
                ${timeWindow === window
                                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50'
                                    : 'bg-gray-900 text-gray-400 hover:bg-gray-800 hover:text-white'
                                }
              `}
                        >
                            {window}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default RadarControls;
