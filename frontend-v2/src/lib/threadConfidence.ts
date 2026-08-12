// Thread confidence presentation — BUCKETS, never a raw percentage.
//
// Council R4 N14 (open three rounds, "zero movement on the render half"):
// /threads rows and the Brief desk printed "100% confidence" straight off
// `avg_confidence`, while the SAME payload already carried a coarse band that
// does not track that number — the live witness is "Biden Cancer Spread",
// avg_confidence 1.0 served under band "medium". A point estimate the engine
// never claimed is a precision lie, so the surface reads the band the API
// actually ships and buckets the raw number only when the field is absent.
//
// The served band is `confidence` from thread_intelligence.confidence_band
// (high | medium | thin | degraded — a joint function of evidence/source/geo
// counts AND assignment confidence). The derived fallback mirrors that
// function's assignment-confidence cuts (>= 0.75 high, >= 0.6 medium) so both
// paths land in the same three-tier vocabulary. Nothing here can emit a digit.

export type ConfidenceBucket = 'high' | 'medium' | 'low'

/** Where the rendered bucket came from — 'band' = served, 'derived' = bucketed here. */
export type ConfidenceBucketSource = 'band' | 'derived'

export interface ThreadConfidenceInput {
  avgConfidence: number | null
  confidenceMeasured: boolean
  trend: 'accelerating' | 'stable' | 'fading'
  crisisRelevant: boolean
  /** Coarse band served on the row (`confidence`). Authoritative when present. */
  band?: string | null
}

export interface ThreadConfidencePresentation {
  /** Bar WIDTH only (0-100) — the bucket's representative level. Never printed. */
  barPct: number | null
  confidenceLabel: string
  bucket: ConfidenceBucket | null
  bucketSource: ConfidenceBucketSource | null
  showConfidenceBar: boolean
  trendColor: string
}

// Every band vocabulary the API has served (thread_intelligence.confidence_band
// plus the synonyms leadConfidence.ts already tolerates) folded onto three tiers.
const BAND_BUCKET: Record<string, ConfidenceBucket> = {
  high: 'high',
  strong: 'high',
  medium: 'medium',
  moderate: 'medium',
  thin: 'low',
  limited: 'low',
  low: 'low',
  degraded: 'low',
}

// Representative level per bucket. Drives the bar so the picture agrees with
// the word — a "medium" row can never paint a full bar off a raw 1.0.
const BUCKET_LEVEL: Record<ConfidenceBucket, number> = { high: 85, medium: 65, low: 35 }

/** Served band → bucket. Unknown/absent bands return null so the caller derives. */
export function bandBucket(band?: string | null): ConfidenceBucket | null {
  if (!band) return null
  return BAND_BUCKET[band.trim().toLowerCase()] ?? null
}

/** Raw assignment confidence → bucket, mirroring confidence_band's own cuts. */
export function derivedBucket(avgConfidence?: number | null): ConfidenceBucket | null {
  if (typeof avgConfidence !== 'number' || !Number.isFinite(avgConfidence)) return null
  if (avgConfidence >= 0.75) return 'high'
  if (avgConfidence >= 0.6) return 'medium'
  return 'low'
}

export interface ConfidenceBucketInput {
  band?: string | null
  avgConfidence?: number | null
}

/**
 * The ONE bucket resolution every confidence surface reads (threads rows,
 * thread focus stats, Brief desk rows) so they cannot disagree: served band
 * first, measured number second, honest null when neither exists.
 */
export function resolveConfidenceBucket(
  input: ConfidenceBucketInput,
): { bucket: ConfidenceBucket | null; source: ConfidenceBucketSource | null } {
  const served = bandBucket(input.band)
  if (served) return { bucket: served, source: 'band' }
  const derived = derivedBucket(input.avgConfidence)
  if (derived) return { bucket: derived, source: 'derived' }
  return { bucket: null, source: null }
}

/** Sentence copy for a row ("medium confidence" / "unscored"). Never a percent. */
export function confidenceBucketLabel(bucket: ConfidenceBucket | null): string {
  return bucket == null ? 'unscored' : `${bucket} confidence`
}

/** Stat-tile copy ("Medium" / "Unscored") for the same bucket. Never a percent. */
export function confidenceBucketWord(bucket: ConfidenceBucket | null): string {
  if (bucket == null) return 'Unscored'
  return bucket.charAt(0).toUpperCase() + bucket.slice(1)
}

/** Honest tooltip: says which layer produced the bucket, and that it is a band. */
export function confidenceBucketTip(
  bucket: ConfidenceBucket | null,
  source: ConfidenceBucketSource | null,
): string {
  if (bucket == null) return 'No calibrated confidence measurement is available for this story.'
  if (source === 'band') {
    return 'Confidence BAND served with this story (evidence, sources, geography and assignment confidence together) — a band, not a point estimate.'
  }
  return 'Confidence band derived from this story\'s measured assignment confidence — the payload served no band of its own. A band, not a point estimate.'
}

export function threadConfidencePresentation(
  input: ThreadConfidenceInput,
): ThreadConfidencePresentation {
  // A row that reports no measurement AND no band is genuinely unscored; a band
  // alone is still a measurement of quality, so it keeps the row scored.
  const measuredNumber = input.confidenceMeasured && Number.isFinite(input.avgConfidence)
    ? (input.avgConfidence as number)
    : null
  const { bucket, source } = resolveConfidenceBucket({
    band: input.band,
    avgConfidence: measuredNumber,
  })

  let trendColor = '#60a5fa'
  if (input.trend === 'accelerating') {
    trendColor = input.crisisRelevant ? '#ef4444' : '#34d399'
  } else if (input.trend === 'fading') {
    trendColor = '#64748b'
  }

  return {
    barPct: bucket == null ? null : BUCKET_LEVEL[bucket],
    confidenceLabel: confidenceBucketLabel(bucket),
    bucket,
    bucketSource: source,
    showConfidenceBar: bucket != null,
    trendColor,
  }
}
