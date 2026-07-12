export type SourceFamily = 'state' | 'wire' | 'independent'

interface SourceFamilyMeta {
  label: string
  className: string
  tip: string
}

const SOURCE_FAMILY_META: Record<SourceFamily, SourceFamilyMeta> = {
  state: {
    label: 'State',
    className: 'source-family-badge--state',
    tip: 'State-controlled or publicly funded source family',
  },
  wire: {
    label: 'Wire',
    className: 'source-family-badge--wire',
    tip: 'International wire service source family',
  },
  independent: {
    label: 'Independent',
    className: 'source-family-badge--independent',
    tip: 'Independent or regional source family',
  },
}

// Unknown families must not inherit a confident classification: an outlet we
// have not classified is "unclassified", not "independent".
const UNKNOWN_FAMILY_META: SourceFamilyMeta = {
  label: 'Unclassified',
  className: 'source-family-badge--unknown',
  tip: 'Source family not yet classified by Atlas',
}

export function getSourceFamilyMeta(family?: SourceFamily | string | null): SourceFamilyMeta {
  if (family === 'state' || family === 'wire' || family === 'independent') {
    return SOURCE_FAMILY_META[family]
  }
  return UNKNOWN_FAMILY_META
}
