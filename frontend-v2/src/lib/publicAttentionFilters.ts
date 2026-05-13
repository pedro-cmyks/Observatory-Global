const PUBLIC_ATTENTION_NOISE = [
    /\b(NFL|NBA|MLB|NHL|FIFA|UFC|ESPN|MLS|Premier League|Champions League|World Series|Super Bowl)\b/i,
    /\b(actor|actress|singer|rapper|celebrity|filmography|discography|reality television|television personality)\b/i,
    /\b(Oscar|Grammy|Emmy|Billboard|box office|red carpet|paparazzi|streaming series)\b/i,
    /\b(Kardashian|Taylor Swift|Bieber|Beyonce|Drake|LeBron|Messi|Ronaldo)\b/i,
    /\b(horoscope|zodiac|recipe|crossword|wedding|sneaker|shopping guide|discount code)\b/i,
]

export function isPublicAttentionRelevant(title: string): boolean {
    return !PUBLIC_ATTENTION_NOISE.some(pattern => pattern.test(title.replace(/_/g, ' ')))
}
