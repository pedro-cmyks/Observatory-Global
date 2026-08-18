import { useCallback } from 'react'
import { normalizeLang, usePageLanguage } from './pageLanguage'

/**
 * UI-CHROME i18n — the labels WE write (tile captions, section kickers,
 * buttons, empty states, tooltips).
 *
 * This is deliberately NOT a translation system for MEASURED CONTENT.
 * Headlines, outlet names, receipts, thread labels and any prose the backend
 * serves belong to the translate lanes (TranslatableHeadline / /api/v2/
 * translate), which are honest about being machine translations of a source
 * text. Chrome is authored copy: it is written once, in each language, by us.
 *
 * Two rules make a translated page safe to ship:
 *   1. English is the universal fallback. A key without Spanish renders its
 *      English — never a blank cell, never a raw `brief.vital.signals` key.
 *   2. A translation may not assert more than the original. The catalogue
 *      tests enforce this mechanically: same placeholders, same digits.
 *
 * The language comes from the EXISTING page-language store (pageLanguage.ts) —
 * one language source of truth for the whole app, so the reader's choice
 * re-targets content translation and chrome together, reactively, no reload.
 * Chrome exists in en + es only; every other page language resolves to English
 * chrome rather than to an interface nobody reviewed.
 */

export type UiLang = 'en' | 'es'

export interface UiCopyEntry {
    en: string
    es?: string
}

/** The languages the CHROME is authored in (≠ the content translation targets). */
export const UI_LANGS: UiLang[] = ['en', 'es']

