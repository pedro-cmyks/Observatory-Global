import React from 'react';
import { useRadarStore } from '../../store/radarStore';

const RadarControls: React.FC = () => {
    const timeWindow = useRadarStore((state) => state.timeWindow);
    const setTimeWindow = useRadarStore((state) => state.setTimeWindow);
    const activeLayers = useRadarStore((state) => state.activeLayers);
    const toggleLayer = useRadarStore((state) => state.toggleLayer);
    const isLoading = useRadarStore((state) => state.isLoading);

    return (
        <div
            className="flex items-center gap-4 bg-black/90 backdrop-blur-xl border border-cyan-900/30 px-5 py-2.5 rounded-full shadow-[0_0_20px_rgba(6,182,212,0.15)]"
            style={{
                position: 'fixed',
                zIndex: 9999,
                bottom: '1.5rem',
                left: '50%',
                transform: 'translateX(-50%)',
                pointerEvents: 'auto'
            }}
        >
            {/* Loading Indicator */}
            {isLoading && (
                <div className="absolute -top-1 -right-1">
                    <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,211,238,0.8)]"></div>
                </div>
            )}

            {/* Time Window Segmented Control */}
            <div className="flex items-center bg-gray-900/80 rounded-full p-0.5 border border-gray-800/50">
                {(['1h', '6h', '12h', '24h', 'all'] as const).map((window) => (
                    <button
                        key={window}
                        onClick={() => setTimeWindow(window)}
                        className={`
                            px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full transition-all duration-200
                            ${timeWindow === window
                                ? 'bg-cyan-600/90 text-white shadow-[0_0_10px_rgba(6,182,212,0.5)]'
                                : 'text-gray-500 hover:text-cyan-300 hover:bg-gray-800/50'
                            }
                        `}
                    >
                        {window}
                    </button>
                ))}
            </div>

            {/* Vertical Separator */}
            <div className="w-px h-6 bg-cyan-900/30"></div>

            {/* Layer Toggles */}
            <div className="flex items-center gap-3">
                <LayerToggle
                    label="Heat"
                    active={activeLayers.heatmap}
                    onClick={() => toggleLayer('heatmap')}
                    color="text-orange-400"
                />
                <LayerToggle
                    label="Flow"
                    active={activeLayers.flows}
                    onClick={() => toggleLayer('flows')}
                    color="text-cyan-400"
                />
                <LayerToggle
                    label="Nodes"
                    active={activeLayers.nodes}
                    onClick={() => toggleLayer('nodes')}
                    color="text-green-400"
                />
            </div>
        </div>
    );
};

const LayerToggle: React.FC<{
    label: string;
    active: boolean;
    onClick: () => void;
    color: string;
}> = ({ label, active, onClick, color }) => (
    <button
        onClick={onClick}
        className={`
            flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider transition-all duration-200
            ${active ? `${color}` : 'text-gray-600 hover:text-gray-400'}
        `}
    >
        <div className={`
            w-1.5 h-1.5 rounded-full transition-all duration-300
            ${active ? `bg-current shadow-[0_0_6px_currentColor]` : 'bg-gray-700 shadow-none'}
        `}></div>
        {label}
    </button>
);

export default RadarControls;
