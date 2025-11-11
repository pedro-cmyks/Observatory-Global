import React from 'react'

interface CountryPickerProps {
  selectedCountry: string
  onCountryChange: (country: string) => void
  disabled?: boolean
}

const COUNTRIES = [
  { code: 'US', name: 'United States' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'CO', name: 'Colombia' },
  { code: 'BR', name: 'Brazil' },
  { code: 'MX', name: 'Mexico' },
  { code: 'AR', name: 'Argentina' },
  { code: 'ES', name: 'Spain' },
  { code: 'FR', name: 'France' },
  { code: 'DE', name: 'Germany' },
  { code: 'IT', name: 'Italy' },
  { code: 'JP', name: 'Japan' },
  { code: 'KR', name: 'South Korea' },
  { code: 'AU', name: 'Australia' },
  { code: 'CA', name: 'Canada' },
  { code: 'IN', name: 'India' },
]

const CountryPicker: React.FC<CountryPickerProps> = ({
  selectedCountry,
  onCountryChange,
  disabled = false,
}) => {
  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <label
        htmlFor="country-select"
        style={{
          display: 'block',
          marginBottom: '0.5rem',
          fontWeight: 600,
          fontSize: '1rem',
        }}
      >
        Select Country:
      </label>
      <select
        id="country-select"
        value={selectedCountry}
        onChange={(e) => onCountryChange(e.target.value)}
        disabled={disabled}
        style={{
          width: '100%',
          maxWidth: '300px',
          padding: '0.6rem 1rem',
          fontSize: '1rem',
          border: '1px solid #ccc',
          borderRadius: '8px',
          backgroundColor: disabled ? '#f5f5f5' : 'white',
          cursor: disabled ? 'not-allowed' : 'pointer',
          color: '#213547',
        }}
      >
        {COUNTRIES.map((country) => (
          <option key={country.code} value={country.code}>
            {country.name} ({country.code})
          </option>
        ))}
      </select>
    </div>
  )
}

export default CountryPicker
