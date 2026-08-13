import type { ReactNode } from 'react'
import type { CoarseTier } from '../lib/sourceTiers'
import { COARSE_TIERS, TIER_TIP, coarseTierLabel } from '../lib/sourceTiers'
import { resolveTierChip } from '../lib/sourceProvenance'
import type { DailyPublicationArtifact, EditionServing } from '../lib/dailyPublication'
import './PrintersMarks.css'

/* ============================================================================
   PRINTER'S MARKS — design exploration (2026-08-13), NOT SHIPPED.

   Prepress furniture for the Brief, under the house rule that no mark may be
   ornament: every mark renders a measurement the page already owns.

   - RegistrationMark  — the SEAL as a registration target: seal time + grade;
                         a degraded seal renders as physical MISREGISTRATION,
                         the live fallback as an UNREGISTERED (dashed) mark.
   - VoiceMixStrip     — a color control bar whose patches ARE the day's voice
                         mix, measured from the receipts the page serves.
   - TrimFrame         — crop marks around the sealed edition content only;
                         live overlays sit outside the trim by construction.

   Everything is gated behind `?marks=` in BriefNewspaper.tsx — the page is
   byte-identical without the param. `?marksState=` is a MOCKUP-ONLY override
   so all three seal states can be screenshotted regardless of what the
   backend sealed last night; it fabricates nothing when absent.
   ========================================================================= */

export type SealRegState = 'full' | 'partial' | 'live'

export interface RegMarkData {
    state: SealRegState
    /** Local seal moment, e.g. "02:31" (null on the live fallback). */
    sealTime: string | null
    /** staleBanner.age verbatim, e.g. "sealed 9 h ago". */
    ageLabel: string | null
    /** Readiness cells answered / total (5W+H) — the grade's number. */
    answered: number | null
    total: number | null
    /** Degradation labels the edition already admits to. */
    degradation: string[]
    /** Why the live view is served (live state only). */
    reason: string | null
    nextSeal: string | null
}

/** Derive the registration-mark data from fields the page already computed.
 *  `force` is the mockup-only state override (see header comment). */
export function buildRegMarkData(
    artifact: DailyPublicationArtifact | null,
    serving: EditionServing,
    opts: { ageLabel?: string | null; liveReason?: string | null; nextSeal?: string | null; force?: string | null },
): RegMarkData {
    const sealedAtRaw = artifact?.sealed_at
        ?? (artifact?.completion?.generated_at as string | undefined)
        ?? null
    const sealedDate = sealedAtRaw ? new Date(sealedAtRaw) : null
    const sealTime = sealedDate && !Number.isNaN(sealedDate.getTime())
        ? sealedDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
        : null

    const readiness = artifact?.package?.readiness
    const cells = readiness ? Object.values(readiness) : []
    const answered = cells.length > 0 ? cells.filter(c => c?.status === 'ready').length : null
    const total = cells.length > 0 ? cells.length : null

    let state: SealRegState = serving.serve === 'live'
        ? 'live'
        : (artifact?.status === 'ready' ? 'full' : 'partial')

    // MOCKUP-ONLY: force a state for screenshots. Numbers the real payload
    // lacks are substituted with plausible placeholders and the doc says so.
    const force = opts.force
    if (force === 'full' || force === 'partial' || force === 'live') {
        state = force
        if (force === 'partial') {
            return {
                state, sealTime: sealTime ?? '02:31', ageLabel: opts.ageLabel ?? null,
                answered: answered !== null && total !== null && answered < total ? answered : 4,
                total: total ?? 6,
                degradation: ['partial edition · 4 of 6 answered'],
                reason: null, nextSeal: opts.nextSeal ?? null,
            }
        }
        if (force === 'full') {
            return {
                state, sealTime: sealTime ?? '02:31', ageLabel: opts.ageLabel ?? null,
                answered: total ?? 6, total: total ?? 6, degradation: [],
                reason: null, nextSeal: opts.nextSeal ?? null,
            }
        }
        return {
            state, sealTime: null, ageLabel: null, answered: null, total: null,
            degradation: [], reason: opts.liveReason ?? 'no edition has sealed within the last day',
            nextSeal: opts.nextSeal ?? 'next seal attempt 02:30',
        }
    }

    return {
        state,
        sealTime,
        ageLabel: opts.ageLabel ?? null,
        answered,
        total,
        degradation: serving.degradation,
        reason: state === 'live' ? (opts.liveReason ?? null) : null,
        nextSeal: opts.nextSeal ?? null,
    }
}

