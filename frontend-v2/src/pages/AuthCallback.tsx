// /auth/callback — where the verification email lands. supabase-js
// (detectSessionInUrl, default on) consumes the token fragment as the root
// AuthProvider's client initializes; this page's job is to give the moment a
// face: "Account verified — you can use Atlas now", or the honest
// expired/used-link state. The URL params are captured SYNCHRONOUSLY on
// first render (useState initializer) because supabase-js strips the
// fragment once it processes it.
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { parseAuthCallbackParams, describeCallbackError } from '../lib/authForms'
import { useReaderTheme, ReaderThemeToggle } from '../lib/readerTheme'
import { AtlasMark } from '../components/AtlasMark'
import '../styles/readerTheme.css'
import './AuthPages.css'

const SESSION_WAIT_MS = 8000

export function AuthCallback() {
  const navigate = useNavigate()
  const { theme, toggle } = useReaderTheme()
  const { session } = useAuth()
  // capture before supabase-js strips the fragment
  const [params] = useState(() =>
    parseAuthCallbackParams(window.location.hash, window.location.search))
  const [timedOut, setTimedOut] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setTimedOut(true), SESSION_WAIT_MS)
    return () => clearTimeout(t)
  }, [])

  let body: React.ReactNode
  if (params.error) {
    body = (
      <div className="auth-result">
        <div className="auth-result-glyph auth-result-glyph--warn">!</div>
        <h1 className="auth-title">This link didn’t work</h1>
        <p className="auth-sub">{describeCallbackError(params.error)}</p>
        <div className="auth-result-cta">
          <button className="auth-btn" onClick={() => navigate('/register')}>Create account / sign in</button>
          <button className="auth-btn auth-btn--ghost" onClick={() => navigate('/register?mode=forgot')}>Request a password reset</button>
        </div>
      </div>
    )
  } else if (session) {
    body = (
      <div className="auth-result">
        <div className="auth-result-glyph">✓</div>
        <h1 className="auth-title">Account verified</h1>
        <p className="auth-sub">You’re signed in{session.user?.email ? ` as ${session.user.email}` : ''} — your investigations now sync across devices. Atlas is all yours.</p>
        <div className="auth-result-cta">
          <button className="auth-btn" onClick={() => navigate('/brief')}>Read the Brief</button>
          <button className="auth-btn auth-btn--ghost" onClick={() => navigate('/app')}>Open the console</button>
        </div>
      </div>
    )
  } else if (!timedOut) {
    body = (
      <div className="auth-result">
        <div className="auth-result-glyph">…</div>
        <h1 className="auth-title">Verifying</h1>
        <p className="auth-sub">Confirming your email with the account service…</p>
      </div>
    )
  } else {
    body = (
      <div className="auth-result">
        <div className="auth-result-glyph auth-result-glyph--warn">!</div>
        <h1 className="auth-title">No session arrived</h1>
        <p className="auth-sub">This page expected a verification link from an Atlas email, but no valid session came with it. The link may have expired or been used already.</p>
        <div className="auth-result-cta">
          <button className="auth-btn" onClick={() => navigate('/register')}>Create account / sign in</button>
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
