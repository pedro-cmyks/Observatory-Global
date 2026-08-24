// /auth/reset — where the password-recovery email lands. The recovery link
// gives supabase-js a temporary session (type=recovery); with it live, this
// page offers the new-password form → updateUser({password}) → done. Without
// a session (expired/used link, or someone typing the URL) it says so
// honestly and points at requesting another email. URL error params are
// captured synchronously before supabase-js strips the fragment.
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { parseAuthCallbackParams, describeCallbackError, validateNewPassword } from '../lib/authForms'
import { useReaderTheme, ReaderThemeToggle } from '../lib/readerTheme'
import { AtlasMark } from '../components/AtlasMark'
import '../styles/readerTheme.css'
import './AuthPages.css'

const SESSION_WAIT_MS = 8000

export function AuthReset() {
  const navigate = useNavigate()
  const { theme, toggle } = useReaderTheme()
  const { session, email, updatePassword } = useAuth()
  const [params] = useState(() =>
    parseAuthCallbackParams(window.location.hash, window.location.search))
  const [timedOut, setTimedOut] = useState(false)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setTimedOut(true), SESSION_WAIT_MS)
    return () => clearTimeout(t)
  }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (busy) return
    setNote(null)
    const err = validateNewPassword(password, confirm)
    if (err) { setNote(err); return }
    setBusy(true)
    try {
      const res = await updatePassword(password)
      if (!res.ok) { setNote(res.message); return }
      setDone(true)
    } finally {
      setBusy(false)
    }
  }

  let body: React.ReactNode
  if (params.error) {
    body = (
      <div className="auth-result">
        <div className="auth-result-glyph auth-result-glyph--warn">!</div>
        <h1 className="auth-title">This reset link did not work</h1>
        <p className="auth-sub">{describeCallbackError(params.error)}</p>
        <div className="auth-result-cta">
          <button className="auth-btn" onClick={() => navigate('/register?mode=forgot')}>Request a new reset email</button>
        </div>
      </div>
    )
  } else if (done) {
    body = (
      <div className="auth-result">
        <div className="auth-result-glyph">✓</div>
        <h1 className="auth-title">Password updated</h1>
        <p className="auth-sub">You are signed in{email ? ` as ${email}` : ''}. Use the new password for your next sign-in.</p>
        <div className="auth-result-cta">
          <button className="auth-btn" onClick={() => navigate('/brief')}>Read the Brief</button>
        </div>
      </div>
    )
  } else if (session) {
    body = (
      <>
        <p className="auth-kicker">Reset password</p>
        <h1 className="auth-title">Set a new password.</h1>
        <p className="auth-sub">For {email ?? 'your account'}.</p>
        <form className="auth-form" onSubmit={submit}>
          <div className="auth-field">
            <label className="auth-label" htmlFor="reset-pass">New password</label>
            <input id="reset-pass" className="auth-input" type="password" autoComplete="new-password"
                   placeholder="8 characters or more" value={password}
                   onChange={e => setPassword(e.target.value)} />
          </div>
          <div className="auth-field">
            <label className="auth-label" htmlFor="reset-pass2">Confirm new password</label>
            <input id="reset-pass2" className="auth-input" type="password" autoComplete="new-password"
                   placeholder="Repeat the password" value={confirm}
                   onChange={e => setConfirm(e.target.value)} />
          </div>
          <button className="auth-btn" type="submit" disabled={busy}>
            {busy ? 'Saving…' : 'Set new password'}
          </button>
        </form>
        {note && <p className="auth-note auth-note--error">{note}</p>}
      </>
    )
  } else if (!timedOut) {
    body = (
      <div className="auth-result">
        <div className="auth-result-glyph">…</div>
        <h1 className="auth-title">Checking your link</h1>
        <p className="auth-sub">We are opening the recovery session from your email link…</p>
      </div>
    )
  } else {
    body = (
      <div className="auth-result">
        <div className="auth-result-glyph auth-result-glyph--warn">!</div>
        <h1 className="auth-title">No recovery session</h1>
        <p className="auth-sub">This page expected a password-reset link from an Atlas email. No valid recovery session arrived. Email links work only one time, and they expire quickly.</p>
        <div className="auth-result-cta">
          <button className="auth-btn" onClick={() => navigate('/register?mode=forgot')}>Request a new reset email</button>
        </div>
      </div>
    )
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
        <div className="auth-card">{body}</div>
      </main>
    </div>
  )
}
