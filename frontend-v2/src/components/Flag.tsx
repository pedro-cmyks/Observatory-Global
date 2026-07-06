import 'flag-icons/css/flag-icons.min.css';
import './Flag.css';

// Real, bundled country flags (flag-icons SVGs) — replaces regional-indicator
// emoji flags. The SVGs are same-origin bundled assets, so they render under
// the app's CSP (external CDNs are blocked). Use anywhere a flag sits next to a
// country name: <Flag code="VE" />.

// GDELT / FIPS country codes that differ from ISO-3166-1 alpha-2. Atlas stores
// many codes in GDELT form, so remap before resolving the flag class.
const GDELT_TO_ISO: Record<string, string> = {
    CH: 'CN', RI: 'ID', RB: 'RS', KV: 'XK', CG: 'CD', CF: 'CG',
    KS: 'KR', KN: 'KP', GZ: 'PS', UK: 'GB',
};

// ISO alpha-2 codes flag-icons ships an SVG for (from flags/4x3). Anything else
// falls back to a neutral globe so we never render a blank box.
const SUPPORTED = new Set([
    'ad', 'ae', 'af', 'ag', 'ai', 'al', 'am', 'ao', 'aq', 'ar', 'as', 'at', 'au',
    'aw', 'ax', 'az', 'ba', 'bb', 'bd', 'be', 'bf', 'bg', 'bh', 'bi', 'bj', 'bl',
    'bm', 'bn', 'bo', 'bq', 'br', 'bs', 'bt', 'bv', 'bw', 'by', 'bz', 'ca', 'cc',
    'cd', 'cf', 'cg', 'ch', 'ci', 'ck', 'cl', 'cm', 'cn', 'co', 'cp', 'cr', 'cu',
    'cv', 'cw', 'cx', 'cy', 'cz', 'de', 'dg', 'dj', 'dk', 'dm', 'do', 'dz', 'ec',
    'ee', 'eg', 'eh', 'er', 'es', 'et', 'fi', 'fj', 'fk', 'fm', 'fo', 'fr', 'ga',
    'gb', 'gd', 'ge', 'gf', 'gg', 'gh', 'gi', 'gl', 'gm', 'gn', 'gp', 'gq', 'gr',
    'gs', 'gt', 'gu', 'gw', 'gy', 'hk', 'hm', 'hn', 'hr', 'ht', 'hu', 'ic', 'id',
    'ie', 'il', 'im', 'in', 'io', 'iq', 'ir', 'is', 'it', 'je', 'jm', 'jo', 'jp',
    'ke', 'kg', 'kh', 'ki', 'km', 'kn', 'kp', 'kr', 'kw', 'ky', 'kz', 'la', 'lb',
    'lc', 'li', 'lk', 'lr', 'ls', 'lt', 'lu', 'lv', 'ly', 'ma', 'mc', 'md', 'me',
    'mf', 'mg', 'mh', 'mk', 'ml', 'mm', 'mn', 'mo', 'mp', 'mq', 'mr', 'ms', 'mt',
    'mu', 'mv', 'mw', 'mx', 'my', 'mz', 'na', 'nc', 'ne', 'nf', 'ng', 'ni', 'nl',
    'no', 'np', 'nr', 'nu', 'nz', 'om', 'pa', 'pc', 'pe', 'pf', 'pg', 'ph', 'pk',
    'pl', 'pm', 'pn', 'pr', 'ps', 'pt', 'pw', 'py', 'qa', 're', 'ro', 'rs', 'ru',
    'rw', 'sa', 'sb', 'sc', 'sd', 'se', 'sg', 'sh', 'si', 'sj', 'sk', 'sl', 'sm',
    'sn', 'so', 'sr', 'ss', 'st', 'sv', 'sx', 'sy', 'sz', 'tc', 'td', 'tf', 'tg',
    'th', 'tj', 'tk', 'tl', 'tm', 'tn', 'to', 'tr', 'tt', 'tv', 'tw', 'tz', 'ua',
    'ug', 'um', 'us', 'uy', 'uz', 'va', 'vc', 've', 'vg', 'vi', 'vn', 'vu', 'wf',
    'ws', 'xk', 'ye', 'yt', 'za', 'zm', 'zw',
]);

export function resolveFlagCode(code: string | null | undefined): string | null {
    if (!code) return null;
    const upper = code.toUpperCase();
    const iso = (GDELT_TO_ISO[upper] ?? code).toLowerCase();
    if (!/^[a-z]{2}$/.test(iso)) return null;
    return SUPPORTED.has(iso) ? iso : null;
}

interface FlagProps {
    code: string | null | undefined;
    /** Accessible label (defaults to the country code). */
    title?: string | null;
    className?: string;
}

/**
 * Renders a real bundled flag for an ISO-3166 / GDELT country code. Invalid or
 * unknown codes (or global aggregates) fall back to a neutral globe glyph.
 */
export function Flag({ code, title, className }: FlagProps) {
    const iso = resolveFlagCode(code);
    if (!iso) {
        return (
            <span className={`atlas-flag atlas-flag--globe ${className ?? ''}`.trim()} aria-hidden="true">🌐</span>
        );
    }
    return (
        <span
            className={`fi fi-${iso} atlas-flag ${className ?? ''}`.trim()}
            role="img"
            aria-label={title ?? code ?? iso}
            title={title ?? undefined}
        />
    );
}

export default Flag;