/** One pass of the registration target: crosshair + circle around center. */
function RegGlyphPass({ dx = 0, dy = 0, dashed = false, className }: {
    dx?: number; dy?: number; dashed?: boolean; className: string
}) {
    return (
        <g
            className={className}
            transform={`translate(${dx} ${dy})`}
            fill="none"
            strokeWidth="1.1"
            strokeDasharray={dashed ? '2.2 2' : undefined}
        >
            <circle cx="16" cy="16" r="7.5" />
            <line x1="16" y1="2.5" x2="16" y2="29.5" />
            <line x1="2.5" y1="16" x2="29.5" y2="16" />
        </g>
    )
}

/** Variant 1 — registration mark carrying the seal.
 *  full    = one crisp mark (both passes coincide: in register).
 *  partial = the impression pass shifts 0.9px per unanswered W — the grade
 *            made physical as misregistration fringe.
 *  live    = both passes dashed and clearly apart: nothing was registered. */
export function RegistrationMark({ data }: { data: RegMarkData }) {
    const unanswered = data.answered !== null && data.total !== null
        ? Math.max(0, data.total - data.answered)
        : 0
    const off = data.state === 'live' ? 5 : data.state === 'partial' ? Math.min(0.9 * Math.max(unanswered, 1) + 0.6, 4.5) : 0
    const dashed = data.state === 'live'

    const gradeLine = data.state === 'live'
        ? 'LIVE VIEW — no fresh seal'
        : data.state === 'full'
            ? `FULL — ${data.answered ?? '·'}/${data.total ?? '·'} answered`
            : `PARTIAL — ${data.answered ?? '·'}/${data.total ?? '·'} answered`
    const headLine = data.state === 'live'
        ? 'REG · UNREGISTERED'
        : `REG · SEALED ${data.sealTime ?? '—'}`

    const tip = data.state === 'live'
        ? `Unregistered: the front page is the live fallback — ${data.reason ?? 'no fresh seal'}. ${data.nextSeal ?? ''}`.trim()
        : [
            `Registration = the nightly seal. ${data.ageLabel ?? ''}`.trim(),
            data.state === 'partial'
                ? `Misregistration is the grade: each unanswered editorial question (${unanswered} of ${data.total}) shifts the impression pass. ${data.degradation.join(' · ')}`
                : 'In register: the edition sealed complete.',
        ].join(' — ')

    return (
        <span className={`pm-reg pm-reg--${data.state}`} data-tip={tip}>
            <svg viewBox="0 0 32 32" width="26" height="26" aria-hidden="true" className="pm-reg-glyph">
                <RegGlyphPass className="pm-reg-plate" dashed={dashed} />
                {(data.state !== 'full') && (
                    <RegGlyphPass className="pm-reg-impression" dx={off} dy={-off * 0.6} dashed={dashed} />
                )}
            </svg>
            <span className="pm-reg-label">
                <span className="pm-reg-head">{headLine}</span>
                <span className="pm-reg-grade">{gradeLine}</span>
            </span>
        </span>
    )
}

/* ========================================================================= */

export interface VoicePatch {
    tier: CoarseTier
    count: number
    share: number
}

export interface VoiceMixData {
    patches: VoicePatch[]
    totalReceipts: number
    /** 'sealed' → frozen receipts; 'live' → live receipts. */
    basis: 'sealed' | 'live'
}

export interface MixableReceipt {
    source?: string | null
    source_origin_country?: string | null
    is_state_media?: boolean | null
}

/** Classify every receipt the page serves into the coarse tier ladder —
 *  the SAME classifier the receipt rows' tier chips use, so the strip and
 *  the chips can never disagree. */
export function buildVoiceMix(receipts: MixableReceipt[], basis: 'sealed' | 'live'): VoiceMixData | null {
    if (receipts.length === 0) return null
    const counts: Record<CoarseTier, number> = { wire: 0, state: 0, major: 0, local: 0, unknown: 0 }
    for (const r of receipts) {
        counts[resolveTierChip(r.source, r.source_origin_country, r.is_state_media).tier] += 1
    }
    const total = receipts.length
    const patches = COARSE_TIERS
        .filter(t => counts[t] > 0)
        .map(t => ({ tier: t, count: counts[t], share: counts[t] / total }))
    return { patches, totalReceipts: total, basis }
}

/** "18%", or "<1%" for a present-but-tiny tier — a patch that exists never
 *  claims zero ink. */
function shareLabel(share: number): string {
    const pct = Math.round(share * 100)
    return pct === 0 ? '<1%' : `${pct}%`
}

