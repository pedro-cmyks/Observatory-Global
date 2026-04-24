import React, { useEffect, useState, useCallback } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { timeRangeToHours } from '../lib/timeRanges'
import { getThemeLabel } from '../lib/themeLabels'

function matrixAbbrev(label: string): string {
    const words = label.replace(/[:\-]/g, ' ').split(/\s+/).filter(w => w.length > 1)
    if (words.length === 0) return '?'
    if (words.length === 1) return words[0].slice(0, 4)
    return words.map(w => w[0].toUpperCase()).join('').slice(0, 4)
}
import './CorrelationMatrix.css'

interface CorrelationData {
    mode: 'country' | 'theme'
    entities: string[]
    entity_names: Record<string, string>
    matrix: number[][]
    hours: number
}

interface MatrixTooltip {
    x: number
    y: number
    title: string
    subtitle: string
}

export const CorrelationMatrix: React.FC = () => {
    const [mode, setMode] = useState<'country' | 'theme'>('country')
    const [data, setData] = useState<CorrelationData | null>(null)
    const [loading, setLoading] = useState(true)
    const [hoverCoords, setHoverCoords] = useState<[number, number] | null>(null)
    const [tooltipData, setTooltipData] = useState<MatrixTooltip | null>(null)
    
    const { setCountry, setFocus } = useFocus()
    const { timeRange } = useFocusData()

    const hours = timeRangeToHours(timeRange)

    const fetchMatrix = useCallback(async () => {
        setLoading(true)
        try {
            const res = await fetch(`/api/v2/correlation?mode=${mode}&hours=${hours}&limit=12`)
            if (res.ok) {
                const jsonData = await res.json()
                setData(jsonData)
            }
        } catch (e) {
            console.error('[CorrelationMatrix] Fetch error:', e)
        } finally {
            setLoading(false)
        }
    }, [mode, hours])

    useEffect(() => {
        fetchMatrix()
        const interval = setInterval(fetchMatrix, 5 * 60 * 1000)
        return () => clearInterval(interval)
    }, [fetchMatrix])

    const handleCellClick = (rowIdx: number, colIdx: number) => {
        if (!data || rowIdx === colIdx) return
        
        const e1 = data.entities[rowIdx]
        const name1 = data.entity_names[e1] || e1

        if (mode === 'country') {
            setCountry(e1)
        } else {
            setFocus('theme', e1, name1)
        }
    }

    const handleMouseEnter = (rowIdx: number, colIdx: number, e: React.MouseEvent) => {
        setHoverCoords([rowIdx, colIdx])
        if (!data || rowIdx === colIdx) return
        
        const name1 = data.entity_names[data.entities[rowIdx]]
        const name2 = data.entity_names[data.entities[colIdx]]
        const score = data.matrix[rowIdx][colIdx]
        
        setTooltipData({
            x: e.clientX,
            y: e.clientY - 40,
            title: `${name1} ↔ ${name2}`,
            subtitle: `Similarity: ${(score * 100).toFixed(1)}%`
        })
    }

    const handleMouseLeave = () => {
        setHoverCoords(null)
        setTooltipData(null)
    }

    // Normalize to actual data range so small variance becomes visible
    let normalizeScore = (_s: number) => 0
    if (data && data.matrix.length > 0) {
        const offDiag = data.matrix.flatMap((row, r) => row.filter((_, c) => r !== c))
        const dataMin = Math.min(...offDiag)
        const dataMax = Math.max(...offDiag)
        const range = dataMax - dataMin || 1
        normalizeScore = (s: number) => Math.pow((s - dataMin) / range, 0.6)
    }

    return (
        <div className="correlation-matrix-container">
            <div className="matrix-controls">
                <button
                    className={`matrix-toggle ${mode === 'country' ? 'active' : ''}`}
                    onClick={() => setMode('country')}
                >
                    [Country × Country]
                </button>
                <button
                    className={`matrix-toggle ${mode === 'theme' ? 'active' : ''}`}
                    onClick={() => setMode('theme')}
                >
                    [Theme × Theme]
                </button>
            </div>

            <div className="matrix-grid-wrapper">
                {loading && !data ? (
                    <div className="matrix-loading">
                        {Array.from({ length: 144 }).map((_, i) => (
                            <div key={i} className="skeleton-cell" />
                        ))}
                    </div>
                ) : data && data.matrix.length > 0 ? (
                    <div
                        className={`matrix-grid ${hoverCoords ? 'hover-active' : ''}`}
                        style={{
                            gridTemplateColumns: `auto repeat(${data.entities.length}, 24px)`,
                            gridTemplateRows: `${mode === 'theme' ? 40 : 60}px repeat(${data.entities.length}, 24px)`
                        }}
                        onMouseLeave={handleMouseLeave}
                    >
                        {/* Empty top-left corner */}
                        <div></div>

                        {/* Column Headers */}
                        {data.entities.map((e, idx) => {
                            const fullLabel = mode === 'theme' ? getThemeLabel(e) : (data.entity_names[e] || e)
                            const label = mode === 'theme' ? matrixAbbrev(fullLabel) : e
                            return (
                                <div
                                    key={`col-${idx}`}
                                    className={`matrix-col-header ${mode === 'theme' ? 'theme-mode' : ''} ${hoverCoords && hoverCoords[1] === idx ? 'highlight' : ''}`}
                                    title={fullLabel}
                                >
                                    {label}
                                </div>
                            )
                        })}

                        {/* Rows */}
                        {data.entities.map((rowEntity, rowIdx) => {
                            const rowLabel = mode === 'theme'
                                ? getThemeLabel(rowEntity).slice(0, 8)
                                : rowEntity
                            const rowFullLabel = mode === 'theme' ? getThemeLabel(rowEntity) : (data.entity_names[rowEntity] || rowEntity)
                            return (
                            <React.Fragment key={`row-${rowIdx}`}>
                                {/* Row Header */}
                                <div
                                    className={`matrix-row-header ${hoverCoords && hoverCoords[0] === rowIdx ? 'highlight' : ''}`}
                                    title={rowFullLabel}
                                >
                                    {rowLabel}
                                </div>

                                {/* Cells */}
                                {data.matrix[rowIdx].map((score, colIdx) => {
                                    const norm = normalizeScore(score)
                                    const bg = rowIdx !== colIdx
                                        ? norm < 0.15
                                            ? `rgba(29, 158, 117, ${(norm * 0.6).toFixed(3)})`
                                            : norm < 0.5
                                                ? `rgba(56, 189, 148, ${norm.toFixed(3)})`
                                                : `rgba(74, 222, 128, ${norm.toFixed(3)})`
                                        : undefined
                                    return (
                                        <div
                                            key={`cell-${rowIdx}-${colIdx}`}
                                            className={`matrix-cell ${rowIdx === colIdx ? 'diagonal' : ''}`}
                                            style={bg ? { backgroundColor: bg } : {}}
                                            onMouseEnter={(e) => handleMouseEnter(rowIdx, colIdx, e)}
                                            onClick={() => handleCellClick(rowIdx, colIdx)}
                                        />
                                    )
                                })}
                            </React.Fragment>
                        )})}
                    </div>
                ) : (
                    <div className="matrix-error">Correlation data unavailable</div>
                )}
            </div>

            {tooltipData && (
                <div style={{
                    position: 'fixed',
                    left: tooltipData.x + 10,
                    top: tooltipData.y + 10,
                    background: 'rgba(10, 22, 40, 0.95)',
                    border: '1px solid #1e3a5f',
                    borderRadius: '4px',
                    padding: '8px 12px',
                    pointerEvents: 'none',
                    zIndex: 1000,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                    whiteSpace: 'nowrap'
                }}>
                    <div style={{ color: '#fff', fontSize: '11px', fontWeight: 'bold', marginBottom: '4px' }}>
                        {tooltipData.title}
                    </div>
                    <div style={{ color: '#94a3b8', fontSize: '10px' }}>
                        {tooltipData.subtitle}
                    </div>
                </div>
            )}
        </div>
    )
}
