import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { getWaitlistCount, postWaitlist } from '../lib/waitlist'

const COUNT_DISPLAY_THRESHOLD = 25
const SUPPORT_URL = 'https://ko-fi.com/observatoryglobalatlas'

interface WorkbenchWaitlistGateProps {
  onKeepExploring: () => void
}

type Status = 'idle' | 'submitting' | 'success' | 'error'

export function WorkbenchWaitlistGate({ onKeepExploring }: WorkbenchWaitlistGateProps) {
  const [email, setEmail] = useState('')
  const [useCase, setUseCase] = useState('')
  const [company, setCompany] = useState('') // honeypot
  const [status, setStatus] = useState<Status>('idle')
  const [count, setCount] = useState<number | null>(null)

  useEffect(() => {
    let alive = true
    getWaitlistCount().then((n) => {
      if (alive) setCount(n)
    })
    return () => {
      alive = false
    }
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (status === 'submitting') return
    setStatus('submitting')
    try {
      const { ok } = await postWaitlist({ email, use_case: useCase || undefined, company })
      setStatus(ok ? 'success' : 'error')
    } catch {
      setStatus('error')
    }
  }

  const countLabel =
    count !== null && count >= COUNT_DISPLAY_THRESHOLD
      ? `${count} already on the list`
      : 'Private beta · early access'

  return createPortal(
    <div
      className="workspace-preview-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="workspace-preview-title"
    >
      <div className="workspace-preview-panel">
        <span className="workspace-preview-kicker">Workbench · private beta</span>
        <h3 id="workspace-preview-title">Be among the first to use it</h3>
        <p>
          Atlas doesn't tell you what to believe. It shows you how information
          moves, where it comes from, and how it changes over time. The Workbench
          is where you build that investigation — connecting narratives, sources,
          and countries on a single map.
        </p>

        {status === 'success' ? (
          <p className="workspace-preview-note workspace-waitlist-success">
            You're in. We'll email you soon with your access.
          </p>
        ) : (
          <form className="workspace-waitlist-form" onSubmit={handleSubmit}>
            <span className="workspace-waitlist-count">{countLabel}</span>
            <input
              type="email"
              required
              placeholder="you@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="workspace-waitlist-input"
              aria-label="Email address"
            />
            <textarea
              placeholder="What would you use it for? (optional)"
              value={useCase}
              onChange={(e) => setUseCase(e.target.value)}
              className="workspace-waitlist-textarea"
              aria-label="What would you use it for"
              rows={2}
            />
            {/* honeypot: visually hidden, real users never fill it */}
            <input
              type="text"
              tabIndex={-1}
              autoComplete="off"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              className="workspace-waitlist-honeypot"
            />
            {status === 'error' && (
              <span className="workspace-waitlist-error">
                Couldn't send. Check your email and try again.
              </span>
            )}
            <button
              type="submit"
              className="workspace-preview-primary"
              disabled={status === 'submitting'}
            >
              {status === 'submitting' ? 'Sending…' : 'Request access'}
            </button>
          </form>
        )}

        <div className="workspace-preview-actions workspace-waitlist-footer">
          <a
            className="workspace-preview-secondary"
            href={SUPPORT_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            Support Atlas
          </a>
          <button type="button" className="workspace-preview-ghost" onClick={onKeepExploring}>
            Keep exploring
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
