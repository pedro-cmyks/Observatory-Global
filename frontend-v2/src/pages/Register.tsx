// /register — the campaign door (LinkedIn awareness → create an account).
// Standalone page: email+password signup with email verification, plus the
// sign-in, magic-link and forgot-password lanes as modes of the same card.
// All Supabase calls live in AuthContext — this page owns only form state
// and honest copy. Reading Atlas NEVER requires an account (W0-D5): the
// account exists to sync investigations across devices, and the page says
// exactly that.
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { validateEmail, validateNewPassword } from '../lib/authForms'
import { useReaderTheme, ReaderThemeToggle } from '../lib/readerTheme'
import { AtlasMark } from '../components/AtlasMark'
import '../styles/readerTheme.css'
import './AuthPages.css'

type Mode = 'register' | 'login' | 'magic' | 'forgot'

const MODE_COPY: Record<Mode, { kicker: string; title: string; sub: string; cta: string }> = {
  register: {
    kicker: 'Create your account',
    title: 'Atlas, on every device.',
    sub: 'Free. Your account syncs your investigations across devices. Reading the Brief never requires signing in.',
    cta: 'Create free account',
  },
  login: {
    kicker: 'Welcome back',
    title: 'Sign in to Atlas.',
    sub: 'Your investigations pick up where you left them, on any device.',
    cta: 'Sign in',
  },
  magic: {
    kicker: 'Passwordless',
    title: 'Get a sign-in link.',
    sub: 'We email you a one-time link — no password needed.',
    cta: 'Email me a sign-in link',
  },
  forgot: {
    kicker: 'Reset password',
    title: 'Forgot your password?',
    sub: 'We email you a link to set a new one.',
    cta: 'Send reset link',
  },
}

function readMode(raw: string | null): Mode {
  return raw === 'login' || raw === 'magic' || raw === 'forgot' ? raw : 'register'
}

