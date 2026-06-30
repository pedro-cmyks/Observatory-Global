const PUBLIC_ATTENTION_NOISE = [
    /\b(NFL|NBA|MLB|NHL|FIFA|UFC|ESPN|MLS|Premier League|Champions League|World Series|Super Bowl)\b/i,
    /\b(actor|actress|singer|rapper|celebrity|filmography|discography|reality television|television personality)\b/i,
    /\b(Oscar|Grammy|Emmy|Billboard|box office|red carpet|paparazzi|streaming series)\b/i,
    /\b(Kardashian|Taylor Swift|Bieber|Beyonce|Drake|LeBron|Messi|Ronaldo|Haaland)\b/i,
    /\b(horoscope|zodiac|recipe|crossword|wedding|sneaker|shopping guide|discount code)\b/i,
    // Wikipedia namespace / meta pages (any language) — never a real attention
    // signal. "Wikipédia:Accueil principal" (the FR homepage) was ranking #1.
    /^(Wikip[eé]dia|Wikipedia|Special|Spezial|Especial|Sp[eé]ciale|Speciale|Portal|Portail|Categor|Cat[eé]gorie|Kategori|Help|Aide|Ayuda|Hilfe|Template|Wiktionary)\s*[:：]/i,
    /\b(Main Page|Accueil principal|Hoofdpagina|Pagina principale|Hauptseite|Portada|P[aá]gina principal|Strona główna|Главная страница)\b/i,
    // Disambiguated film / TV / album / game articles (the "(2026 film)" style).
    /\((\d{4} )?(film|movie|TV series|video game|album|song|pel[ií]cula)\)/i,
    // Non-English sports tournaments/leagues the English patterns above miss.
    /\b(Copa Mundial|Coupe du monde|Coppa del Mondo|Mundial de F[uú]tbol|Weltmeisterschaft|Bundesliga|La Liga|Serie A|Ligue 1)\b/i,
]

export function isPublicAttentionRelevant(title: string): boolean {
    return !PUBLIC_ATTENTION_NOISE.some(pattern => pattern.test(title.replace(/_/g, ' ')))
}
