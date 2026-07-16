import React, { useEffect, useState } from 'react';
import { shouldTranslate } from '../lib/translatableText';
import './TranslatableText.css';

/**
 * Instagram-style translation for FREE TEXT (#204b) — thread/topic labels that
 * have no signal_id and no source_lang. Sibling of TranslatableHeadline:
 * translated shown BY DEFAULT for non-matching viewers, with a "See original"
 * toggle. While loading (and on same:true / degraded responses) the ORIGINAL
 * text renders — never a blank.
 *
 * Backed by POST /api/v2/translate/text (Redis-cached server-side); memoized
 * per (text, lang) in a module Map + sessionStorage so repeat renders and
 * route round-trips don't re-fetch.
 */

// Viewer's target language (ISO 639-1 base). Browser language, default 'en'.
const TARGET_LANG = (typeof navigator !== 'undefined'
    ? (navigator.language || 'en')
    : 'en').slice(0, 2).toLowerCase();

const LABELS: Record<string, { original: string; translation: string }> = {
    es: { original: 'Ver original', translation: 'Ver traducción' },
    en: { original: 'See original', translation: 'See translation' },
    pt: { original: 'Ver original', translation: 'Ver tradução' },
    fr: { original: "Voir l'original", translation: 'Voir la traduction' },
};
const L = LABELS[TARGET_LANG] || LABELS.en;

// Process-lifetime memo: string = translation, null = "no translation needed"
// (same:true or degraded — don't re-ask this session).
const memo = new Map<string, string | null>();
// De-dupe concurrent requests for the same label (it renders in many rows).
const inflight = new Map<string, Promise<string | null>>();

const SS_PREFIX = 'atlas_ttext_v1:';

function ssGet(key: string): string | null | undefined {
    try {
        const raw = sessionStorage.getItem(SS_PREFIX + key);
        if (raw == null) return undefined;
        return (JSON.parse(raw) as { t: string | null }).t;
    } catch {
        return undefined;
    }
}

function ssSet(key: string, value: string | null): void {
    try {
        sessionStorage.setItem(SS_PREFIX + key, JSON.stringify({ t: value }));
    } catch { /* quota / privacy mode — memo Map still covers the session */ }
}

function fetchTranslation(text: string, cacheKey: string): Promise<string | null> {
    const existing = inflight.get(cacheKey);
    if (existing) return existing;
    const p = fetch('/api/v2/translate/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, target_lang: TARGET_LANG }),
    })
        .then(r => (r.ok ? r.json() : null))
        .then((d: { translated?: string; same?: boolean; degraded?: boolean } | null) => {
            const t = d?.translated?.trim();
            // same:true, degraded, or an echo of the input → keep the original.
            if (!d || d.same || d.degraded || !t || t.toLowerCase() === text.trim().toLowerCase()) {
                memo.set(cacheKey, null);
                // Degraded = transient (provider down); don't pin it across the
                // session store — only same/no-op results persist.
                if (d && !d.degraded) ssSet(cacheKey, null);
                return null;
            }
            memo.set(cacheKey, t);
            ssSet(cacheKey, t);
            return t;
        })
        .catch(() => {
            memo.set(cacheKey, null); // don't retry-storm this session
            return null;
        })
        .finally(() => inflight.delete(cacheKey));
    inflight.set(cacheKey, p);
    return p;
}

interface Props {
    text: string;
    className?: string;
}

export const TranslatableText: React.FC<Props> = ({ text, className }) => {
    const eligible = shouldTranslate(text, TARGET_LANG);
    const cacheKey = `${text}:${TARGET_LANG}`;
    const [translated, setTranslated] = useState<string | null>(() => {
        if (!eligible) return null;
        const m = memo.get(cacheKey);
        if (m !== undefined) return m;
        const s = ssGet(cacheKey);
        if (s !== undefined) { memo.set(cacheKey, s); return s; }
        return null;
    });
    const [showOriginal, setShowOriginal] = useState(false);

    useEffect(() => {
        if (!eligible || memo.has(cacheKey)) return;
        let alive = true;
        fetchTranslation(text, cacheKey).then(t => { if (alive && t) setTranslated(t); });
        return () => { alive = false; };
    }, [eligible, cacheKey, text]);

    // Not eligible / no translation (yet) → the original text, plain. While
    // the fetch is in flight this branch shows the original — never blank.
    if (!eligible || !translated) {
        return className ? <span className={className}>{text}</span> : <>{text}</>;
    }

    const display = showOriginal ? text : translated;

    return (
        <span className={`translatable-headline${className ? ` ${className}` : ''}`}>
            {display}
            <button
                type="button"
                className="th-toggle"
                onClick={(e) => { e.stopPropagation(); setShowOriginal(v => !v); }}
                data-tip={showOriginal ? 'Translated' : 'Original'}
            >
                {showOriginal ? L.translation : L.original}
            </button>
        </span>
    );
};

export default TranslatableText;
