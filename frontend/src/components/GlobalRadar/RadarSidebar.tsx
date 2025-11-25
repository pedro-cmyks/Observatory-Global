import React from 'react';
import { useRadarStore } from '../../store/radarStore';

const RadarSidebar: React.FC = () => {
    const selectedNode = useRadarStore((state) => state.selectedNode);
    const selectNode = useRadarStore((state) => state.selectNode);

    console.log('🟢 SIDEBAR RENDER - selectedNode:', selectedNode);

    // Always render but slide off-screen when not selected
    const isOpen = !!selectedNode;

    return (
        <div
            className="fixed top-0 right-0 h-screen w-96 bg-black/95 backdrop-blur border-l border-gray-800 shadow-2xl overflow-y-auto transition-transform duration-300 ease-in-out"
            style={{
                zIndex: 10000,
                pointerEvents: isOpen ? 'auto' : 'none',
                transform: isOpen ? 'translateX(0)' : 'translateX(100%)'
            }}
        >
            {/* Close Button */}
            {isOpen && (
                <button
                    onClick={() => {
                        console.log('🟢 SIDEBAR: Close button clicked');
                        selectNode(null);
                    }}
                    className="absolute top-4 right-4 text-gray-400 hover:text-white p-2 z-50"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            )}

            {selectedNode && (
                <div className="p-6 pt-16">
                    {/* Header */}
                    <div className="mb-6 pb-4 border-b border-gray-800">
                        <h2 className="text-2xl font-bold mb-3">{selectedNode.name}</h2>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                            <div className="bg-blue-900/20 border border-blue-800/50 rounded px-3 py-2">
                                <div className="text-blue-400/70 uppercase tracking-wider mb-1">Intensity</div>
                                <div className="text-blue-300 font-bold text-lg">{(selectedNode.intensity * 100).toFixed(0)}%</div>
                            </div>
                            <div className={`border rounded px-3 py-2 ${selectedNode.sentiment > 0
                                    ? 'bg-green-900/20 border-green-800/50'
                                    : 'bg-red-900/20 border-red-800/50'
                                }`}>
                                <div className={`uppercase tracking-wider mb-1 ${selectedNode.sentiment > 0 ? 'text-green-400/70' : 'text-red-400/70'}`}>Sentiment</div>
                                <div className={`font-bold text-lg ${selectedNode.sentiment > 0 ? 'text-green-300' : 'text-red-300'}`}>
                                    {selectedNode.sentiment > 0 ? '+' : ''}{selectedNode.sentiment.toFixed(2)}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Themes */}
                    <div className="mb-6">
                        <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-3">Dominant Themes</h3>
                        <div className="flex flex-wrap gap-2">
                            {selectedNode.themes.map((theme) => (
                                <span key={theme} className="px-2.5 py-1 rounded bg-gray-800/80 text-gray-300 text-xs border border-gray-700/50 font-medium">
                                    {theme}
                                </span>
                            ))}
                        </div>
                    </div>

                    {/* Intelligence Metrics */}
                    <div className="space-y-5">
                        {/* Volume Metrics */}
                        <div>
                            <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-3">Volume Metrics</h3>
                            <div className="space-y-2 text-xs">
                                <div className="flex justify-between items-center">
                                    <span className="text-gray-400">Total Mentions</span>
                                    <span className="text-white font-semibold">{Math.round(selectedNode.intensity * 12547)}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-gray-400">Unique Sources</span>
                                    <span className="text-white font-semibold">{Math.round(selectedNode.intensity * 342)}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-gray-400">Velocity (per hour)</span>
                                    <span className="text-cyan-400 font-semibold">+{Math.round(selectedNode.intensity * 87)}</span>
                                </div>
                            </div>
                        </div>

                        {/* Key Actors */}
                        <div>
                            <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-3">Key Actors</h3>
                            <div className="space-y-1.5 text-xs">
                                <div className="flex items-center gap-2">
                                    <div className="w-1 h-1 rounded-full bg-blue-400"></div>
                                    <span className="text-gray-300">Government Officials (42%)</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-1 h-1 rounded-full bg-purple-400"></div>
                                    <span className="text-gray-300">Media Outlets (28%)</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-1 h-1 rounded-full bg-green-400"></div>
                                    <span className="text-gray-300">International Orgs (18%)</span>
                                </div>
                                <div className="text-[10px] text-gray-500 mt-2">Placeholder data - GDELT integration pending</div>
                            </div>
                        </div>

                        {/* Source Diversity */}
                        <div>
                            <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-3">Source Diversity</h3>
                            <div className="h-1.5 bg-gray-800/50 rounded-full overflow-hidden">
                                <div className="h-full bg-gradient-to-r from-blue-500 to-purple-500" style={{ width: `${selectedNode.intensity * 75}%` }}></div>
                            </div>
                            <div className="flex justify-between text-[10px] text-gray-500 mt-1.5">
                                <span>Echo Chamber</span>
                                <span>High Diversity</span>
                            </div>
                        </div>

                        {/* Timeline Placeholder */}
                        <div>
                            <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-3">Activity Timeline</h3>
                            <div className="bg-gray-900/50 border border-gray-800/50 rounded p-4 text-center">
                                <div className="text-xs text-gray-500 mb-2">Sparkline visualization</div>
                                <div className="text-[10px] text-gray-600">Coming soon: 24h intensity graph</div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default RadarSidebar;
