// El dial VISTE la tarjeta (P1.5 — spec 2026-08-18-depth-dial-design §6,
// semántica en sitio): en /brief el dial ya no navega; OBSERVAR y CONSTRUIR
// SUMAN bloques a cada tarjeta de historia. Este módulo puro decide QUÉ
// bloques aplican a una fila dada — el componente solo renderiza.
//
// Reglas duras:
//  · LEER = cero bloques (el Brief de hoy, byte-idéntico — G-ADITIVO).
//  · Solo datos YA SERVIDOS en la fila: un campo ausente no produce bloque,
//    jamás un placeholder (las filas selladas traen menos campos y por eso
//    visten menos — honesto por construcción).
//  · CONSTRUIR ⊇ OBSERVAR: construir nunca quita un bloque de observar
//    (aditivo siempre); lo que construir AÑADE (save prominente, workbench,
//    método abierto) vive en el componente, no aquí.
//  · Registro de prosa (banco R1): nada de sigma/velocity crudos — los
//    bloques cargan bandas, chips y conteos con base, nunca telemetría.
import type { CountBase } from './countQualifier'
import { resolveTemporalChip, type TemporalSignatureMeta } from './temporalSignatureChip'
import {
    resolveConfidenceBucket,
    type ConfidenceBucket,
    type ConfidenceBucketSource,
} from './threadConfidence'
import { rowCountBase, threadRowKind } from './threadRowKind'
import type { DialPosition } from './depthDial'

/** La fila mínima que el decisor lee — un SUBCONJUNTO tolerante de TopThread
 *  (vivo, fetch_threads) y DailyPublicationThread (sellado). Todo opcional:
 *  la ausencia decide, nunca inventa. */
export interface DepthCardRow {
    thread_id?: string
    anchor_topics?: string[] | null
    top_entities?: unknown[] | null
    top_countries?: string[] | null
    signal_count?: number | null
    count_window_hours?: number | null
    gated_signal_count?: number | null
    confidence?: string | null
    avg_confidence?: number | null
    confidence_measured?: boolean
    temporal_signature?: string | null
    signature_meta?: TemporalSignatureMeta | null
    discussion_count?: number | null
}

export type DepthBlock =
    | { kind: 'subjects'; entities: string[] }
    | { kind: 'coverage'; codes: string[] }
    | { kind: 'temporal'; signature: string; meta: TemporalSignatureMeta | null }
    | { kind: 'confidence'; bucket: ConfidenceBucket; source: ConfidenceBucketSource }
    | { kind: 'count'; count: number; windowHours: number | null; base: CountBase }
    | { kind: 'discussion'; n: number }

export interface DepthBlockOpts {
    /** Códigos de país que la tarjeta base YA muestra (sus chips de cobertura
     *  de LEER) — el bloque carga solo el RESTO, nunca duplica. */
    omitCoverage?: string[]
    /** Fila de la edición SELLADA: su conteo se congeló al sello (base
     *  'frozen', sin ventana viva). Los campos que el sello no carga
     *  simplemente no producen bloque. */
    sealed?: boolean
}

const MAX_SUBJECTS = 4
const MAX_COVERAGE = 6

/**
 * Qué bloques viste esta fila a esta profundidad. Orden fijo (prosa primero,
 * medición después): sujetos · cobertura · firma temporal · confianza ·
 * conteo con base · discusión.
 */
export function depthBlocksForRow(
    row: DepthCardRow,
    depth: DialPosition,
    opts: DepthBlockOpts = {},
): DepthBlock[] {
    if (depth === 'leer') return []
    const blocks: DepthBlock[] = []
    const sealed = opts.sealed === true

    // Sujetos clave — top_entities servido (fetch_threads); el sello no lo
    // carga, así que la guardia natural es la ausencia.
    const entities = (row.top_entities ?? [])
        .map(e => String(e ?? '').trim())
        .filter(e => e.length > 0)
        .slice(0, MAX_SUBJECTS)
    if (entities.length > 0) blocks.push({ kind: 'subjects', entities })

    // Cobertura — SOLO los países que la tarjeta base no muestra ya.
    const omit = new Set((opts.omitCoverage ?? []).map(c => String(c)))
    const codes = (row.top_countries ?? [])
        .filter(cc => typeof cc === 'string' && cc.length > 0 && !omit.has(cc))
        .slice(0, MAX_COVERAGE)
    if (codes.length > 0) blocks.push({ kind: 'coverage', codes })

    // Firma temporal — el chip existente decide su propio vocabulario
    // (continuous/NULL → nada; absence over guess).
    const temporal = resolveTemporalChip(row.temporal_signature, row.signature_meta ?? null)
    if (temporal && row.temporal_signature) {
        blocks.push({
            kind: 'temporal',
            signature: row.temporal_signature,
            meta: row.signature_meta ?? null,
        })
    }

    // Banda de confianza — el MISMO gating que threadConfidencePresentation:
    // la banda servida manda; el número crudo solo cuenta cuando la fila lo
    // declara medido. Nunca un dígito (N14).
    const measured = row.confidence_measured === true
        && typeof row.avg_confidence === 'number'
        && Number.isFinite(row.avg_confidence)
        ? row.avg_confidence
        : null
    const conf = resolveConfidenceBucket({ band: row.confidence ?? null, avgConfidence: measured })
    if (conf.bucket != null && conf.source != null) {
        blocks.push({ kind: 'confidence', bucket: conf.bucket, source: conf.source })
    }

    // Conteo con ventana y base — sellado = 'frozen' (congelado al sello, la
    // ventana viva no aplica); vivo = la misma base que el rail del console
    // (rowCountBase sobre el kind de la fila).
    if (typeof row.signal_count === 'number' && Number.isFinite(row.signal_count) && row.signal_count > 0) {
        const base: CountBase = sealed
            ? 'frozen'
            : rowCountBase(
                threadRowKind({ thread_id: String(row.thread_id ?? ''), anchor_topics: row.anchor_topics ?? null }),
                row,
            )
        blocks.push({
            kind: 'count',
            count: row.signal_count,
            windowHours: sealed ? null : (row.count_window_hours ?? null),
            base,
        })
    }

    // Discusión — people-side, jamás evidencia; solo cuando el conteo servido
    // es positivo.
    if (typeof row.discussion_count === 'number' && row.discussion_count > 0) {
        blocks.push({ kind: 'discussion', n: row.discussion_count })
    }

    return blocks
}
