// Country-code boundary (fix round 2026-07-17, item 1 — "click China opens
// Switzerland").
//
// CONTRACT: Atlas' app-wide country code system is ISO 3166-1 alpha-2. The
// backend normalizes GDELT's FIPS codes at ingest (country_codes.FIPS_TO_ISO),
// and every frontend consumer — resolveCountryName, CountryBrief fetches,
// /evidence/day, focus context — keys ISO. The map geojson (Natural Earth)
// also carries ISO_A2. So NOTHING on the click path may convert ISO → FIPS:
// that conversion turned ISO 'CN' (China) into FIPS 'CH', which every ISO
// consumer reads as Switzerland. Same collision class: BN (ISO Brunei / FIPS
// Benin), KN (ISO St Kitts / FIPS North Korea), CG/CF (the Congo swap), NI
// (ISO Nicaragua / FIPS Nigeria), AU (ISO Australia / FIPS Austria).
//
// Residue: some backend rows still carry legacy GDELT codes that have NO ISO
// meaning (GZ, KS, RB, RI, KV, EI, UK). Those are safe to remap — they can
// never collide with an assigned ISO code. The rule is therefore ISO-FIRST:
// a code that exists in the consumer's ISO keyspace is used as-is; only
// otherwise do we try the legacy alias table.

/** Legacy GDELT/FIPS codes with NO assigned ISO 3166-1 alpha-2 meaning →
 *  their ISO equivalent. NEVER add a key here that is itself an assigned ISO
 *  code (CH, BN, KN, CG, CF, NI, AU…) — that recreates the China→Switzerland
 *  bug. Frozen by countryCodeBoundary.test.ts. */
export const LEGACY_GDELT_TO_ISO: Record<string, string> = {
    GZ: 'PS', // Gaza → Palestine
    KS: 'KR', // South Korea
    RB: 'RS', // Serbia
    RI: 'ID', // Indonesia (GDELT) — note FIPS RI is Serbia; Atlas data uses RI=Indonesia
    KV: 'XK', // Kosovo
    EI: 'IE', // Ireland
    UK: 'GB', // United Kingdom
}

/**
 * Resolve an inbound country code (possibly legacy-GDELT residue from old
 * backend rows) to the ISO code a consumer keys on. ISO-first: if the code is
 * already valid in the consumer's keyspace, it IS the answer.
 */
export function resolveInboundIso(
    code: string | null | undefined,
    hasIso: (iso: string) => boolean,
): string | null {
    if (!code) return null
    if (hasIso(code)) return code
    return LEGACY_GDELT_TO_ISO[code] ?? code
}
