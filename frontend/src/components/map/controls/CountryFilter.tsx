import React, { useState, useMemo } from 'react'
import { useMapStore } from '../../../store/mapStore'

const CountryFilter: React.FC = () => {
  const { flowsData, selectedCountries, setSelectedCountries, toggleCountry } = useMapStore()
  const [isOpen, setIsOpen] = useState(false)

  const countries = useMemo(() => {
    if (!flowsData?.hotspots) return []
    return flowsData.hotspots
      .filter((h) => h.country_code && h.country_name) // Filter out invalid entries
      .map((h) => ({
        code: h.country_code,
        name: h.country_name,
      }))
      .sort((a, b) => {
        // Defensive sorting with null checks
        const nameA = a.name || ''
        const nameB = b.name || ''
        return nameA.localeCompare(nameB)
      })
  }, [flowsData])

  const handleSelectAll = () => {
    setSelectedCountries(countries.map((c) => c.code))
  }

  const handleClearAll = () => {
    setSelectedCountries([])
  }

  return (
    <div
      style={{
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderRadius: '8px',
        padding: '0.75rem',
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
        minWidth: '200px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '0.5rem',
        }}
      >
        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#333' }}>
          Countries {selectedCountries.length > 0 && `(${selectedCountries.length})`}
        </div>
        <button
          onClick={() => setIsOpen(!isOpen)}
          style={{
            padding: '0.2rem 0.5rem',
            fontSize: '0.7rem',
            backgroundColor: '#f0f0f0',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          {isOpen ? '▲' : '▼'}
        </button>
      </div>

      {isOpen && (
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <button
              onClick={handleSelectAll}
              style={{
                flex: 1,
                padding: '0.3rem',
                fontSize: '0.7rem',
                backgroundColor: '#f0f0f0',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Select All
            </button>
            <button
              onClick={handleClearAll}
              style={{
                flex: 1,
                padding: '0.3rem',
                fontSize: '0.7rem',
                backgroundColor: '#f0f0f0',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Clear
            </button>
          </div>

          {countries.map((country) => (
            <label
              key={country.code}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.3rem 0',
                fontSize: '0.75rem',
                cursor: 'pointer',
              }}
            >
              <input
                type="checkbox"
                checked={selectedCountries.includes(country.code)}
                onChange={() => toggleCountry(country.code)}
                style={{ cursor: 'pointer' }}
              />
              <span>
                {country.code} - {country.name}
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

export default CountryFilter
