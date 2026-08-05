/**
 * Does this device have a hovering pointer?
 *
 * A phone does not. Every `data-tip` tooltip in the app is a hover affordance,
 * and on a touch screen the browser fires a synthetic hover on tap — which is
 * how a tooltip was caught stuck open over a thread title during the mobile
 * audit. Under `(hover: none)` we simply never show tips.
 *
 * The matcher is injected so this is testable without a DOM.
 */
export type MediaMatcher = (query: string) => { matches: boolean }

export function hoverIsAvailable(matchMedia?: MediaMatcher): boolean {
  if (!matchMedia) return true
  return matchMedia('(hover: hover)').matches
}
