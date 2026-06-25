import { useEffect, useState } from 'react'

// Consumer MVP mobile breakpoint. At/below this width we render the phone
// read surfaces (single-column Brief, full-screen thread); above it the
// desktop console. 768 = the common tablet-portrait / phone boundary.
export const MOBILE_MAX = 768

/** Pure, node-testable: is this viewport width a mobile read surface? */
export function isMobileWidth(width: number, max: number = MOBILE_MAX): boolean {
  return width <= max
}

/** React hook: tracks whether the viewport is a mobile read surface. */
export function useIsMobile(max: number = MOBILE_MAX): boolean {
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? isMobileWidth(window.innerWidth, max) : false,
  )
  useEffect(() => {
    const onResize = () => setIsMobile(isMobileWidth(window.innerWidth, max))
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [max])
  return isMobile
}
