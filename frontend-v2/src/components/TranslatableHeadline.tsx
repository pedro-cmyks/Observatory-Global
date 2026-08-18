import React, { useEffect, useState } from 'react';
import { translationTarget, usePageLanguage } from '../lib/pageLanguage';
import { type ChildTranslationStatus, resolveShowOriginal, shouldRetryFetch } from '../lib/sectionTranslation';
import {
    type TranslateFailure,
    describeUnavailable,
    translateRetryAfterSeconds,
    translateSignal,
} from '../lib/translateQueue';
import { useReportTranslationStatus, useSectionTranslation } from './TranslatedSection';

/**
 * Instagram-style headline translation. A signal is stored in its ORIGINAL
 * language; for viewers whose language differs we show the translation BY
 * DEFAULT, with a "see original" toggle (the inverse of the usual
 * "see translation" affordance — Pedro's ask). English-origin (or
 * same-as-viewer) headlines render plain, no network call.
 *
 * Translation is fetched through lib/translateQueue (W3, 2026-08-13): every
 * headline mounting in the same tick joins ONE `POST /api/v2/translate/batch`
 * instead of firing its own `GET /api/v2/translate?signal_id=`. Measured
 * reason: a Brief load fired ~26 separate translate requests against a
 * 20-per-5-minutes shared bucket, so the lane 429'd wholesale and the client
 * rendered every 429 as "no translation needed". Results are memoized per
 * (id, lang) here; the server caches them in signal_translations.
 *
 * Target language = the reader's translation target (masthead picker /
 * Settings → Page Language choice; browser language only as the initial
 * default) via usePageLanguage(), the reactive form of translationTarget() —
 * changing the picker re-targets every mounted headline without a reload.
 */

const LABELS: Record<string, { original: string; translation: string; translating: string }> = {
    es: { original: 'Ver original', translation: 'Ver traducción', translating: 'Traduciendo…' },
    en: { original: 'See original', translation: 'See translation', translating: 'Translating…' },
    pt: { original: 'Ver original', translation: 'Ver tradução', translating: 'Traduzindo…' },
    fr: { original: "Voir l'original", translation: 'Voir la traduction', translating: 'Traduction…' },
};
const labelsFor = (lang: string) => LABELS[lang] || LABELS.en;

// Process-lifetime memo so repeat renders / re-opens don't re-fetch.
const memo = new Map<string, string>();
// Settled negatives (identity / same language / no such signal). Cached too:
// re-asking is pure waste and, on a shared bucket, actively harmful. Failures
// are NEVER pinned here — an unavailable answer is not an answer.
const settledNone = new Set<string>();

type FetchResult =
    | { kind: 'ok'; text: string }
    | { kind: 'none' }
    | { kind: 'unavailable'; reason: TranslateFailure };

// One fetch shape for the initial lane and the section-Translate retry lane.
// An echo of the original counts as a no-op (nothing to toggle); a transport
// or provider failure is reported as such and must never be dressed up as one.
async function fetchSignalTranslation(
    signalId: number,
    targetLang: string,
    original: string,
    cacheKey: string,
): Promise<FetchResult> {
    const outcome = await translateSignal(signalId, targetLang);
    if (outcome.status === 'unavailable') return { kind: 'unavailable', reason: outcome.reason };
    if (outcome.status === 'none') { settledNone.add(cacheKey); return { kind: 'none' }; }
    if (outcome.text.toLowerCase() === original.trim().toLowerCase()) {
        settledNone.add(cacheKey);
        return { kind: 'none' };
    }
    memo.set(cacheKey, outcome.text);
    return { kind: 'ok', text: outcome.text };
}

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

