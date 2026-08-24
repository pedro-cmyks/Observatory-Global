// authForms — pure logic for the email+password account lane (campaign
// registration, 2026-08-24). Form validation + HONEST Supabase error mapping:
// Supabase returns distinct messages for distinct causes (wrong password vs
// unverified email vs rate limit) and the UI must surface them distinctly —
// never a generic "something went wrong". No supabase imports here so the
// whole module is vitest-able in node.

export type AuthErrorCode =
  | 'invalid_credentials' // wrong email or password (Supabase doesn't say which — honest about that)
  | 'email_not_confirmed' // account exists but the email was never verified
  | 'user_exists'         // signup attempted for an already-registered email
  | 'rate_limited'        // security cooldown or the mailer's hourly cap
  | 'weak_password'       // server-side password policy rejection
  | 'session_missing'     // recovery/update attempted without a session
  | 'unknown'

export interface MappedAuthError {
  code: AuthErrorCode
  message: string
}

/** Minimal, honest email shape check (the server re-validates). */
export function validateEmail(email: string): string | null {
  const e = email.trim()
  if (!e) return 'Enter your email address.'
  // one @, something on both sides, a dot in the domain — no RFC cosplay
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e)) return 'That doesn’t look like an email address.'
  return null
}

export const MIN_PASSWORD_LENGTH = 8

/**
 * New-password validation (signup + reset). Login NEVER validates length —
 * an old account may predate the policy and the server is the judge there.
 */
export function validateNewPassword(password: string, confirm: string): string | null {
  if (!password) return 'Choose a password.'
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`
  }
  if (password !== confirm) return 'The two passwords don’t match.'
  return null
}

/**
 * Map a raw Supabase auth error message to a stable code + honest user copy.
 * Distinct causes get distinct messages; anything unrecognized passes the
 * server's own words through (never swallowed into a generic).
 */
export function mapAuthError(raw: string): MappedAuthError {
  const m = raw.toLowerCase()
  if (m.includes('invalid login credentials')) {
    return {
      code: 'invalid_credentials',
      message: 'Wrong email or password. If you signed up with a magic link only, use “Forgot password” to set one.',
    }
  }
  if (m.includes('email not confirmed')) {
    return {
      code: 'email_not_confirmed',
      message: 'This account’s email hasn’t been verified yet — open the verification link we emailed you, then sign in.',
    }
  }
  if (m.includes('already registered') || m.includes('already exists')) {
    return {
      code: 'user_exists',
      message: 'An account with this email already exists — sign in instead, or use “Forgot password”.',
    }
  }
  // "For security purposes, you can only request this after N seconds."
  const cooldown = /after (\d+) seconds/.exec(m)
  if (m.includes('for security purposes') && cooldown) {
    return {
      code: 'rate_limited',
      message: `Too soon — you can request this again in ${cooldown[1]} seconds.`,
    }
  }
  if (m.includes('rate limit')) {
    return {
      code: 'rate_limited',
      message: 'Email rate limit reached — the mailer only sends a few per hour. Try again later.',
    }
  }
  if (m.includes('password should be')) {
    // server policy message is already specific — pass it through
    return { code: 'weak_password', message: raw }
  }
  if (m.includes('auth session missing')) {
    return {
      code: 'session_missing',
      message: 'No active session — open the link from your email again, or request a new one.',
    }
  }
  return { code: 'unknown', message: raw }
}

/** The slice of a Supabase signUp() response this module needs. */
export interface SignUpUserSlice {
  user: { identities?: unknown[] | null; email?: string | null } | null
  session: unknown | null
}

export interface SignUpOutcome {
  ok: boolean
  code?: AuthErrorCode
  message: string
}

/**
 * Interpret a signUp() success payload. With email confirmation ON, Supabase
 * answers 200 for an ALREADY-REGISTERED email too (anti-enumeration) but the
 * obfuscated user carries an EMPTY identities array — that's the documented
 * tell, and the user deserves the honest "you already have an account".
 */
export function interpretSignUpResult(data: SignUpUserSlice, email: string): SignUpOutcome {
  const identities = data.user?.identities
  if (data.user && Array.isArray(identities) && identities.length === 0) {
    return {
      ok: false,
      code: 'user_exists',
      message: 'An account with this email already exists — sign in instead, or use “Forgot password”.',
    }
  }
  if (data.session) {
    // confirmation disabled server-side: signed in immediately
    return { ok: true, message: 'Account created — you’re signed in.' }
  }
  return {
    ok: true,
    message: `Almost there — we sent a verification link to ${email}. Open it to activate your account.`,
  }
}

/* ------------------------------------------------------------------------- */
/* Auth-redirect landing pages (/auth/callback, /auth/reset)                  */
/* ------------------------------------------------------------------------- */

export interface AuthCallbackParams {
  error: { code: string; description: string } | null
  /** e.g. 'signup' | 'recovery' | 'magiclink' when the URL carries one */
  type: string | null
}

/**
 * Parse the params Supabase appends to a redirect URL. Errors arrive as
 * error / error_code / error_description, tokens carry a type= — BOTH may
 * live in the hash fragment (implicit flow) or the query string. Pure so the
 * landing pages can capture location synchronously before supabase-js
 * strips the fragment.
 */
export function parseAuthCallbackParams(hash: string, search: string): AuthCallbackParams {
  const merged = new URLSearchParams()
  for (const raw of [search, hash]) {
    const trimmed = raw.replace(/^[#?]/, '')
    if (!trimmed) continue
    for (const [k, v] of new URLSearchParams(trimmed)) merged.set(k, v)
  }
  const err = merged.get('error')
  const errCode = merged.get('error_code')
  const errDesc = merged.get('error_description')
  return {
    error: err || errCode || errDesc
      ? {
          code: errCode ?? err ?? 'unknown',
          description: (errDesc ?? '').replace(/\+/g, ' '),
        }
      : null,
    type: merged.get('type'),
  }
}

/** Honest copy for a failed email-link landing. */
export function describeCallbackError(p: NonNullable<AuthCallbackParams['error']>): string {
  if (p.code === 'otp_expired' || /expired/i.test(p.description)) {
    return 'This link has expired — email links are single-use and short-lived. Request a new one below.'
  }
  if (p.code === 'access_denied' && !p.description) {
    return 'This link was rejected — it may have been used already. Request a new one below.'
  }
  // pass the server's own description through — never a generic
  return p.description || `The link could not be processed (${p.code}). Request a new one below.`
}
