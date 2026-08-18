import React, { useEffect, useState } from 'react';
import { shouldTranslate } from '../lib/translatableText';
import { usePageLanguage } from '../lib/pageLanguage';
import { type ChildTranslationStatus, resolveShowOriginal, shouldRetryFetch } from '../lib/sectionTranslation';
import {
    type TranslateFailure,
    describeUnavailable,
    translateFreeText,
    translateRetryAfterSeconds,
} from '../lib/translateQueue';
import { useReportTranslationStatus, useSectionTranslation } from './TranslatedSection';
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
 * Target language = the reader's translation target (masthead picker /
 * Settings → Page Language choice; browser language only as the initial
 * default) via usePageLanguage(), the reactive form of translationTarget() —
 * changing the picker re-targets every mounted label without a reload.
 */

const LABELS: Record<string, { original: string; translation: string }> = {
    es: { original: 'Ver original', translation: 'Ver traducción' },
    en: { original: 'See original', translation: 'See translation' },
    pt: { original: 'Ver original', translation: 'Ver tradução' },
    fr: { original: "Voir l'original", translation: 'Voir la traduction' },
};
const labelsFor = (lang: string) => LABELS[lang] || LABELS.en;

// Process-lifetime memo: string = translation, null = SETTLED "no translation
// needed" (the server said same-language). A failure is never stored here —
// before W3 a 429 landed in this map as `null` and pinned the untranslated
// text for the rest of the session, which is precisely how "Translate all"
// became a no-op even after the rate-limit window had passed.
const memo = new Map<string, string | null>();

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

type FetchResult =
    | { kind: 'ok'; text: string }
    | { kind: 'none' }
    | { kind: 'unavailable'; reason: TranslateFailure };

/**
 * De-duped + circuit-broken by lib/translateQueue: identical text asked for by
 * many rows costs one request, and while the shared translate circuit is open
 * (a 429 on ANY translate lane) this resolves instantly without touching the
 * network. Only SETTLED outcomes are cached; failures stay retryable.
 */
async function fetchTranslation(text: string, cacheKey: string, targetLang: string): Promise<FetchResult> {
    const outcome = await translateFreeText(text, targetLang);
    if (outcome.status === 'unavailable') return { kind: 'unavailable', reason: outcome.reason };
    if (outcome.status === 'none' || outcome.text.toLowerCase() === text.trim().toLowerCase()) {
        memo.set(cacheKey, null);
        ssSet(cacheKey, null);
        return { kind: 'none' };
    }
    memo.set(cacheKey, outcome.text);
    ssSet(cacheKey, outcome.text);
    return { kind: 'ok', text: outcome.text };
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
    /** A request is out right now. */
    loading: boolean;
    /** Set when the last attempt could not be completed (429 / provider down /
     *  offline) — never conflated with "nothing to translate". */
    unavailable: TranslateFailure | null;
    /** Reader-facing sentence for `unavailable`, only when they asked. */
    unavailableNote: string | null;
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
    // Per-item toggle rides ON TOP of the enclosing section's mode (default
    // context when no <TranslatedSection> above — behavior unchanged). null =
    // follow the section; a click overrides until the next section action.
    const { mode, epoch } = useSectionTranslation();
    const [localOriginal, setLocalOriginal] = useState<boolean | null>(null);
    useEffect(() => { setLocalOriginal(null); }, [mode, epoch]);
    const showOriginal = resolveShowOriginal(localOriginal, mode);

    const [loading, setLoading] = useState(false);
    const [unavailable, setUnavailable] = useState<TranslateFailure | null>(null);

    const run = (): (() => void) => {
        let alive = true;
        setLoading(true);
        setUnavailable(null);
        fetchTranslation(text, cacheKey, targetLang)
            .then(r => {
                if (!alive) return;
                if (r.kind === 'ok') setTranslated(r.text);
                else if (r.kind === 'unavailable') setUnavailable(r.reason);
            })
            .finally(() => { if (alive) setLoading(false); });
        return () => { alive = false; };
    };

    // Explicit section Translate: retry. Only a genuine no-op is memoized now
    // (failures are not), so this re-asks exactly the things that failed.
    useEffect(() => {
        if (!shouldRetryFetch({ mode, epoch }) || !eligible || translated) return;
        if (memo.get(cacheKey) === null) return; // settled: nothing to translate
        return run();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [mode, epoch, eligible, cacheKey, text, targetLang, translated]);

    useEffect(() => {
        // cacheKey changes in place when the page language changes (Settings):
        // adopt the new language's cached value, or clear and re-fetch.
        setUnavailable(null);
        if (!eligible) { setTranslated(null); return; }
        const m = memo.get(cacheKey);
        if (m !== undefined) { setTranslated(m); return; }
        const s = ssGet(cacheKey);
        if (s !== undefined) { memo.set(cacheKey, s); setTranslated(s); return; }
        setTranslated(null);
        return run();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [eligible, cacheKey, text, targetLang]);

    // Report the REAL state to the enclosing section (inert no-op without one).
    const status: ChildTranslationStatus = !eligible
        ? 'none'
        : translated ? 'done'
        : loading ? 'pending'
        : unavailable ? 'failed'
        : 'none';
    useReportTranslationStatus(status);

    return {
        eligible,
        text,
        translated,
        loading,
        unavailable,
        unavailableNote: unavailable && mode === 'translated'
            ? describeUnavailable(unavailable, translateRetryAfterSeconds())
            : null,
        showOriginal,
        // While the fetch is in flight (translated === null) this is the
        // original — never blank, exactly as before.
        display: translated && !showOriginal ? translated : text,
        hasToggle: eligible && !!translated,
        toggleLabel: showOriginal ? L.translation : L.original,
        toggleTip: showOriginal ? 'Translated' : 'Original',
        toggle: () => setLocalOriginal(!showOriginal),
    };
}

/**
 * The exact markup `TranslatableText` has always rendered, pulled out so a
 * consumer driving the hook directly (NarrativeThreads' mobile row) can reuse
 * it byte-for-byte for the desktop shape rather than re-deriving it — one
 * hook instance, no drift between the two render sites.
 */
export const TranslatableTextInline: React.FC<{ state: TranslatableTextState; className?: string }> = ({ state, className }) => {
    // Not eligible / no translation (yet) and nothing to declare → the original
    // text, plain. While the fetch is in flight this branch shows the original
    // — never blank.
    if (!state.hasToggle && !state.unavailableNote) {
        return className ? <span className={className}>{state.text}</span> : <>{state.text}</>;
    }

    return (
        <span className={`translatable-headline${className ? ` ${className}` : ''}`}>
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
            {/* Asked for, not delivered — said on the row, not swallowed. */}
            {!state.hasToggle && state.unavailableNote && (
                <span className="th-unavailable"> · {state.unavailableNote}</span>
            )}
        </span>
    );
};

export const TranslatableText: React.FC<Props> = ({ text, className }) => {
    const state = useTranslatableText(text);
    return <TranslatableTextInline state={state} className={className} />;
};

export default TranslatableText;
