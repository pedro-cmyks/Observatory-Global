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
            className="fixed top-0 right-0 h-screen w-96 overflow-y-auto transition-transform duration-300 ease-in-out font-sans"
            style={{
                zIndex: 10000,
                pointerEvents: isOpen ? 'auto' : 'none',
                transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
                background: '#0f172a', // Solid dark slate background
                borderLeft: '1px solid #1e293b',
                boxShadow: '-4px 0 24px rgba(0, 0, 0, 0.5)'
            }}
        >
            {/* Close Button */}
            {isOpen && (
                <button
                    onClick={() => selectNode(null)}
                    className="absolute top-4 right-4 z-50 p-2 rounded-full hover:bg-gray-800 transition-colors text-gray-400 hover:text-white"
                    aria-label="Close sidebar"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            )}

            {selectedNode && (
                <div className="p-6 pt-16">
                    {/* Header */}
                    <div className="mb-8">
                        <div className="text-[10px] font-medium text-blue-400 tracking-widest uppercase mb-2">
                            Signal Intelligence • {selectedNode.id}
                        </div>
                        <h2 className="text-3xl font-bold text-white mb-6 leading-tight">
                            {selectedNode.name}
                        </h2>

                        <div className="grid grid-cols-2 gap-4">
                            {/* Intensity Card */}
                            <div className="bg-slate-900 rounded p-4 border border-slate-800">
                                <div className="text-slate-400 text-[10px] uppercase tracking-wider font-semibold mb-1">Intensity</div>
                                <div className="text-2xl font-bold text-white">
                                    {(selectedNode.intensity * 100).toFixed(0)}<span className="text-sm text-slate-500 ml-1">%</span>
                                </div>
                                <div className="w-full bg-slate-800 h-1 mt-3 rounded-full overflow-hidden">
                                    <div className="bg-blue-500 h-full rounded-full" style={{ width: `${selectedNode.intensity * 100}%` }}></div>
                                </div>
                            </div>

                            {/* Sentiment Card */}
                            <div className="bg-slate-900 rounded p-4 border border-slate-800">
                                <div className="text-slate-400 text-[10px] uppercase tracking-wider font-semibold mb-1">Sentiment</div>
                                <div className={`text-2xl font-bold ${selectedNode.sentiment >= 0 ? 'text-emerald-400' : 'text-rose-400'
                                    }`}>
                                    {selectedNode.sentiment > 0 ? '+' : ''}{selectedNode.sentiment.toFixed(2)}
                                </div>
                                <div className="w-full bg-slate-800 h-1 mt-3 rounded-full overflow-hidden">
                                    <div className={`h-full rounded-full ${selectedNode.sentiment >= 0 ? 'bg-emerald-500' : 'bg-rose-500'
                                        }`} style={{ width: `${Math.abs(selectedNode.sentiment) * 100}%` }}></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-8">
                        {/* Volume Metrics */}
                        <div>
                            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">
                                Volume Metrics
                            </h3>
                            <div className="bg-slate-900/50 rounded border border-slate-800 p-4 grid grid-cols-2 gap-4">
                                <div>
                                    <div className="text-[10px] text-slate-500 mb-1">Total Mentions</div>
                                    <div className="text-lg font-mono text-slate-200">
                                        {(selectedNode.intensity * 15000).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-[10px] text-slate-500 mb-1">Active Sources</div>
                                    <div className="text-lg font-mono text-slate-200">
                                        {selectedNode.sourceCount || Math.round(selectedNode.intensity * 200)}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Dominant Themes */}
                        <div>
                            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">
                                Dominant Themes
                            </h3>
                            {selectedNode.topThemes && selectedNode.topThemes.length > 0 ? (
                                <div className="space-y-3">
                                    {selectedNode.topThemes.map((theme, idx) => (
                                        <div key={idx} className="flex items-center justify-between text-sm">
                                            <span className="text-slate-300">{theme.label}</span>
                                            <div className="flex items-center gap-3">
                                                <div className="w-20 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-purple-500 rounded-full"
                                                        style={{ width: `${Math.min((theme.count / (selectedNode.topThemes![0].count || 1)) * 100, 100)}%` }}
                                                    ></div>
                                                </div>
                                                <span className="text-slate-500 font-mono text-xs w-6 text-right">{theme.count}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="flex flex-wrap gap-2">
                                    {selectedNode.themes.map((theme) => (
                                        <span key={theme} className="px-2 py-1 rounded bg-slate-800 text-slate-300 text-xs">
                                            {theme}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Key Actors */}
                        <div>
                            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">
                                Key Actors
                            </h3>
                            {selectedNode.keyActors && selectedNode.keyActors.length > 0 ? (
                                <div className="grid grid-cols-1 gap-2">
                                    {selectedNode.keyActors.map((actor, idx) => (
                                        <div key={idx} className="flex items-center justify-between py-2 border-b border-slate-800/50 last:border-0">
                                            <div className="flex items-center gap-3">
                                                <div className="w-5 h-5 rounded bg-slate-800 flex items-center justify-center text-[10px] text-slate-400 font-bold">
                                                    {actor.name.charAt(0)}
                                                </div>
                                                <span className="text-slate-300 text-sm">{actor.name}</span>
                                            </div>
                                            <span className="text-slate-500 font-mono text-xs">{actor.count}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-xs text-slate-500 italic">No key actors identified</div>
                            )}
                        </div>

                        {/* Source Intelligence */}
                        <div>
                            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">
                                Source Intelligence
                            </h3>

                            <div className="bg-slate-900/50 rounded border border-slate-800 p-4">
                                {/* Diversity Meter */}
                                <div className="mb-4">
                                    <div className="flex justify-between items-end mb-2">
                                        <span className="text-[10px] text-slate-500">Diversity Score</span>
                                        <span className={`text-xs font-bold font-mono ${selectedNode.sourceDiversity > 0.7 ? 'text-emerald-400' :
                                                selectedNode.sourceDiversity > 0.4 ? 'text-yellow-400' : 'text-red-400'
                                            }`}>
                                            {(selectedNode.sourceDiversity * 100).toFixed(0)}/100
                                        </span>
                                    </div>
                                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full rounded-full ${selectedNode.sourceDiversity > 0.7 ? 'bg-emerald-500' :
                                                    selectedNode.sourceDiversity > 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                                                }`}
                                            style={{ width: `${selectedNode.sourceDiversity * 100}%` }}
                                        ></div>
                                    </div>
                                </div>

                                {/* Top Sources */}
                                {selectedNode.topSources && selectedNode.topSources.length > 0 && (
                                    <div>
                                        <div className="text-[10px] text-slate-500 mb-2">Top Outlets</div>
                                        <div className="flex flex-wrap gap-2">
                                            {selectedNode.topSources.map((source, idx) => (
                                                <a
                                                    key={idx}
                                                    href={`https://${source}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-[10px] px-2 py-1 rounded bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                                                >
                                                    {source}
                                                </a>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Timeline */}
                        <div className="pt-2">
                            <div className="flex items-center justify-between mb-2">
                                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                                    Activity Timeline
                                </h3>
                                <div className="bg-red-500/10 text-red-400 text-[9px] px-1.5 py-0.5 rounded flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
                                    LIVE (15m)
                                </div>
                            </div>

                            <div className="h-16 border-b border-l border-slate-800 relative bg-gradient-to-t from-slate-900/50 to-transparent">
                                {/* Sparkline */}
                                <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
                                    <path
                                        d="M0,50 Q10,45 20,48 T40,40 T60,35 T80,45 T100,30 T120,38 T140,25 T160,35 T180,20 T200,40 T220,25 T240,35 T260,15 T280,30 T300,20"
                                        fill="none"
                                        stroke="#3b82f6"
                                        strokeWidth="2"
                                        strokeOpacity="0.5"
                                    />
                                    <path
                                        d="M0,50 Q10,45 20,48 T40,40 T60,35 T80,45 T100,30 T120,38 T140,25 T160,35 T180,20 T200,40 T220,25 T240,35 T260,15 T280,30 T300,20 V64 H0 Z"
                                        fill="url(#gradient)"
                                        opacity="0.1"
                                    />
                                    <defs>
                                        <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                            <stop offset="0%" stopColor="#3b82f6" />
                                            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                                        </linearGradient>
                                    </defs>
                                </svg>
                            </div>
                            <div className="flex justify-between text-[9px] text-slate-600 mt-1 font-mono">
                                <span>-24h</span>
                                <span>Now</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default RadarSidebar;
