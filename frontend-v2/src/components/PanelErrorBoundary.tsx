import React from 'react'
import './PanelErrorBoundary.css'

interface PanelErrorBoundaryProps {
  panelName: string
  children: React.ReactNode
}

interface PanelErrorBoundaryState {
  hasError: boolean
  error: string | null
}

export class PanelErrorBoundary extends React.Component<PanelErrorBoundaryProps, PanelErrorBoundaryState> {
  state: PanelErrorBoundaryState = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): PanelErrorBoundaryState {
    return { hasError: true, error: error.message }
  }

  componentDidCatch(error: Error) {
    console.error(`[PanelErrorBoundary:${this.props.panelName}]`, error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="panel-error-state">
          <div className="panel-error-icon">⚠</div>
          <div className="panel-error-label">{this.props.panelName}</div>
          <div className="panel-error-msg">UNAVAILABLE</div>
          <button
            className="panel-error-retry"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            RETRY
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