export const UI_COPY = {
    // ---------------- phone navigation ----------------
    // The bar is the reader's only way between surfaces on a phone, so it is
    // translated even though the console BEHIND two of its tabs is not: a
    // reader must be able to find their way back to the Brief.
    'nav.aria': { en: 'Atlas sections', es: 'Secciones de Atlas' },
    'nav.brief': { en: 'Brief', es: 'Diario' },
    'nav.lens': { en: 'Lens', es: 'Lente' },
    'nav.live': { en: 'Live', es: 'En vivo' },

    // ---------------- masthead ----------------
    'brief.masthead.eyebrow': {
        en: 'The Daily Instrument · Global Edition',
        es: 'El Instrumento Diario · Edición Global',
    },
    'brief.masthead.tagline': {
        en: 'Narrative intelligence — measured from coverage, not editorialized.',
        es: 'Inteligencia narrativa — medida desde la cobertura, sin editorializar.',
    },
    'brief.masthead.window': {
        en: 'Measured · Last 24 hours',
        es: 'Medido · Últimas 24 horas',
    },
    'brief.masthead.windowTip': {
        en: 'The Brief is the day’s edition — always the last 24 hours. For other time windows, open the console.',
        es: 'El Diario es la edición del día — siempre las últimas 24 horas. Para otras ventanas de tiempo, abre la consola.',
    },
    'brief.action.home': { en: '← Home', es: '← Inicio' },
    'brief.action.console': { en: 'Open Console', es: 'Abrir consola' },
    'brief.action.share': { en: '↑ Share', es: '↑ Compartir' },
    'brief.action.retry': { en: 'Retry live refresh', es: 'Reintentar actualización' },
    'brief.eclipse.tip': {
        en: 'A total attention eclipse is active — enter the console',
        es: 'Hay un eclipse de atención total activo — entra a la consola',
    },
    'brief.eclipse.aria': { en: 'Enter the eclipse', es: 'Entrar al eclipse' },

    // ---------------- depth dial (P1) ----------------
    // El conmutador LEER·OBSERVAR·CONSTRUIR (spec 2026-08-18-depth-dial §6).
    // El tip es honesto por construcción: el dial cambia vestuario, no datos.
    'dial.leer': { en: 'Read', es: 'Leer' },
    'dial.observar': { en: 'Observe', es: 'Observar' },
    'dial.construir': { en: 'Build', es: 'Construir' },
    'dial.tip': {
        en: 'Depth: how much instrument you see. Your place, focus and warnings travel with you.',
        es: 'Profundidad: cuánto instrumento ves. Tu lugar, tu foco y las advertencias viajan contigo.',
    },

    // ---------------- language control ----------------
    'brief.lang.label': { en: 'Language', es: 'Idioma' },
    'brief.lang.auto': { en: 'Auto (browser)', es: 'Automático (navegador)' },
    'brief.lang.tip': {
        en: 'Language. Marked (·) languages also have a translated interface; every other language translates headlines and source text only — and those always say they were translated.',
        es: 'Idioma. Los idiomas marcados (·) también tienen la interfaz traducida; los demás traducen solo titulares y texto de las fuentes — y esos siempre indican que fueron traducidos.',
    },

    // ---------------- loading / cache / error ----------------
    'brief.loading': { en: 'Loading brief…', es: 'Cargando el diario…' },
    'brief.cache.stale': {
        en: 'Showing cached brief while Atlas refreshes live data.',
        es: 'Mostrando el diario en caché mientras Atlas actualiza los datos en vivo.',
    },
    'brief.empty.title': { en: 'No brief available', es: 'No hay diario disponible' },

    // ---------------- freshness band ----------------
    'brief.freshness.aria': {
        en: 'Daily edition freshness',
        es: 'Vigencia de la edición diaria',
    },
    'brief.freshness.ariaExpand': {
        en: 'Daily edition freshness — tap to expand',
        es: 'Vigencia de la edición diaria — toca para ampliar',
    },
    'brief.freshness.sealed': { en: 'SEALED DAILY EDITION', es: 'EDICIÓN DIARIA SELLADA' },
    'brief.freshness.live': { en: 'LIVE VIEW', es: 'VISTA EN VIVO' },
    'brief.freshness.degradedTip': {
        en: 'This edition sealed incomplete and is served anyway, labelled. Nothing here was invented to fill the gaps.',
        es: 'Esta edición se selló incompleta y se sirve igual, etiquetada. Nada aquí se inventó para llenar los vacíos.',
    },
    'brief.freshness.receipts': {
        en: 'full text {ok}/{attempted} receipts',
        es: 'texto completo {ok}/{attempted} recibos',
    },

    // ---------------- method fold (mobile) ----------------
    // Vagón 3 (panel ciego 2026-08-18): the one-line summary the folded
    // seal/readiness/vitals strip collapses to on a phone. Chrome label only —
    // the facts live inside the fold, none of them deleted.
    'brief.methodFold.label': { en: 'Method & measurement', es: 'Método y medición' },

    // ---------------- markets band ----------------
    'brief.markets.collapsed': {
        en: 'World markets · live overlay, not sealed ▸',
        es: 'Mercados mundiales · capa en vivo, sin sellar ▸',
    },
    'brief.markets.ariaExpand': {
        en: 'World markets — live overlay, not part of the sealed edition — tap to expand',
        es: 'Mercados mundiales — capa en vivo, fuera de la edición sellada — toca para ampliar',
    },

    // ---------------- readiness rail ----------------
    'brief.readiness.aria': { en: 'Editorial readiness', es: 'Preparación editorial' },

    // ---------------- instrument strip (vitals) ----------------
    'brief.vitals.aria': { en: 'Today’s measured vitals', es: 'Los signos vitales medidos de hoy' },
    'brief.vital.signals': { en: 'Signals', es: 'Señales' },
    'brief.vital.signals.sub': { en: 'ingested in the last 24h', es: 'ingeridas en las últimas 24 h' },
    'brief.vital.countries': { en: 'Countries', es: 'Países' },
    'brief.vital.countries.sub': { en: 'with coverage in-window', es: 'con cobertura en la ventana' },
    'brief.vital.sources': { en: 'Sources', es: 'Fuentes' },
    'brief.vital.sources.sub': { en: 'outlet domains · raw 24h feed', es: 'dominios de medios · flujo bruto 24 h' },
    'brief.vital.sentiment': { en: 'Avg sentiment', es: 'Sentimiento medio' },
    'brief.vital.sentiment.mobile': { en: 'Sentiment · ±1 · ×10 below', es: 'Sentimiento · ±1 · ×10 abajo' },
    'brief.vital.stories': { en: 'Tracked stories', es: 'Historias seguidas' },
    'brief.vital.stories.sub': {
        en: 'ranked stories served this window',
        es: 'historias ordenadas servidas en esta ventana',
    },
    'brief.vital.stories.unknown': {
        en: 'unknown — the story lane did not answer',
        es: 'sin dato — el canal de historias no respondió',
    },
    'brief.vital.stories.tip': {
        en: 'Ranked stories served this window.',
        es: 'Historias ordenadas servidas en esta ventana.',
    },
    'brief.vital.gaps': { en: 'Coverage gaps', es: 'Vacíos de cobertura' },
    'brief.vital.gaps.mobile': { en: 'Gaps · unverified', es: 'Vacíos · sin verificar' },
    'brief.vital.gaps.sub': {
        en: 'categories with attention but zero verified rows',
        es: 'categorías con atención pero cero filas verificadas',
    },
    'brief.vital.gaps.unknown': {
        en: 'unknown — the coverage-gap lane did not answer',
        es: 'sin dato — el canal de vacíos de cobertura no respondió',
    },
    'brief.vital.gaps.tip': {
        en: 'Categories with attention but zero verified rows.',
        es: 'Categorías con atención pero cero filas verificadas.',
    },

    // ---------------- historical coverage note ----------------
    'brief.historical.label': { en: 'Historical processed', es: 'Histórico procesado' },
    'brief.historical.topicCoverage': { en: '{pct}% topic coverage', es: '{pct}% de cobertura temática' },
    'brief.historical.sentimentCoverage': { en: '{pct}% NLP sentiment', es: '{pct}% de sentimiento NLP' },
    'brief.historical.tip': {
        en: 'This long-window brief is served from compact processed historical aggregates synced from the local archive, not from raw historical rows.',
        es: 'Este diario de ventana larga se sirve desde agregados históricos procesados y compactos, sincronizados del archivo local, no desde filas históricas en bruto.',
    },

    // ---------------- sections ----------------
    'brief.section.world': { en: 'The World', es: 'El Mundo' },
    'brief.section.world.kicker': { en: 'Serious geopolitics', es: 'Geopolítica en serio' },
    'brief.section.radar': { en: 'Under the Radar', es: 'Bajo el Radar' },
    'brief.section.radar.kicker': { en: 'The Atlas edge', es: 'La ventaja de Atlas' },
    'brief.section.culture': { en: 'Culture, Sport & Life', es: 'Cultura, Deporte y Vida' },
    'brief.section.culture.kicker': {
        en: 'Where the rest of us live',
        es: 'Donde vivimos los demás',
    },
    'brief.sections.aria': {
        en: 'Sections of today’s edition',
        es: 'Secciones de la edición de hoy',
    },
    'brief.section.world.lede': {
        en: 'The day’s hardest news, ranked by measured coverage. One lead, then the rest of the desk — each with its own receipts. Coverage counts are the volume of press, not a judgement of importance.',
        es: 'Las noticias más duras del día, ordenadas por cobertura medida. Una principal, luego el resto de la mesa — cada una con sus propios recibos. Los conteos de cobertura son volumen de prensa, no un juicio de importancia.',
    },
    'brief.section.radar.lede.a': {
        en: 'What the ranked front page leaves out: stories the pipeline',
        es: 'Lo que la portada ordenada deja fuera: historias que el sistema',
    },
    'brief.section.radar.lede.em': { en: 'sees', es: 've' },
    'brief.section.radar.lede.b': {
        en: 'but has not verified, and stories eclipsed by the day’s dominant coverage. Nothing is deleted — it is surfaced with its honest status.',
        es: 'pero no ha verificado, e historias eclipsadas por la cobertura dominante del día. Nada se borra — se muestra con su estado honesto.',
    },
    'brief.section.culture.lede': {
        en: 'A celebrity obituary or a World Cup semifinal is not noise — someone is reading it, and a soft label can hide a hard story folded inside it. Nothing here was judged unimportant by a machine; it simply has its own section instead of crowding out the front page. You decide what matters.',
        es: 'El obituario de una celebridad o una semifinal del Mundial no son ruido — alguien los está leyendo, y una etiqueta blanda puede esconder una historia dura doblada dentro. Nada aquí fue juzgado sin importancia por una máquina; simplemente tiene su propia sección en vez de desplazar la portada. Tú decides qué importa.',
    },
    'brief.radar.missing': { en: 'What is missing', es: 'Lo que falta' },
    'brief.gap.aria': {
        en: 'The Gap — today’s measured blindspot',
        es: 'El Vacío — el punto ciego medido de hoy',
    },
    'brief.gap.kicker': {
        en: 'The coverage Atlas did not see',
        es: 'La cobertura que Atlas no vio',
    },
    'brief.gap.title': { en: 'The Gap', es: 'El Vacío' },
    'brief.rising.aria': {
        en: 'What is rising — measured acceleration',
        es: 'Lo que sube — aceleración medida',
    },
    'brief.rising.kicker': { en: 'Measured acceleration', es: 'Aceleración medida' },
    'brief.rising.title': { en: 'What Is Rising', es: 'Lo Que Sube' },

    // The standfirst's own clauses. The numbers are measured; the sentence
    // around them is ours. "no LLM selected or ranked the edition" is a load-
    // bearing claim — it must survive translation without softening.
    'brief.standfirst.sealed': {
        en: '{nodes} measured story nodes, {receipts} frozen receipts; no LLM selected or ranked the edition.',
        es: '{nodes} nodos de historia medidos, {receipts} recibos congelados; ningún LLM seleccionó ni ordenó la edición.',
    },
    'brief.standfirst.live': {
        en: '{signals} signals across {countries} countries from {sources} sources',
        es: '{signals} señales en {countries} países desde {sources} fuentes',
    },
    'brief.standfirst.lead': { en: 'lead', es: 'principal' },

    // ---------------- story cards & receipts ----------------
    'brief.card.lead': { en: 'Lead', es: 'Principal' },
    'brief.card.story': { en: 'Story', es: 'Historia' },
    'brief.card.signals': { en: '{n} signals', es: '{n} señales' },
    'brief.card.measured': { en: 'Measured · last 24h', es: 'Medido · últimas 24 h' },
    'brief.card.topRanked': { en: 'top-ranked thread · 24h window', es: 'hilo mejor posicionado · ventana 24 h' },
    'brief.card.topRankedTip': {
        en: 'Top-ranked story in this window (movement, volume and coherence). Sample evidence headlines shown when available.',
        es: 'Historia mejor posicionada en esta ventana (movimiento, volumen y coherencia). Se muestran titulares de evidencia de muestra cuando existen.',
    },
    'brief.card.whoTellsIt': { en: 'Who is telling it', es: 'Quién la cuenta' },
    'brief.card.whyNow': { en: 'Why now', es: 'Por qué ahora' },
    'brief.card.receipts': { en: 'Receipts', es: 'Recibos' },
    'brief.card.receiptsCaption': {
        en: 'Receipts — real source · outlet origin when known',
        es: 'Recibos — fuente real · origen del medio cuando se conoce',
    },
    'brief.card.open': { en: 'Open story →', es: 'Abrir historia →' },
    'brief.card.save': { en: '◇ Save', es: '◇ Guardar' },
    'brief.card.saved': { en: '◆ Saved', es: '◆ Guardada' },
    'brief.card.savedTip': { en: 'Remove from investigation', es: 'Quitar de la investigación' },
    // Vagón 1 (panel ciego 2026-08-18): the grab-bag mark the payload already
    // carries, worded as the measurement it is — no judgment, no adjective.
    'brief.warn.mixedGeo': { en: 'Mixed geography', es: 'Geografía mezclada' },
    'brief.warn.mixedGeo.tip': {
        en: 'The measurement found receipts from more than one distinct event/geography filed under this story — its significant countries do not appear together in the same receipts. Read the receipts, not only the label.',
        es: 'La medición detectó recibos de más de un evento/geografía distinto archivados bajo esta historia — sus países significativos no aparecen juntos en los mismos recibos. Lee los recibos, no solo la etiqueta.',
    },
    'brief.lane.retry': { en: 'Ask the story lane again ↻', es: 'Preguntar de nuevo al canal de historias ↻' },
    'brief.lead.laneFailed': { en: 'lane did not answer', es: 'el canal no respondió' },
    'brief.lead.awaiting': { en: 'awaiting verification', es: 'esperando verificación' },
    'brief.lead.awaitingBody': {
        en: 'Today’s top stories are awaiting verification — their labels have not yet been checked against their own receipts. Rather than lead with an unverified label, see the unassembled desk below for the raw receipts.',
        es: 'Las historias principales de hoy están esperando verificación — sus etiquetas aún no se han contrastado con sus propios recibos. En vez de encabezar con una etiqueta sin verificar, mira la mesa sin ensamblar más abajo para ver los recibos en bruto.',
    },
    'brief.lead.belowBar': { en: 'no story clears the bar', es: 'ninguna historia supera la barra' },
    // Two authored forms rather than an appended "s": Spanish agreement is not
    // a suffix, and the singular sentence reads differently in both languages.
    'brief.lead.belowBarBody.one': {
        en: 'No assembled story clears the {pct}% confidence bar this window — {n} tracked cluster sits below it. Rather than lead with a label we don’t trust, see the unassembled desk below for the raw receipts.',
        es: 'Ninguna historia ensamblada supera la barra de confianza del {pct}% en esta ventana — {n} grupo rastreado queda por debajo. En vez de encabezar con una etiqueta en la que no confiamos, mira la mesa sin ensamblar más abajo para ver los recibos en bruto.',
    },
    'brief.lead.belowBarBody.other': {
        en: 'No assembled story clears the {pct}% confidence bar this window — {n} tracked clusters sit below it. Rather than lead with a label we don’t trust, see the unassembled desk below for the raw receipts.',
        es: 'Ninguna historia ensamblada supera la barra de confianza del {pct}% en esta ventana — {n} grupos rastreados quedan por debajo. En vez de encabezar con una etiqueta en la que no confiamos, mira la mesa sin ensamblar más abajo para ver los recibos en bruto.',
    },

    // ---------------- back matter ----------------
    'brief.heat.title': { en: 'Heating Up', es: 'Calentándose' },
    'brief.map.title': { en: 'Signal density — last 24h', es: 'Densidad de señal — últimas 24 h' },
    'brief.map.tip': {
        en: 'Signal density: how many media signals Atlas captured per country in this window. Darker = more coverage. Coverage volume reflects media attention, not geopolitical importance.',
        es: 'Densidad de señal: cuántas señales de medios capturó Atlas por país en esta ventana. Más oscuro = más cobertura. El volumen de cobertura refleja atención mediática, no importancia geopolítica.',
    },
    'brief.mostActive.title': { en: 'Most Active', es: 'Más Activos' },
    'brief.sources.title': { en: 'Sources', es: 'Fuentes' },
    'brief.byCategory.title': { en: 'By Category', es: 'Por Categoría' },
    'brief.byTheme.title': { en: 'By Theme', es: 'Por Tema' },
    'brief.mostNegative.title': { en: 'Most Negative', es: 'Más Negativos' },
    'brief.mostPositive.title': { en: 'Most Positive', es: 'Más Positivos' },
    'brief.watches.kicker': { en: 'Saved watches', es: 'Seguimientos guardados' },
    // No `es`: the word is identical in both languages. Omitting it (rather
    // than duplicating) keeps "has a translation" meaningful in the catalogue.
    'brief.watches.global': { en: 'Global' },
    'brief.watches.open': { en: 'Open in Atlas →', es: 'Abrir en Atlas →' },
    'brief.watches.remove': { en: 'Remove watch', es: 'Quitar seguimiento' },
    'brief.watches.noChange': { en: 'no change', es: 'sin cambios' },

    // ---------------- country edition ----------------
    // Country mood tile. The words are a BUCKET of the measured aggregate, not
    // a new claim — the thresholds are unchanged, only their names.
    'brief.mood.positive': { en: 'POSITIVE', es: 'POSITIVO' },
    'brief.mood.negative': { en: 'NEGATIVE', es: 'NEGATIVO' },
    'brief.mood.neutral': { en: 'NEUTRAL' },

    'brief.country.label': { en: 'Country:', es: 'País:' },
    'brief.country.search': { en: 'Search country…', es: 'Buscar país…' },
    'brief.country.noMatch': { en: 'No country matches “{query}”.', es: 'Ningún país coincide con «{query}».' },
    'brief.country.searchHint': {
        en: 'This box searches country names. Try one — or ask a full question and Atlas will read it across the stories.',
        es: 'Esta caja busca nombres de países. Prueba con uno — o haz una pregunta completa y Atlas la leerá a través de las historias.',
    },
    'brief.country.notInTop': { en: 'not in top countries', es: 'fuera de los países principales' },
    'brief.country.kicker': { en: 'Country edition', es: 'Edición de país' },
    'brief.country.signals': { en: 'Signals', es: 'Señales' },
    'brief.country.signalsSub': { en: 'in the last 24h', es: 'en las últimas 24 h' },
    'brief.country.stories': { en: 'Stories', es: 'Historias' },
    'brief.country.storiesSub': { en: 'country-scoped stories', es: 'historias del ámbito del país' },
    'brief.country.mood': { en: 'Country mood', es: 'Ánimo del país' },
    'brief.country.moodSub': { en: 'window aggregate', es: 'agregado de la ventana' },
    'brief.country.moodTip': {
        en: 'Aggregate sentiment across this country’s signals in the window.',
        es: 'Sentimiento agregado de las señales de este país en la ventana.',
    },
    'brief.country.loading': {
        en: 'Assembling this country’s edition for the last {hours}h…',
        es: 'Ensamblando la edición de este país de las últimas {hours} h…',
    },
    'brief.country.failed': {
        en: 'Atlas could not assemble this country’s edition right now — the door did not answer, so nothing about this country’s coverage is claimed either way.',
        es: 'Atlas no pudo ensamblar la edición de este país ahora mismo — la puerta no respondió, así que no se afirma nada sobre su cobertura en ningún sentido.',
    },
    'brief.country.retry': { en: 'Try this country again ↻', es: 'Intentar este país de nuevo ↻' },
    'brief.country.openInAtlas': { en: 'Open country in Atlas →', es: 'Abrir el país en Atlas →' },
    'brief.country.today': { en: 'Today', es: 'Hoy' },
    'brief.country.todayKicker': { en: 'The country now', es: 'El país ahora' },
    'brief.country.radarKicker': {
        en: 'Domestic signal, not yet surfacing',
        es: 'Señal doméstica, aún sin aflorar',
    },

    // ---------------- day anatomy (reader) ----------------
    // Segment kickers for the near → changed → odd → world anatomy (spec
    // 2026-08-17 §3). `changedSince` renders only when hoursSince() returns
    // non-null — a first visit gets the plain kicker, never "0h ago". The
    // proposed-place hint is the §6 "never silent" obligation made visible.
    'anatomy.kicker.near': { en: 'Near you · {place}', es: 'Cerca de ti · {place}' },
    'anatomy.kicker.changed': { en: 'What changed', es: 'Qué cambió' },
    'anatomy.kicker.changedSince': {
        en: 'What changed · since your last read, {h}h ago',
        es: 'Qué cambió · desde tu última lectura, hace {h}h',
    },
    'anatomy.kicker.odd': { en: 'What is odd', es: 'Qué está raro' },
    'anatomy.kicker.world': { en: 'The world', es: 'El mundo' },
    'anatomy.place.change': { en: 'change', es: 'cambiar' },
    'anatomy.place.proposed': {
        en: 'guessed from your device — tap to change',
        es: 'propuesto por tu dispositivo — toca para cambiar',
    },

    // ---------------- footer / colophon / error ----------------
    'brief.method.lead': {
        en: 'Positions and prominence are measured from coverage volume, languages and countries.',
        es: 'Las posiciones y la prominencia se miden a partir del volumen de cobertura, los idiomas y los países.',
    },
    'brief.method.body': {
        en: 'Nothing is hidden — every story has a section. "Surging / fading" is the change in signals versus the prior 10 hours of the raw feed; coverage-country is where an outlet’s row is geo-tagged, not necessarily the story’s subject. Receipts link to the source. Where a verification gate found no admissible row, we say so plainly rather than fill the space.',
        es: 'Nada se oculta — cada historia tiene una sección. «Subiendo / bajando» es el cambio en señales frente a las 10 horas anteriores del flujo bruto; el país de cobertura es donde se geoetiqueta la fila de un medio, no necesariamente el sujeto de la historia. Los recibos enlazan a la fuente. Donde una barra de verificación no encontró ninguna fila admisible, lo decimos claramente en vez de rellenar el espacio.',
    },
    'brief.footer.cta': {
        en: 'Enter Atlas — full intelligence terminal →',
        es: 'Entrar a Atlas — terminal de inteligencia completo →',
    },
    'brief.colophon.edition': { en: 'The Atlas Edition · L1', es: 'La Edición Atlas · L1' },
    'brief.colophon.generated': { en: 'Generated {when}', es: 'Generado {when}' },
    'brief.colophon.window': { en: 'Measured · last 24 hours', es: 'Medido · últimas 24 horas' },
    'brief.error.load': { en: 'Failed to load briefing data.', es: 'No se pudieron cargar los datos del informe.' },
    'brief.error.unavailable': {
        en: 'Live briefing unavailable — retry when the data service recovers.',
        es: 'Informe en vivo no disponible — reintenta cuando el servicio de datos se recupere.',
    },
    'brief.error.retry': { en: 'Retry briefing', es: 'Reintentar informe' },
    'brief.offline': {
        en: 'Offline — showing the last Brief you loaded.',
        es: 'Sin conexión — mostrando el último Diario que cargaste.',
    },
} as const satisfies Record<string, UiCopyEntry>

