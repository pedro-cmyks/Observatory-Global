// One coverage gap, rendered identically wherever gaps appear: the L1 Brief's
// "What is missing" and the L2 dock's "Under the Radar" lens. Class names are
// the Brief's originals so the shipped visual is preserved byte-for-byte; the
// stylesheet moved here supplies console fallbacks for the reader-theme vars.
import { decodeEntities } from '../lib/decodeEntities'
import type { CoverageGap } from '../lib/coverageGaps'
import { receiptBasis, GAP_RECEIPT_TIER_TIP } from '../lib/gapReceiptBasis'
import { verifiedCountPhrase } from '../lib/statPhrases'
import './CoverageGapCard.css'

interface Props {
  gap: CoverageGap
  /** Largest raw_signals in the set — the shared bar denominator. */
  maxRaw: number
  onOpen: (slug: string) => void
}

export function CoverageGapCard({ gap: g, maxRaw, onOpen }: Props) {
  return (
    <div className="brief-gap-cell">
      <button
        className="brief-gap"
        onClick={() => onOpen(g.slug)}
        data-tip="Category with real coverage in the last 24h where NOTHING cleared the quality gate — attention without verified evidence. 'gate pending' means not yet scored, not rejected."
      >
        <span className="brief-gap-label">{decodeEntities(g.label)}</span>
        <span className="brief-gap-cat">Coverage gap</span>
        <span className="brief-gauge">
          <span><span className="num raw">{g.raw_signals.toLocaleString()}</span><span className="lbl">raw signals</span></span>
          <span><span className="num ver">{g.verified}</span><span className="lbl">verified</span></span>
        </span>
        <span className="brief-gbar" aria-hidden="true" style={{ width: `${Math.max(8, Math.round((g.raw_signals / maxRaw) * 100))}%` }}>
          <i style={{ width: g.raw_signals > 0 ? `${Math.round((g.verified / g.raw_signals) * 100)}%` : '0%' }} />
        </span>
        {/* X4 (2026-08-13, blind college C5): the gauge above prints "172 raw
            signals / 0 verified" — two engine terms and no sentence. The plain
            reading goes directly under the numbers, which stay exactly as they
            were. "not yet" is load-bearing in both branches: unverified is
            pending, never rejected. */}
        <span className="brief-gap-plain">{verifiedCountPhrase(g.raw_signals, g.verified)}</span>
        <span className={`brief-gap-status brief-gap-status--${g.status}`}>
          <span className="d" />
          {g.status === 'gate_pending' ? 'gate pending — not yet scored' : `${g.verified} of ${g.raw_signals.toLocaleString()} admitted — none cleared the quality gate`}
        </span>
      </button>
      {(g.extended_receipts?.length ?? 0) > 0 && (
        <div className="brief-gap-receipts">
          <span className="brief-gap-receipts-label" data-tip={GAP_RECEIPT_TIER_TIP}>
            UNVERIFIED · EXTENDED (~75% MODEL)
          </span>
          {g.extended_receipts!.map(r => {
            // W5 "precision theatre": this row used to print `score 0.99`, which
            // reads as calibrated confidence on a tier whose measured precision
            // is 29-43%. The chip now names the BASIS the engine actually
            // recorded; the raw number lives in the tip, labelled uncalibrated.
            const basis = receiptBasis(r)
            return (
              <a
                key={r.headline}
                className="brief-gap-receipt"
                href={r.url ?? undefined}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="brief-gap-receipt-headline">{decodeEntities(r.headline)}</span>
                <span className="brief-gap-receipt-meta">
                  {r.source ?? 'source unknown'} ·{' '}
                  <span className="brief-gap-receipt-basis" data-tip={basis.tip}>{basis.chip}</span> ↗
                </span>
              </a>
            )
          })}
        </div>
      )}
    </div>
  )
}
