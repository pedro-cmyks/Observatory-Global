// AuthContext (accounts-v1). Session state + magic-link sign-in + the sync
// engine lifecycle. Anonymous = no session = pure localStorage (W0-D5
// privacy stance unchanged); signing in is the explicit opt-in to sync.
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabaseClient } from '../lib/supabaseClient'
import { startSyncEngine, stopSyncEngine } from '../lib/investigationSync'
import { setTelemetryUser, track } from '../lib/telemetry'

interface AuthState {
  configured: boolean          // env present — accounts UI renders at all
  session: Session | null
  email: string | null
  sendMagicLink: (email: string) => Promise<{ ok: boolean; message: string }>
  signOut: () => Promise<void>
}

const AuthCtx = createContext<AuthState>({
  configured: false, session: null, email: null,
  sendMagicLink: async () => ({ ok: false, message: 'not configured' }),
  signOut: async () => {},
})

export function useAuth(): AuthState { return useContext(AuthCtx) }

export function AuthProvider({ children }: { children: ReactNode }) {
  const sb = supabaseClient()
  const [session, setSession] = useState<Session | null>(null)

  useEffect(() => {
    if (!sb) return
    void sb.auth.getSession().then(({ data }) => setSession(data.session))
    const { data: sub } = sb.auth.onAuthStateChange((_evt, s) => setSession(s))
    return () => sub.subscription.unsubscribe()
  }, [sb])

  // Identity + sync lifecycle follow the session.
  useEffect(() => {
    const uid = session?.user?.id ?? null
    setTelemetryUser(uid)
    if (uid) { track('sign_in'); const off = startSyncEngine(uid); return off }
    stopSyncEngine()
  }, [session?.user?.id])

  const sendMagicLink = async (email: string) => {
    if (!sb) return { ok: false, message: 'not configured' }
    const { error } = await sb.auth.signInWithOtp({
      email, options: { emailRedirectTo: window.location.origin },
    })
    return error ? { ok: false, message: error.message }
                 : { ok: true, message: 'Check your email for the sign-in link.' }
  }

  const signOut = async () => {
    if (!sb) return
    stopSyncEngine()
    await sb.auth.signOut()
    // localStorage investigations REMAIN — local-first; sync just stops.
  }

  return (
    <AuthCtx.Provider value={{
      configured: !!sb, session, email: session?.user?.email ?? null,
      sendMagicLink, signOut,
    }}>{children}</AuthCtx.Provider>
  )
}
