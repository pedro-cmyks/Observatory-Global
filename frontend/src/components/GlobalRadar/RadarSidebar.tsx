import React from 'react';
import { useRadarStore } from '../../store/radarStore';

const RadarSidebar: React.FC = () => {
    const { selectedNode, selectNode } = useRadarStore();

    if (!selectedNode) return null;

    return (
        <div className="absolute top-0 right-0 h-full w-96 bg-black/95 backdrop-blur border-l border-gray-800 shadow-2xl z-50 overflow-y-auto transform transition-transform duration-300 ease-in-out">
            {/* Close Button */}
            <button
                onClick={() => selectNode(null)}
                className="absolute top-4 right-4 text-gray-400 hover:text-white p-2"
            >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>

            <div className="p-8 pt-16">
                {/* Header */}
                <div className="mb-8">
                    <h2 className="text-3xl font-bold mb-2">{selectedNode.name}</h2>
                    <div className="flex items-center gap-4 text-sm">
                        <span className="px-2 py-1 rounded bg-blue-900/30 text-blue-400 border border-blue-800">
                            Intensity: {(selectedNode.intensity * 100).toFixed(0)}%
                        </span>
                        <span className={`px-2 py-1 rounded border ${selectedNode.sentiment > 0
                                ? 'bg-green-900/30 text-green-400 border-green-800'
                                : 'bg-red-900/30 text-red-400 border-red-800'
                            }`}>
                            Sentiment: {selectedNode.sentiment > 0 ? '+' : ''}{selectedNode.sentiment}
                        </span>
                    </div>
                </div>

                {/* Themes */}
                <div className="mb-8">
                    <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">Dominant Themes</h3>
                    <div className="flex flex-wrap gap-2">
                        {selectedNode.themes.map((theme) => (
                            <span key={theme} className="px-3 py-1 rounded-full bg-gray-800 text-gray-300 text-sm border border-gray-700">
                                #{theme}
                            </span>
                        ))}
                    </div>
                </div>

                {/* Placeholder for more data */}
                <div className="space-y-6">
                    <div>
                        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">Key Actors</h3>
                        <div className="bg-gray-900/50 rounded p-4 border border-gray-800 text-sm text-gray-400">
                            Data not available in placeholder mode.
                        </div>
                    </div>

                    <div>
                        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">Source Diversity</h3>
                        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-blue-500 to-purple-500 w-3/4"></div>
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-2">
                            <span>Low</span>
                            <span>High</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default RadarSidebar;
