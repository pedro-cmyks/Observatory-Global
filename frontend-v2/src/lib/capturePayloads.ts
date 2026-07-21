// Pure payload builders for the one-gesture ◆ capture (Exploration Flywheel
// Task 3.1). Every builder returns the exact shape a call site needs to hand
// straight to pinItem/addCitation — no side effects, no store access, so the
// capture affordance (wherever it lives — universe node, neighbor chip,
// person/country chip, receipt row) can call one function and be done.

import type { PinnedItem, PinnedItemType } from '../contexts/WorkspaceContext'
import type { CitationInput, CitationGateStatus } from './workbench'
import { decodeEntities } from './decodeEntities'

type PinPayload = Omit<PinnedItem, 'notes' | 'timestamp'>

/** A thread/topic node (universe body, neighbor chip, dynamic-topic id) as a
 *  workbench pin. `id` is the raw thread/topic id (e.g. 'dynamic-topic-9' or
 *  an atlas slug--cc) — the same id `?theme=` already expects. */
export function threadPin(id: string, label: string): PinPayload {
  return {
    id: `theme-${id}`,
    type: 'theme' as PinnedItemType,
    title: label,
    urlParams: `?theme=${id}`,
  }
}

/** A named person (Key Subjects chip, EntityPanel, etc). Name rides both the
 *  raw id (so unpin/isPinned match the same identity everywhere else uses)
 *  and the URL-encoded query param. */
export function personPin(name: string): PinPayload {
  return {
    id: `person-${name}`,
    type: 'person' as PinnedItemType,
    title: name,
    urlParams: `?person=${encodeURIComponent(name)}`,
  }
}

/** A country chip (ISO-2 code + display name). */
export function countryPin(iso: string, name: string): PinPayload {
  return {
    id: `country-${iso}`,
    type: 'country' as PinnedItemType,
    title: name,
    urlParams: `?country=${iso}`,
  }
}

/** A single evidence/receipt row → a Citation-ready payload. `gateStatus`
 *  defaults to 'unknown' (spec: absence over guess — a row with no gate
 *  signal is not silently upgraded to any tier). The headline is decoded
 *  here (not at render time) so a frozen citation carries clean text. */
export function receiptFrom(row: {
  headline: string
  source?: string
  url?: string
  publishedDate?: string
  sourceLang?: string
  originCountry?: string
  gateStatus?: CitationGateStatus
}): CitationInput {
  return {
    headline: decodeEntities(row.headline),
    source: row.source,
    url: row.url,
    publishedDate: row.publishedDate,
    sourceLang: row.sourceLang,
    originCountry: row.originCountry,
    gateStatus: row.gateStatus ?? 'unknown',
  }
}