/** Variant 2 — color control strip that IS the day's voice mix. Patch width
 *  ∝ share of receipts; colors are the tier family the receipt chips already
 *  use; UNKNOWN prints as a crosshatch (unmeasured ink, never a solid). */
export function VoiceMixStrip({ mix }: { mix: VoiceMixData }) {
    return (
        <div className="pm-strip" role="img" aria-label={
            `Voice mix control strip: ${mix.patches.map(p => `${coarseTierLabel(p.tier)} ${shareLabel(p.share)}`).join(', ')} of ${mix.totalReceipts} ${mix.basis} receipts.`
        }>
            <span
                className="pm-strip-slug"
                data-tip={`A press control strip measures the inks on the sheet — this one measures the voices in the edition: every receipt served on this page, classified by the same source-tier chip you see on the receipt rows. Basis: ${mix.totalReceipts} ${mix.basis === 'sealed' ? 'frozen receipts in the sealed edition' : 'receipts in the live view'}.`}
            >
                INK · VOICE MIX — {mix.totalReceipts} {mix.basis === 'sealed' ? 'frozen' : 'live'} receipts
            </span>
            <span className="pm-strip-bar">
                {mix.patches.map(p => (
                    <span
                        key={p.tier}
                        className={`pm-patch pm-patch--${p.tier}`}
                        style={{ flexGrow: p.count }}
                        data-tip={`${coarseTierLabel(p.tier)} — ${p.count} of ${mix.totalReceipts} receipts (${shareLabel(p.share)}). ${TIER_TIP[p.tier]}`}
                    >
                        <span className="pm-patch-label">{coarseTierLabel(p.tier)} {shareLabel(p.share)}</span>
                    </span>
                ))}
            </span>
        </div>
    )
}

/* ========================================================================= */

function CropCorner({ pos }: { pos: 'tl' | 'tr' | 'bl' | 'br' }) {
    // Two hairlines per corner, offset from the trim corner like real crop
    // marks (they never touch the trim — the gap is the bleed).
    return (
        <svg className={`pm-crop pm-crop--${pos}`} viewBox="0 0 20 20" width="20" height="20" aria-hidden="true">
            <line x1="0" y1="16" x2="12" y2="16" />
            <line x1="16" y1="0" x2="16" y2="12" />
        </svg>
    )
}

/** Variant 3 — crop marks framing the sealed edition content only. The label
 *  carries the seal moment; everything rendered outside the frame (vitals,
 *  markets, map, bottom index) is live instrumentation, outside the trim. */
export function TrimFrame({ sealTime, gradeLine, children }: {
    sealTime: string | null
    gradeLine: string | null
    children: ReactNode
}) {
    return (
        <div className="pm-trimbox">
            <CropCorner pos="tl" /><CropCorner pos="tr" /><CropCorner pos="bl" /><CropCorner pos="br" />
            <span
                className="pm-trim-label"
                data-tip="Crop marks frame what the 02:30 press run sealed. Everything outside the trim — vitals, markets, map, indexes — is live instrumentation, measured now, not part of the sealed edition."
            >
                TRIM — SEALED EDITION{sealTime ? ` · ${sealTime}` : ''}{gradeLine ? ` · ${gradeLine}` : ''}
            </span>
            {children}
            <span className="pm-trim-outside" aria-hidden="true">outside the trim: live instrumentation</span>
        </div>
    )
}

/** Live fallback for the crop variant: there is no trim because nothing was
 *  sealed — stated, not decorated. */
export function NoTrimSlug({ reason, nextSeal }: { reason: string | null; nextSeal: string | null }) {
    return (
        <div className="pm-notrim" data-tip="No crop marks today: the front page is the live fallback, so no region of this page is a sealed edition.">
            NO TRIM — LIVE VIEW · {reason ?? 'no fresh seal'}{nextSeal ? ` · ${nextSeal}` : ''}
        </div>
    )
}

/** Stable wrapper so BriefNewspaper can gate the trim without defining an
 *  inline component (which would remount the edition panels every render). */
export function PMTrimWrap({ mode, sealTime, gradeLine, reason, nextSeal, children }: {
    mode: 'off' | 'frame' | 'live'
    sealTime: string | null
    gradeLine: string | null
    reason: string | null
    nextSeal: string | null
    children: ReactNode
}) {
    if (mode === 'off') return <>{children}</>
    if (mode === 'live') return <><NoTrimSlug reason={reason} nextSeal={nextSeal} />{children}</>
    return <TrimFrame sealTime={sealTime} gradeLine={gradeLine}>{children}</TrimFrame>
}
