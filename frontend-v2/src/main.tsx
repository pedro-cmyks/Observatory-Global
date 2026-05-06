import { Component, StrictMode, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import './styles/variables.css'
import { ThemeProvider } from './contexts/ThemeContext'
import App from './App.tsx'
import { Landing } from './pages/Landing.tsx'
import { Docs } from './pages/Docs.tsx'

class RootErrorBoundary extends Component<{ children: ReactNode }, { crashed: boolean }> {
  state = { crashed: false }
  static getDerivedStateFromError() { return { crashed: true } }
  componentDidCatch(error: Error) { console.error('[RootErrorBoundary]', error) }
  render() {
    if (this.state.crashed) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0a0f1a', color: '#94a3b8', fontFamily: 'system-ui, sans-serif', gap: 12 }}>
          <div style={{ fontSize: 32 }}>⚠</div>
          <div style={{ fontSize: 14, color: '#e2e8f0' }}>Something went wrong</div>
          <button onClick={() => { this.setState({ crashed: false }); window.location.reload() }} style={{ marginTop: 8, padding: '6px 16px', background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#94a3b8', cursor: 'pointer', fontSize: 12 }}>Reload</button>
        </div>
      )
    }
    return this.props.children
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RootErrorBoundary>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/app" element={<App />} />
            <Route path="/docs" element={<Docs />} />
            <Route path="/docs/*" element={<Docs />} />
            <Route path="*" element={<Landing />} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </RootErrorBoundary>
  </StrictMode>,
)
