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

function shouldTranslate(sourceLang?: string | null): boolean {
    if (!sourceLang) return false;
    const s = sourceLang.slice(0, 2).toLowerCase();
    // 'xx'/'un' = unknown (GDELT) — don't guess; only translate when we KNOW
    // the source language and it differs from the viewer's.
    if (s === 'xx' || s === 'un' || s === 'und') return false;
    return s !== TARGET_LANG;
}

interface Props {
    signalId: number;
    original: string;
    sourceLang?: string | null;
}

export const TranslatableHeadline: React.FC<Props> = ({ signalId, original, sourceLang }) => {
    const eligible = shouldTranslate(sourceLang);
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

    // No translation available / not eligible → plain original headline.
    if (!eligible || (!translated && !loading)) {
        return <>{original}</>;
    }

    const display = translated && !showOriginal ? translated : original;
    const flag = showOriginal || !translated;

    return (
        <span className="translatable-headline">
            {display}
            {translated && (
                <button
                    type="button"
                    className="th-toggle"
                    onClick={(e) => { e.stopPropagation(); setShowOriginal(v => !v); }}
                    data-tip={flag ? `Original (${(sourceLang || '').toUpperCase()})` : 'Translated'}
                >
                    {showOriginal ? L.translation : L.original}
                </button>
            )}
            {!translated && loading && <span className="th-loading"> · {L.translating}</span>}
        </span>
    );
};

export default TranslatableHeadline;
