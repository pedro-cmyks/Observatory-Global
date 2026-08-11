import React, { useEffect, useState } from 'react';
import { shouldTranslate } from '../lib/translatableText';
import { usePageLanguage } from '../lib/pageLanguage';
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
 *
 * Target language = the page-language setting (Settings → Page Language;
 * defaults to the browser language) via usePageLanguage() — changing it in
 * Settings re-targets every mounted label without a reload.
 */

const LABELS: Record<string, { original: string; translation: string }> = {
    es: { original: 'Ver original', translation: 'Ver traducción' },
    en: { original: 'See original', translation: 'See translation' },
    pt: { original: 'Ver original', translation: 'Ver tradução' },
    fr: { original: "Voir l'original", translation: 'Voir la traduction' },
};
const labelsFor = (lang: string) => LABELS[lang] || LABELS.en;

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

function fetchTranslation(text: string, cacheKey: string, targetLang: string): Promise<string | null> {
    const existing = inflight.get(cacheKey);
    if (existing) return existing;
    const p = fetch('/api/v2/translate/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, target_lang: targetLang }),
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

/**
 * All the translate/toggle state for one free-text label, with nothing about
 * WHERE it renders. Extracted (#236 follow-up) as the exact mirror of
 * `useTranslatableHeadline`, and for the same reason: a consumer that needs
 * the toggle to land in a different part of the DOM than the text —
 * NarrativeThreads' mobile row, whose `.narrative-label-text` is a
 * `-webkit-line-clamp: 2` box that silently swallowed the toggle whenever a
 * long title filled both lines — can drive both pieces from ONE hook instance
 * instead of two independent, unsynced copies. `TranslatableText` below is
 * just this hook + the original inline markup; every other consumer
 * (BriefNewspaper's four sites) is untouched.
 */
export interface TranslatableTextState {
    eligible: boolean;
    text: string;
    translated: string | null;
    showOriginal: boolean;
    /** Text to show right now — mirrors the original `display` computation
     *  exactly, and falls back to the original while the fetch is in flight
     *  so this is never blank. */
    display: string;
    /** True exactly when the original component would render the toggle
     *  button (i.e. eligible AND a translation has arrived). */
    hasToggle: boolean;
    toggleLabel: string;
    toggleTip: string;
    toggle: () => void;
}

export function useTranslatableText(text: string): TranslatableTextState {
    const targetLang = usePageLanguage();
    const L = labelsFor(targetLang);
    const eligible = shouldTranslate(text, targetLang);
    const cacheKey = `${text}:${targetLang}`;
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
        // cacheKey changes in place when the page language changes (Settings):
        // adopt the new language's cached value, or clear and re-fetch.
        if (!eligible) { setTranslated(null); return; }
        const m = memo.get(cacheKey);
        if (m !== undefined) { setTranslated(m); return; }
        const s = ssGet(cacheKey);
        if (s !== undefined) { memo.set(cacheKey, s); setTranslated(s); return; }
        setTranslated(null);
        let alive = true;
        fetchTranslation(text, cacheKey, targetLang).then(t => { if (alive && t) setTranslated(t); });
        return () => { alive = false; };
    }, [eligible, cacheKey, text, targetLang]);

    return {
        eligible,
        text,
        translated,
        showOriginal,
        // While the fetch is in flight (translated === null) this is the
        // original — never blank, exactly as before.
        display: translated && !showOriginal ? translated : text,
        hasToggle: eligible && !!translated,
        toggleLabel: showOriginal ? L.translation : L.original,
        toggleTip: showOriginal ? 'Translated' : 'Original',
        toggle: () => setShowOriginal(v => !v),
    };
}

/**
 * The exact markup `TranslatableText` has always rendered, pulled out so a
 * consumer driving the hook directly (NarrativeThreads' mobile row) can reuse
 * it byte-for-byte for the desktop shape rather than re-deriving it — one
 * hook instance, no drift between the two render sites.
 */
export const TranslatableTextInline: React.FC<{ state: TranslatableTextState; className?: string }> = ({ state, className }) => {
    // Not eligible / no translation (yet) → the original text, plain. While
    // the fetch is in flight this branch shows the original — never blank.
    if (!state.hasToggle) {
        return className ? <span className={className}>{state.text}</span> : <>{state.text}</>;
    }

    return (
        <span className={`translatable-headline${className ? ` ${className}` : ''}`}>
            {state.display}
            <button
                type="button"
                className="th-toggle"
                onClick={(e) => { e.stopPropagation(); state.toggle(); }}
                data-tip={state.toggleTip}
            >
                {state.toggleLabel}
            </button>
        </span>
    );
};

export const TranslatableText: React.FC<Props> = ({ text, className }) => {
    const state = useTranslatableText(text);
    return <TranslatableTextInline state={state} className={className} />;
};

export default TranslatableText;
