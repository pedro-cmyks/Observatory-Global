// Shared body-level pin toast (extracted from PinReceiptButton so the Brief's
// ◇ Save can use the SAME idiom — council R4 N37).
//
// Fixed + layout-decoupled so it can fire from inside a row/<a> without
// disturbing geometry. Best-effort: never throws, never blocks; if the DOM is
// unavailable (tests/SSR) the call is a silent no-op. An optional ACTION button
// carries the correction a save may need (e.g. "this belongs in its own
// investigation") — one click, no modal.
import './pinToast.css'

let toastEl: HTMLDivElement | null = null
let textEl: HTMLSpanElement | null = null
let actionEl: HTMLButtonElement | null = null
let toastTimer: number | null = null

const SHOW_MS = 1800
const SHOW_WITH_ACTION_MS = 5200 // an action needs time to be read and clicked

export interface PinToastAction {
  label: string
  run: () => void
}

export function flashPinToast(message: string, action?: PinToastAction): void {
  try {
    if (typeof document === 'undefined') return
    if (!toastEl) {
      toastEl = document.createElement('div')
      toastEl.className = 'pin-receipt-toast'
      toastEl.setAttribute('role', 'status')
      textEl = document.createElement('span')
      textEl.className = 'pin-receipt-toast__text'
      actionEl = document.createElement('button')
      actionEl.type = 'button'
      actionEl.className = 'pin-receipt-toast__action'
      toastEl.append(textEl, actionEl)
      document.body.appendChild(toastEl)
    }
    if (textEl) textEl.textContent = message
    if (actionEl) {
      actionEl.onclick = null
      if (action) {
        actionEl.textContent = action.label
        actionEl.hidden = false
        actionEl.onclick = () => {
          try { action.run() } finally { hide() }
        }
      } else {
        actionEl.textContent = ''
        actionEl.hidden = true
      }
    }
    // pointer-events are off at rest (the toast must never eat a click); an
    // actionable toast turns them on for its own lifetime.
    toastEl.classList.toggle('pin-receipt-toast--actionable', !!action)
    toastEl.classList.add('pin-receipt-toast--show')
    if (toastTimer) window.clearTimeout(toastTimer)
    toastTimer = window.setTimeout(hide, action ? SHOW_WITH_ACTION_MS : SHOW_MS)
  } catch {
    /* toast is non-essential */
  }
}

function hide(): void {
  toastEl?.classList.remove('pin-receipt-toast--show', 'pin-receipt-toast--actionable')
}
