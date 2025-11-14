import React, { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.setState({
      error,
      errorInfo,
    })
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
    // Reload the page to reset state
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: '#1a202c',
            color: '#fff',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '2rem',
            zIndex: 9999,
          }}
        >
          <div
            style={{
              maxWidth: '600px',
              backgroundColor: '#2d3748',
              borderRadius: '8px',
              padding: '2rem',
              boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
            }}
          >
            <h1
              style={{
                fontSize: '1.5rem',
                fontWeight: 'bold',
                marginBottom: '1rem',
                color: '#ef4444',
              }}
            >
              Something went wrong
            </h1>

            <p style={{ marginBottom: '1rem', color: '#cbd5e0' }}>
              The map encountered an error and could not render. This may be due to:
            </p>

            <ul style={{ marginBottom: '1.5rem', paddingLeft: '1.5rem', color: '#cbd5e0' }}>
              <li>Invalid data from the backend</li>
              <li>Network connectivity issues</li>
              <li>Browser compatibility problems</li>
            </ul>

            {this.state.error && (
              <details style={{ marginBottom: '1.5rem' }}>
                <summary
                  style={{
                    cursor: 'pointer',
                    color: '#4299e1',
                    marginBottom: '0.5rem',
                  }}
                >
                  Error Details
                </summary>
                <pre
                  style={{
                    backgroundColor: '#1a202c',
                    padding: '1rem',
                    borderRadius: '4px',
                    overflow: 'auto',
                    fontSize: '0.875rem',
                    color: '#ef4444',
                  }}
                >
                  {this.state.error.toString()}
                  {this.state.errorInfo && `\n\n${this.state.errorInfo.componentStack}`}
                </pre>
              </details>
            )}

            <button
              onClick={this.handleReset}
              style={{
                backgroundColor: '#4299e1',
                color: '#fff',
                padding: '0.75rem 1.5rem',
                borderRadius: '4px',
                border: 'none',
                fontSize: '1rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'background-color 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#3182ce'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#4299e1'
              }}
            >
              Reload Application
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
