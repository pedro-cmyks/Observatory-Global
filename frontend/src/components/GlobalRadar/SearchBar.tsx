import React, { useState, useEffect } from 'react';
import { useRadarStore } from '../../store/radarStore';

export const SearchBar: React.FC = () => {
    const { searchQuery, setSearchQuery } = useRadarStore();
    const [localValue, setLocalValue] = useState(searchQuery);

    // Sync local state with store (in case store is updated elsewhere)
    useEffect(() => {
        setLocalValue(searchQuery);
    }, [searchQuery]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setSearchQuery(localValue);
    };

    return (
        <div className="absolute top-6 left-1/2 transform -translate-x-1/2 z-50 w-full max-w-md px-4">
            <form onSubmit={handleSubmit} className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <svg className="h-4 w-4 text-gray-400 group-focus-within:text-blue-400 transition-colors" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
                <input
                    type="text"
                    value={localValue}
                    onChange={(e) => setLocalValue(e.target.value)}
                    className="block w-full pl-10 pr-3 py-2.5 border border-gray-700 rounded-lg leading-5 bg-gray-900/80 text-gray-300 placeholder-gray-500 focus:outline-none focus:bg-gray-900 focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 sm:text-sm backdrop-blur-md transition-all shadow-lg hover:bg-gray-800/80"
                    placeholder="Filter by topic, entity, or keyword..."
                />
                {localValue && (
                    <button
                        type="button"
                        onClick={() => {
                            setLocalValue('');
                            setSearchQuery('');
                        }}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-white transition-colors"
                    >
                        <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                )}
            </form>
        </div>
    );
};
