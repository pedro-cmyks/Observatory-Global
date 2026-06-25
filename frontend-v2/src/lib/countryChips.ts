// Country chips on threads reflect COVERAGE volume (where a story is being
// reported from), NOT the story's subject country — the subject-geography fix
// is #238. Until then, label them honestly so the surface never implies a
// false subject (e.g. a Venezuela earthquake whose chips read US/BR/RU).

export const COVERAGE_CHIP_LABEL = 'Covered from'

export function coverageChipTip(country: string): string {
  return `Where this story is being covered from — not necessarily its subject. (${country})`
}
