import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { buildDossier, dossierToMarkdown, fmtDay } from '../lib/dossier'
import { fetchDossierEnrichment, resolveThreadTopicId, type DossierEnrichment } from '../lib/dossierEnrichment'
import {
    connectionsSummaryLines, coverageLensNote, buildFrozenCrossRefs,
    nodeStoryWindow, investigationStoryWindow,
    type ClusterResult, type ConnectionsData, type ConnectionNode,
} from '../lib/dossierConnections'
import { synthesizeDossier, synthesisMarkdown, isArticle, splitCitations, type DossierSynthesis } from '../lib/dossierSynthesis'
import {
    buildCorroborationRequest, runCorroborationJob, loadCachedCorroboration,
    saveCorroboration, corroborationMarkdown, statusChip,
    citationTierChip, citationTierClass, citationCollapseNote,
    citationDateText, citationAged, agedTip, corroborationWindowText, verdictFacets,
    pinSearchStatusText, corroborationCoverageText,
    type CorroborationData, type CorroborationJobProgress,
} from '../lib/dossierCorroboration'
import { DossierConnections } from './DossierConnections'
import { track, trackOnce } from '../lib/telemetry'
import { humanizeReadinessValue } from '../lib/humanizeInternals'
import { addPin, removePin, renameInvestigation, type Investigation } from '../lib/workbench'
import { enqueueUrls, extractSnapshotUrls, fullTextYield, stateTag, useArticleStates } from '../lib/articleEnrichment'
import {
    fetchCrossRead, crossFindingLabel, crossFindingLabelLong, independenceTip,
    type CrossRead,
} from '../lib/aiRead'
import { LabelReviewChip } from '../lib/labelReviewChip'
import { deriveVerdictChips, type NodeStateRef, type VerdictChipDescriptor } from '../lib/verdictChips'
import { VerdictChip } from './VerdictChip'
import { buildClaimTable, claimTableMarkdown } from '../lib/claimLedger'
import { resolveLauncherVerbs } from '../lib/launcherVerbs'
import { sourceMix, formatSourceMix } from '../lib/sourceTiers'
import { TierChip } from './TierChip'
import {
    validateProse, joinValidatedText, corroborationBackedFrom, type MeasuredContext,
} from '../lib/proseValidator'
import {
    buildInvestigationPublication,
    buildPublicationReadinessMarkdown,
    buildRelationsMarkdown,
    summarizeInvestigationEdges,
    readableReasonCode,
    type InvestigationPublicationResult,
} from '../lib/investigationPublication'
import './DossierView.css'

// Cross-read finding labels + independence tips live in lib/aiRead.ts (pure,
// unit-tested): 'shared_source' (Council R3 P1) = two syndicated copies of one
// wire story agree — NOT independent corroboration; corroborate-v2 R2 refines
// that by the MEASURED reason (attributed primary source / shared quotes), so
// a derivation is never mislabeled as a wire echo.

/** P0.6a: article text with inline [n] receipt markers → clickable superscript
 *  anchors into the numbered receipts list below the article. */
function renderWithCitations(text: string) {
    return splitCitations(text).map((part, i) =>
        part.kind === 'text'
            ? <span key={i}>{part.text}</span>
            : (
                <sup key={i} className="dossier-cite-ref">
                    <a
                        href={`#dossier-cite-${part.n}`}
                        onClick={e => {
                            e.preventDefault()
                            // 'auto' not 'smooth': smooth scrollIntoView silently no-ops on the
                            // overlay scroller in Chrome (verified live) — instant jump always works.
                            document.getElementById(`dossier-cite-${part.n}`)?.scrollIntoView({ behavior: 'auto', block: 'center' })
                        }}
                    >[{part.n}]</a>
                </sup>
            ),
    )
}

/** Council Phase 3 (Lane B) — generated synthesis prose is validated against the
 *  MEASURED set (claim figures, coverage counts, corroboration verdict) BEFORE it
 *  renders. An unbacked "confirmed"/"verified" is softened to "reported
 *  (uncorroborated)" (Marcos' rule: never assert corroboration we didn't
 *  measure); an unbacked figure keeps its text but wears a caveat marker. Backed
 *  text still flows through the [n] citation renderer. */
function renderValidatedProse(text: string, ctx: MeasuredContext) {
    return validateProse(text, ctx).map((seg, i) => {
        if (seg.kind === 'ok') return <span key={i}>{renderWithCitations(seg.text)}</span>
        if (seg.kind === 'unbacked-confirmation') {
            return (
                <span key={i} className="dossier-prose-softened" data-tip={seg.note}>{seg.text}</span>
            )
        }
        return (
            <span key={i} className="dossier-prose-unbacked" data-tip={seg.note}>
                {seg.text}<sup className="dossier-prose-caveat" aria-label="not backed by a measured value">⚠</sup>
            </span>
        )
    })
}

/** Phase 3 report view — a structured dossier generated from the FROZEN
 *  Workbench pins (#227 snapshots), with a Markdown export. Dossier v2 (W3)
 *  adds who-says-what + voice sections MEASURED at generation time. */
