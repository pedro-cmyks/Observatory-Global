// Claim ledger (Carolina's spec / council Phase 2) — the layer ABOVE receipts.
//
// A receipt (Citation, workbench.ts) is one source line with frozen provenance.
// A Claim is the analyst's *judgement over two receipts*: outlet X says 4,734
// dead, outlet Y says 4,930 — CORROBORATES / CONTRADICTS / CONTEXT. The dossier
// renders those side by side and, crucially, flags when NO official/wire source
// backs a contested figure (the "official source missing" caveat).
//
// This module is PURE (no localStorage). The store wrappers — addClaim /
// removeClaim / relabelClaim / listClaims — live in workbench.ts, mirroring the
// Citation precedent, so a Claim persists on `Investigation.claims`.
import type { Citation } from './workbench'
import { classifyOutlet, isOfficialishTier } from './sourceTiers'

/** How the analyst relates two receipts. */
export type ClaimRelation = 'CORROBORATES' | 'CONTRADICTS' | 'CONTEXT'

export const CLAIM_RELATIONS: ClaimRelation[] = ['CORROBORATES', 'CONTRADICTS', 'CONTEXT']

/** A value the analyst keys in to compare against a receipt (e.g. an official /
 *  wire toll they have but haven't pinned as a receipt). Used when a Claim's
 *  `citationIdB` is null (citation vs typed value). */
export interface TypedValue {
  figure?: number | null
  /** What the value is / where it came from — renders as the "outlet" cell. */
  label?: string
  /** True when this is an official/wire figure (government, UN, wire agency). */
  official?: boolean
}

/** A judgement linking TWO receipts (or a receipt + a typed value) with a
 *  relation. Stored on `Investigation.claims`. */
export interface Claim {
  id: string
  investigationId: string
  /** First receipt (Citation.id). */
  citationIdA: string
  /** Second receipt (Citation.id), or null when comparing against a typed value. */
  citationIdB: string | null
  relation: ClaimRelation
  /** Optional focal figure the analyst is comparing (overrides the A-side
   *  headline extraction when the headline carries no number). */
  figure?: number | null
  /** Present when citationIdB is null (citation vs a keyed-in value). */
  typedValue?: TypedValue | null
  note?: string
  createdAt: string
}

/** Everything the caller supplies; `id`/`createdAt` are stamped by {@link makeClaim}. */
export type ClaimInput = Omit<Claim, 'id' | 'createdAt'> & { id?: string; createdAt?: string }

/** Deterministic id for a claim. Keyed on the receipt PAIR only (not the
 *  relation) so a relabel keeps the same row and a pair holds one claim.
 *  Order-independent for two receipts; a typed-value claim gets its own id. */
export function claimId(a: string, b: string | null): string {
  if (b === null) return `claim:${a}::typed`
  const [x, y] = [a, b].sort()
  return `claim:${x}::${y}`
}

/** Construct a Claim from an input, stamping a stable id + createdAt. Pure —
 *  `now` is passed in so it stays deterministic/testable. */
export function makeClaim(input: ClaimInput, now: string): Claim {
  return {
    ...input,
    id: input.id ?? claimId(input.citationIdA, input.citationIdB),
    createdAt: input.createdAt ?? now,
  }
}

// International wire agencies + official bodies. A contested figure that no
// source on this list backs is flagged "official source missing".
const OFFICIAL_SOURCE_TOKENS = [
  'reuters', 'associated press', 'afp', 'agence france', 'efe', 'bloomberg',
  'anadolu', 'tass', 'xinhua', 'kyodo', 'yonhap', 'pa media', 'press association',
  'dpa', 'pti', 'ians', 'ap news',
]

/** True when a source name reads as an official-ish body — an international
 *  wire agency OR a state broadcaster (#217: wire/state = official-ish). The
 *  local token list stays as a fast path; the coarse tier classifier
 *  (sourceTiers.ts) is the shared, single-source-of-truth backstop that also
 *  catches state channels (RT/CGTN/Xinhua). Word-boundary so "AP" hits but
 *  "Apple Daily" does not. */
