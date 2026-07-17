// Jargon purge helpers (council wish 7): progressive disclosure — a human
// sentence by default, the measured internal one hover away. Nothing is
// deleted: callers keep the raw string in a data-tip.

/** CAMEO codebook strings are machine imperatives ("Use unconventional
 * violence") — rewrite the common verb frames into event nouns. The raw
 * codebook string belongs in the hover, not the row. */
export function humanizeCameoEvent(raw: string | null | undefined): string {
  const s = (raw ?? '').trim()
  if (!s) return 'Conflict event'
  // Specific high-frequency codebook entries first.
  if (/^conduct .*bombing$/i.test(s)) return 'Bombing'
  if (/^use conventional military force$/i.test(s)) return 'Military force'
  let out = s
  const employ = out.match(/^Employ\s+(.+)$/i)
  if (employ) return capitalize(`${employ[1]} use`)
  out = out
    .replace(/^Use\s+/i, '')
    .replace(/^Engage in\s+/i, '')
    .replace(/^Conduct\s+/i, '')
    .replace(/^Carry out\s+/i, '')
    .replace(/^Impose\s+/i, '')
    .trim()
  return capitalize(out || 'Conflict event')
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export interface HumanizedValue {
  /** What to render by default. */
  text: string
  /** The verbatim internal — for the data-tip. */
  raw: string
  /** True when the raw string was an internal token, not human copy. */
  internal: boolean
}

const KEY_PHRASES: Record<string, (v: string) => string> = {
  changed_10h: v => `volume movement ${v} over the last 10h`,
  gate_score: v => `relevance-gate score ${v}`,
  avg_confidence: v => `measured confidence ${v}`,
}

/** Detect internal tokens leaking into user-facing cells (the dossier WHY-cell
 * `changed_10h=-38` / node-hash class) and paraphrase them; human copy passes
 * through untouched. */
export function humanizeReadinessValue(raw: string): HumanizedValue {
  const s = (raw ?? '').trim()
  // key=value with a snake_case key — matched ANYWHERE in the string, because
  // the production payload shape is "Label: key=value" (fix round 2026-07-17
  // item 4: the ^-anchored version let `…: changed_10h=+15` leak verbatim).
  // Every occurrence is paraphrased in place; surrounding prose is kept.
  const kvRe = /([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\s*=\s*([+-]?[\w.%]+)/gi
  if (kvRe.test(s)) {
    kvRe.lastIndex = 0
    const text = s.replace(kvRe, (_m, key: string, value: string) => {
      const fn = KEY_PHRASES[key.toLowerCase()]
      return fn ? fn(value) : `${key.replace(/_/g, ' ')} ${value}`
    })
    return { text, raw: s, internal: true }
  }
  // opaque thread/topic ids
  if (/^(dynamic-topic|emergent-cluster|cluster)-\d+$/i.test(s)) {
    return { text: 'internal thread reference', raw: s, internal: true }
  }
  // hex-ish node hashes (no vowel words, ≥12 hex chars)
  if (/^[a-f0-9]{12,}$/i.test(s)) {
    return { text: 'internal node reference', raw: s, internal: true }
  }
  return { text: s, raw: s, internal: false }
}
