// AccountSection (accounts-v1 + password lane): lives INSIDE the Workbench —
// contextually where sync matters ("your investigations, on any device").
// States: not-configured (honest, hidden behind nothing), signed-out
// (password sign-in DEFAULT with magic-link + forgot-password + register as
// alternatives), signed-in (email + sync badge + sign out). No product data
// is gated.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { validateEmail } from '../lib/authForms'
import './AccountSection.css'

export function AccountSection() {
  const { configured, session, email, sendMagicLink, signInWithPassword, requestPasswordReset, signOut } = useAuth()
  const navigate = useNavigate()
  const [draft, setDraft] = useState('')
  const [password, setPassword] = useState('')
  const [magicMode, setMagicMode] = useState(false)
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  if (!configured) return null   // env absent: accounts simply don't exist

  if (session) {
    return (
      <div className="account-section" data-signed-in>
        <span className="account-dot" aria-hidden />
        <span className="account-email" data-tip={email ?? ''}>{email}</span>
        <span className="account-sync" data-tip="Investigations sync to your account — local copy stays on this device">synced</span>
        <button className="account-btn" onClick={() => void signOut()}>Sign out</button>
      </div>
    )
  }

  const emailOrNote = (): string | null => {
    const trimmed = draft.trim()
    const err = validateEmail(trimmed)
    if (err) { setNote({ ok: false, text: err }); return null }
    return trimmed
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (busy) return
    setNote(null)
    const trimmed = emailOrNote()
    if (!trimmed) return
    if (!magicMode && !password) { setNote({ ok: false, text: 'Enter your password.' }); return }
    setBusy(true)
    const res = magicMode
      ? await sendMagicLink(trimmed)
      : await signInWithPassword(trimmed, password)
    setBusy(false)
    if (!magicMode && res.ok) return // session lands via onAuthStateChange
    setNote({ ok: res.ok, text: res.message })
  }

  const forgot = async () => {
    if (busy) return
    setNote(null)
    const trimmed = emailOrNote()
    if (!trimmed) return
    setBusy(true)
    const res = await requestPasswordReset(trimmed)
    setBusy(false)
    setNote({ ok: res.ok, text: res.message })
  }

  return (
    <div className="account-section">
      <p className="account-pitch">Sign in to keep investigations on every device. Free.</p>
      <form className="account-form" onSubmit={submit}>
        <input className="account-input" type="email" required placeholder="you@example.com"
               autoComplete="email" value={draft} onChange={e => setDraft(e.target.value)} />
        {!magicMode && (
          <input className="account-input" type="password" placeholder="Password"
                 autoComplete="current-password" value={password}
                 onChange={e => setPassword(e.target.value)} />
        )}
        <button className="account-btn" type="submit" disabled={busy}>
          {busy ? 'Working…' : magicMode ? 'Send sign-in link' : 'Sign in'}
        </button>
      </form>
      {note && <p className={`account-note${note.ok ? '' : ' account-note--error'}`}>{note.text}</p>}
      <div className="account-alt">
        {!magicMode && (
          <button type="button" className="account-alt-link"
                  data-tip="Emails a link to set a new password — type your email first"
                  onClick={() => void forgot()}>Forgot password?</button>
        )}
        <button type="button" className="account-alt-link"
                onClick={() => { setMagicMode(m => !m); setNote(null) }}>
          {magicMode ? 'Use a password instead' : 'Email me a sign-in link instead'}
        </button>
        <button type="button" className="account-alt-link"
                onClick={() => navigate('/register')}>New here? Create a free account</button>
      </div>
    </div>
  )
}
