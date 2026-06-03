import { lazy, Suspense } from 'react'

const InteractiveWorkspace = lazy(() =>
    import('./InteractiveWorkspace').then(m => ({ default: m.InteractiveWorkspace }))
)

interface InvestigationWorkspaceProps {
    onNavigate: (urlParams: string) => void
}

function shouldLockWorkspacePreview(): boolean {
    const host = typeof window !== 'undefined' ? window.location.hostname : ''
    const isLocalHost = host === 'localhost' || host === '127.0.0.1' || host === '::1'
    return import.meta.env.PROD && !isLocalHost && import.meta.env.VITE_ENABLE_WORKBENCH !== 'true'
}

export function InvestigationWorkspace(props: InvestigationWorkspaceProps) {
    return (
        <Suspense fallback={<div style={{ padding: 24, color: '#64748b', fontSize: 12 }}>Loading workspace…</div>}>
            <InteractiveWorkspace {...props} lockedForPublicPreview={shouldLockWorkspacePreview()} />
        </Suspense>
    )
}