export function isOfficialSource(source: string | null | undefined): boolean {
  const s = (source ?? '').trim().toLowerCase()
  if (!s) return false
  if (/\bap\b/.test(s) || /\bafp\b/.test(s)) return true
  if (OFFICIAL_SOURCE_TOKENS.some(tok => s.includes(tok))) return true
  return isOfficialishTier(classifyOutlet(source).tier)
}

// ── Locale numeral discipline (corroborate-v2 F1, council C-N17) ────────────
// Indonesian "1.700" parsed as 1.7 made the best match the top CONTRADICTION.
// This set + {@link parseFigureToken} MIRROR `_COMMA_DECIMAL_LANGS` and
// `_parse_figure_token` in backend/app/services/corroboration.py rule for rule,
// so a headline's toll parses identically on both ends. Keep them in lockstep:
// languages that write decimals with a COMMA and group thousands with a DOT.
const COMMA_DECIMAL_LANGS = new Set([
  'es', 'pt', 'de', 'fr', 'it', 'id', 'in', 'tr', 'ru', 'uk', 'nl', 'da',
  'sv', 'no', 'nb', 'nn', 'fi', 'pl', 'cs', 'sk', 'el', 'ro', 'hu', 'vi',
  'az', 'kk', 'sr', 'hr', 'bg', 'ca', 'sl', 'lt', 'lv', 'et', 'mk', 'sq',
  'bs', 'ka', 'hy', 'be',
])

const FIGURE_TOKEN_RE = /\d[\d.,]*\d|\d/

/** One numeric token → number under the locale's separator convention.
 *  Universal rule first: when BOTH separators appear, the LAST one is the
 *  decimal mark. Then per-locale: a single separator followed by exactly three
 *  digits is thousands-grouping in that locale's grouping character; otherwise
 *  it is the decimal mark. Unknown-locale single-dot stays decimal
 *  (conservative: preserves the pre-v2 behavior for English). */
function parseFigureToken(raw: string, commaDecimal: boolean): number | null {
  const tok = raw.replace(/^[.,]+/, '').replace(/[.,]+$/, '')
  if (!tok) return null
  const hasDot = tok.includes('.')
  const hasComma = tok.includes(',')
  let out: number
  if (hasDot && hasComma) {
    const dec = tok.lastIndexOf('.') > tok.lastIndexOf(',') ? '.' : ','
    const grp = dec === '.' ? ',' : '.'
    out = Number(tok.split(grp).join('').replace(dec, '.'))
  } else if (hasDot) {
    const parts = tok.split('.')
    if (parts.length > 2) out = Number(parts.join(''))          // 1.234.567 — unambiguous
    else if (commaDecimal && parts[1].length === 3) out = Number(parts.join(''))  // id/es/de: 1.700 = 1700
    else out = Number(tok)
  } else if (hasComma) {
    const parts = tok.split(',')
    if (parts.length > 2) out = Number(parts.join(''))          // 1,234,567 — unambiguous
    else if (commaDecimal) out = Number(parts.join('.'))        // es: 7,6 = 7.6
    else if (parts[1].length === 3) out = Number(parts.join(''))  // en: 1,700 = 1700
    else out = Number(parts.join('.'))
  } else {
    out = Number(tok)
  }
  return Number.isFinite(out) ? out : null
}

/** First number in the text under the source language's numeral locale.
 *  `sourceLang` is optional: without it the parse is the conservative
 *  English-default one (a bare "1.700" stays 1.7 — we never invent a locale we
 *  weren't told). Mirrors `extract_figure(text, lang=…)` in the backend, which
 *  stays the authoritative end. */
export function extractFigure(
  text: string | null | undefined,
  sourceLang?: string | null,
): number | null {
  if (!text) return null
  const m = text.match(FIGURE_TOKEN_RE)
  if (!m) return null
  const lang = (sourceLang ?? '').trim().toLowerCase().slice(0, 2)
  return parseFigureToken(m[0], COMMA_DECIMAL_LANGS.has(lang))
}

/** "4734" → "4,734"; null → "—" (em dash). */
export function formatFigure(n: number | null): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return '—'
  return n.toLocaleString('en-US')
}

