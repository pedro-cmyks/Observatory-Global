import { useState, useRef, useEffect } from 'react'
import { Download, Link, FileText, Image, Table, Check, X } from '../lib/icons'
import * as htmlToImage from 'html-to-image'
import {
    buildThemeBriefingMarkdown,
    buildThemeSignalsCsv,
    rowsToCsv,
    sanitizeFilenamePart,
    type ThemeExportData,
} from '../lib/exportFormatters'
import './ExportMenu.css'

interface ExportMenuProps {
    themeName: string
    data: ThemeExportData
    insight: string | null
    captureRef: React.RefObject<HTMLElement | null>
}

interface DriftPoint {
    date: string
    sentiment: number
    volume: number
}

export function ExportMenu({ themeName, data, insight, captureRef }: ExportMenuProps) {
    const [open, setOpen] = useState(false)
    const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'failed'>('idle')
    const menuRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    // Fix round 2026-07-17 item 5: closing the menu on the same tick hid the
    // "Copied!" swap — the click gave ZERO feedback. Same pattern DossierView
    // uses: show "Copied ✓" in place for a beat, then close.
    const handleCopyLink = async () => {
        try {
            await navigator.clipboard.writeText(window.location.href)
        } catch {
            // Round-2 item 4: a failed copy must SAY so — the silent return
            // left the user believing the link was on the clipboard. Same
            // in-place swap as "Copied ✓"; the menu STAYS OPEN for a retry.
            setCopyStatus('failed')
            setTimeout(() => setCopyStatus('idle'), 2500)
            return
        }
        setCopyStatus('copied')
        setTimeout(() => {
            setCopyStatus('idle')
            setOpen(false)
        }, 1500)
    }

    const downloadFile = (filename: string, content: string, type: string) => {
        const blob = new Blob([content], { type })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const handleExportCSV = async () => {
        if (!data || !data.signals) return

        const filenameTheme = sanitizeFilenamePart(themeName)
        const signalsCsv = buildThemeSignalsCsv(data.signals)
        downloadFile(`atlas-signals-${filenameTheme}-${new Date().toISOString().split('T')[0]}.csv`, signalsCsv, 'text/csv')
        
        // 2. Export Narrative Drift
        try {
            // Find the raw theme code from the data object if available, otherwise use the label
            const themeCode = data.theme || themeName
            const res = await fetch(`/api/v2/theme/${encodeURIComponent(themeCode)}/drift?days=14`)
            if (res.ok) {
                const driftJson = await res.json() as { drift?: DriftPoint[] }
                if (driftJson.drift && driftJson.drift.length > 0) {
                    const driftCsv = rowsToCsv(['date', 'sentiment', 'volume'], driftJson.drift.map(d => [
                        d.date,
                        d.sentiment,
                        d.volume,
                    ]))
                    // Add a tiny delay so the browser doesn't block the second download
                    setTimeout(() => {
                        downloadFile(`atlas-drift-${filenameTheme}-${new Date().toISOString().split('T')[0]}.csv`, driftCsv, 'text/csv')
                    }, 500)
                }
            }
        } catch (err) {
            console.error("Failed to export drift data:", err)
        }

        setOpen(false)
    }

    const handleExportBriefing = () => {
        if (!data) return

        const md = buildThemeBriefingMarkdown({ themeName, data, insight })
        downloadFile(`atlas-briefing-${sanitizeFilenamePart(themeName)}-${new Date().toISOString().split('T')[0]}.md`, md, 'text/markdown')
        setOpen(false)
    }

    const handleExportPNG = async () => {
        if (!captureRef.current) return
        setOpen(false)
        
        try {
            const dataUrl = await htmlToImage.toPng(captureRef.current, {
                quality: 1,
                backgroundColor: '#0a0c10',
                pixelRatio: 2,
                style: {
                    transform: 'none',
                    borderRadius: '0'
                }
            })
            
            const a = document.createElement('a')
            a.download = `atlas-snapshot-${themeName.toLowerCase()}-${new Date().toISOString().split('T')[0]}.png`
            a.href = dataUrl
            a.click()
        } catch (err) {
            console.error('Failed to export PNG', err)
            alert('Failed to generate image. The panel might contain cross-origin resources.')
        }
    }

    return (
        <div className="export-menu-wrap" ref={menuRef}>
            <button 
                className="export-menu-btn" 
                onClick={() => setOpen(!open)}
                data-tip="Export intelligence"
            >
                <Download size={14} />
                Export
            </button>
            
            {open && (
                <div className="export-menu-dropdown">
                    <button className="export-menu-item" onClick={handleCopyLink}>
                        {copyStatus === 'copied' ? <Check size={14} color="#10b981" />
                            : copyStatus === 'failed' ? <X size={14} color="#f87171" />
                                : <Link size={14} />}
                        {copyStatus === 'copied' ? 'Copied ✓'
                            : copyStatus === 'failed' ? 'Copy failed'
                                : 'Copy Shareable Link'}
                    </button>
                    <div className="export-menu-divider" />
                    <button className="export-menu-item" onClick={handleExportCSV}>
                        <Table size={14} />
                        Export Data (CSV)
                    </button>
                    <button className="export-menu-item" onClick={handleExportBriefing}>
                        <FileText size={14} />
                        Export Briefing (MD)
                    </button>
                    <button className="export-menu-item" onClick={handleExportPNG}>
                        <Image size={14} />
                        Export Snapshot (PNG)
                    </button>
                </div>
            )}
        </div>
    )
}