export function Register() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { theme, toggle } = useReaderTheme()
  const {
    configured, session, email: sessionEmail,
    signUpWithPassword, signInWithPassword, sendMagicLink, requestPasswordReset,
  } = useAuth()

  const [mode, setMode] = useState<Mode>(() => readMode(params.get('mode')))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null)
  // after a successful signup/magic/forgot send: replace the form with the
  // "check your email" state so the next step is unmistakable
  const [sent, setSent] = useState<{ title: string; body: string } | null>(null)

  // Deep links (?mode=login / ?mode=forgot) keep working after mount.
  useEffect(() => { setMode(readMode(params.get('mode'))) }, [params])

  const swapMode = (m: Mode) => {
    setMode(m); setNote(null); setSent(null); setPassword(''); setConfirm('')
  }

  const copy = MODE_COPY[mode]
  const needsPassword = mode === 'register' || mode === 'login'
  const alreadySignedIn = useMemo(() => Boolean(session), [session])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (busy) return
    setNote(null)
    const trimmed = email.trim()
    const emailErr = validateEmail(trimmed)
    if (emailErr) { setNote({ ok: false, text: emailErr }); return }
    if (mode === 'register') {
      const pwErr = validateNewPassword(password, confirm)
      if (pwErr) { setNote({ ok: false, text: pwErr }); return }
    }
    if (mode === 'login' && !password) {
      setNote({ ok: false, text: 'Enter your password.' }); return
    }
    setBusy(true)
    try {
      if (mode === 'register') {
        const res = await signUpWithPassword(trimmed, password)
        if (!res.ok) { setNote({ ok: false, text: res.message }); return }
        if (res.message.includes('signed in')) { navigate('/brief'); return }
        setSent({ title: 'Check your email', body: res.message })
      } else if (mode === 'login') {
        const res = await signInWithPassword(trimmed, password)
        if (!res.ok) { setNote({ ok: false, text: res.message }); return }
        navigate('/brief')
      } else if (mode === 'magic') {
        const res = await sendMagicLink(trimmed)
        if (!res.ok) { setNote({ ok: false, text: res.message }); return }
        setSent({ title: 'Check your email', body: `We sent a one-time sign-in link to ${trimmed}.` })
      } else {
        const res = await requestPasswordReset(trimmed)
        if (!res.ok) { setNote({ ok: false, text: res.message }); return }
        setSent({ title: 'Check your email', body: res.message })
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="atlas-reader auth-root" data-rtheme={theme}>
      <header className="auth-nav">
        <button className="auth-mk" onClick={() => navigate('/')} aria-label="Atlas home">
          <AtlasMark size={15} />ATLAS<span className="auth-dot">.</span>
        </button>
        <div className="auth-nav-r">
          <ReaderThemeToggle theme={theme} onToggle={toggle} />
        </div>
      </header>

      <main className="auth-main">
        <div className="auth-card">
          {!configured ? (
            <div className="auth-result">
              <div className="auth-result-glyph auth-result-glyph--warn">!</div>
              <h1 className="auth-title">Accounts aren’t available here</h1>
              <p className="auth-sub">This deployment has no account backend configured. Atlas still works fully without an account — investigations stay on this device.</p>
              <div className="auth-result-cta">
                <button className="auth-btn" onClick={() => navigate('/brief')}>Read the Brief</button>
              </div>
            </div>
          ) : sent ? (
            <div className="auth-result">
              <div className="auth-result-glyph">✉</div>
              <h1 className="auth-title">{sent.title}</h1>
              <p className="auth-sub">{sent.body}</p>
              <p className="auth-fine">Nothing arriving? Check spam, or wait a minute — the mailer sends at most a few emails per hour.</p>
              <div className="auth-links">
                <button className="auth-link" onClick={() => setSent(null)}>← Back</button>
              </div>
            </div>
          ) : (
            <>
              <p className="auth-kicker">{copy.kicker}</p>
              <h1 className="auth-title">{copy.title}</h1>
              <p className="auth-sub">{copy.sub}</p>

              {alreadySignedIn && (
                <p className="auth-note auth-note--ok">
                  You’re already signed in{sessionEmail ? ` as ${sessionEmail}` : ''}. <button className="auth-link" onClick={() => navigate('/brief')}>Go to the Brief →</button>
                </p>
              )}

              <form className="auth-form" onSubmit={submit}>
                <div className="auth-field">
                  <label className="auth-label" htmlFor="auth-email">Email</label>
                  <input id="auth-email" className="auth-input" type="email" autoComplete="email"
                         placeholder="you@example.com" value={email}
                         onChange={e => setEmail(e.target.value)} />
                </div>
                {needsPassword && (
                  <div className="auth-field">
                    <label className="auth-label" htmlFor="auth-pass">Password</label>
                    <input id="auth-pass" className="auth-input" type="password"
                           autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                           placeholder={mode === 'register' ? 'At least 8 characters' : 'Your password'}
                           value={password} onChange={e => setPassword(e.target.value)} />
                  </div>
                )}
                {mode === 'register' && (
                  <div className="auth-field">
                    <label className="auth-label" htmlFor="auth-pass2">Confirm password</label>
                    <input id="auth-pass2" className="auth-input" type="password" autoComplete="new-password"
                           placeholder="Repeat the password" value={confirm}
                           onChange={e => setConfirm(e.target.value)} />
                  </div>
                )}
                <button className="auth-btn" type="submit" disabled={busy}>
                  {busy ? 'Working…' : copy.cta}
                </button>
              </form>

              {note && (
                <p className={`auth-note ${note.ok ? 'auth-note--ok' : 'auth-note--error'}`}>{note.text}</p>
              )}

              <div className="auth-links">
                {mode !== 'register' && (
                  <button className="auth-link" onClick={() => swapMode('register')}>New here? Create a free account</button>
                )}
                {mode !== 'login' && (
                  <button className="auth-link" onClick={() => swapMode('login')}>Already have an account? Sign in</button>
                )}
                {mode === 'login' && (
                  <button className="auth-link" onClick={() => swapMode('forgot')}>Forgot your password?</button>
                )}
                {mode !== 'magic' && (
                  <button className="auth-link" onClick={() => swapMode('magic')}>Prefer no password? Get a sign-in link by email</button>
                )}
              </div>
              {mode === 'register' && (
                <p className="auth-fine">We’ll email you a verification link. No ads, no tracking, nothing paywalled — the account only syncs your work.</p>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  )
}