export function DossierView({ investigation, onClose, autoCorroborate, onMutate, onOpenThread, onOpenParams, onFreshQuery }: {
    investigation: Investigation; onClose: () => void; autoCorroborate?: boolean
    /** Called after a verdict chip mutates pinned state (drop receipt) so the
     *  parent re-reads the store and re-renders this frozen view. */
    onMutate?: () => void
    /** Open a thread by id+label. Serves BOTH the walked-kin nodes (chains spec §4,
     *  the WorkbenchConstellation contract) AND the Task 5.2 typed launchers. */
    onOpenThread?: (threadId: string, label: string) => void
    /** Task 5.2 — typed launcher nav (grammar in lib/launcherVerbs). All optional:
     *  when a callback is absent its launcher is not rendered. onFreshQuery GENERATES
     *  a new query (not a navigation). */
    onOpenParams?: (params: string) => void
    onFreshQuery?: (query: string) => void
}) {
    // onOpenThread / onOpenParams are threaded through for the not-yet-wired
    // connected-thread / semantic-neighbor launchers; referenced here so the
    // unused optional props never trip noUnusedLocals while 5.3/5.4 land the
    // fresh-query + corroborate verbs. onFreshQuery IS consumed (coverage gaps).
    void onOpenThread; void onOpenParams
    const now = useMemo(() => new Date().toISOString(), [])
    const [enrichment, setEnrichment] = useState<DossierEnrichment | undefined>(undefined)
    const dossier = useMemo(
        () => buildDossier(investigation, now, enrichment),
        [investigation, now, enrichment],
    )
    // Claim ledger (Carolina's spec): contested figures across the pinned
    // receipts, put side by side with an "official source missing" caveat.
    const claimRows = useMemo(
        () => buildClaimTable(investigation.citations, investigation.claims),
        [investigation.citations, investigation.claims],
    )
    // Source mix (#217): coarse credibility rollup over the pinned receipts, so
    // an analyst sees at a glance whether a story is wire-driven or single-
    // local-sourced. "2 wire · 5 major · 11 local · 3 unknown".
    const sourceMixText = useMemo(
        () => formatSourceMix(sourceMix(investigation.citations.map(c => c.source))),
        [investigation.citations],
    )
    const [copied, setCopied] = useState(false)
    // Export feedback (council wish 12): downloads must confirm themselves too.
    const [downloaded, setDownloaded] = useState(false)
    // Enrichment F1 (spec 2026-07-20): server-fetched full text per receipt.
    // Opening the dossier also BACKFILLS old pins (pre-F1 investigations, e.g.
    // NATO-Ankara) by enqueueing their evidence URLs; the states hook polls
    // bounded while fetches land — the report renders progressively, never blocks.
    const evidenceUrls = useMemo(
        () => Array.from(new Set(investigation.pins.flatMap(p => extractSnapshotUrls(p.snapshot)))),
        [investigation.pins],
    )
    useEffect(() => { enqueueUrls(evidenceUrls) }, [evidenceUrls])
    const articleStates = useArticleStates(evidenceUrls)
    const ftYield = fullTextYield(evidenceUrls, articleStates)
    // Title is a presentation/label concern (the frozen pins never change). The
    // H1 leads with the analyst's explicit rename if any, else the synthesis
    // headline (a real thesis, not the worst-conflated first-pin), else the
    // auto first-pin title. Rename persists on the investigation (survives reopen).
    const [customTitle, setCustomTitle] = useState<string | null>(
        investigation.titleCustom ? investigation.title : null,
    )
    const [editingTitle, setEditingTitle] = useState(false)
    const [titleDraft, setTitleDraft] = useState('')
    // Connection analysis is fetched inside DossierConnections; it hands the
    // measured data up here so the synthesis + Markdown export carry the findings.
    const [conn, setConn] = useState<{ data: ConnectionsData; cluster: ClusterResult } | null>(null)
    const onConnections = useCallback((data: ConnectionsData, cluster: ClusterResult) => {
        setConn({ data, cluster })
    }, [])
    // Chains spec §4: pinning a walked-kin node from the connection-analysis
    // section grows the investigation — the same flywheel move as the
    // workbench's WorkbenchConstellation → pinStory, just on the full-report
    // side. Metadata-only pin (no snapshot); opening it later backfills
    // evidence like any thread pin.
    const pinWalkedTopic = useCallback((n: { id: string; label: string; category: string | null }) => {
        addPin(investigation.id, {
            anchorId: n.id,
            anchorType: 'thread',
            label: n.label,
            category: n.category ?? undefined,
            retrievalLane: 'constellation-walk',
            open: { surface: 'thread_detail', params: { thread_id: n.id } },
        })
        onMutate?.()
    }, [investigation.id, onMutate])

    // P0.3 story windows: header = whole-investigation span; per-pin windows
    // render on the pin cards once the connection measurement lands.
    const storyWindow = useMemo(
        () => (conn ? investigationStoryWindow(conn.data.nodes) : null),
        [conn],
    )
    const nodeForPin = useCallback((pinTopicId: string | null): ConnectionNode | null => {
        if (!pinTopicId || !conn) return null
        return conn.data.nodes.find(n => n.id === pinTopicId || n.collapsed_from?.includes(pinTopicId)) ?? null
    }, [conn])

    // Verdict-chip flywheel (Inés): every self-critique the dossier raises →
    // an actionable chip. Isolated connection nodes surface the "unrelated"
    // critique; single-sourced / metadata-only / taxonomy pins surface from the
    // frozen evidence alone. Resolving a chip logs #204 gold with provenance.
    const nodeStates = useMemo<NodeStateRef[]>(() => {
        if (!conn) return []
        const isolatedIds = new Set(conn.cluster.isolated.map(n => n.id))
        const out: NodeStateRef[] = []
        for (const p of dossier.pins) {
            const node = nodeForPin(resolveThreadTopicId(p))
            if (node && isolatedIds.has(node.id)) out.push({ id: p.anchorId, state: 'isolated' })
        }
        return out
    }, [conn, dossier.pins, nodeForPin])
    const chipsByPin = useMemo(() => {
        const byPin = new Map<string, VerdictChipDescriptor[]>()
        for (const c of deriveVerdictChips(dossier.pins, nodeStates)) {
            byPin.set(c.targetId, [...(byPin.get(c.targetId) ?? []), c])
        }
        return byPin
    }, [dossier.pins, nodeStates])
    const performVerdict = useCallback((d: VerdictChipDescriptor) => {
        // Only the destructive action mutates pinned state; flag/relabel/request
        // actions persist through the verdict log alone (the chip flips to
        // resolved on its own). Drop-receipt removes the offending pin.
        if (d.kind === 'unrelated-receipt' && d.targetKind === 'pin') {
            removePin(investigation.id, d.targetId)
            onMutate?.()
        }
    }, [investigation.id, onMutate])

    // #2 synthesis — the standalone brief. One grounded LLM pass over the frozen
    // pins + the measured connection verdict. Fires once the connection is
    // measured (so the verdict feeds it), or from pins alone as a fallback.
    const [synth, setSynth] = useState<DossierSynthesis | null | undefined>(undefined)
    // Refs so the single synthesis call always reads the freshest dossier + conn,
    // and its result lands as long as the component is mounted — independent of
    // which effect instance fired it (the fallback-timer closure would otherwise
    // be cancelled the moment `conn` arrives, swallowing the brief).
    const dossierRef = useRef(dossier)
    dossierRef.current = dossier
    const connRef = useRef(conn)
    connRef.current = conn
    // Declared with the other synthesis refs (the crossRead STATE is set up
    // below) so the synthesis closure can read the freshest cross-read.
    const crossReadRef = useRef<CrossRead | null>(null)
    const mounted = useRef(true)
    // StrictMode's simulated unmount sets this false — reset on (re)mount or
    // the synthesis result is silently swallowed in dev.
    useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
    const synthStarted = useRef(false)
    useEffect(() => {
        if (dossier.pinCount === 0) { setSynth(null); return }
        if (synthStarted.current) return
        const run = () => {
            if (synthStarted.current) return
            synthStarted.current = true
            // crossReadRef: a cross-read already measured for this investigation
            // hands its TENSIONS to the synthesis, so the prose can never settle
            // a point two read sources disagree on (Frank 2026-08-12).
            synthesizeDossier(dossierRef.current, connRef.current, crossReadRef.current)
                .then(s => { if (mounted.current) setSynth(s) })
        }
        // 1 pin → no connection to wait for; 2+ → fire as soon as the verdict is
        // measured, else fall back after 9s so a failed measurement never blocks
        // the brief. run() always reads the latest conn via connRef.
        if (dossier.pinCount < 2 || conn) { run(); return }
        const t = setTimeout(run, 9000)
        return () => clearTimeout(t)
    }, [investigation.id, conn, dossier.pinCount])

    // P0.6b web corroboration — pins checked against live web coverage with
    // source-independence weighting. Cached per investigation (re-run on
    // demand); DOC 2.0 permits one query per five seconds, so duration grows
    // with evidence-bearing pins. It is button-triggered, never automatic —
    // except via the Workbench CORROBORATE ramp.
    const [corrob, setCorrob] = useState<CorroborationData | null>(
        () => loadCachedCorroboration(investigation.id),
    )
    const [corrobRunning, setCorrobRunning] = useState(false)
    const [corrobFailed, setCorrobFailed] = useState(false)
    const corrobAutoFired = useRef(false)
    // F2 cross-read: corroboration/tension map over quote-backed claims from
    // the fetched bodies. Button-triggered (first run pays the read pass per
    // uncached article; findings cached server-side 15 min).
    const [crossRead, setCrossRead] = useState<CrossRead | null>(null)
    crossReadRef.current = crossRead
    const [crossRunning, setCrossRunning] = useState(false)
    const [crossFailed, setCrossFailed] = useState(false)
    const runCrossRead = useCallback(async () => {
        if (evidenceUrls.length < 2 || crossRunning) return
        setCrossRunning(true)
        setCrossFailed(false)
        track('dossier_crossread', { urls: evidenceUrls.length })
        const data = await fetchCrossRead(evidenceUrls)
        if (mounted.current) {
            setCrossRead(data)
            setCrossFailed(data == null)   // rate limit / network — say so, never silent
            setCrossRunning(false)
        }
    }, [evidenceUrls, crossRunning])
    // V5: the run is a JOB the client polls. A real route (2+ evidence pins)
    // costs ~5.75s per search query — the DOC 2.0 one-query-per-five-seconds
    // limit — which is over the proxy's response ceiling by construction, so a
    // single long request came back as a silent 502 (fresh Frank test: 2 of 4).
    // Progress is the honest wait: the analyst sees queries land one by one.
    const [corrobProgress, setCorrobProgress] = useState<CorroborationJobProgress | null>(null)
    const runCorroboration = useCallback(async (force: boolean) => {
        if (dossierRef.current.pinCount === 0) return
        setCorrobRunning(true)
        setCorrobFailed(false)
        setCorrobProgress(null)
        track('dossier_corroborate', { pins: dossierRef.current.pinCount, force })
        const body = buildCorroborationRequest(
            dossierRef.current.pins, connRef.current?.data.nodes ?? null)
        const data = await runCorroborationJob(body, force, {
            onProgress: p => { if (mounted.current) setCorrobProgress(p) },
        })
        if (!mounted.current) return
        if (data) {
            saveCorroboration(investigation.id, data)
            setCorrob(data)
        } else {
            setCorrobFailed(true)   // keep any cached result on screen
        }
        setCorrobRunning(false)
    }, [investigation.id])
    useEffect(() => {
        if (!autoCorroborate || corrobAutoFired.current) return
        corrobAutoFired.current = true
        if (!corrob) void runCorroboration(false)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [autoCorroborate])

    // Council Phase 3 (Lane B) — the measured set the synthesis prose is checked
    // against before it renders: every claim-ledger figure, the coverage counts
    // (press/public, per-country, per-language), the corroboration counts, and
    // whether ANY corroboration verdict is `established`. A prose figure with no
    // measured backing wears a caveat; an unbacked "confirmed" is softened.
    const measuredCtx = useMemo<MeasuredContext>(() => {
        const figures: number[] = []
        for (const r of claimRows) if (r.figure !== null) figures.push(r.figure)
        const d = conn?.data.distributions
        if (d) {
            figures.push(d.roles.press ?? 0, d.roles.public ?? 0)
            for (const c of d.countries ?? []) figures.push(c.n)
            for (const l of d.languages ?? []) figures.push(l.n)
            for (const s of d.sentimentByNode ?? []) figures.push(s.sentiment)
        }
        if (corrob) for (const p of corrob.pins) {
            figures.push(p.independent_outlets, p.total_articles, p.syndicated_clusters)
        }
        return { figures, corroborationBacked: corroborationBackedFrom(corrob) }
    }, [claimRows, conn, corrob])

    // W3: measured sections load after the frozen core renders; a fetch
    // failure leaves the report intact (sections simply absent).
    useEffect(() => {
        let alive = true
        fetchDossierEnrichment(investigation)
            .then(e => { if (alive) setEnrichment(e) })
            .catch(() => { /* frozen core stands alone */ })
        return () => { alive = false }
    }, [investigation])

    // Shared L1/L3 publication contract. This normalizes EVERY heterogeneous
    // Workbench pin into the typed graph, then measures 5W+H readiness without
    // asking the LLM to decide what matters or whether two things are related.
    // A missing endpoint degrades to an absent panel; the frozen dossier stays.
    const [publication, setPublication] = useState<InvestigationPublicationResult | null | undefined>(undefined)
    useEffect(() => {
        let alive = true
        if (investigation.pins.length === 0) {
            setPublication(null)
            return () => { alive = false }
        }
        setPublication(undefined)
        buildInvestigationPublication(investigation)
            .then(result => { if (alive) setPublication(result) })
        return () => { alive = false }
    }, [investigation])

    // T5.1: generating a report is the deepest value moment in the analyst loop.
    useEffect(() => {
        track('dossier_generated', { pins: dossier.pinCount })
        trackOnce('first_value_moment', { kind: 'dossier' })
    }, [dossier.pinCount])

    // Effective title: explicit rename > synthesis headline > auto first-pin title.
    const effectiveTitle = customTitle ?? (synth?.headline || null) ?? investigation.title

    // Run prose through the validator + soften unbacked confirmations ("confirmed"
    // → "reported (uncorroborated)"). Applied to BOTH the on-screen title and the
    // Markdown export so the deliverable (the file a journalist publishes) carries
    // the same honesty gate as the screen — the auto-title "Confirmed: …" case + the
    // raw synthesisMarkdown export path the panel gate flagged.
    const validatedText = (s: string) => joinValidatedText(validateProse(s, measuredCtx))
    // A rename the analyst typed themselves is their words, not generated prose —
    // never rewrite it; only synthesis/auto titles pass through the gate.
    const displayTitle = customTitle ? effectiveTitle : validatedText(effectiveTitle)

    const startRename = () => { setTitleDraft(effectiveTitle); setEditingTitle(true) }
    const commitRename = () => {
        const next = titleDraft.trim()
        renameInvestigation(investigation.id, next)
        // Blank clears the override → fall back to synthesis/auto title again.
        setCustomTitle(next || null)
        setEditingTitle(false)
        track('dossier_renamed')
    }

    const markdown = () => {
        // Export/filename use the same chosen title the report leads with — the
        // title runs through the honesty gate too (auto/synthesis titles only).
        let base = dossierToMarkdown({ ...dossier, title: displayTitle })
        // Synthesis leads the report (above the templated summary) so the export
        // opens with the finding, not a pin count. VALIDATED — the exported file
        // must not assert an unbacked "confirmed" the on-screen view softens.
        if (synth && (synth.headline || synth.synthesis || isArticle(synth))) {
            const sblock = validatedText(synthesisMarkdown(synth).join('\n'))
            const sMarker = '## Executive summary'
            const sAt = base.indexOf(sMarker)
            base = sAt === -1 ? `${sblock}\n${base}` : `${base.slice(0, sAt)}${sblock}\n${base.slice(sAt)}`
        }
        // Source mix (#217): the coarse credibility rollup travels with the export.
        if (sourceMixText) {
            const smBlock = `## Source mix\n\n${investigation.citations.length} pinned receipt${investigation.citations.length === 1 ? '' : 's'} · ${sourceMixText}\n`
            const smMarker = '\n## Timeline'
            const smAt = base.indexOf(smMarker)
            base = smAt === -1 ? `${base}\n${smBlock}` : `${base.slice(0, smAt)}\n${smBlock}${base.slice(smAt)}`
        }
        // Enrichment F1: source excerpts travel with the export — excerpt +
        // citation only (legal: the file never republishes full articles).
        {
            const oks = evidenceUrls
                .map(u => articleStates.get(u))
                .filter(a => a?.status === 'ok' && a.excerpt)
            if (oks.length > 0) {
                const lines = [
                    '## From the source',
                    '',
                    `Full text fetched for ${ftYield.ok} of ${ftYield.total} pinned receipts (paywalls/bot walls make partial yield normal).`,
                    '',
                    ...oks.map(a => `> “${a!.excerpt}”\n> — ${a!.outlet ?? 'source'} · fetched ${a!.fetched_at ? a!.fetched_at.slice(0, 10) : 'earlier'}${a!.via === 'wayback' ? ' · via Wayback Machine' : ''} · ${a!.url}`),
                    '',
                ]
                const ftBlock = lines.join('\n')
                const ftMarker = '\n## Timeline'
                const ftAt = base.indexOf(ftMarker)
                base = ftAt === -1 ? `${base}\n${ftBlock}` : `${base.slice(0, ftAt)}\n${ftBlock}${base.slice(ftAt)}`
            }
        }
        // F2 cross-read findings travel with the export — quotes + honest labels.
        if (crossRead && crossRead.findings.length > 0) {
            const lines = [
                '## Source cross-read (AI READ — verify the quotes)',
                '',
                ...crossRead.findings.flatMap(f => {
                    const label = crossFindingLabelLong(f.kind, f.independence?.reason)
                    const indep = f.independence ? ` _(${f.independence.label})_` : ''
                    return [
                        `**${label}**${indep} — ${f.note}`,
                        `> “${f.a.quote}” — ${f.a.outlet || f.a.url}`,
                        `> “${f.b.quote}” — ${f.b.outlet || f.b.url}`,
                        '',
                    ]
                }),
            ]
            const crBlock = lines.join('\n')
            const crMarker = '\n## Timeline'
            const crAt = base.indexOf(crMarker)
            base = crAt === -1 ? `${base}\n${crBlock}` : `${base.slice(0, crAt)}\n${crBlock}${base.slice(crAt)}`
        }
        // Claim ledger: the contested-figures table travels with the export.
        if (claimRows.length > 0) {
            const clBlock = claimTableMarkdown(claimRows).join('\n') + '\n'
            const clMarker = '\n## Timeline'
            const clAt = base.indexOf(clMarker)
            base = clAt === -1 ? `${base}\n${clBlock}` : `${base.slice(0, clAt)}\n${clBlock}${base.slice(clAt)}`
        }
        // P0.6b: the web-corroboration section travels with the export.
        if (corrob) {
            const cblock = corroborationMarkdown(corrob).join('\n') + '\n'
            const cMarker = '\n## Timeline'
            const cAt = base.indexOf(cMarker)
            base = cAt === -1 ? `${base}\n${cblock}` : `${base.slice(0, cAt)}\n${cblock}${base.slice(cAt)}`
        }
        if (publication?.package) {
            const relBlock = buildRelationsMarkdown(publication.graph)
            const pblock = buildPublicationReadinessMarkdown(publication.package)
                + (relBlock ? `\n${relBlock}` : '') + '\n'
            const pMarker = '\n## Timeline'
            const pAt = base.indexOf(pMarker)
            base = pAt === -1 ? `${base}\n${pblock}` : `${base.slice(0, pAt)}\n${pblock}${base.slice(pAt)}`
        }
        if (!conn || conn.data.nodes.length < 2) return base
        const block = connectionsSummaryLines(conn.data, conn.cluster, {
            lensNote: coverageLensNote(conn.data.distributions?.languages ?? []),
            crossRefs: buildFrozenCrossRefs(investigation.pins, conn.data),
        }).join('\n') + '\n'
        // Insert the connection findings before the Timeline section.
        const marker = '\n## Timeline'
        const at = base.indexOf(marker)
        return at === -1 ? `${base}\n${block}` : `${base.slice(0, at)}\n${block}${base.slice(at)}`
    }

    const copy = async () => {
        try { await navigator.clipboard.writeText(markdown()); setCopied(true); setTimeout(() => setCopied(false), 1500) } catch { /* ignore */ }
    }
    const download = () => {
        const blob = new Blob([markdown()], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `atlas-report-${effectiveTitle.replace(/[^a-z0-9]+/gi, '-').toLowerCase().slice(0, 40)}.md`
        a.click()
        URL.revokeObjectURL(url)
        setDownloaded(true)
        setTimeout(() => setDownloaded(false), 1600)
    }

    return (
        <div className="dossier-overlay" onClick={onClose}>
            <div className="dossier" onClick={e => e.stopPropagation()}>
                <div className="dossier-head">
                    <div>
                        <div className="dossier-kicker">INVESTIGATION REPORT</div>
                        {editingTitle ? (
                            <input
                                className="dossier-title-input"
                                autoFocus
                                value={titleDraft}
                                placeholder={synth?.headline || investigation.title}
                                onChange={e => setTitleDraft(e.target.value)}
                                onKeyDown={e => {
                                    if (e.key === 'Enter') commitRename()
                                    else if (e.key === 'Escape') setEditingTitle(false)
                                }}
                                onBlur={commitRename}
                            />
                        ) : (
                            <h1
                                className="dossier-title"
                                onClick={startRename}
                                title="Click to rename this report"
                            >
                                {displayTitle}
                                <span className="dossier-title-edit" aria-hidden> ✎</span>
                            </h1>
                        )}
                    </div>
                    <div className="dossier-actions">
                        <button
                            className="dossier-btn dossier-btn--corroborate"
                            onClick={() => void runCorroboration(!!corrob)}
                            disabled={corrobRunning || dossier.pinCount === 0}
                            data-tip="Check every evidence-bearing pin against live web coverage — independent sources weighted. Metadata-only context is marked not applicable. DOC 2.0 permits one query every five seconds, so duration grows with the route."
                        >{corrobRunning ? 'Corroborating every evidence pin…' : corrob ? 'Re-corroborate' : 'Corroborate'}</button>
                        <button
                            className="dossier-btn"
                            onClick={runCrossRead}
                            disabled={crossRunning || evidenceUrls.length < 2}
                            data-tip="AI-read the fetched source texts and map corroborations/tensions between their quote-backed claims. Labeled possible — every finding carries both verbatim quotes so you verify in one glance."
                        >{crossRunning ? 'Reading sources…' : crossRead ? 'Re-cross-read' : 'Cross-read'}</button>
                        <button className="dossier-btn" onClick={copy}>{copied ? 'Copied ✓' : 'Copy MD'}</button>
                        <button className="dossier-btn" onClick={download}>{downloaded ? 'Downloaded ✓' : 'Download'}</button>
                        <button className="dossier-close" onClick={onClose} aria-label="Close">×</button>
                    </div>
                </div>

                <div className="dossier-meta">
                    Generated {new Date(dossier.generatedAt).toLocaleString()} · {dossier.pinCount} pin{dossier.pinCount === 1 ? '' : 's'} · frozen at pin time
                    {ftYield.total > 0 && (
                        <span data-tip="Receipts whose article text was fetched and extracted server-side (spec 2026-07-20). Paywalls/bot walls make partial yield the normal state — never an error.">
                            {' '}· full text {ftYield.ok}/{ftYield.total} source{ftYield.total === 1 ? '' : 's'}
                        </span>
                    )}
                    {storyWindow && <> · story window {fmtDay(storyWindow.first)} → {fmtDay(storyWindow.last)}</>}
                    {dossier.queries.length > 0 && <> · queries: {dossier.queries.join(' · ')}</>}
                </div>

                {(synth || (synth === undefined && dossier.pinCount > 0)) && (
                    <section className="dossier-section dossier-synthesis">
                        <h2>Synthesis</h2>
                        {synth === undefined ? (
                            <p className="dossier-meta">Writing the standalone brief…</p>
                        ) : synth && (synth.headline || synth.synthesis || isArticle(synth)) ? (
                            <>
                                {synth.headline && <p className="dossier-synth-headline">{synth.headline}</p>}
                                {isArticle(synth) ? (
                                    <>
                                        {synth.lede && <p className="dossier-synth-lede">{renderValidatedProse(synth.lede, measuredCtx)}</p>}
                                        {(synth.body ?? []).map((para, i) => (
                                            <p key={i}>{renderValidatedProse(para, measuredCtx)}</p>
                                        ))}
                                        {synth.unknowns && synth.unknowns.length > 0 && (
                                            <div className="dossier-synth-unknowns">
                                                <div className="dossier-synth-unknowns-title">What we don't know</div>
                                                <ul>
                                                    {synth.unknowns.map((u, i) => <li key={i}>{u}</li>)}
                                                </ul>
                                            </div>
                                        )}
                                        {synth.citations && synth.citations.length > 0 && (
                                            <ol className="dossier-synth-citations">
                                                {synth.citations.map(c => (
                                                    <li key={c.n} id={`dossier-cite-${c.n}`} value={c.n}>
                                                        {c.url
                                                            ? <a href={c.url} target="_blank" rel="noopener noreferrer">{c.headline}</a>
                                                            : c.headline}
                                                        {(c.source || c.date) && (
                                                            <span className="dossier-src"> — {[c.source, c.date ? fmtDay(c.date) : null].filter(Boolean).join(', ')}</span>
                                                        )}
                                                        {/* Frank reads the numbered citations AS the
                                                            sourcing list — a state outlet must be
                                                            marked here too, not only in corroboration. */}
                                                        <TierChip source={c.source} />
                                                        <span className="dossier-cite-pin"> ({c.pin})</span>
                                                    </li>
                                                ))}
                                            </ol>
                                        )}
                                    </>
                                ) : (
                                    <>
                                        {synth.synthesis && <p>{renderValidatedProse(synth.synthesis, measuredCtx)}</p>}
                                        {synth.gap && <p className="dossier-synth-gap">Key gap: {synth.gap}</p>}
                                    </>
                                )}
                                <p className="dossier-meta" data-tip="One grounded LLM pass over the frozen pins + the measured connection verdict. Every claim carries a numbered receipt from the frozen evidence. Measured now, not frozen; degrades to absence.">
                                    measured at generation time{synth.provider ? ` · ${synth.provider}` : ''} — grounded in pinned evidence + measured connections
                                </p>
                            </>
                        ) : (
                            <p className="dossier-meta">Synthesis unavailable — the templated summary below stands in.</p>
                        )}
                    </section>
                )}

                <section className="dossier-section">
                    <h2>Executive summary</h2>
                    <p>{dossier.summary}</p>
                </section>

                {dossier.pinCount > 0 && (
                    <section className="dossier-section dossier-readiness">
                        <h2>Editorial readiness — 5W+H</h2>
                        {publication === undefined ? (
                            <p className="dossier-meta">Measuring the pinned investigation against the shared L1/L3 publication contract…</p>
                        ) : publication ? (
                            <>
                                <div className="dossier-readiness-grid">
                                    {(['who', 'what', 'when', 'where', 'how', 'why'] as const).map(key => {
                                        const item = publication.package.readiness[key]
                                        return (
                                            <div key={key} className={`dossier-ready-card dossier-ready-card--${item.status}`}>
                                                <div className="dossier-ready-head">
                                                    <span>{key}</span>
                                                    <span>{item.status}</span>
                                                </div>
                                                {item.values.length > 0 && (
                                                    <div className="dossier-ready-values">
                                                        {/* Jargon purge (wish 7): internals like `changed_10h=-38` or
                                                            node hashes leak into these cells — render the human
                                                            paraphrase, keep the verbatim internal in the hover. */}
                                                        {item.values.map((v, i) => {
                                                            const h = humanizeReadinessValue(v)
                                                            return (
                                                                <span key={i}>
                                                                    {i > 0 && ' · '}
                                                                    {h.internal
                                                                        ? <span className="dossier-ready-internal" data-tip={`measured internal: ${h.raw}`}>{h.text}</span>
                                                                        : h.text}
                                                                </span>
                                                            )
                                                        })}
                                                    </div>
                                                )}
                                                {item.reason_codes.length > 0 && (
                                                    <div className="dossier-ready-reasons">
                                                        {item.reason_codes.map(readableReasonCode).join(' · ')}
                                                    </div>
                                                )}
                                            </div>
                                        )
                                    })}
                                </div>
                                <p className="dossier-meta">
                                    {publication.graph.nodes.length} typed node{publication.graph.nodes.length === 1 ? '' : 's'} · {publication.graph.edges.length} measured/inferred/contextual relation{publication.graph.edges.length === 1 ? '' : 's'} · {publication.package.receipts.length} receipt{publication.package.receipts.length === 1 ? '' : 's'}
                                    {publication.graph.completion.resolved_nodes < publication.graph.completion.requested_nodes
                                        ? ` · ${publication.graph.completion.requested_nodes - publication.graph.completion.resolved_nodes} metadata-only`
                                        : ''}
                                </p>
                                {publication.package.gaps.length > 0 && (
                                    <ul className="dossier-ready-gap-list">
                                        {publication.package.gaps.map(gap => (
                                            <li key={gap}>{readableReasonCode(gap)}</li>
                                        ))}
                                    </ul>
                                )}
                                {(() => {
                                    const edges = summarizeInvestigationEdges(publication.graph)
                                    if (edges.length === 0) return null
                                    return (
                                        <div className="dossier-relations">
                                            <h3 className="dossier-relations-title">Typed relations</h3>
                                            <ul className="dossier-relations-list">
                                                {edges.map((e, i) => (
                                                    <li key={`${e.relation}-${e.source}-${e.target}-${i}`} className={`dossier-relation dossier-relation--${e.tier}`}>
                                                        <span className="dossier-relation-tier">{e.tier}</span>
                                                        <span className="dossier-relation-body">
                                                            <strong>{e.relation}</strong> · {e.source} ↔ {e.target} · {e.receiptCount} receipt{e.receiptCount === 1 ? '' : 's'}
                                                            {e.caveats.length > 0 && (
                                                                <span className="dossier-relation-caveat"> · {e.caveats.map(readableReasonCode).join(' · ')}</span>
                                                            )}
                                                        </span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )
                                })()}
                            </>
                        ) : (
                            <p className="dossier-meta">Publication readiness unavailable — frozen evidence and the rest of the report remain intact.</p>
                        )}
                    </section>
                )}

                <section className="dossier-section">
                    <h2>Evidence ({dossier.pinCount})</h2>
                    {dossier.pins.length === 0 ? (
                        <p className="dossier-empty">No pins yet — pin anchors or truncated stories to build the report.</p>
                    ) : (
                        dossier.pins.map(p => {
                            const hasEvidence = (p.snapshot?.evidence ?? []).length > 0
                            const pinNode = nodeForPin(resolveThreadTopicId(p))
                            const win = pinNode ? nodeStoryWindow(pinNode) : null
                            return (
                            <div key={p.anchorId} className="dossier-pin">
                                <div className="dossier-pin-head">
                                    <span className="dossier-pin-label">
                                        {p.label}
                                        {/* N15: Label Court verdict FROZEN at pin time —
                                            failed/partial pinned labels stay marked under
                                            review in the report (dot variant, dense head). */}
                                        <LabelReviewChip labelStatus={p.snapshot?.labelStatus} variant="dot" />
                                    </span>
                                    <span className="dossier-pin-type">{p.anchorType}</span>
                                    {!hasEvidence && (
                                        <span className="dossier-pin-noev" data-tip="This pin froze metadata only — no evidence headlines were captured at pin time. Re-open the source to inspect it live.">
                                            metadata only — no frozen evidence
                                        </span>
                                    )}
                                </div>
                                {win && (
                                    <div className="dossier-pin-window">story window {fmtDay(win.first)} → {fmtDay(win.last)}</div>
                                )}
                                {p.snapshot?.summary && <div className="dossier-pin-summary">{p.snapshot.summary}</div>}
                                {hasEvidence && (
                                    <ul className="dossier-evidence">
                                        {p.snapshot!.evidence!.map((e, i) => {
                                            const art = e.url ? articleStates.get(e.url) : undefined
                                            const tag = stateTag(art)
                                            return (
                                            <li key={i}>
                                                {e.url ? <a href={e.url} target="_blank" rel="noopener noreferrer">{e.headline}</a> : e.headline}
                                                {(e.source || e.date) ? (
                                                    <span className="dossier-src"> — {e.source ?? ''}{e.source && e.date ? ', ' : ''}{e.date ? fmtDay(e.date) : ''}</span>
                                                ) : null}
                                                {/* The tier the Brief already shows on its receipts —
                                                    state media in the evidence list was unmarked here
                                                    while the corroboration list marked it. Same
                                                    classifier, same chip; unknown renders nothing. */}
                                                <TierChip source={e.source} />
                                                {tag && <span className="dossier-ft-tag">{tag}</span>}
                                                {/* Enrichment F1: excerpt + citation, never republished full text */}
                                                {art?.status === 'ok' && art.excerpt && (
                                                    <blockquote className="dossier-fulltext">
                                                        “{art.excerpt}”
                                                        <span className="dossier-ft-meta"> — FROM THE SOURCE · fetched {art.fetched_at ? art.fetched_at.slice(0, 10) : 'earlier'}{art.via === 'wayback' ? ' · via Wayback Machine' : ''}</span>
                                                    </blockquote>
                                                )}
                                            </li>
                                            )
                                        })}
                                    </ul>
                                )}
                                {/* Story Lens Task 9: the neighborhood as MEASURED at pin
                                    time (the lens banner's "Pin story" button) — frozen,
                                    never re-fetched, same discipline as the evidence list
                                    above. */}
                                {p.snapshot?.siblings && p.snapshot.siblings.length > 0 && (
                                    <div className="dossier-pin-neighborhood">
                                        <div className="dossier-pin-neighborhood-title">MEASURED NEIGHBORHOOD (frozen)</div>
                                        {p.snapshot.siblings.map((s) => (
                                            <div key={s.id} className="dossier-pin-neighborhood-row">
                                                {s.label} <span className="dossier-pin-neighborhood-reason">↔ {s.reason}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                                {p.note && <div className="dossier-note">Note: {p.note}</div>}
                                {(chipsByPin.get(p.anchorId) ?? []).map(chip => (
                                    <VerdictChip
                                        key={chip.id}
                                        descriptor={chip}
                                        investigationId={investigation.id}
                                        perform={performVerdict}
                                        onChange={onMutate}
                                    />
                                ))}
                            </div>
                            )
                        })
                    )}
                </section>

                {sourceMixText && (
                    <section className="dossier-section dossier-source-mix">
                        <h2>Source mix</h2>
                        <p className="dossier-meta" data-tip="Coarse credibility tiers (#217) of the pinned receipts: wire = international agency, state = state broadcaster, major = established national press, local = registered/regional outlet, unknown = no signal (never guessed). Wire-driven vs single-local-sourced at a glance.">
                            {investigation.citations.length} pinned receipt{investigation.citations.length === 1 ? '' : 's'} · {sourceMixText}
                        </p>
                    </section>
                )}

                {claimRows.length > 0 && (
                    <section className="dossier-section dossier-claims">
                        <h2>Contested figures</h2>
                        <p className="dossier-meta" data-tip="Figures the analyst marked as corroborating or contradicting across pinned receipts. When no official/wire source backs a contested number, the row is flagged.">
                            claim ledger · figures put side by side, with source provenance
                        </p>
                        <div className="dossier-claims-scroll">
                            <table className="dossier-claim-table">
                                <thead>
                                    <tr>
                                        <th>Figure</th>
                                        <th>Outlet</th>
                                        <th>Country</th>
                                        <th>Date</th>
                                        <th>Relation</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {claimRows.map((r, i) => (
                                        <tr
                                            key={`${r.claimId}-${i}`}
                                            className={`dossier-claim-row dossier-claim-row--${r.relation.toLowerCase()}${r.official ? ' dossier-claim-row--official' : ''}`}
                                        >
                                            <td className="dossier-claim-figure">{r.figureText}</td>
                                            <td>
                                                {r.outlet ?? '—'}
                                                {r.official && <span className="dossier-claim-official" data-tip="Official / wire source (government, UN, or an international wire agency).">official</span>}
                                            </td>
                                            <td>{r.country ?? '—'}</td>
                                            <td>{r.date ? fmtDay(r.date) : '—'}</td>
                                            <td><span className={`dossier-claim-rel dossier-claim-rel--${r.relation.toLowerCase()}`}>{r.relation}</span></td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        {/* Caveat: one line per claim with no official/wire backing. */}
                        {[...new Map(claimRows.filter(r => !r.officialSourcePresent).map(r => [r.claimId, r])).values()].map(r => (
                            <p key={r.claimId} className="dossier-claim-caveat" role="note">
                                No official/wire source backs this {r.relation.toLowerCase()} figure — treat as contested.
                                {/* Task 5.4 — a contested figure gets the corroborate verb.
                                    Corroboration is a PAID LLM pass → explicit click only; it
                                    forces a fresh web-corroboration run over every evidence pin. */}
                                {resolveLauncherVerbs('contested-figure').map(v => (
                                    <button
                                        key={v.verb}
                                        className="dossier-launcher dossier-launcher--corroborate"
                                        data-tip={v.tip}
                                        disabled={corrobRunning || dossier.pinCount === 0}
                                        onClick={() => void runCorroboration(true)}
                                    >{corrobRunning ? 'Corroborating…' : v.label}</button>
                                ))}
                            </p>
                        ))}
                    </section>
                )}

                {dossier.pinCount >= 2 && (
                    <section className="dossier-section">
                        <h2>Connection analysis</h2>
                        <p className="dossier-meta" data-tip="Do these pinned stories form one narrative, and which sub-clusters connect? Semantic proximity + shared entities, measured now.">
                            do these stories connect — and which sub-narratives hold?
                        </p>
                        <DossierConnections
                            inv={investigation} onData={onConnections}
                            onOpenThread={onOpenThread} onPinTopic={pinWalkedTopic}
                        />
                    </section>
                )}

                {(crossRead || crossRunning || crossFailed) && (
                    <section className="dossier-section dossier-crossread">
                        <h2>Source cross-read</h2>
                        {crossRunning ? (
                            <p className="dossier-meta">AI-reading the fetched source texts and comparing quote-backed claims…</p>
                        ) : crossFailed ? (
                            <p className="dossier-meta">Cross-read unavailable right now (rate limit or network) — the frozen report stands; try again in a few minutes.</p>
                        ) : crossRead && (
                            <>
                                <p className="dossier-meta" data-tip={crossRead.note ?? ''}>
                                    AI READ{crossRead.model ? ` · ${crossRead.model}` : ''} · {crossRead.articles_with_claims} of {crossRead.articles_read} read sources with quote-backed claims · {crossRead.independent_corroborations ?? 0} independent corroboration{(crossRead.independent_corroborations ?? 0) === 1 ? '' : 's'}{(crossRead.shared_source_findings ?? 0) > 0 ? ` · ${crossRead.shared_source_findings} same-source (not counted)` : ''} · verify the quotes
                                </p>
                                {crossRead.findings.length === 0 && (
                                    <p className="dossier-meta">{crossRead.reason ? `Not comparable: ${crossRead.reason}.` : 'No corroborations or tensions visible between the quote-backed claims.'}</p>
                                )}
                                {crossRead.findings.map((f, i) => (
                                    <div key={i} className={`dossier-crossread-finding dossier-crossread-finding--${f.kind}`}>
                                        <span className="dossier-crossread-kind">{crossFindingLabel(f.kind, f.independence?.reason)}</span>
                                        {f.independence && (
                                            <span className={`dossier-crossread-independence dossier-crossread-independence--${f.independence.independent ? 'yes' : 'no'}`}
                                                data-tip={independenceTip(f.independence)}>
                                                {f.independence.label}
                                            </span>
                                        )}
                                        <p className="dossier-crossread-note">{f.note}</p>
                                        <blockquote>“{f.a.quote}” <span className="dossier-ft-meta">— {f.a.outlet || f.a.url}</span></blockquote>
                                        <blockquote>“{f.b.quote}” <span className="dossier-ft-meta">— {f.b.outlet || f.b.url}</span></blockquote>
                                        {/* Task 5.4 — a discrepancy between two sources gets the
                                            corroborate verb (PAID → explicit click; forces a fresh
                                            web-corroboration pass). Secondary: open each original
                                            source to read it directly. Only tensions carry it —
                                            corroborations/shared-source rows are already resolved. */}
                                        {f.kind === 'tension' && (
                                            <div className="dossier-launchers">
                                                {resolveLauncherVerbs('cross-read-tension').map(v => (
                                                    <button
                                                        key={v.verb}
                                                        className="dossier-launcher dossier-launcher--corroborate"
                                                        data-tip={v.tip}
                                                        disabled={corrobRunning || dossier.pinCount === 0}
                                                        onClick={() => void runCorroboration(true)}
                                                    >{corrobRunning ? 'Corroborating…' : v.label}</button>
                                                ))}
                                                {f.a.url && (
                                                    <a
                                                        className="dossier-launcher dossier-launcher--read"
                                                        href={f.a.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        data-tip="Read the first source directly"
                                                    >{f.a.outlet || 'source A'} ↗</a>
                                                )}
                                                {f.b.url && (
                                                    <a
                                                        className="dossier-launcher dossier-launcher--read"
                                                        href={f.b.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        data-tip="Read the second source directly"
                                                    >{f.b.outlet || 'source B'} ↗</a>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </>
                        )}
                    </section>
                )}

                {(corrob || corrobRunning || corrobFailed) && (
                    <section className="dossier-section dossier-corroboration">
                        <h2>Web corroboration</h2>
                        {corrobRunning ? (
                            <p className="dossier-meta">
                                Checking every evidence-bearing pin against live web coverage… DOC 2.0 permits one query every five seconds, so duration grows with the route.
                                {(corrobProgress?.queries_total ?? 0) > 0 && (
                                    <> {' '}<strong>{corrobProgress?.queries_done ?? 0} of {corrobProgress?.queries_total} search queries done.</strong></>
                                )}
                            </p>
                        ) : corrob ? (
                            <>
                                {corrob.search_available ? (
                                    <p className="dossier-meta" data-tip={corrob.meta?.independence_rule ?? ''}>
                                        measured {new Date(corrob.measured_at).toLocaleString()} · independent sources weighted · {corrob.search_source} · {corroborationWindowText(corrob)}
                                    </p>
                                ) : (
                                    <p className="dossier-meta">{corrob.meta?.search_note ?? 'Web-search lane unavailable — corroboration not measured.'}</p>
                                )}
                                {/* V5: a degraded run says which part of it is missing. An
                                    unmeasured pin must never read as "no coverage found". */}
                                {corroborationCoverageText(corrob) && (
                                    <p className="dossier-meta dossier-corrob-partial">
                                        ⚠ {corroborationCoverageText(corrob)}
                                    </p>
                                )}
                                {corrob.pins.map(p => (
                                    <div key={p.id} className="dossier-pin">
                                        <div className="dossier-pin-head">
                                            <span className={`badge dossier-corrob-chip dossier-corrob-chip--${p.status}`}>{statusChip(p.status)}</span>
                                            <span className="dossier-pin-label">{p.label}</span>
                                        </div>
                                        {/* The note is the backend's OWN sentence — in v2 it already
                                            names the voices and the ownership collapse ("only 2
                                            independent voice(s) (4 outlets; same-state outlets counted
                                            as one voice)"). Rendered whole, never truncated, never
                                            restated in our own words beside it. */}
                                        <div className="dossier-pin-summary">{p.note}</div>
                                        {pinSearchStatusText(p) && (
                                            <div className="dossier-meta dossier-corrob-lane">
                                                ⚠ {pinSearchStatusText(p)}
                                            </div>
                                        )}
                                        {/* corroborate-v2 verdict block — template-shaped and aged
                                            matches are SHOWN set-aside (muted), never folded into
                                            the backing count. Renders only when a verdict travels
                                            with the pin; today that is the per-claim lane
                                            (/api/v2/corroborate), which the report does not call. */}
                                        {verdictFacets(p.verdict).length > 0 && (
                                            <div className="dossier-corrob-verdict">
                                                {verdictFacets(p.verdict).map(f => (
                                                    <span
                                                        key={f.key}
                                                        className={`dossier-corrob-facet${f.setAside ? ' dossier-corrob-facet--aside' : ''}`}
                                                        data-tip={f.tip}
                                                    >{f.label}</span>
                                                ))}
                                            </div>
                                        )}
                                        {p.citations.length > 0 && (
                                            <ul className="dossier-evidence">
                                                {p.citations.map((c, i) => {
                                                    // corroborate-v2 R1: the credibility tier and the
                                                    // ownership group come MEASURED from the backend —
                                                    // the receipt says why it did not count twice.
                                                    const chip = citationTierChip(c)
                                                    const collapse = citationCollapseNote(c)
                                                    // R3: the receipt's own date, and whether it falls
                                                    // outside the window this run measured. An undated
                                                    // row is never called aged.
                                                    const day = citationDateText(c)
                                                    const aged = citationAged(c, corrob)
                                                    return (
                                                        <li key={i} className={aged ? 'dossier-corrob-cit--aged' : undefined}>
                                                            {c.url ? <a href={c.url} target="_blank" rel="noopener noreferrer">{c.title}</a> : c.title}
                                                            <span className="dossier-src"> — {c.outlet}{day ? `, ${day}` : ''}{c.lane === 'client-supplied' ? ' (supplied)' : ''}</span>
                                                            {aged && (
                                                                <span className="dossier-corrob-aged" data-tip={agedTip(corrob.window_days)}>· outside the {corrob.window_days}-day window</span>
                                                            )}
                                                            {chip && (
                                                                <span
                                                                    className={`l2-tier-chip l2-tier-chip--${citationTierClass(c)}`}
                                                                    data-tip={c.credibility?.provenance ? `Credibility tier recorded at measurement (${c.credibility.provenance}).` : 'Credibility tier recorded at measurement.'}
                                                                >{chip.replace(/^\[|\]$/g, '')}</span>
                                                            )}
                                                            {collapse && (
                                                                <span className="dossier-corrob-collapse" data-tip={collapse}>· one voice</span>
                                                            )}
                                                        </li>
                                                    )
                                                })}
                                            </ul>
                                        )}
                                    </div>
                                ))}
                                {corrob.coverage_asymmetry?.note && (
                                    <div className="dossier-pin">
                                        <div className="dossier-pin-head">
                                            <span className="dossier-pin-label">Coverage asymmetry</span>
                                            <span className="dossier-pin-type">what the web emphasizes vs the pinned evidence</span>
                                        </div>
                                        <div className="dossier-pin-summary">{corrob.coverage_asymmetry.note}</div>
                                        <p className="dossier-meta">phrased from the gathered titles only{corrob.coverage_asymmetry.provider ? ` · ${corrob.coverage_asymmetry.provider}` : ''}</p>
                                    </div>
                                )}
                            </>
                        ) : (
                            <p className="dossier-meta">Corroboration failed — the search lane did not answer. Re-run from the button above.</p>
                        )}
                    </section>
                )}

                {dossier.enrichment && Object.keys(dossier.enrichment.whoSaysWhat).length > 0 && (
                    <section className="dossier-section">
                        <h2>Who says what — press vs public</h2>
                        <p className="dossier-meta" data-tip="Typed member roles: press = verified evidence, public = forum/social discussion (never verified). Measured now, not frozen at pin time.">
                            measured at generation time · typed member roles
                        </p>
                        {dossier.pins.map(p => {
                            const e = dossier.enrichment!.whoSaysWhat[p.anchorId]
                            if (!e) return null
                            return (
                                <div key={p.anchorId} className="dossier-pin">
                                    <div className="dossier-pin-head">
                                        <span className="dossier-pin-label">{p.label}</span>
                                        <span className="dossier-pin-type">{e.relationship}</span>
                                    </div>
                                    <div className="dossier-pin-summary">
                                        press {e.evidenceCount} · public {e.discussionCount}
                                        {e.moodCount > 0 ? ` · mood ${e.moodCount}` : ''} — {e.rationale}
                                    </div>
                                    {e.sourceTiers && (
                                        <div className="dossier-pin-tiers" data-tip="Credibility tiers of the sources backing this story (#217) — labels with provenance, measured now.">
                                            receipts by tier: {Object.entries(e.sourceTiers)
                                                .sort((a, b) => b[1] - a[1])
                                                .map(([t, n]) => `${t} ${n}`).join(' · ')}
                                        </div>
                                    )}
                                </div>
                            )
                        })}
                    </section>
                )}

                {dossier.enrichment && Object.keys(dossier.enrichment.voice).length > 0 && (
                    <section className="dossier-section">
                        <h2>Voice — who covers, not just who is covered</h2>
                        <p className="dossier-meta">self-voice = outlet ownership, not language · 168h window</p>
                        {Object.entries(dossier.enrichment.voice).map(([cc, v]) => (
                            <div key={cc} className="dossier-pin">
                                <div className="dossier-pin-head">
                                    <span className="dossier-pin-label">{cc}</span>
                                </div>
                                <div className="dossier-pin-summary">
                                    {v.selfVoiceRatio !== null && <>self-voice {(v.selfVoiceRatio * 100).toFixed(0)}% · </>}
                                    {v.dominantOutsider && <>dominant outsider {v.dominantOutsider} · </>}
                                    {v.stateMediaPct !== null && <>state media {v.stateMediaPct.toFixed(0)}% · </>}
                                    {v.topForeignOrigins.length > 0 && <>top foreign: {v.topForeignOrigins.join(', ')}</>}
                                </div>
                            </div>
                        ))}
                    </section>
                )}

                {dossier.categoryGroups.some(g => g.category !== null) && (
                    <section className="dossier-section">
                        <h2>Categories covered</h2>
                        <ul className="dossier-timeline">
                            {dossier.categoryGroups.map((g, i) => (
                                <li key={i}>
                                    <span className="dossier-tl-action">{g.category ?? 'uncategorized'}</span>
                                    <span className="dossier-tl-detail">
                                        {g.anchorIds.map(id => dossier.pins.find(p => p.anchorId === id)?.label).filter(Boolean).join('; ')}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </section>
                )}

                <section className="dossier-section">
                    <h2>Timeline</h2>
                    <ul className="dossier-timeline">
                        {dossier.timeline.map((s, i) => (
                            <li key={i}>
                                <span className="dossier-tl-action">{s.action}</span>
                                <span className="dossier-tl-detail">{s.detail}</span>
                            </li>
                        ))}
                    </ul>
                </section>

                {dossier.enrichment && dossier.enrichment.coverageGaps.length > 0 && (
                    <section className="dossier-section">
                        <h2>What is missing — attention without verified coverage</h2>
                        <p className="dossier-meta" data-tip="Categories with attention (raw signals) but zero gate-verified coverage in the last 24h. The wedge's 'what is missing', measured at generation.">
                            measured at generation time · global, last 24h
                        </p>
                        <ul className="dossier-timeline">
                            {dossier.enrichment.coverageGaps.map((g, i) => (
                                <li key={i}>
                                    <span className="dossier-tl-action">{g.label}</span>
                                    <span className="dossier-tl-detail">
                                        {g.rawSignals} raw signals · {g.status === 'gate_pending' ? 'awaiting gate' : 'none verified'}
                                    </span>
                                    {/* Task 5.3 — measured coverage absence: the category has
                                        attention but no verified coverage. GENERATE a query for it. */}
                                    {onFreshQuery && resolveLauncherVerbs('coverage-gap').map(v => (
                                        <button
                                            key={v.verb}
                                            className="dossier-launcher dossier-launcher--fresh-query"
                                            data-tip={v.tip}
                                            onClick={() => onFreshQuery(g.label)}
                                        >{v.label}</button>
                                    ))}
                                </li>
                            ))}
                        </ul>
                    </section>
                )}

                <section className="dossier-section dossier-gaps">
                    <h2>Gaps &amp; uncertainty</h2>
                    <ul>
                        {dossier.gaps.map((g, i) => (
                            <li key={i}>
                                <span className="dossier-gap-text">{g}</span>
                                {/* Task 5.3 — a gap is an ABSENCE: the one place the app
                                    GENERATES rather than navigates. The launcher spins a
                                    fresh query for the missing coverage. Gated on onFreshQuery
                                    so the report-export/inert path stays byte-identical. */}
                                {onFreshQuery && resolveLauncherVerbs('coverage-gap').map(v => (
                                    <button
                                        key={v.verb}
                                        className="dossier-launcher dossier-launcher--fresh-query"
                                        data-tip={v.tip}
                                        onClick={() => onFreshQuery(g)}
                                    >{v.label}</button>
                                ))}
                            </li>
                        ))}
                    </ul>
                </section>
            </div>
        </div>
    )
}
