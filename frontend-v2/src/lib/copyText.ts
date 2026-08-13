// Shared clipboard write with an HONEST return value.
//
// The rule this encodes is one this codebase already learned the hard way
// (ExportMenu, fix round 2026-07-17 item 4): a failed copy that returns
// silently leaves the reader believing the text is on their clipboard. Callers
// get a boolean and must say which happened.

export interface ClipboardLike {
  writeText: (text: string) => Promise<void>
}

function defaultClipboard(): ClipboardLike | null {
  if (typeof navigator === 'undefined') return null
  const c = navigator.clipboard
  return c && typeof c.writeText === 'function' ? c : null
}

/** True only when the text actually reached the clipboard. */
export async function copyText(
  text: string,
  clipboard: ClipboardLike | null = defaultClipboard(),
): Promise<boolean> {
  if (!text || !text.trim()) return false
  if (!clipboard) return false
  try {
    await clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}
