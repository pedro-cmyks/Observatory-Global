import { Download, ExternalLink, PinOff, FolderKanban } from 'lucide-react'
import { useWorkspace } from '../contexts/WorkspaceContext'
import './InvestigationWorkspace.css'

interface InvestigationWorkspaceProps {
    onNavigate: (urlParams: string) => void
}

export function InvestigationWorkspace({ onNavigate }: InvestigationWorkspaceProps) {
    const { isOpen, setIsOpen, items, unpinItem, updateNotes, exportWorkspace } = useWorkspace()

    return (
        <>
            <div 
                className={`workspace-toggle-tab ${isOpen ? 'open' : ''}`}
                onClick={() => setIsOpen(!isOpen)}
                title="Investigation Workspace"
            >
                <FolderKanban size={18} />
            </div>

            <div className={`investigation-workspace ${isOpen ? 'workspace-open' : ''}`}>
                <div className="workspace-header">
                    <h2>
                        <FolderKanban size={16} color="#10b981" />
                        Workspace
                    </h2>
                    <div className="workspace-header-actions">
                        <button 
                            className="workspace-icon-btn" 
                            onClick={exportWorkspace}
                            title="Export Workspace as Markdown"
                            disabled={items.length === 0}
                            style={{ opacity: items.length === 0 ? 0.5 : 1 }}
                        >
                            <Download size={16} />
                        </button>
                        <button 
                            className="workspace-icon-btn" 
                            onClick={() => setIsOpen(false)}
                            title="Close Workspace"
                        >
                            ×
                        </button>
                    </div>
                </div>

                <div className="workspace-content">
                    {items.length === 0 ? (
                        <div className="workspace-empty">
                            <p>Your workspace is empty.</p>
                            <p style={{ marginTop: '8px', opacity: 0.7 }}>Pin themes, entities, and signals as you investigate to collect notes and export reports.</p>
                        </div>
                    ) : (
                        items.map(item => (
                            <div key={item.id} className="workspace-item">
                                <div className="workspace-item-header">
                                    <div className="workspace-item-title-area">
                                        <span className="workspace-item-type">{item.type}</span>
                                        <span className="workspace-item-title">{item.title}</span>
                                    </div>
                                    <div className="workspace-item-actions">
                                        <button 
                                            className="workspace-action-btn"
                                            onClick={() => onNavigate(item.urlParams)}
                                            title="Open in View"
                                        >
                                            <ExternalLink size={14} />
                                        </button>
                                        <button 
                                            className="workspace-action-btn unpin"
                                            onClick={() => unpinItem(item.id)}
                                            title="Unpin"
                                        >
                                            <PinOff size={14} />
                                        </button>
                                    </div>
                                </div>
                                <div className="workspace-item-notes">
                                    <textarea
                                        className="workspace-textarea"
                                        placeholder="Add investigative notes..."
                                        value={item.notes}
                                        onChange={(e) => updateNotes(item.id, e.target.value)}
                                    />
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </>
    )
}
