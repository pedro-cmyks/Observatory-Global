import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useIsMobile } from '../hooks/useIsMobile'
import './OnboardingCoachmark.css'
import './CountryFocusWalkthrough.css'

// L2 deep-review A4: a contextual 2-step walkthrough fired the FIRST time a
// user selects a country, teaching the select/deselect model (the A1 focus
// chip). Distinct from the first-session OnboardingCoachmark tour — own storage
// key, own trigger (handleCountryClick), so the two never collide. Reuses the
// .onboarding-* card chrome per spec ("reuse the pattern, not the component").
export const COUNTRY_WALKTHROUGH_KEY = 'atlas_country_walkthrough_v1'

interface Step {
    eyebrow: string
    title: string
    body: string
    // Optional element to ring-highlight + anchor the card beside (desktop).
    selector?: string
}

function getTargetRect(selector?: string): DOMRect | null {
    if (!selector) return null
    const el = document.querySelector(selector)
    if (!el) return null
    const rect = el.getBoundingClientRect()
    if (rect.width === 0 && rect.height === 0) return null
    return rect
}

function getCardStyle(rect: DOMRect | null): CSSProperties {
    if (!rect) return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
    const width = 360
    const gap = 14
    // Prefer below the target (the chip lives top-left over the map); clamp on screen.
    const top = Math.min(rect.bottom + gap, window.innerHeight - 240)
    const left = Math.min(Math.max(16, rect.left), window.innerWidth - width - 16)
    return { top, left, width }
}

interface Props {
    countryName: string
    onDismiss: () => void
}

export function CountryFocusWalkthrough({ countryName, onDismiss }: Props) {
    const isMobile = useIsMobile()
    // T2.1: the way out is no longer a ✕ but the first crumb of the scope path
    // — the band under the command bar on desktop, the Lens header row on the
    // phone. Name the right place, and name the real gesture.
    const pathWhere = isMobile ? 'at the top of the Lens' : 'under the command bar'
    const steps: Step[] = [
        {
            eyebrow: 'Country selected',
            title: `${countryName} is now in focus`,
            // Desktop = side-by-side panels; mobile = bottom tabs. The whole
            // console re-scopes either way, but name the right surfaces.
            body: isMobile
                ? 'Its brief opened in the Stream tab, and the map dimmed to the countries it relates to. The Map, Stories and Pulse tabs all re-scoped to it — switch tabs to explore.'
                : 'Its brief opened in the center panel and the map dimmed to the countries it relates to. The stream, stories and dock all re-scoped to this country.',
        },
        {
            eyebrow: 'Return anytime',
            title: `${isMobile ? 'Tap' : 'Click'} World to see the whole world again`,
            body: `The scope path (${pathWhere}) reads World ▸ ${countryName} — it shows which folder you are in. Every crumb to the left is one step back out; World clears the country and returns the console to the global view.`,
            selector: '[data-tour="focus-clear"]',
        },
    ]

    const [step, setStep] = useState(0)
    const [targetRect, setTargetRect] = useState<DOMRect | null>(null)
    const current = steps[Math.min(step, steps.length - 1)]

    // Mark seen on mount so an incomplete walkthrough never re-triggers.
    useEffect(() => {
        try { localStorage.setItem(COUNTRY_WALKTHROUGH_KEY, '1') } catch { /* noop */ }
    }, [])

    useEffect(() => {
        // Mobile = bottom sheet (matches the main tour): no anchoring, no ring.
        if (isMobile) { setTargetRect(null); return }
        const update = () => setTargetRect(getTargetRect(current.selector))
        update()
        const id = window.setTimeout(update, 120)
        window.addEventListener('resize', update)
        window.addEventListener('scroll', update, true)
        return () => {
            window.clearTimeout(id)
            window.removeEventListener('resize', update)
            window.removeEventListener('scroll', update, true)
        }
    }, [current.selector, isMobile])

    const highlightStyle = targetRect
        ? { top: targetRect.top - 6, left: targetRect.left - 6, width: targetRect.width + 12, height: targetRect.height + 12 }
        : undefined

    const next = () => {
        if (step < steps.length - 1) setStep(step + 1)
        else onDismiss()
    }

    return (
        <div className="onboarding-layer" aria-live="polite">
            <div className="onboarding-scrim" onClick={onDismiss} />
            {highlightStyle && <div className="onboarding-highlight" style={highlightStyle} />}
            <div
                className={`onboarding-card${isMobile ? ' cfw-card-mobile' : ''}`}
                style={isMobile ? undefined : getCardStyle(targetRect)}
            >
                <div className="onboarding-step-indicator">
                    {steps.map((_, i) => (
                        <span key={i} className={`onboarding-dot ${i === step ? 'active' : ''}`} />
                    ))}
                </div>
                <div className="onboarding-eyebrow">{current.eyebrow}</div>
                <p className="onboarding-title">{current.title}</p>
                <p className="onboarding-body">{current.body}</p>
                <div className="onboarding-actions">
                    <button className="onboarding-skip" onClick={onDismiss}>Got it</button>
                    <div className="onboarding-action-group">
                        <button className="onboarding-next" onClick={next}>
                            {step < steps.length - 1 ? 'Next' : 'Done'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
