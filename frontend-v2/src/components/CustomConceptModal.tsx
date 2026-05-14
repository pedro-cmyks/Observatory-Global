import { useState, useEffect, useRef } from 'react'
import { X, Plus, Search } from 'lucide-react'
import { getThemeLabel } from '../lib/themeLabels'
import type { CustomConcept } from '../hooks/useCustomConcepts'
import './CustomConceptModal.css'

interface ThemeHit {
    code: string
    label: string
}

interface Props {
    initial?: CustomConcept
    onSave: (label: string, description: string, themes: string[]) => void
    onClose: () => void
}

export function CustomConceptModal({ initial, onSave, onClose }: Props) {
    const [label, setLabel] = useState(initial?.label ?? '')
    const [description, setDescription] = useState(initial?.description ?? '')
    const [selectedThemes, setSelectedThemes] = useState<string[]>(initial?.themes ?? [])
    const [themeQuery, setThemeQuery] = useState('')
    const [themeHits, setThemeHits] = useState<ThemeHit[]>([])
    const [searching, setSearching] = useState(false)
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

    useEffect(() => {
        if (!themeQuery.trim()) { setThemeHits([]); return }
        if (timerRef.current) clearTimeout(timerRef.current)
        timerRef.current = setTimeout(async () => {
            setSearching(true)
            try {
                const res = await fetch(`/api/v2/search?q=${encodeURIComponent(themeQuery)}&hours=168`)
                const data = await res.json()
                const hits: ThemeHit[] = (data.themes ?? []).slice(0, 8).map((t: { code: string }) => ({
                    code: t.code,
                    label: getThemeLabel(t.code),
                }))
                setThemeHits(hits.filter(h => !selectedThemes.includes(h.code)))
            } catch { /* noop */ }
            setSearching(false)
        }, 300)
        return () => { if (timerRef.current) clearTimeout(timerRef.current) }
    }, [themeQuery, selectedThemes])

    const addTheme = (code: string) => {
        if (!selectedThemes.includes(code)) setSelectedThemes(prev => [...prev, code])
        setThemeQuery('')
        setThemeHits([])
    }

    const removeTheme = (code: string) => setSelectedThemes(prev => prev.filter(t => t !== code))

    const valid = label.trim().length >= 2 && selectedThemes.length >= 1

    const handleSave = () => {
        if (!valid) return
        onSave(label.trim(), description.trim(), selectedThemes)
        onClose()
    }

    return (
        <div className="concept-modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
            <div className="concept-modal" role="dialog" aria-label="Create investigative concept">
                <div className="concept-modal-header">
                    <span className="concept-modal-title">{initial ? 'Edit Concept' : 'New Investigative Concept'}</span>
                    <button className="concept-modal-close" onClick={onClose} aria-label="Close"><X size={16} /></button>
                </div>

                <div className="concept-modal-body">
                    <label className="concept-field-label">Concept name *</label>
                    <input
                        className="concept-input"
                        placeholder="e.g. Artisanal Gold Mining"
                        value={label}
                        onChange={e => setLabel(e.target.value)}
                        maxLength={60}
                        autoFocus
                    />

                    <label className="concept-field-label">Description</label>
                    <textarea
                        className="concept-input concept-textarea"
                        placeholder="What are you investigating? Who, what, where."
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        maxLength={200}
                        rows={3}
                    />

                    <label className="concept-field-label">Signal themes * <span className="concept-field-hint">Search and pick GDELT themes that match this concept</span></label>
                    <div className="concept-theme-search-wrap">
                        <Search size={13} className="concept-theme-search-icon" />
                        <input
                            className="concept-input concept-theme-input"
                            placeholder="Search themes: conflict, corruption, migration…"
                            value={themeQuery}
                            onChange={e => setThemeQuery(e.target.value)}
                        />
                        {searching && <span className="concept-theme-searching">…</span>}
                    </div>

                    {themeHits.length > 0 && (
                        <div className="concept-theme-hits">
                            {themeHits.map(h => (
                                <button key={h.code} className="concept-theme-hit" onClick={() => addTheme(h.code)}>
                                    <Plus size={11} /> {h.label}
                                </button>
                            ))}
                        </div>
                    )}

                    {selectedThemes.length > 0 && (
                        <div className="concept-selected-themes">
                            {selectedThemes.map(code => (
                                <span key={code} className="concept-selected-chip">
                                    {getThemeLabel(code)}
                                    <button onClick={() => removeTheme(code)} aria-label={`Remove ${getThemeLabel(code)}`}><X size={10} /></button>
                                </span>
                            ))}
                        </div>
                    )}
                    {selectedThemes.length === 0 && (
                        <p className="concept-theme-empty">Add at least one theme to define the signal footprint.</p>
                    )}
                </div>

                <div className="concept-modal-footer">
                    <button className="concept-btn-cancel" onClick={onClose}>Cancel</button>
                    <button className="concept-btn-save" onClick={handleSave} disabled={!valid}>
                        {initial ? 'Save changes' : 'Create concept'}
                    </button>
                </div>
            </div>
        </div>
    )
}
