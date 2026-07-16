/**
 * Pure decision helper for free-text translation (#204b — thread/topic labels).
 *
 * Unlike signal headlines (TranslatableHeadline), labels carry NO source_lang,
 * so the decision is heuristic:
 *   - raw thread-id / fallback labels ("dynamic topic 123", "cluster 42") are
 *     never translated — they are identifiers, not language;
 *   - ASCII-English-ish text shown to an English viewer renders plain (no call);
 *   - everything else is worth one POST — the endpoint answers same:true when
 *     no translation is needed and the caller keeps the original.
 */

// Fallback / identifier labels — never send these to the translator.
const FALLBACK_LABEL_RE = /^(dynamic[ -]topic[ -]?\d+|cluster[ -]?\d+)\b/i

// Typographic punctuation common in English headlines that is technically
// non-ASCII but says nothing about the language.
const TYPOGRAPHIC_RE = /[‘’“”–—… ·]/g

function looksEnglishAscii(text: string): boolean {
    const stripped = text.replace(TYPOGRAPHIC_RE, '')
    // eslint-disable-next-line no-control-regex
    return /^[\x00-\x7F]*$/.test(stripped)
}

export function shouldTranslate(text: string, targetLang: string): boolean {
    const t = (text || '').trim()
    if (!t) return false
    if (FALLBACK_LABEL_RE.test(t)) return false
    const lang = (targetLang || '').slice(0, 2).toLowerCase()
    if (!lang) return false
    if (lang === 'en' && looksEnglishAscii(t)) return false
    return true
}
