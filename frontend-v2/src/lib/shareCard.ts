export interface ShareInput {
  label: string
  whyNow?: string | null
  url: string
}

/** The text that accompanies a shared thread (and the clipboard fallback). */
export function buildShareText({ label, whyNow, url }: ShareInput): string {
  const lines = [`📡 ${label}`]
  if (whyNow) lines.push(whyNow)
  lines.push(`via Atlas — ${url}`)
  return lines.join('\n')
}

type Result = 'shared' | 'copied' | 'failed'

// Safety net: never let a share attempt hang the UI (e.g. clipboard.writeText
// can hang in an unfocused/headless context). Resolves to the fallback if the
// promise doesn't settle in time.
function withTimeout<T>(p: Promise<T>, ms: number, fallback: T): Promise<T> {
  return Promise.race([p, new Promise<T>(resolve => setTimeout(() => resolve(fallback), ms))])
}

/**
 * Share a thread as text + link: the Web Share API on mobile (native sheet),
 * clipboard fallback on desktop / unsupported browsers.
 *
 * NOTE (follow-up): an image share-card was prototyped (`ShareCard` offscreen
 * markup) but html-to-image's `toPng` stalls embedding cross-origin Google
 * Fonts even with `skipFonts`; the image card is deferred until that is solved
 * (self-host the card fonts or pre-rasterize). Text+link share ships now.
 */
export async function shareThread(input: ShareInput): Promise<Result> {
  const text = buildShareText(input)
  const nav = navigator as Navigator & { canShare?: (d: ShareData) => boolean }
  try {
    if (typeof nav.share === 'function') {
      await navigator.share({ text, title: input.label, url: input.url })
      return 'shared'
    }
  } catch {
    /* user cancelled or share unavailable — fall through to clipboard */
  }
  // Clipboard fallback, guarded so it can never hang the button.
  try {
    const ok = await withTimeout(
      navigator.clipboard.writeText(text).then(() => true).catch(() => false),
      2000,
      false,
    )
    return ok ? 'copied' : 'failed'
  } catch {
    return 'failed'
  }
}
