import { useEffect, useState } from 'react'
import './OfflineBanner.css'

/**
 * Shows a small banner when the device is offline. The service worker serves
 * the last cached Brief, so the reader still sees content — this banner just
 * makes the staleness honest (a spinner-into-the-void would not).
 */
export function OfflineBanner() {
  const [online, setOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true,
  )
  useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => {
      window.removeEventListener('online', on)
      window.removeEventListener('offline', off)
    }
  }, [])
  if (online) return null
  return (
    <div className="offline-banner" role="status">
      Offline — showing the last Brief you loaded.
    </div>
  )
}
