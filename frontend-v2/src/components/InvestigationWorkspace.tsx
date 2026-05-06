import { InteractiveWorkspace } from './InteractiveWorkspace'

interface InvestigationWorkspaceProps {
    onNavigate: (urlParams: string) => void
}

export function InvestigationWorkspace(props: InvestigationWorkspaceProps) {
    return <InteractiveWorkspace {...props} />
}
