import { lazy, Suspense } from 'react'

const InteractiveWorkspace = lazy(() =>
    import('./InteractiveWorkspace').then(m => ({ default: m.InteractiveWorkspace }))
)

interface InvestigationWorkspaceProps {
    onNavigate: (urlParams: string) => void
}

export function InvestigationWorkspace(props: InvestigationWorkspaceProps) {
    return (
        <Suspense fallback={<div style={{ padding: 24, color: '#64748b', fontSize: 12 }}>Loading workspace…</div>}>
            <InteractiveWorkspace {...props} />
        </Suspense>
    )
}
