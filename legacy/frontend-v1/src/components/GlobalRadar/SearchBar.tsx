import React, { useState, useEffect, useRef } from 'react';
import { useRadarStore } from '../../store/radarStore';

interface SearchResult {
    themes: Array<{ code: string; signal_count: number; total_mentions: number }>;
    entities: Array<{ name: string; type: string; signal_count: number; total_mentions: number }>;
    countries: Array<{ code: string; name: string; lat: number; lon: number }>;
}

export const SearchBar: React.FC = () => {
    const { searchQuery, setSearchQuery, selectNode, setTopicFilter } = useRadarStore();
    const [localValue, setLocalValue] = useState(searchQuery);
    const [isSearching, setIsSearching] = useState(false);
    const [searchResults, setSearchResults] = useState<SearchResult | null>(null);
    const [showResults, setShowResults] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Handle clicks outside dropdown to close it
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setShowResults(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Debounced search function
    useEffect(() => {
        if (!localValue || localValue.length < 2) {
            setSearchResults(null);
            setShowResults(false);
            return;
        }

        const timeoutId = setTimeout(async () => {
            setIsSearching(true);
            try {
                const response = await fetch(
                    `http://localhost:8080/v1/search?q=${encodeURIComponent(localValue)}`
                );
                if (response.ok) {
                    const data = await response.json();
                    setSearchResults(data.results);
                    setShowResults(true);
                }
            } catch (error) {
                console.error('Search error:', error);
            } finally {
                setIsSearching(false);
            }
        }, 300);

        return () => clearTimeout(timeoutId);
    }, [localValue]);

    const handleSelectCountry = (country: { code: string; name: string; lat: number; lon: number }) => {
        selectNode({
            id: country.code,
            name: country.name,
            lat: country.lat,
            lon: country.lon,
            intensity: 1,
            sentiment: 0,
            themes: [],
            sourceCount: 0,
            sourceDiversity: 0,
            topSources: [],
            keyActors: [],
            topThemes: []
        });
        setShowResults(false);
        setLocalValue('');
    };

    const handleSelectTheme = (theme: string) => {
        setTopicFilter(theme);
        setShowResults(false);
        setLocalValue(theme);
    };

    const totalResults = searchResults
        ? searchResults.themes.length + searchResults.entities.length + searchResults.countries.length
        : 0;

    return (
        <div className="absolute top-6 left-1/2 transform -translate-x-1/2 z-50 w-full max-w-md px-4" ref={dropdownRef}>
            <form onSubmit={(e) => { e.preventDefault(); }} className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    {isSearching ? (
                        <svg className="animate-spin h-4 w-4 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                    ) : (
                        <svg className="h-4 w-4 text-gray-400 group-focus-within:text-blue-400 transition-colors" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    )}
                </div>
                <input
                    type="text"
                    value={localValue}
                    onChange={(e) => setLocalValue(e.target.value)}
                    className="block w-full pl-10 pr-3 py-2.5 border border-gray-700 rounded-lg leading-5 bg-gray-900/80 text-gray-300 placeholder-gray-500 focus:outline-none focus:bg-gray-900 focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 sm:text-sm backdrop-blur-md transition-all shadow-lg hover:bg-gray-800/80"
                    placeholder="Search themes, countries, or actors..."
                />
                {localValue && (
                    <button
                        type="button"
                        onClick={() => {
                            setLocalValue('');
                            setSearchQuery('');
                            setShowResults(false);
                        }}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-white transition-colors"
                    >
                        <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                )}
            </form>

            {/* Search Results Dropdown */}
            {showResults && searchResults && totalResults > 0 && (
                <div className="absolute w-full mt-2 bg-gray-900/95 backdrop-blur-lg border border-gray-700 rounded-lg shadow-2xl max-h-96 overflow-y-auto">
                    {/* Countries */}
                    {searchResults.countries.length > 0 && (
                        <div className="p-2 border-b border-gray-800">
                            <div className="text-xs font-bold text-gray-400 uppercase tracking-wider px-2 py-1">Countries</div>
                            {searchResults.countries.slice(0, 5).map((country) => (
                                <button
                                    key={country.code}
                                    onClick={() => handleSelectCountry(country)}
                                    className="w-full text-left px-3 py-2 rounded hover:bg-gray-800 transition-colors text-sm text-gray-300 flex items-center gap-2"
                                >
                                    <span className="text-blue-400 font-mono">{country.code}</span>
                                    <span>{country.name}</span>
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Themes */}
                    {searchResults.themes.length > 0 && (
                        <div className="p-2 border-b border-gray-800">
                            <div className="text-xs font-bold text-gray-400 uppercase tracking-wider px-2 py-1">Themes</div>
                            {searchResults.themes.slice(0, 5).map((theme) => (
                                <button
                                    key={theme.code}
                                    onClick={() => handleSelectTheme(theme.code)}
                                    className="w-full text-left px-3 py-2 rounded hover:bg-gray-800 transition-colors text-sm text-gray-300"
                                >
                                    <div className="flex justify-between items-center">
                                        <span className="text-cyan-400 font-mono text-xs">{theme.code}</span>
                                        <span className="text-xs text-gray-500">{theme.signal_count} signals</span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Entities */}
                    {searchResults.entities.length > 0 && (
                        <div className="p-2">
                            <div className="text-xs font-bold text-gray-400 uppercase tracking-wider px-2 py-1">Actors</div>
                            {searchResults.entities.slice(0, 5).map((entity, idx) => (
                                <div
                                    key={`${entity.name}-${idx}`}
                                    className="px-3 py-2 rounded text-sm text-gray-300"
                                >
                                    <div className="flex justify-between items-center">
                                        <div>
                                            <span className="text-green-400">{entity.name}</span>
                                            <span className="text-xs text-gray-500 ml-2">({entity.type})</span>
                                        </div>
                                        <span className="text-xs text-gray-500">{entity.signal_count} mentions</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};
