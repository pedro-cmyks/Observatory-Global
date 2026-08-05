import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useIsMobile } from '../hooks/useIsMobile'
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

// Mobile IA is tabbed (Brief / Lens / Live since #236 Task 6), not the desktop
// side-by-side panels — so the phone gets its own short tour anchored only to
// elements that are ALWAYS on screen (the search bar + the bottom tab bar).
// The card is a bottom sheet (see CSS) so Skip/Next are always reachable — the
// desktop beside-target positioning clipped off-screen and trapped the user.
//
// NEEDS A SECOND PASS IN TASK 8: Map and Pulse return as SECTIONS inside the
// Lens, and step 2 should name them once they do — right now the Lens is the
// threads field plus whatever you opened, so the copy describes only that.
const MOBILE_STEPS: TourStep[] = [
    {
        selector: '[data-tour="search"]',
        eyebrow: 'Start here',
        title: 'Search is the way in',
        body: 'Ask Atlas for a country, person, source, or theme — like "Colombia" or a public figure. It opens a focused view.',
        actionLabel: 'Focus search',
        action: 'focus-search',
    },
    {
        selector: '[data-tour="mobile-tabs"]',
        eyebrow: 'Three views',
        title: 'Switch with the bottom tabs',
        body: 'Brief = the day, read like a front page. Lens = whatever you are looking at right now. Live = the raw signal feed as it arrives.',
    },
    {
        selector: '',
        eyebrow: 'Pivot, don’t just scroll',
        title: 'Tap anything to drill in',
        body: 'Tap a thread, a source, or a headline and the Lens re-scopes to it. Anything you open can be pinned in the Workbench.',
    },
]

function getTargetRect(selector: string): DOMRect | null {
    if (!selector) return null
    const element = document.querySelector(selector)
    if (!element) return null
    const rect = element.getBoundingClientRect()
    // A target inside a hidden mobile tab has a 0×0 / off-screen box — treat it
    // as "no target" so we never anchor the card to something invisible.
    if (rect.width === 0 && rect.height === 0) return null
    return rect
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
    const isMobile = useIsMobile()
    const steps = isMobile ? MOBILE_STEPS : STEPS
    const [step, setStep] = useState(0)
    const [visible, setVisible] = useState(() => {
        try {
            // #244: an intent-carrying entry (landing story card / brief deep
            // link opened a specific theme/country) must NOT be covered by the
            // tour — the user came for a story, show it. Deferred, not marked
            // seen: the tour still fires on their next plain visit.
            const params = new URLSearchParams(window.location.search)
            if (params.get('theme') || params.get('country') || params.get('attention')) return false
            return !localStorage.getItem(STORAGE_KEY)
        } catch {
            return false
        }
    })
    const [targetRect, setTargetRect] = useState<DOMRect | null>(null)

    // Mark seen on first mount so navigating away without completing doesn't re-trigger
    useEffect(() => {
        if (visible) {
            try { localStorage.setItem(STORAGE_KEY, '1') } catch { /* noop */ }
        }
    }, []) // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        if (runId > 0) {
            setStep(0)
            setVisible(true)
        }
    }, [runId])

    useEffect(() => {
        if (!visible) return

        const updateRect = () => setTargetRect(getTargetRect(steps[step].selector))
        updateRect()
        const id = window.setTimeout(updateRect, 150)
        window.addEventListener('resize', updateRect)
        window.addEventListener('scroll', updateRect, true)
        return () => {
            window.clearTimeout(id)
            window.removeEventListener('resize', updateRect)
            window.removeEventListener('scroll', updateRect, true)
        }
    }, [step, visible, isMobile]) // eslint-disable-line react-hooks/exhaustive-deps

    // Clamp when the step set shrinks (e.g. desktop→mobile rotation mid-tour).
    const safeStep = Math.min(step, steps.length - 1)

    if (!visible) return null

    const dismiss = () => {
        try { localStorage.setItem(STORAGE_KEY, '1') } catch { /* noop */ }
        setVisible(false)
    }

    const next = () => {
        if (safeStep < steps.length - 1) {
            setStep(safeStep + 1)
        } else {
            dismiss()
        }
    }

    const runAction = () => {
        const action = steps[safeStep].action
        if (action === 'focus-search') {
            const input = document.querySelector<HTMLInputElement>('[data-tour="search"] input')
            input?.focus()
        }
        if (action === 'open-workspace') onOpenWorkspace?.()
        if (action === 'open-brief') onOpenBrief?.()
    }

    const current = steps[safeStep]
    // On mobile the highlight ring is distracting and the targets move with the
    // bottom-sheet card, so skip it; desktop keeps the anchored highlight.
    const highlightStyle = !isMobile && targetRect
        ? {
            top: targetRect.top - 6,
            left: targetRect.left - 6,
            width: targetRect.width + 12,
            height: targetRect.height + 12,
        }
        : undefined

    return (
        <div className="onboarding-layer" aria-live="polite">
            <div className="onboarding-scrim" onClick={isMobile ? dismiss : undefined} />
            {highlightStyle && <div className="onboarding-highlight" style={highlightStyle} />}
            <div
                className={`onboarding-card${isMobile ? ' onboarding-card--mobile' : ''}`}
                style={isMobile ? undefined : getCardStyle(targetRect)}
            >
                <div className="onboarding-step-indicator">
                    {steps.map((_, i) => (
                        <span key={i} className={`onboarding-dot ${i === safeStep ? 'active' : ''}`} />
                    ))}
                </div>
                <div className="onboarding-eyebrow">{current.eyebrow}</div>
                <p className="onboarding-title">{current.title}</p>
                <p className="onboarding-body">{current.body}</p>
                {entryContext && safeStep === 0 && (
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
                            {safeStep < steps.length - 1 ? 'Next' : 'Done'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