export function shouldTranslate(
    sourceLang: string | null | undefined,
    original: string,
    targetLang: string = translationTarget(),
    /** `explicit` = the reader pressed "Translate all" on this section. The
     *  ASCII guard below is a COST heuristic, not a measurement: a GDELT
     *  receipt filed source_lang='xx' whose German headline happens to carry no
     *  umlaut ("Sprengstoff-Drohne in Leipzig: Spur nach Russland?") is
     *  indistinguishable from English by shape. Leaving it plain is right for
     *  the ambient page and wrong the moment someone asks for ALL — measured on
     *  the 2026-08-13 Brief, where two German receipts sat untouched under a
     *  button claiming the section was translated. On an explicit ask we spend
     *  the call: it rides the same batch request, the server caches it in
     *  signal_translations forever, and a genuine no-op returns the same string
     *  and settles silently. */
    opts?: { explicit?: boolean },
): boolean {
    if (!(original || '').trim()) return false;
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
    if (unknown) return opts?.explicit ? true : isClearlyNonEnglish(original);
    return s !== (targetLang || '').slice(0, 2).toLowerCase();
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
    /** Set when the last attempt could not be completed (429 / provider down /
     *  offline). Distinct from "no translation needed" — the whole point. */
    unavailable: TranslateFailure | null;
    /** Reader-facing sentence for `unavailable`, or null. Only rendered when
     *  the reader explicitly asked (section mode 'translated'), so an ambient
     *  page never nags. */
    unavailableNote: string | null;
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
    const targetLang = usePageLanguage();
    const L = labelsFor(targetLang);

    // Per-item toggle rides ON TOP of the enclosing section's mode (default
    // context when no <TranslatedSection> above — behavior unchanged). null =
    // follow the section; a click overrides until the next section action.
    const { mode, epoch } = useSectionTranslation();

    // An explicit section Translate widens eligibility for unknown-source rows
    // (see shouldTranslate). Ambient pages are untouched.
    const explicit = mode === 'translated' && epoch > 0;
    const eligible = shouldTranslate(sourceLang, original, targetLang, { explicit });
    const cacheKey = `${signalId}:${targetLang}`;
    const [translated, setTranslated] = useState<string | null>(() => memo.get(cacheKey) ?? null);
    const [loading, setLoading] = useState(false);
    const [unavailable, setUnavailable] = useState<TranslateFailure | null>(null);

    const [localOriginal, setLocalOriginal] = useState<boolean | null>(null);
    useEffect(() => { setLocalOriginal(null); }, [mode, epoch]);
    const showOriginal = resolveShowOriginal(localOriginal, mode);

    // One request lane shared by the initial mount and the section-Translate
    // retry. `alive` guards a late resolve after unmount / key change; the
    // batch queue de-dupes concurrent asks for the same id, so a re-run costs
    // nothing when one is already out.
    const run = (): (() => void) => {
        let alive = true;
        setLoading(true);
        setUnavailable(null);
        fetchSignalTranslation(signalId, targetLang, original, cacheKey)
            .then(r => {
                if (!alive) return;
                if (r.kind === 'ok') setTranslated(r.text);
                else if (r.kind === 'unavailable') setUnavailable(r.reason);
            })
            .finally(() => { if (alive) setLoading(false); });
        return () => { alive = false; };
    };

    useEffect(() => {
        // cacheKey changes in place when the page language changes (Settings):
        // adopt the new language's cached translation, or clear and re-fetch.
        const cached = memo.get(cacheKey);
        if (cached !== undefined) { setTranslated(cached); setUnavailable(null); return; }
        setTranslated(null);
        setUnavailable(null);
        if (!eligible || settledNone.has(cacheKey)) return;
        return run();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [eligible, cacheKey, signalId, original, targetLang]);

    // Explicit section Translate: retry a fetch that failed (failures are never
    // memoized, so this is a plain re-ask). A settled no-op is not retried —
    // there is nothing to get, and the shared bucket is finite.
    useEffect(() => {
        if (!shouldRetryFetch({ mode, epoch }) || !eligible || translated) return;
        if (settledNone.has(cacheKey)) return;
        return run();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [mode, epoch, eligible, cacheKey, signalId, original, targetLang, translated]);

    // Report the REAL state up to the enclosing section so its control can be
    // derived from what happened rather than from the click. Inert no-op
    // outside a <TranslatedSection>.
    const status: ChildTranslationStatus = !eligible
        ? 'none'
        : translated ? 'done'
        : loading ? 'pending'
        : unavailable ? 'failed'
        : 'none';
    useReportTranslationStatus(status);

    const display = translated && !showOriginal ? translated : original;
    const flag = showOriginal || !translated;

    return {
        eligible,
        original,
        sourceLang,
        translated,
        loading,
        unavailable,
        unavailableNote: unavailable && mode === 'translated'
            ? describeUnavailable(unavailable, translateRetryAfterSeconds())
            : null,
        showOriginal,
        display,
        hasToggle: !!translated,
        toggleLabel: showOriginal ? L.translation : L.original,
        toggleTip: flag ? `Original (${(sourceLang || '').toUpperCase()})` : 'Translated',
        translatingLabel: L.translating,
        toggle: () => setLocalOriginal(!showOriginal),
    };
}

/**
 * The exact markup `TranslatableHeadline` has always rendered, pulled out so
 * a consumer driving the hook directly (SignalStream's mobile row) can reuse
 * it byte-for-byte for the desktop shape rather than re-deriving it — one
 * hook instance, no drift between the two render sites.
 */
export const TranslatableHeadlineInline: React.FC<{ state: TranslatableHeadlineState }> = ({ state }) => {
    // Not eligible, or nothing in flight and nothing to declare → plain
    // original headline (unchanged for every ambient surface).
    if (!state.eligible || (!state.translated && !state.loading && !state.unavailableNote)) {
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
            {/* The reader asked and we could not deliver — say so on the row
                itself, next to the text that stayed foreign. */}
            {!state.translated && !state.loading && state.unavailableNote && (
                <span className="th-unavailable"> · {state.unavailableNote}</span>
            )}
        </span>
    );
};

export const TranslatableHeadline: React.FC<Props> = (props) => {
    const state = useTranslatableHeadline(props);
    return <TranslatableHeadlineInline state={state} />;
};

export default TranslatableHeadline;
