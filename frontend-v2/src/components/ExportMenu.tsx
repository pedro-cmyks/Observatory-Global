import { useState, useRef, useEffect } from 'react'
import { Download, Link, FileText, Image, Table, Check } from 'lucide-react'
import * as htmlToImage from 'html-to-image'
import './ExportMenu.css'

interface ExportMenuProps {
    themeName: string
    data: any // using any here for brevity, we will parse carefully
    insight: string | null
    captureRef: React.RefObject<HTMLElement | null>
}

export function ExportMenu({ themeName, data, insight, captureRef }: ExportMenuProps) {
    const [open, setOpen] = useState(false)
    const [copied, setCopied] = useState(false)
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

    const handleCopyLink = () => {
        navigator.clipboard.writeText(window.location.href)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
        setOpen(false)
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

    const handleExportCSV = () => {
        if (!data || !data.signals) return
        
        const headers = ['date', 'source', 'title', 'sentiment', 'url']
        const rows = data.signals.map((s: any) => [
            s.timestamp,
            s.source || 'Unknown',
            `"${(s.title || '').replace(/"/g, '""')}"`,
            s.sentiment || 0,
            s.url || ''
        ])
        
        const csv = [headers.join(','), ...rows.map((r: any[]) => r.join(','))].join('\n')
        downloadFile(`atlas-export-${themeName.toLowerCase()}-${new Date().toISOString().split('T')[0]}.csv`, csv, 'text/csv')
        setOpen(false)
    }

    const handleExportBriefing = () => {
        if (!data) return

        let md = `# Atlas Intelligence Briefing: ${themeName}\n\n`
        md += `**Generated:** ${new Date().toUTCString()}\n\n`
        
        if (insight) {
            md += `## AI Insight\n${insight}\n\n`
        }

        md += `## Metrics\n`
        md += `- **Total Signals:** ${data.summary?.total_signals || 0}\n`
        md += `- **Average Sentiment:** ${data.summary?.avg_sentiment?.toFixed(2) || 0}\n\n`

        if (data.topSources && data.topSources.length > 0) {
            md += `## Top Sources\n`
            data.topSources.slice(0, 10).forEach((s: any) => {
                md += `- ${s.name}: ${s.count} signals\n`
            })
            md += '\n'
        }

        if (data.relatedThemes && data.relatedThemes.length > 0) {
            md += `## Related Topics\n`
            data.relatedThemes.slice(0, 10).forEach((t: any) => {
                md += `- ${t.theme}: ${t.count} co-occurrences\n`
            })
            md += '\n'
        }

        downloadFile(`atlas-briefing-${themeName.toLowerCase()}-${new Date().toISOString().split('T')[0]}.md`, md, 'text/markdown')
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
                title="Export Intelligence"
            >
                <Download size={14} />
                Export
            </button>
            
            {open && (
                <div className="export-menu-dropdown">
                    <button className="export-menu-item" onClick={handleCopyLink}>
                        {copied ? <Check size={14} color="#10b981" /> : <Link size={14} />}
                        {copied ? 'Copied!' : 'Copy Shareable Link'}
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
