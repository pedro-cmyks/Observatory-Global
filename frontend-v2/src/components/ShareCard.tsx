import { useState } from 'react'
import { shareThread, type ShareInput } from '../lib/shareCard'
import './ShareCard.css'

interface Props {
  input: ShareInput
  /** Reserved for the deferred image-card follow-up. */
  evidence?: string[]
}

/**
 * Share button for a narrative thread — the viral loop. Web Share API native
 * sheet on mobile (text + link), clipboard fallback on desktop. (An image
 * share-card is a deferred follow-up; see lib/shareCard.ts.)
 */
export function ShareThreadButton({ input }: Props) {
  const [state, setState] = useState<'idle' | 'busy' | 'copied'>('idle')

  const onShare = async () => {
    if (state === 'busy') return
    setState('busy')
    const result = await shareThread(input)
    if (result === 'copied') {
      setState('copied')
      setTimeout(() => setState('idle'), 1800)
    } else {
      setState('idle')
    }
  }

  return (
    <button
      type="button"
      className="share-thread-btn"
      onClick={onShare}
      data-tip="Share this thread"
      disabled={state === 'busy'}
    >
      {state === 'copied' ? 'Copied ✓' : state === 'busy' ? 'Sharing…' : 'Share ↗'}
    </button>
  )
}
