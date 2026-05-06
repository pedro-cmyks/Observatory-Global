import { useState } from 'react'
import './OnboardingCoachmark.css'

const STORAGE_KEY = 'atlas_onboarding_v1'

const STEPS = [
    {
        icon: '🌍',
        title: 'Click any country on the map',
        body: (
            <>
                Tap a country to open its <strong>Coverage Brief</strong> — top narratives,
                sentiment tone, key people, and signal volume. This is your entry point
                into what any country is talking about right now.
            </>
        ),
    },
    {
        icon: '📈',
        title: 'Narrative Threads shows the big picture',
        body: (
            <>
                The right panel tracks <strong>global topic narratives</strong> — not
                individual articles, but the patterns that emerge across thousands of
                signals. Watch the trend arrows and spread bars to see what's accelerating
                and how far it's reached.
            </>
        ),
    },
    {
        icon: '📌',
        title: 'Pin items to build your investigation',
        body: (
            <>
                Every country, topic, or person panel has a <strong>pin icon</strong> in
                its header. Pinned items appear in the <strong>Workspace Board</strong>
                (folder icon, bottom-left) as a visual relationship graph you can explore
                and annotate.
            </>
        ),
    },
]

export function OnboardingCoachmark() {
    const [step, setStep] = useState(0)
    const [visible, setVisible] = useState(() => {
        try {
            return !localStorage.getItem(STORAGE_KEY)
        } catch {
            return false
        }
    })

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

    const current = STEPS[step]

    return (
        <div className="onboarding-overlay" onClick={dismiss}>
            <div className="onboarding-card" onClick={e => e.stopPropagation()}>
                <div className="onboarding-step-indicator">
                    {STEPS.map((_, i) => (
                        <div key={i} className={`onboarding-dot ${i === step ? 'active' : ''}`} />
                    ))}
                </div>
                <div className="onboarding-icon">{current.icon}</div>
                <p className="onboarding-title">{current.title}</p>
                <p className="onboarding-body">{current.body}</p>
                <div className="onboarding-actions">
                    <button className="onboarding-skip" onClick={dismiss}>
                        Skip intro
                    </button>
                    <button className="onboarding-next" onClick={next}>
                        {step < STEPS.length - 1 ? 'Next →' : 'Got it'}
                    </button>
                </div>
            </div>
        </div>
    )
}
