// AuthContext (accounts-v1 + password lane 2026-08-24). Session state +
// magic-link sign-in + email+password signup/login/recovery + the sync
// engine lifecycle. Anonymous = no session = pure localStorage (W0-D5
// privacy stance unchanged); signing in is the explicit opt-in to sync.
//
// The password lane is ADDITIVE — magic link stays as the alternative.
// Every method returns { ok, code?, message } with HONEST copy mapped in
// lib/authForms (wrong password ≠ unverified email ≠ rate limit).
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabaseClient } from '../lib/supabaseClient'
import { startSyncEngine, stopSyncEngine } from '../lib/investigationSync'
import { setTelemetryUser, track } from '../lib/telemetry'
import { mapAuthError, interpretSignUpResult, type AuthErrorCode } from '../lib/authForms'

export interface AuthActionResult {
  ok: boolean
  code?: AuthErrorCode
  message: string
}

const NOT_CONFIGURED: AuthActionResult = { ok: false, message: 'not configured' }

interface AuthState {
  configured: boolean          // env present — accounts UI renders at all
  session: Session | null
  email: string | null
  sendMagicLink: (email: string) => Promise<AuthActionResult>
  signUpWithPassword: (email: string, password: string) => Promise<AuthActionResult>
  signInWithPassword: (email: string, password: string) => Promise<AuthActionResult>
  requestPasswordReset: (email: string) => Promise<AuthActionResult>
  updatePassword: (newPassword: string) => Promise<AuthActionResult>
  signOut: () => Promise<void>
}

const AuthCtx = createContext<AuthState>({
  configured: false, session: null, email: null,
  sendMagicLink: async () => NOT_CONFIGURED,
  signUpWithPassword: async () => NOT_CONFIGURED,
  signInWithPassword: async () => NOT_CONFIGURED,
  requestPasswordReset: async () => NOT_CONFIGURED,
  updatePassword: async () => NOT_CONFIGURED,
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

  const sendMagicLink = async (email: string): Promise<AuthActionResult> => {
    if (!sb) return NOT_CONFIGURED
    const { error } = await sb.auth.signInWithOtp({
      email, options: { emailRedirectTo: window.location.origin },
    })
    if (error) return { ok: false, ...mapAuthError(error.message) }
    return { ok: true, message: 'Check your email for the sign-in link.' }
  }

  // Registration: email verification lands on /auth/callback (its own page —
  // the campaign entrant deserves an explicit "account verified" moment, not
  // a silent drop onto the console).
  const signUpWithPassword = async (email: string, password: string): Promise<AuthActionResult> => {
    if (!sb) return NOT_CONFIGURED
    const { data, error } = await sb.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: window.location.origin + '/auth/callback' },
    })
    if (error) return { ok: false, ...mapAuthError(error.message) }
    const outcome = interpretSignUpResult(data, email)
    if (outcome.ok) track('sign_up')
    return outcome
  }

  const signInWithPassword = async (email: string, password: string): Promise<AuthActionResult> => {
    if (!sb) return NOT_CONFIGURED
    const { error } = await sb.auth.signInWithPassword({ email, password })
    if (error) return { ok: false, ...mapAuthError(error.message) }
    return { ok: true, message: 'Signed in.' }
  }

  const requestPasswordReset = async (email: string): Promise<AuthActionResult> => {
    if (!sb) return NOT_CONFIGURED
    const { error } = await sb.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin + '/auth/reset',
    })
    if (error) return { ok: false, ...mapAuthError(error.message) }
    return { ok: true, message: `If an account exists for ${email}, a reset link is on its way.` }
  }

  // Used by /auth/reset once the recovery session is live.
  const updatePassword = async (newPassword: string): Promise<AuthActionResult> => {
    if (!sb) return NOT_CONFIGURED
    const { error } = await sb.auth.updateUser({ password: newPassword })
    if (error) return { ok: false, ...mapAuthError(error.message) }
    return { ok: true, message: 'Password updated — you’re signed in.' }
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
      sendMagicLink, signUpWithPassword, signInWithPassword,
      requestPasswordReset, updatePassword, signOut,
    }}>{children}</AuthCtx.Provider>
  )
}
