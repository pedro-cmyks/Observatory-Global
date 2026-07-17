// Shared HTML-entity decoder (council P0-3 — the `html.unescape` debt, client
// side). Headlines/labels can arrive entity-encoded (e.g. '&#x41F;…' for
// non-Latin scripts — the "Cyrillic hex soup"). Decode for display.
//
// Browser path: a <textarea> — RCDATA, so no script executes and we only read
// back textContent-equivalent text. Node/test/SSR path: a pure regex decoder
// for numeric + the common named entities (previously the string was returned
// unchanged in non-DOM envs).
//
// Also drops a trailing incomplete entity ('…लगा&#') left by a mid-entity
// label truncation.

function safeFromCodePoint(cp: number): string {
  try {
    return Number.isFinite(cp) && cp > 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : ''
  } catch {
    return ''
  }
}

const NAMED: Record<string, string> = {
  amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ',
  ndash: '–', mdash: '—', hellip: '…', rsquo: '’', lsquo: '‘',
  rdquo: '”', ldquo: '“',
}

export function decodeEntities(s: string): string {
  if (!s || !s.includes('&')) return s
  const trimmed = s.replace(/&#[0-9a-fx]*$/i, '')
  if (typeof document === 'undefined') {
    return trimmed
      .replace(/&#x([0-9a-f]+);/gi, (_, h: string) => safeFromCodePoint(parseInt(h, 16)))
      .replace(/&#(\d+);/g, (_, d: string) => safeFromCodePoint(parseInt(d, 10)))
      .replace(/&([a-z]+);/gi, (m, name: string) => NAMED[name.toLowerCase()] ?? m)
  }
  const el = document.createElement('textarea')
  el.innerHTML = trimmed
  return el.value
}
