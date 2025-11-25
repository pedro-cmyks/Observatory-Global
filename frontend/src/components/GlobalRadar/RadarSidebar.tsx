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
            className="fixed top-0 right-0 h-screen w-96 overflow-y-auto transition-transform duration-300 ease-in-out"
            style={{
                zIndex: 10000,
                pointerEvents: isOpen ? 'auto' : 'none',
                transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
                background: 'linear-gradient(to left, rgba(0, 0, 0, 0.95), rgba(10, 10, 15, 0.92))',
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
                borderLeft: '1px solid rgba(75, 85, 99, 0.3)',
                boxShadow: '-4px 0 24px rgba(0, 0, 0, 0.5)'
            }}
        >
            {/* Close Button */}
            {isOpen && (
                <button
                    onClick={() => {
                        console.log('🟢 SIDEBAR: Close button clicked');
                        selectNode(null);
                    }}
                    className="absolute top-4 right-4 z-50 group"
                    style={{
                        background: 'rgba(55, 65, 81, 0.4)',
                        borderRadius: '50%',
                        padding: '8px',
                        border: '1px solid rgba(156, 163, 175, 0.2)',
                        transition: 'all 0.2s ease'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(75, 85, 99, 0.6)';
                        e.currentTarget.style.borderColor = 'rgba(156, 163, 175, 0.4)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(55, 65, 81, 0.4)';
                        e.currentTarget.style.borderColor = 'rgba(156, 163, 175, 0.2)';
                    }}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="white" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            )}

            {selectedNode && (
                <div className="p-6 pt-16" style={{ background: 'rgba(0, 0, 0, 0.2)' }}>
                    {/* Header */}
                    <div className="mb-6 pb-5" style={{ borderBottom: '1px solid rgba(75, 85, 99, 0.3)' }}>
                        <h2 className="text-2xl font-bold mb-4 text-white" style={{ textShadow: '0 2px 8px rgba(0,0,0,0.8)' }}>{selectedNode.name}</h2>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                            <div style={{
                                background: 'rgba(30, 58, 138, 0.3)',
                                border: '1px solid rgba(59, 130, 246, 0.4)',
                                borderRadius: '6px',
                                padding: '12px',
                                backdropFilter: 'blur(10px)'
                            }}>
                                <div className="text-blue-300 uppercase tracking-wider mb-1 font-semibold" style={{ fontSize: '9px' }}>Intensity</div>
                                <div className="text-blue-200 font-bold text-lg">{(selectedNode.intensity * 100).toFixed(0)}%</div>
                            </div>
                            <div style={{
                                background: selectedNode.sentiment > 0
                                    ? 'rgba(6, 78, 59, 0.3)'
                                    : 'rgba(127, 29, 29, 0.3)',
                                border: selectedNode.sentiment > 0
                                    ? '1px solid rgba(34, 197, 94, 0.4)'
                                    : '1px solid rgba(239, 68, 68, 0.4)',
                                borderRadius: '6px',
                                padding: '12px',
                                backdropFilter: 'blur(10px)'
                            }}>
                                <div className={`uppercase tracking-wider mb-1 font-semibold ${selectedNode.sentiment > 0 ? 'text-green-300' : 'text-red-300'}`} style={{ fontSize: '9px' }}>Sentiment</div>
                                <div className={`font-bold text-lg ${selectedNode.sentiment > 0 ? 'text-green-200' : 'text-red-200'}`}>
                                    {selectedNode.sentiment > 0 ? '+' : ''}{selectedNode.sentiment.toFixed(2)}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Themes */}
                    <div className="mb-6 p-4" style={{
                        background: 'rgba(17, 24, 39, 0.4)',
                        borderRadius: '8px',
                        border: '1px solid rgba(55, 65, 81, 0.3)'
                    }}>
                        <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">Dominant Themes</h3>
                        <div className="flex flex-wrap gap-2">
                            {selectedNode.themes.map((theme) => (
                                <span key={theme} style={{
                                    padding: '6px 10px',
                                    borderRadius: '4px',
                                    background: 'rgba(55, 65, 81, 0.5)',
                                    color: 'rgb(209, 213, 219)',
                                    fontSize: '11px',
                                    border: '1px solid rgba(75, 85, 99, 0.4)',
                                    fontWeight: 500
                                }}>
                                    {theme}
                                </span>
                            ))}
                        </div>
                    </div>

                    {/* Intelligence Metrics */}
                    <div className="space-y-5">
                        {/* Volume Metrics */}
                        <div className="p-4" style={{
                            background: 'rgba(17, 24, 39, 0.4)',
                            borderRadius: '8px',
                            border: '1px solid rgba(55, 65, 81, 0.3)'
                        }}>
                            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">Volume Metrics</h3>
                            <div className="space-y-2 text-xs">
                                <div className="flex justify-between items-center py-1">
                                    <span className="text-gray-300">Total Mentions</span>
                                    <span className="text-white font-semibold">{Math.round(selectedNode.intensity * 12547)}</span>
                                </div>
                                <div className="flex justify-between items-center py-1">
                                    <span className="text-gray-300">Unique Sources</span>
                                    <span className="text-white font-semibold">{Math.round(selectedNode.intensity * 342)}</span>
                                </div>
                                <div className="flex justify-between items-center py-1">
                                    <span className="text-gray-300">Velocity (per hour)</span>
                                    <span className="text-cyan-300 font-semibold">+{Math.round(selectedNode.intensity * 87)}</span>
                                </div>
                            </div>
                        </div>

                        {/* Key Actors */}
                        <div className="p-4" style={{
                            background: 'rgba(17, 24, 39, 0.4)',
                            borderRadius: '8px',
                            border: '1px solid rgba(55, 65, 81, 0.3)'
                        }}>
                            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">Key Actors</h3>
                            <div className="space-y-1.5 text-xs">
                                <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400" style={{ boxShadow: '0 0 4px rgba(96, 165, 250, 0.6)' }}></div>
                                    <span className="text-gray-200">Government Officials (42%)</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-purple-400" style={{ boxShadow: '0 0 4px rgba(192, 132, 252, 0.6)' }}></div>
                                    <span className="text-gray-200">Media Outlets (28%)</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-green-400" style={{ boxShadow: '0 0 4px rgba(74, 222, 128, 0.6)' }}></div>
                                    <span className="text-gray-200">International Orgs (18%)</span>
                                </div>
                                <div className="text-[10px] text-gray-500 mt-2 italic">Placeholder data - GDELT integration pending</div>
                            </div>
                        </div>

                        {/* Source Diversity */}
                        <div className="p-4" style={{
                            background: 'rgba(17, 24, 39, 0.4)',
                            borderRadius: '8px',
                            border: '1px solid rgba(55, 65, 81, 0.3)'
                        }}>
                            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">Source Diversity</h3>
                            <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(31, 41, 55, 0.6)' }}>
                                <div className="h-full bg-gradient-to-r from-blue-500 to-purple-500" style={{
                                    width: `${selectedNode.intensity * 75}%`,
                                    boxShadow: '0 0 8px rgba(147, 51, 234, 0.5)'
                                }}></div>
                            </div>
                            <div className="flex justify-between text-[10px] text-gray-400 mt-2">
                                <span>Echo Chamber</span>
                                <span>High Diversity</span>
                            </div>
                        </div>

                        {/* Timeline Placeholder */}
                        <div className="p-4" style={{
                            background: 'rgba(17, 24, 39, 0.4)',
                            borderRadius: '8px',
                            border: '1px solid rgba(55, 65, 81, 0.3)'
                        }}>
                            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">Activity Timeline</h3>
                            <div className="p-4 text-center" style={{
                                background: 'rgba(0, 0, 0, 0.3)',
                                borderRadius: '6px',
                                border: '1px solid rgba(55, 65, 81, 0.2)'
                            }}>
                                <div className="text-xs text-gray-400 mb-2">Sparkline visualization</div>
                                <div className="text-[10px] text-gray-500 italic">Coming soon: 24h intensity graph</div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default RadarSidebar;