/** One rendered line of the claim table (one receipt or typed value in a claim). */
export interface ClaimTableRow {
  claimId: string
  relation: ClaimRelation
  figure: number | null
  figureText: string
  outlet: string | null
  country: string | null
  date: string | null
  headline: string | null
  /** This row is itself an official/wire source. */
  official: boolean
  /** ANY row in this claim comes from an official/wire source. */
  officialSourcePresent: boolean
}

/** Build the analyst's claim table: each claim expands to its receipt rows
 *  (figure · outlet · country · date · relation) so contested figures sit side
 *  by side. `officialSourcePresent` is claim-level — false = no wire/official
 *  source backs the figure (the "official source missing" caveat). Pure. */
export function buildClaimTable(citations: Citation[], claims: Claim[]): ClaimTableRow[] {
  const byId = new Map(citations.map(c => [c.id, c]))
  const rows: ClaimTableRow[] = []

  for (const claim of claims) {
    const a = byId.get(claim.citationIdA)
    if (!a) continue
    const b = claim.citationIdB ? byId.get(claim.citationIdB) : undefined
    // A two-receipt claim needs both receipts resolvable; a typed-value claim
    // needs only the A receipt.
    if (claim.citationIdB && !b) continue

    // Gather each side as a provisional row, then compute the claim-level flag.
    const sides: Omit<ClaimTableRow, 'officialSourcePresent'>[] = []

    // Each receipt's headline is read in ITS OWN source language (F1) — a
    // Spanish "1.700" is 1700, an unlabeled one stays 1.7 (absence over guess).
    const aFigure = claim.figure ?? extractFigure(a.headline, a.sourceLang)
    sides.push({
      claimId: claim.id,
      relation: claim.relation,
      figure: aFigure,
      figureText: formatFigure(aFigure),
      outlet: a.source ?? null,
      country: a.originCountry ?? null,
      date: a.publishedDate ?? null,
      headline: a.headline,
      official: isOfficialSource(a.source),
    })

    if (b) {
      const bFigure = extractFigure(b.headline, b.sourceLang)
      sides.push({
        claimId: claim.id,
        relation: claim.relation,
        figure: bFigure,
        figureText: formatFigure(bFigure),
        outlet: b.source ?? null,
        country: b.originCountry ?? null,
        date: b.publishedDate ?? null,
        headline: b.headline,
        official: isOfficialSource(b.source),
      })
    } else if (claim.typedValue) {
      const tv = claim.typedValue
      const fig = tv.figure ?? null
      sides.push({
        claimId: claim.id,
        relation: claim.relation,
        figure: fig,
        figureText: formatFigure(fig),
        outlet: tv.label ?? 'typed value',
        country: null,
        date: null,
        headline: null,
        official: Boolean(tv.official),
      })
    }

    const officialSourcePresent = sides.some(s => s.official)
    for (const s of sides) rows.push({ ...s, officialSourcePresent })
  }

  return rows
}

function mdCell(v: string | null): string {
  return (v ?? '—').replace(/\|/g, '\\|')
}

/** Markdown for the claim table (goes into the report export). A CONTRADICTS
 *  claim with no official source backing gets a caveat line. Pure. */
export function claimTableMarkdown(rows: ClaimTableRow[]): string[] {
  if (rows.length === 0) return []
  const lines: string[] = ['## Contested figures (claim ledger)', '']
  lines.push('| Figure | Outlet | Country | Date | Relation | Official source |')
  lines.push('| --- | --- | --- | --- | --- | --- |')
  for (const r of rows) {
    lines.push(
      `| ${mdCell(r.figureText)} | ${mdCell(r.outlet)} | ${mdCell(r.country)} | ${mdCell(r.date)} | ${r.relation} | ${r.officialSourcePresent ? 'present' : 'MISSING'} |`,
    )
  }
  lines.push('')
  // One caveat per claim that has no official/wire backing.
  const seen = new Set<string>()
  for (const r of rows) {
    if (r.officialSourcePresent || seen.has(r.claimId)) continue
    seen.add(r.claimId)
    lines.push(`> No official/wire source backs this ${r.relation.toLowerCase()} figure — treat as contested.`)
  }
  if (seen.size > 0) lines.push('')
  return lines
}
