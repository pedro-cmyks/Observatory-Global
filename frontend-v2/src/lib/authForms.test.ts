// authForms — the password-lane pure logic. Rules under test:
// - validation catches empty/malformed email, short/mismatched new passwords
// - login-side code NEVER length-validates (only new-password paths do)
// - Supabase error messages map to DISTINCT codes: wrong password vs
//   unverified email vs already-registered vs rate limit — never one generic
// - the anti-enumeration signUp 200 (existing user → identities: []) is
//   detected and surfaced honestly
// - redirect params parse from hash OR query, and expired links get the
//   honest expired copy
import { describe, it, expect } from 'vitest'
import {
  validateEmail,
  validateNewPassword,
  MIN_PASSWORD_LENGTH,
  mapAuthError,
  interpretSignUpResult,
  parseAuthCallbackParams,
  describeCallbackError,
} from './authForms'

describe('validateEmail', () => {
  it('rejects empty and malformed shapes', () => {
    expect(validateEmail('')).toBeTruthy()
    expect(validateEmail('   ')).toBeTruthy()
    expect(validateEmail('nope')).toBeTruthy()
    expect(validateEmail('a@b')).toBeTruthy() // no dot in domain
    expect(validateEmail('a b@c.com')).toBeTruthy()
  })
  it('accepts normal addresses (trimmed)', () => {
    expect(validateEmail('pedro@example.com')).toBeNull()
    expect(validateEmail('  atlas-selftest-ui-20260824@mailinator.com  ')).toBeNull()
  })
})

describe('validateNewPassword', () => {
  it('requires a password of the minimum length', () => {
    expect(validateNewPassword('', '')).toBeTruthy()
    expect(validateNewPassword('short', 'short')).toContain(String(MIN_PASSWORD_LENGTH))
  })
  it('requires the confirmation to match', () => {
    expect(validateNewPassword('longenough1', 'longenough2')).toContain('match')
  })
  it('passes a matching, long-enough pair', () => {
    expect(validateNewPassword('longenough1', 'longenough1')).toBeNull()
  })
})

describe('mapAuthError — distinct causes, distinct copy', () => {
  it('wrong credentials ≠ unverified email', () => {
    const wrong = mapAuthError('Invalid login credentials')
    const unverified = mapAuthError('Email not confirmed')
    expect(wrong.code).toBe('invalid_credentials')
    expect(unverified.code).toBe('email_not_confirmed')
    expect(wrong.message).not.toBe(unverified.message)
    expect(unverified.message).toMatch(/verif/i)
  })
  it('already-registered maps to user_exists', () => {
    expect(mapAuthError('User already registered').code).toBe('user_exists')
  })
  it('security cooldown surfaces the wait seconds', () => {
    const m = mapAuthError('For security purposes, you can only request this after 42 seconds.')
    expect(m.code).toBe('rate_limited')
    expect(m.message).toContain('42')
  })
  it('mailer rate limit maps to rate_limited with the hourly-cap honesty', () => {
    const m = mapAuthError('Email rate limit exceeded')
    expect(m.code).toBe('rate_limited')
    expect(m.message).toMatch(/hour/i)
  })
  it('weak-password passes the server policy text through verbatim', () => {
    const raw = 'Password should be at least 6 characters.'
    const m = mapAuthError(raw)
    expect(m.code).toBe('weak_password')
    expect(m.message).toBe(raw)
  })
  it('unknown errors pass the raw server message through — never a generic', () => {
    const m = mapAuthError('Database error saving new user')
    expect(m.code).toBe('unknown')
    expect(m.message).toBe('Database error saving new user')
  })
})

describe('interpretSignUpResult', () => {
  it('detects the anti-enumeration existing-user response (identities: [])', () => {
    const out = interpretSignUpResult({ user: { identities: [] }, session: null }, 'a@b.co')
    expect(out.ok).toBe(false)
    expect(out.code).toBe('user_exists')
  })
  it('fresh user with confirmation pending → check-your-email, naming the address', () => {
    const out = interpretSignUpResult(
      { user: { identities: [{ id: 'x' }] }, session: null },
      'new@example.com',
    )
    expect(out.ok).toBe(true)
    expect(out.message).toContain('new@example.com')
    expect(out.message).toMatch(/verif/i)
  })
  it('session present (confirmation disabled server-side) → signed in', () => {
    const out = interpretSignUpResult(
      { user: { identities: [{ id: 'x' }] }, session: { access_token: 't' } },
      'new@example.com',
    )
    expect(out.ok).toBe(true)
    expect(out.message).toMatch(/signed in/i)
  })
})

describe('parseAuthCallbackParams', () => {
  it('reads Supabase error params from the hash fragment', () => {
    const p = parseAuthCallbackParams(
      '#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid+or+has+expired',
      '',
    )
    expect(p.error).toEqual({ code: 'otp_expired', description: 'Email link is invalid or has expired' })
  })
  it('reads them from the query string too', () => {
    const p = parseAuthCallbackParams('', '?error=access_denied&error_code=otp_expired')
    expect(p.error?.code).toBe('otp_expired')
  })
  it('carries the flow type when tokens land', () => {
    const p = parseAuthCallbackParams('#access_token=abc&type=recovery', '')
    expect(p.error).toBeNull()
    expect(p.type).toBe('recovery')
  })
  it('empty URL → no error, no type', () => {
    const p = parseAuthCallbackParams('', '')
    expect(p.error).toBeNull()
    expect(p.type).toBeNull()
  })
})

describe('describeCallbackError', () => {
  it('expired links get the honest single-use copy', () => {
    expect(describeCallbackError({ code: 'otp_expired', description: '' })).toMatch(/expired/i)
  })
  it('other errors pass the server description through', () => {
    expect(
      describeCallbackError({ code: 'server_error', description: 'Error confirming user' }),
    ).toBe('Error confirming user')
  })
})
