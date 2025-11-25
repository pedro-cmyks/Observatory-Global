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
        <div
            className="absolute flex items-center gap-6 bg-black/60 backdrop-blur-md border border-gray-700/50 px-6 py-3 rounded-full shadow-2xl"
            style={{
                zIndex: 1000,
                bottom: '2rem',
                left: '50%',
                transform: 'translateX(-50%)'
            }}
        >

            {/* Time Window Segmented Control */}
            <div className="flex items-center bg-gray-900/50 rounded-full p-1 border border-gray-800">
                {(['1h', '6h', '12h', '24h'] as const).map((window) => (
                    <button
                        key={window}
                        onClick={() => setTimeWindow(window)}
                        className={`
                            px-4 py-1.5 text-xs font-medium rounded-full transition-all duration-200
                            ${timeWindow === window
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/40'
                                : 'text-gray-400 hover:text-white hover:bg-gray-800'
                            }
                        `}
                    >
                        {window}
                    </button>
                ))}
            </div>

            {/* Vertical Separator */}
            <div className="w-px h-8 bg-gray-700/50"></div>

            {/* Layer Toggles */}
            <div className="flex items-center gap-4">
                <LayerToggle
                    label="Heatmap"
                    active={activeLayers.heatmap}
                    onClick={() => toggleLayer('heatmap')}
                    color="text-pink-500"
                />
                <LayerToggle
                    label="Flows"
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

            {isLoading && (
                <div className="absolute -top-3 right-0 w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            )}
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
            flex items-center gap-2 text-xs font-medium transition-all duration-200
            ${active ? 'text-white' : 'text-gray-500 hover:text-gray-300'}
        `}
    >
        <div className={`
            w-2 h-2 rounded-full shadow-[0_0_8px_currentColor] transition-all duration-300
            ${active ? `bg-current ${color}` : 'bg-gray-600 shadow-none'}
        `}></div>
        {label}
    </button>
);

export default RadarControls;