export type UiCopyKey = keyof typeof UI_COPY

type Catalogue = Partial<Record<string, UiCopyEntry>>

/**
 * The chrome language for a page language. Anything we have not authored
 * chrome for resolves to English — an honestly English interface beats a
 * half-invented one.
 */
export function uiLang(pageLang: string | null | undefined): UiLang {
    return normalizeLang(pageLang) === 'es' ? 'es' : 'en'
}

/**
 * Resolve one key. Falls back, in order: requested language → English →
 * the caller's explicit fallback. Never returns the key name.
 */
export function resolveCopy(
    key: UiCopyKey,
    lang: UiLang,
    catalogue: Catalogue = UI_COPY,
    fallback = '',
): string {
    const entry = catalogue[key]
    if (!entry) return fallback
    if (lang === 'es' && entry.es) return entry.es
    return entry.en || fallback
}

/** `{name}` substitution. An unprovided placeholder is left visible, not printed as `undefined`. */
export function formatCopy(template: string, vars: Record<string, string | number>): string {
    return template.replace(/\{([a-zA-Z_]+)\}/g, (whole, name: string) =>
        Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : whole,
    )
}

export interface UiCopy {
    /** Translate a key, optionally interpolating `{placeholders}`. */
    t: (key: UiCopyKey, vars?: Record<string, string | number>) => string
    /** The resolved chrome language — 'en' | 'es'. */
    lang: UiLang
    /** True when the chrome is rendering in Spanish (for lang attributes). */
    isEs: boolean
}

/**
 * Reactive chrome copy. Subscribes to the shared page-language store, so
 * switching language re-renders in place: no reload, no lost scroll position.
 */
export function useUiCopy(): UiCopy {
    const lang = uiLang(usePageLanguage())
    const t = useCallback(
        (key: UiCopyKey, vars?: Record<string, string | number>) => {
            const s = resolveCopy(key, lang)
            return vars ? formatCopy(s, vars) : s
        },
        [lang],
    )
    return { t, lang, isEs: lang === 'es' }
}
