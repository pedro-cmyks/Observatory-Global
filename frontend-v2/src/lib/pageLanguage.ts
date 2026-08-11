import { useSyncExternalStore } from 'react'

/**
 * Page language — the TRANSLATION TARGET for content (headlines, thread
 * labels, source excerpts). NOT a UI-chrome i18n system: app chrome stays
 * as written; only what the translate lanes produce is aimed at this
 * language.
 *
 * Resolution order: the user's stored choice (SettingsPanel) → the browser
 * language → 'en'. Stored in localStorage so it survives reloads; a module
 * variable backs it up when storage is unavailable (privacy mode) so the
 * choice at least holds for the session. Consumers subscribe via
 * `usePageLanguage()` (useSyncExternalStore) so a change in Settings
 * re-targets every mounted translatable component without a reload.
 *
 * The backend translate endpoints accept any ISO 639-1 base code (the
 * prompt is language-name driven, not enum-gated), so the options list
 * below is curated for the picker, not a hard allowlist.
 */

const STORAGE_KEY = 'atlas.page-language.v1'
const CHANGE_EVENT = 'atlas:page-language'

export interface PageLanguageOption {
    code: string
    label: string
}

// Curated picker options (endpoint accepts any ISO 639-1 code; these are the
// languages the corpus actually serves at volume). Labels in their own
// language — a reader hunting for theirs shouldn't need English to find it.
export const PAGE_LANGUAGE_OPTIONS: PageLanguageOption[] = [
    { code: 'en', label: 'English' },
    { code: 'es', label: 'Español' },
    { code: 'pt', label: 'Português' },
    { code: 'fr', label: 'Français' },
    { code: 'de', label: 'Deutsch' },
    { code: 'it', label: 'Italiano' },
    { code: 'ru', label: 'Русский' },
    { code: 'uk', label: 'Українська' },
    { code: 'tr', label: 'Türkçe' },
    { code: 'ar', label: 'العربية' },
    { code: 'fa', label: 'فارسی' },
    { code: 'hi', label: 'हिन्दी' },
    { code: 'zh', label: '中文' },
    { code: 'ja', label: '日本語' },
    { code: 'ko', label: '한국어' },
]

/** ISO 639-1 base code from any BCP-47 tag ('es-CO' → 'es'); null if unusable. */
export function normalizeLang(raw: string | null | undefined): string | null {
    const base = (raw || '').trim().slice(0, 2).toLowerCase()
    return /^[a-z]{2}$/.test(base) ? base : null
}

// Session fallback when localStorage is unavailable (privacy mode / quota).
let memoryLang: string | null = null

export function browserLanguage(): string {
    try {
        return normalizeLang(typeof navigator !== 'undefined' ? navigator.language : null) ?? 'en'
    } catch {
        return 'en'
    }
}

/** The user's explicit choice, or null when following the browser (auto). */
export function getStoredPageLanguage(): string | null {
    try {
        return normalizeLang(localStorage.getItem(STORAGE_KEY))
    } catch {
        return memoryLang
    }
}

/** The effective translation target right now. */
export function getPageLanguage(): string {
    return getStoredPageLanguage() ?? browserLanguage()
}

/** Set the page language; null = back to auto (browser language). */
export function setPageLanguage(lang: string | null): void {
    const normalized = normalizeLang(lang)
    memoryLang = normalized
    try {
        if (normalized) localStorage.setItem(STORAGE_KEY, normalized)
        else localStorage.removeItem(STORAGE_KEY)
    } catch { /* privacy mode — memoryLang carries the session */ }
    try {
        window.dispatchEvent(new Event(CHANGE_EVENT))
    } catch { /* non-browser env (tests) — nothing subscribed */ }
}

export function subscribePageLanguage(cb: () => void): () => void {
    if (typeof window === 'undefined') return () => {}
    const onStorage = (e: StorageEvent) => { if (e.key === STORAGE_KEY) cb() }
    window.addEventListener(CHANGE_EVENT, cb)
    window.addEventListener('storage', onStorage) // cross-tab
    return () => {
        window.removeEventListener(CHANGE_EVENT, cb)
        window.removeEventListener('storage', onStorage)
    }
}

/** Reactive page language — re-renders the consumer when Settings changes it. */
export function usePageLanguage(): string {
    return useSyncExternalStore(subscribePageLanguage, getPageLanguage, () => 'en')
}
