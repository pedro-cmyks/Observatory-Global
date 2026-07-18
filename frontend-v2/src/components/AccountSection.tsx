// AccountSection (accounts-v1): lives INSIDE the Workbench — contextually
// where sync matters ("your investigations, on any device"). Three states:
// not-configured (honest, hidden behind nothing), signed-out (email form),
// signed-in (email + sync badge + sign out). No product data is gated.
import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import './AccountSection.css'

export function AccountSection() {
  const { configured, session, email, sendMagicLink, signOut } = useAuth()
  const [draft, setDraft] = useState('')
  const [note, setNote] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (!configured) return null   // env absent: accounts simply don't exist

  if (session) {
    return (
      <div className="account-section" data-signed-in>
        <span className="account-dot" aria-hidden />
        <span className="account-email" title={email ?? ''}>{email}</span>
        <span className="account-sync" data-tip="Investigations sync to your account — local copy stays on this device">synced</span>
        <button className="account-btn" onClick={() => void signOut()}>Sign out</button>
      </div>
    )
  }

  return (
    <div className="account-section">
      <p className="account-pitch">Sign in to keep investigations on every device. Free.</p>
      <form onSubmit={async (e) => {
        e.preventDefault()
        if (!draft.trim() || busy) return
        setBusy(true)
        const res = await sendMagicLink(draft.trim())
        setNote(res.message)
        setBusy(false)
      }}>
        <input className="account-input" type="email" required placeholder="you@example.com"
               value={draft} onChange={e => setDraft(e.target.value)} />
        <button className="account-btn" type="submit" disabled={busy}>
          {busy ? 'Sending…' : 'Send sign-in link'}
        </button>
      </form>
      {note && <p className="account-note">{note}</p>}
    </div>
  )
}
