/**
 * GLOBAL TOOLTIP CONTROLLER — viewport-aware [data-tip] positioning.
 *
 * WHY THIS EXISTS
 * The app has ~400 `data-tip="…"` triggers. They used to render through a pure
 * CSS `::before` pseudo-element that always drew ABOVE the trigger, centered.
 * A pseudo-element cannot escape an ancestor's `overflow` (so tips near a panel
 * top slid UNDER the fixed header strip) and cannot measure the viewport (so
 * tips near the left/right edge cropped off-screen). The opt-in fix-classes
 * (`tip-below` / `tip-left` / `tip-right`) required every call site to know its
 * own position — they were used 0 times.
 *
 * THE FIX
 * One reusable node appended to <body> with `position: fixed`. Body-level +
 * fixed means NO ancestor overflow/stacking context can clip it. On hover/focus
 * we measure the trigger and the tip, then flip vertically and clamp
 * horizontally so the tip always lands fully inside the viewport. The public
 * contract stays `data-tip="…"` — no component changes.
 */

const GAP = 8 // px between trigger and tip
const MARGIN = 8 // px minimum distance from any viewport edge

let installed = false
let tipEl: HTMLDivElement | null = null
let currentTrigger: Element | null = null

function ensureTipEl(): HTMLDivElement {
  if (tipEl) return tipEl
  const el = document.createElement('div')
  el.className = 'atlas-tip'
  el.setAttribute('role', 'tooltip')
  el.setAttribute('aria-hidden', 'true')
  // Off-screen + invisible until positioned, so the first paint never flashes
  // in the top-left corner.
  el.style.opacity = '0'
  el.style.display = 'none'
  document.body.appendChild(el)
  tipEl = el
  return el
}

function hide() {
  currentTrigger = null
  if (!tipEl) return
  tipEl.style.display = 'none'
  tipEl.style.opacity = '0'
  tipEl.setAttribute('aria-hidden', 'true')
}

function show(trigger: Element) {
  const text = trigger.getAttribute('data-tip')
  if (!text) {
    hide()
    return
  }
  currentTrigger = trigger
  const tip = ensureTipEl()
  tip.textContent = text
  tip.setAttribute('aria-hidden', 'false')

  // Reveal off-screen first so we can measure the wrapped box, then place it.
  tip.style.display = 'block'
  tip.style.left = '-9999px'
  tip.style.top = '0px'
  tip.style.opacity = '0'

  const trg = trigger.getBoundingClientRect()
  const tw = tip.offsetWidth
  const th = tip.offsetHeight
  const vw = document.documentElement.clientWidth
  const vh = document.documentElement.clientHeight

  // Horizontal: center on the trigger, then clamp inside the viewport.
  let left = trg.left + trg.width / 2 - tw / 2
  left = Math.min(Math.max(left, MARGIN), Math.max(MARGIN, vw - tw - MARGIN))

  // Vertical: prefer ABOVE (matches the old default). Flip BELOW when above
  // would clip the top (e.g. a tab-strip help icon under the header). If below
  // also overflows, clamp to the side with more room.
  const preferBelow = trigger.classList.contains('tip-below')
  const aboveTop = trg.top - th - GAP
  const belowTop = trg.bottom + GAP
  let top: number
  if (preferBelow) {
    top = belowTop + th + GAP <= vh - MARGIN ? belowTop : aboveTop
  } else {
    top = aboveTop >= MARGIN ? aboveTop : belowTop
  }
  // Final vertical clamp so a very tall tip never leaves the viewport top/bottom.
  top = Math.min(Math.max(top, MARGIN), Math.max(MARGIN, vh - th - MARGIN))

  tip.style.left = `${Math.round(left)}px`
  tip.style.top = `${Math.round(top)}px`
  tip.style.opacity = '1'
}

function onPointerOver(e: Event) {
  const target = e.target as Element | null
  const trigger = target?.closest?.('[data-tip]') ?? null
  if (trigger === currentTrigger) return // moving within the same trigger's children
  if (trigger) show(trigger)
  else hide()
}

function onFocusIn(e: Event) {
  const target = e.target as Element | null
  const trigger = target?.closest?.('[data-tip]') ?? null
  // Only KEYBOARD focus surfaces a tip (:focus-visible). A mouse click focuses
  // the same element too, and showing there would leave the tip stuck after the
  // pointer moves away — the old hover-only system never did that.
  if (trigger && (trigger as HTMLElement).matches?.(':focus-visible')) show(trigger)
  else hide()
}

function onFocusOut() {
  hide()
}

// Any scroll/resize invalidates the measured trigger rect — cheapest correct
// response is to dismiss (the user is no longer hovering with intent).
function onScrollOrResize() {
  if (currentTrigger) hide()
}

/**
 * Install the global tooltip controller. Idempotent. Returns a cleanup fn.
 * Uses capture-phase delegation on document so it covers every pane
 * (console, Brief, overlays) without per-component wiring.
 */
export function installTooltips(): () => void {
  if (installed || typeof document === 'undefined') return () => {}
  installed = true

  document.addEventListener('mouseover', onPointerOver, true)
  document.addEventListener('focusin', onFocusIn, true)
  document.addEventListener('focusout', onFocusOut, true)
  // Passive listeners — we only read, never preventDefault.
  window.addEventListener('scroll', onScrollOrResize, true)
  window.addEventListener('resize', onScrollOrResize, true)
  window.addEventListener('wheel', onScrollOrResize, { passive: true, capture: true })

  return () => {
    document.removeEventListener('mouseover', onPointerOver, true)
    document.removeEventListener('focusin', onFocusIn, true)
    document.removeEventListener('focusout', onFocusOut, true)
    window.removeEventListener('scroll', onScrollOrResize, true)
    window.removeEventListener('resize', onScrollOrResize, true)
    window.removeEventListener('wheel', onScrollOrResize, true)
    hide()
    tipEl?.remove()
    tipEl = null
    installed = false
  }
}
