export interface Chokepoint {
  id: string
  name: string
  lat: number
  lon: number
  radiusKm: number
  primaryCountry: string
  countries: string[]
  description: string
}

export const CHOKEPOINTS: Chokepoint[] = [
  {
    id: 'hormuz',
    name: 'Strait of Hormuz',
    lat: 26.6, lon: 56.5, radiusKm: 130,
    primaryCountry: 'IR',
    countries: ['IR', 'AE', 'OM', 'SA'],
    description: 'Persian Gulf exit · 20% of global oil transit',
  },
  {
    id: 'bosphorus',
    name: 'Bosphorus',
    lat: 41.1, lon: 29.0, radiusKm: 80,
    primaryCountry: 'TR',
    countries: ['TR', 'RU', 'UA'],
    description: 'Black Sea gateway · grain & military transit',
  },
  {
    id: 'suez',
    name: 'Suez Canal',
    lat: 30.4, lon: 32.4, radiusKm: 110,
    primaryCountry: 'EG',
    countries: ['EG'],
    description: 'Asia–Europe shortcut · 12% of global trade',
  },
  {
    id: 'bab_el_mandeb',
    name: 'Bab-el-Mandeb',
    lat: 12.6, lon: 43.4, radiusKm: 140,
    primaryCountry: 'YE',
    countries: ['YE', 'DJ', 'ER', 'SA'],
    description: 'Red Sea south · Houthi attack corridor',
  },
  {
    id: 'malacca',
    name: 'Strait of Malacca',
    lat: 2.5, lon: 101.5, radiusKm: 260,
    primaryCountry: 'SG',
    countries: ['SG', 'MY', 'ID'],
    description: 'Asia-Pacific corridor · 25% of global trade',
  },
  {
    id: 'taiwan',
    name: 'Taiwan Strait',
    lat: 24.5, lon: 120.5, radiusKm: 190,
    primaryCountry: 'TW',
    countries: ['TW', 'CN'],
    description: 'China–Taiwan military flashpoint',
  },
  {
    id: 'panama',
    name: 'Panama Canal',
    lat: 9.0, lon: -79.5, radiusKm: 85,
    primaryCountry: 'PA',
    countries: ['PA', 'US'],
    description: 'Atlantic–Pacific connector · drought risk',
  },
  {
    id: 'good_hope',
    name: 'Cape of Good Hope',
    lat: -34.0, lon: 18.5, radiusKm: 220,
    primaryCountry: 'ZA',
    countries: ['ZA'],
    description: 'Suez bypass route · active since Houthi crisis',
  },
  {
    id: 'english_channel',
    name: 'English Channel',
    lat: 51.0, lon: 1.5, radiusKm: 230,
    primaryCountry: 'GB',
    countries: ['GB', 'FR', 'BE', 'NL'],
    description: "Europe's busiest sea lane",
  },
  {
    id: 'south_china_sea',
    name: 'South China Sea',
    lat: 7.0, lon: 113.0, radiusKm: 650,
    primaryCountry: 'CN',
    countries: ['CN', 'VN', 'PH', 'MY'],
    description: 'Contested waters · $5T annual trade',
  },
]

// Which chokepoints are geopolitically linked to a given ISO country code
export const COUNTRY_CHOKEPOINTS: Record<string, string[]> = {
  IR: ['hormuz', 'bab_el_mandeb'],
  AE: ['hormuz'],
  OM: ['hormuz'],
  SA: ['hormuz', 'bab_el_mandeb'],
  TR: ['bosphorus'],
  RU: ['bosphorus'],
  UA: ['bosphorus'],
  EG: ['suez'],
  YE: ['bab_el_mandeb'],
  DJ: ['bab_el_mandeb'],
  ER: ['bab_el_mandeb'],
  SG: ['malacca'],
  MY: ['malacca', 'south_china_sea'],
  ID: ['malacca'],
  TW: ['taiwan'],
  CN: ['taiwan', 'south_china_sea'],
  VN: ['south_china_sea'],
  PH: ['south_china_sea'],
  PA: ['panama'],
  US: ['panama'],
  ZA: ['good_hope'],
  GB: ['english_channel'],
  FR: ['english_channel'],
  BE: ['english_channel'],
  NL: ['english_channel'],
}

export function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

export function getChokepointVesselCounts(
  vessels: Array<{ latitude: number; longitude: number }>
): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const v of vessels) {
    for (const cp of CHOKEPOINTS) {
      if (haversineKm(v.latitude, v.longitude, cp.lat, cp.lon) < cp.radiusKm) {
        counts[cp.id] = (counts[cp.id] || 0) + 1
        break
      }
    }
  }
  return counts
}

export function getCountryChokepoints(countryCode: string | null): string[] {
  if (!countryCode) return []
  return COUNTRY_CHOKEPOINTS[countryCode.toUpperCase()] ?? []
}
