export interface KeyPerson {
  name: string
  count: number
}

const COMMON_NON_PERSON_ENTITIES = new Set([
  'america latin',
  'latin america',
  'el pais',
  'saint faith',
  'republica dominicana',
])

export function selectVisibleKeyPersons(people: KeyPerson[] = [], limit = 8): KeyPerson[] {
  return people
    .filter(person => {
      const name = person.name.trim()
      if (!name || person.count <= 0) return false
      if (COMMON_NON_PERSON_ENTITIES.has(name.toLowerCase())) return false
      return name.split(/\s+/).length >= 2
    })
    .slice(0, limit)
}
