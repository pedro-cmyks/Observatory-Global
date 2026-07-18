// Supabase client for ACCOUNTS + investigation sync only (accounts-v1 plan,
// docs/superpowers/plans/2026-07-18-accounts-sync.md). All product data
// still flows through the Fly API — this client exists solely for Auth and
// the RLS-guarded user_investigations table.
//
// Graceful degradation: when the env vars are absent (local dev without
// keys, forks), supabaseClient() returns null and every accounts surface
// renders its honest "not configured" state. Never throw at import time.

import { createClient, type SupabaseClient } from '@supabase/supabase-js'

let cached: SupabaseClient | null | undefined

export function supabaseClient(): SupabaseClient | null {
  if (cached !== undefined) return cached
  const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
  const anon = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined
  cached = url && anon ? createClient(url, anon) : null
  return cached
}

/** Test seam: reset the memoized client (vitest re-imports don't). */
export function _resetSupabaseClient(): void {
  cached = undefined
}
