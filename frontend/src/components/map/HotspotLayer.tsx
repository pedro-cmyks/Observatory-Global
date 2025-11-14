import React, { useMemo } from 'react'
import { Marker } from 'react-map-gl'
import { motion } from 'framer-motion'
import { useMapStore } from '../../store/mapStore'
import { CountryHotspot } from '../../lib/mapTypes'

const getColorFromIntensity = (intensity: number): string => {
  if (intensity < 0.3) return '#3B82F6' // Cool blue
  if (intensity < 0.6) return '#FCD34D' // Warm yellow
  return '#EF4444' // Hot red
}

const getSizeFromTopicCount = (count: number): number => {
  // Scale from 20px to 60px based on topic count
  const minSize = 20
  const maxSize = 60
  const minCount = 0
  const maxCount = 300

  const normalized = Math.min(Math.max((count - minCount) / (maxCount - minCount), 0), 1)
  return minSize + normalized * (maxSize - minSize)
}

const HotspotMarker: React.FC<{ hotspot: CountryHotspot }> = ({ hotspot }) => {
  const { setSelectedHotspot, selectedCountries } = useMapStore()

  // Validate coordinates before rendering
  const hasValidCoordinates =
    typeof hotspot.latitude === 'number' &&
    typeof hotspot.longitude === 'number' &&
    isFinite(hotspot.latitude) &&
    isFinite(hotspot.longitude) &&
    hotspot.latitude >= -90 &&
    hotspot.latitude <= 90 &&
    hotspot.longitude >= -180 &&
    hotspot.longitude <= 180

  if (!hasValidCoordinates) {
    console.warn(`Invalid coordinates for hotspot ${hotspot.country_code}:`, {
      lat: hotspot.latitude,
      lng: hotspot.longitude,
    })
    return null
  }

  const size = getSizeFromTopicCount(hotspot.topic_count)
  const color = getColorFromIntensity(hotspot.intensity)

  // Filter by selected countries
  const isFiltered =
    selectedCountries.length > 0 && !selectedCountries.includes(hotspot.country_code)

  if (isFiltered) return null

  return (
    <Marker longitude={hotspot.longitude} latitude={hotspot.latitude}>
      <motion.div
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 0.8 }}
        whileHover={{ scale: 1.2, opacity: 1 }}
        transition={{ duration: 0.3 }}
        onClick={() => setSelectedHotspot(hotspot)}
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          backgroundColor: color,
          border: '2px solid white',
          boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '10px',
          fontWeight: 'bold',
          color: 'white',
        }}
      >
        {hotspot.country_code}
      </motion.div>
    </Marker>
  )
}

const HotspotLayer: React.FC = () => {
  const { flowsData } = useMapStore()

  const hotspots = useMemo(() => {
    return flowsData?.hotspots || []
  }, [flowsData])

  return (
    <>
      {hotspots.map((hotspot) => (
        <HotspotMarker key={hotspot.country_code} hotspot={hotspot} />
      ))}
    </>
  )
}

export default HotspotLayer
