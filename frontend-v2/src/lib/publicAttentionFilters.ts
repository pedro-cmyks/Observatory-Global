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
    // Web-infrastructure articles inflated by consent banners / browser-UI
    // links, not by attention — "Cookie (informatique)" hit 4M views with zero
    // media and one country (capture-doc C3). Disambiguated-tech parentheticals
    // in any major language + the perennial consent-traffic titles.
    /\((inform[aá]ti(?:que|ca)|computing|Internet|Informatik|informatica)\)/i,
    /^(HTTP cookie|Cookie|Cach[eé]|CAPTCHA|QR code|C[oó]digo QR|Web browser|Navigateur web|Navegador web)$/i,
    // Non-English sports tournaments/leagues the English patterns above miss.
    /\b(Copa Mundial|Coupe du monde|Coppa del Mondo|Mundial de F[uú]tbol|Weltmeisterschaft|Bundesliga|La Liga|Serie A|Ligue 1)\b/i,
    // Bare-domain titles (".xyz" in the global dock — capture-doc L2). A title
    // that IS a domain/TLD is redirect or consent traffic, not attention.
    // Trade-off accepted: also drops "Amazon.com"-style company articles.
    /^\.?[\w-]+\.(xyz|com|net|org|io|co|tv|me|ly|gg|info|biz|online|site|app|dev)$/i,
    /^\.\w+$/,
]

export function isPublicAttentionRelevant(title: string): boolean {
    return !PUBLIC_ATTENTION_NOISE.some(pattern => pattern.test(title.replace(/_/g, ' ')))
}
