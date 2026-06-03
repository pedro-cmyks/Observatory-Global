import { useEffect, useState } from 'react'
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
      ? `Ya van ${count} en la lista`
      : 'Beta privada · primeros accesos'

  return (
    <div
      className="workspace-preview-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="workspace-preview-title"
    >
      <div className="workspace-preview-panel">
        <span className="workspace-preview-kicker">Workbench · beta privada</span>
        <h3 id="workspace-preview-title">Sé de los primeros en usarlo</h3>
        <p>
          Atlas no te dice qué creer. Te muestra cómo se mueve la información, de
          dónde viene y cómo cambia con el tiempo. El Workbench es donde armas esa
          investigación: unes narrativas, fuentes y países en un solo mapa.
        </p>

        {status === 'success' ? (
          <p className="workspace-preview-note workspace-waitlist-success">
            Estás dentro. Te escribimos pronto con tu acceso.
          </p>
        ) : (
          <form className="workspace-waitlist-form" onSubmit={handleSubmit}>
            <span className="workspace-waitlist-count">{countLabel}</span>
            <input
              type="email"
              required
              placeholder="tu@correo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="workspace-waitlist-input"
              aria-label="Correo electrónico"
            />
            <textarea
              placeholder="¿Para qué lo usarías? (opcional)"
              value={useCase}
              onChange={(e) => setUseCase(e.target.value)}
              className="workspace-waitlist-textarea"
              aria-label="Para qué lo usarías"
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
                No se pudo enviar. Revisa el correo e intenta de nuevo.
              </span>
            )}
            <button
              type="submit"
              className="workspace-preview-primary"
              disabled={status === 'submitting'}
            >
              {status === 'submitting' ? 'Enviando…' : 'Pedir acceso'}
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
            Apoyar Atlas
          </a>
          <button type="button" className="workspace-preview-ghost" onClick={onKeepExploring}>
            Keep exploring
          </button>
        </div>
      </div>
    </div>
  )
}
