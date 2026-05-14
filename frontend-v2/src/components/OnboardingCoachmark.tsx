import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import './OnboardingCoachmark.css'

const STORAGE_KEY = 'atlas_onboarding_v3'

type TourAction = 'focus-search' | 'open-brief' | 'open-workspace'

interface TourStep {
    selector: string
    eyebrow: string
    title: string
    body: string
    actionLabel?: string
    action?: TourAction
}

const STEPS: TourStep[] = [
    {
        selector: '[data-tour="search"]',
        eyebrow: 'Start here',
        title: 'Ask Atlas for a country, person, source, or theme',
        body: 'Search is the fastest way into the console. Try a country like Colombia, a public figure, or a geopolitical topic.',
        actionLabel: 'Focus search',
        action: 'focus-search',
    },
    {
        selector: '[data-tour="globe"]',
        eyebrow: 'Global map',
        title: 'Click the map when you want country context',
        body: 'The globe is a live orientation layer. A country click opens its brief in the center panel and pivots the rest of the console.',
    },
    {
        selector: '[data-tour="stream"]',
        eyebrow: 'Signal stream',
        title: 'Use the stream as a pivot engine, not a raw feed',
        body: 'Atlas starts with notable signals. Click a country, person, source, theme, or headline to turn one signal into a focused investigation.',
    },
    {
        selector: '[data-tour="threads"]',
        eyebrow: 'Narrative threads',
        title: 'Follow themes instead of individual headlines',
        body: 'Threads show what is spreading across countries, how sentiment is moving, and which topics deserve a deeper drill-down.',
    },
    {
        selector: '[data-tour="anomaly-attention"]',
        eyebrow: 'Signals vs attention',
        title: 'Use anomalies and public attention as the second lens',
        body: 'Anomaly Alert flags unusual media movement. Public Attention shows what people are reading or searching, so you can compare public interest against the media stream.',
    },
    {
        selector: '[data-tour="workspace-button"]',
        eyebrow: 'Investigation workspace',
        title: 'Pin anything worth keeping',
        body: 'Pins and recent visits build a relationship graph. Open the workspace when you want to connect countries, themes, people, sources, and signals.',
        actionLabel: 'Open workspace',
        action: 'open-workspace',
    },
    {
        selector: '[data-tour="brief-button"]',
        eyebrow: 'Daily brief',
        title: 'Use the brief for non-power users',
        body: 'The brief is the readable entry point. It gives people a global front page before they enter the full analyst console.',
        actionLabel: 'Open brief',
        action: 'open-brief',
    },
]

function getTargetRect(selector: string): DOMRect | null {
    const element = document.querySelector(selector)
    return element?.getBoundingClientRect() ?? null
}

function getCardStyle(rect: DOMRect | null): CSSProperties {
    if (!rect) {
        return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
    }

    const width = 360
    const gap = 14
    const leftSpace = rect.left
    const rightSpace = window.innerWidth - rect.right
    const preferRight = rightSpace >= width + gap || rightSpace >= leftSpace
    const left = preferRight
        ? Math.min(rect.right + gap, window.innerWidth - width - 16)
        : Math.max(16, rect.left - width - gap)
    const top = Math.min(Math.max(16, rect.top), window.innerHeight - 260)

    return { top, left, width }
}

interface OnboardingCoachmarkProps {
    runId?: number
    onOpenBrief?: () => void
    onOpenWorkspace?: () => void
    entryContext?: string
}

export function OnboardingCoachmark({ runId = 0, onOpenBrief, onOpenWorkspace, entryContext }: OnboardingCoachmarkProps) {
    const [step, setStep] = useState(0)
    const [visible, setVisible] = useState(() => {
        try {
            return !localStorage.getItem(STORAGE_KEY)
        } catch {
            return false
        }
    })
    const [targetRect, setTargetRect] = useState<DOMRect | null>(null)

    useEffect(() => {
        if (runId > 0) {
            setStep(0)
            setVisible(true)
        }
    }, [runId])

    useEffect(() => {
        if (!visible) return

        const updateRect = () => setTargetRect(getTargetRect(STEPS[step].selector))
        updateRect()
        const id = window.setTimeout(updateRect, 150)
        window.addEventListener('resize', updateRect)
        window.addEventListener('scroll', updateRect, true)
        return () => {
            window.clearTimeout(id)
            window.removeEventListener('resize', updateRect)
            window.removeEventListener('scroll', updateRect, true)
        }
    }, [step, visible])

    if (!visible) return null

    const dismiss = () => {
        try { localStorage.setItem(STORAGE_KEY, '1') } catch { /* noop */ }
        setVisible(false)
    }

    const next = () => {
        if (step < STEPS.length - 1) {
            setStep(s => s + 1)
        } else {
            dismiss()
        }
    }

    const runAction = () => {
        const action = STEPS[step].action
        if (action === 'focus-search') {
            const input = document.querySelector<HTMLInputElement>('[data-tour="search"] input')
            input?.focus()
        }
        if (action === 'open-workspace') onOpenWorkspace?.()
        if (action === 'open-brief') onOpenBrief?.()
    }

    const current = STEPS[step]
    const highlightStyle = targetRect
        ? {
            top: targetRect.top - 6,
            left: targetRect.left - 6,
            width: targetRect.width + 12,
            height: targetRect.height + 12,
        }
        : undefined

    return (
        <div className="onboarding-layer" aria-live="polite">
            <div className="onboarding-scrim" />
            {highlightStyle && <div className="onboarding-highlight" style={highlightStyle} />}
            <div className="onboarding-card" style={getCardStyle(targetRect)}>
                <div className="onboarding-step-indicator">
                    {STEPS.map((_, i) => (
                        <span key={i} className={`onboarding-dot ${i === step ? 'active' : ''}`} />
                    ))}
                </div>
                <div className="onboarding-eyebrow">{current.eyebrow}</div>
                <p className="onboarding-title">{current.title}</p>
                <p className="onboarding-body">{current.body}</p>
                {entryContext && step === 0 && (
                    <p className="onboarding-entry-context">{entryContext}</p>
                )}
                <div className="onboarding-actions">
                    <button className="onboarding-skip" onClick={dismiss}>
                        Skip tour
                    </button>
                    <div className="onboarding-action-group">
                        {current.actionLabel && (
                            <button className="onboarding-try" onClick={runAction}>
                                {current.actionLabel}
                            </button>
                        )}
                        <button className="onboarding-next" onClick={next}>
                            {step < STEPS.length - 1 ? 'Next' : 'Done'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
