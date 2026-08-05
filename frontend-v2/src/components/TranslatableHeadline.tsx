import React, { useEffect, useRef, useState } from 'react';

/**
 * Instagram-style headline translation. A signal is stored in its ORIGINAL
 * language; for viewers whose language differs we show the translation BY
 * DEFAULT, with a "see original" toggle (the inverse of the usual
 * "see translation" affordance — Pedro's ask). English-origin (or
 * same-as-viewer) headlines render plain, no network call.
 *
 * Translation is fetched lazily from /api/v2/translate (DeepSeek-backed,
 * cached server-side in signal_translations) and memoized per (id, lang) here.
 */

// Viewer's target language (ISO 639-1 base). Browser language, default 'en'.
const TARGET_LANG = (typeof navigator !== 'undefined'
    ? (navigator.language || 'en')
    : 'en').slice(0, 2).toLowerCase();

const LABELS: Record<string, { original: string; translation: string; translating: string }> = {
    es: { original: 'Ver original', translation: 'Ver traducción', translating: 'Traduciendo…' },
    en: { original: 'See original', translation: 'See translation', translating: 'Translating…' },
    pt: { original: 'Ver original', translation: 'Ver tradução', translating: 'Traduzindo…' },
    fr: { original: "Voir l'original", translation: 'Voir la traduction', translating: 'Traduction…' },
};
const L = LABELS[TARGET_LANG] || LABELS.en;

// Process-lifetime memo so repeat renders / re-opens don't re-fetch.
const memo = new Map<string, string>();

// Typographic punctuation that is technically non-ASCII but says nothing about
// the language (curly quotes, dashes, ellipsis, the middot separator).
const TYPOGRAPHIC_RE = /[‘’“”–—… ·]/g;

// "Clearly non-English": contains a non-Latin script or diacritics beyond mere
// typographic punctuation. Used to decide whether a GDELT-unknown headline is
// worth a translate call.
function isClearlyNonEnglish(text: string): boolean {
    const stripped = (text || '').replace(TYPOGRAPHIC_RE, '');
    // eslint-disable-next-line no-control-regex
    return stripped.length > 0 && !/^[\x00-\x7F]*$/.test(stripped);
}

export function shouldTranslate(sourceLang: string | null | undefined, original: string): boolean {
    const s = (sourceLang || '').slice(0, 2).toLowerCase();
    // 'xx'/'un'/'und'/empty = unknown source (GDELT feed). We used to bail here,
    // which silently broke the "translated into your language" promise for the
    // flagship non-English receipts (Greek traffic news filed as source_lang=xx).
    // Now: attempt when the text is CLEARLY non-English — the /api/v2/translate
    // backend auto-detects the real source (DeepSeek), and the same-text guard in
    // the fetch effect drops a no-op when the detected source already equals the
    // viewer's language (so a Greek viewer reading Greek is not "translated").
    // English-ASCII text stays plain (no wasted call, no loop).
    const unknown = !s || s === 'xx' || s === 'un' || s === 'und';
    if (unknown) return isClearlyNonEnglish(original);
    return s !== TARGET_LANG;
}

interface Props {
    signalId: number;
    original: string;
    sourceLang?: string | null;
}

/**
 * All the translate/toggle state for one headline, with nothing about WHERE
 * it renders. Extracted (#236 follow-up) so a consumer that needs the toggle
 * to land in a different part of the DOM than the text — SignalStream's
 * mobile row, which clamps the headline to 2 lines and was silently clipping
 * the toggle whenever it fell inside that clamped box — can drive both
 * pieces from ONE hook instance instead of two independent, unsynced copies.
 * `TranslatableHeadline` below is just this hook + the original inline markup;
 * every other consumer is untouched.
 */
export interface TranslatableHeadlineState {
    eligible: boolean;
    original: string;
    sourceLang?: string | null;
    translated: string | null;
    loading: boolean;
    showOriginal: boolean;
    /** Text to show right now — mirrors the original `display` computation
     *  exactly, valid whether or not there is anything to toggle. */
    display: string;
    /** True exactly when the original component would render the toggle
     *  button (i.e. `translated` has arrived). */
    hasToggle: boolean;
    toggleLabel: string;
    toggleTip: string;
    translatingLabel: string;
    toggle: () => void;
}

export function useTranslatableHeadline({ signalId, original, sourceLang }: Props): TranslatableHeadlineState {
    const eligible = shouldTranslate(sourceLang, original);
    const cacheKey = `${signalId}:${TARGET_LANG}`;
    const [translated, setTranslated] = useState<string | null>(() => memo.get(cacheKey) ?? null);
    const [showOriginal, setShowOriginal] = useState(false);
    const [loading, setLoading] = useState(false);
    const abortRef = useRef<AbortController | null>(null);

    useEffect(() => {
        if (!eligible || memo.has(cacheKey)) return;
        const controller = new AbortController();
        abortRef.current = controller;
        setLoading(true);
        fetch(`/api/v2/translate?signal_id=${signalId}&to=${TARGET_LANG}`, { signal: controller.signal })
            .then(r => (r.ok ? r.json() : null))
            .then((d: { translated?: string } | null) => {
                const t = d?.translated?.trim();
                if (t && t.toLowerCase() !== original.trim().toLowerCase()) {
                    memo.set(cacheKey, t);
                    setTranslated(t);
                }
            })
            .catch(() => { /* silent — fall back to original */ })
            .finally(() => setLoading(false));
        return () => controller.abort();
    }, [eligible, cacheKey, signalId, original]);

    const display = translated && !showOriginal ? translated : original;
    const flag = showOriginal || !translated;

    return {
        eligible,
        original,
        sourceLang,
        translated,
        loading,
        showOriginal,
        display,
        hasToggle: !!translated,
        toggleLabel: showOriginal ? L.translation : L.original,
        toggleTip: flag ? `Original (${(sourceLang || '').toUpperCase()})` : 'Translated',
        translatingLabel: L.translating,
        toggle: () => setShowOriginal(v => !v),
    };
}

/**
 * The exact markup `TranslatableHeadline` has always rendered, pulled out so
 * a consumer driving the hook directly (SignalStream's mobile row) can reuse
 * it byte-for-byte for the desktop shape rather than re-deriving it — one
 * hook instance, no drift between the two render sites.
 */
export const TranslatableHeadlineInline: React.FC<{ state: TranslatableHeadlineState }> = ({ state }) => {
    // No translation available / not eligible → plain original headline.
    if (!state.eligible || (!state.translated && !state.loading)) {
        return <>{state.original}</>;
    }

    return (
        <span className="translatable-headline">
            {state.display}
            {state.hasToggle && (
                <button
                    type="button"
                    className="th-toggle"
                    onClick={(e) => { e.stopPropagation(); state.toggle(); }}
                    data-tip={state.toggleTip}
                >
                    {state.toggleLabel}
                </button>
            )}
            {!state.translated && state.loading && <span className="th-loading"> · {state.translatingLabel}</span>}
        </span>
    );
};

export const TranslatableHeadline: React.FC<Props> = (props) => {
    const state = useTranslatableHeadline(props);
    return <TranslatableHeadlineInline state={state} />;
};

export default TranslatableHeadline;
