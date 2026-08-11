// Council R4 N37 — say where a save lands, before and after the click.
//
// The Brief's ◇ Save (and every other one-gesture capture) appends into
// whatever investigation happens to be active, so an unrelated story can land
// in yesterday's investigation with no signal to the reader. The workbench's
// own guardrail is "pins from unrelated sessions should not silently mix"; the
// proportional fix is not a modal but an explicit TARGET INDICATOR: the
// affordance names its destination up front, the confirmation names it again,
// and the confirmation carries a one-click correction (move to a new
// investigation). These are the pure copy builders for that.
import type { PinTarget } from './workbench'

function pinsPhrase(n: number): string {
  if (n <= 0) return 'no pins yet'
  return `${n} pin${n === 1 ? '' : 's'}`
}

/** Tooltip on the save affordance — read BEFORE the click. */
export function saveTargetTip(target: PinTarget): string {
  if (target.kind === 'new') return 'Save — starts a new investigation for this story'
  const title = (target.title ?? '').trim()
  if (!title) return `Save into the open investigation (${pinsPhrase(target.pinCount)})`
  return `Save into “${title}” (${pinsPhrase(target.pinCount)}) — the investigation now open`
}

/** Confirmation AFTER the click. `itemLabel` names what was just saved (it is
 *  also the title of the freshly created investigation on the `new` path). */
export function saveTargetToast(target: PinTarget, itemLabel: string): string {
  if (target.kind === 'new') return `Started “${itemLabel}” — saved here`
  const title = (target.title ?? '').trim()
  if (!title) return `Saved into the open investigation (${pinsPhrase(target.pinCount)})`
  return `Saved into “${title}” (${pinsPhrase(target.pinCount)})`
}
