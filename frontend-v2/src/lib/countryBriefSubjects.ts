// Typed SUBJECTS for CountryBrief (#176 reframe).
//
// The panel used to ask "is this a person?" and drop the rest, so "El Niño"
// (climate), "República Dominicana" (a country in Spanish) and "America Latin"
// (a truncated GDELT region) vanished or posed as people. Model them as typed
// subjects instead — a person is one type; place/organization/group/event are
// others. Mirrors backend app/services/subjects.py (kept in sync by hand; the
// server also serves key_subjects, the eventual single source of truth).

export interface KeyPerson {
  name: string
  count: number
}

export type SubjectType = 'person' | 'organization' | 'group' | 'place' | 'event'

export interface KeySubject {
  name: string
  count: number
  type: SubjectType
}

const EVENT_NAMES = new Set([
  'el niño', 'la niña', 'el nino', 'la nina',
])

const ORG_NAMES = new Set([
  'bafana bafana', 'naciones unidas', 'united nations', 'union europea',
  'unión europea', 'european union', 'african union', 'union africana',
  'estado islamico', 'estado islámico', 'islamic state', 'el pais', 'el país',
])

const PLACE_NAMES = new Set([
  'america latina', 'america latin', 'latina america', 'latin america',
  'estados unidos', 'reino unido', 'reino saudita', 'oriente medio',
  'medio oriente', 'corea del norte', 'corea del sur', 'arabia saudita',
  'emiratos arabes', 'casa blanca', 'nueva york', 'nueva delhi',
  'ciudad de mexico', 'ciudad de méxico', 'sudafrica', 'sudáfrica',
  'republica dominicana', 'república dominicana',
])

// English geo names (ported from backend utils._GEO_NAME_BLOCKLIST).
const GEO_BLOCKLIST = new Set([
  'abu dhabi', 'saudi arabia', 'north korea', 'south korea', 'north africa',
  'south africa', 'north america', 'south america', 'latin america',
  'united states', 'united kingdom', 'united arab emirates',
  'new york', 'new delhi', 'new zealand', 'new jersey', 'new mexico',
  'hong kong', 'puerto rico', 'costa rica', 'ivory coast', 'sierra leone',
  'burkina faso', 'guinea bissau', 'equatorial guinea', 'papua new guinea',
  'el salvador', 'sri lanka', 'west bank', 'west africa', 'east africa',
  'middle east', 'central asia', 'southeast asia', 'south asia',
  'las vegas', 'los angeles', 'san francisco',
  'san jose', 'san diego', 'rio de janeiro', 'sao paulo', 'buenos aires',
  'kuala lumpur', 'tel aviv', 'cape town', 'addis ababa', 'dar es salaam',
])

const GEO_FIRST_WORDS = new Set(['north', 'south', 'east', 'west', 'central', 'greater', 'upper', 'lower'])
const LEADING_NON_NAME = new Set(['el', 'la', 'los', 'las', 'lo', 'un', 'una', 'unos', 'unas', 'the', 'dar'])

function isValidPerson(name: string): boolean {
  const lower = name.toLowerCase()
  const tokens = lower.split(/\s+/)
  if (tokens.length < 2 || name.length > 60) return false
  if (GEO_BLOCKLIST.has(lower) || PLACE_NAMES.has(lower) || EVENT_NAMES.has(lower) || ORG_NAMES.has(lower)) return false
  if (GEO_FIRST_WORDS.has(tokens[0]) || LEADING_NON_NAME.has(tokens[0])) return false
  if (new Set(tokens).size <= 1) return false  // repeated-token chant ("bafana bafana")
  return true
}

export function classifySubject(name: string): SubjectType | null {
  if (!name) return null
  const lower = name.toLowerCase().trim()
  if (EVENT_NAMES.has(lower)) return 'event'
  if (ORG_NAMES.has(lower)) return 'organization'
  if (PLACE_NAMES.has(lower) || GEO_BLOCKLIST.has(lower)) return 'place'
  if (isValidPerson(name)) return 'person'
  return null
}

// Type, drop unclassifiable noise, preserve incoming (count-desc) order, cap.
export function buildKeySubjects(people: KeyPerson[] = [], limit = 8): KeySubject[] {
  const out: KeySubject[] = []
  for (const p of people) {
    if (!p.name || p.count <= 0) continue
    const type = classifySubject(p.name)
    if (!type) continue
    out.push({ name: p.name, count: p.count, type })
    if (out.length >= limit) break
  }
  return out
}
