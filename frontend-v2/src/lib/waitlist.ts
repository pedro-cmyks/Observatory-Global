export interface WaitlistSubmission {
  email: string
  use_case?: string
  company?: string // honeypot, always empty in the real UI
}

export async function postWaitlist(body: WaitlistSubmission): Promise<{ ok: boolean; status: number }> {
  const res = await fetch('/api/v2/waitlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return { ok: res.ok, status: res.status }
}

export async function getWaitlistCount(): Promise<number | null> {
  try {
    const res = await fetch('/api/v2/waitlist/count')
    if (!res.ok) return null
    const data = (await res.json()) as { count?: number }
    return typeof data.count === 'number' ? data.count : null
  } catch {
    return null
  }
}
