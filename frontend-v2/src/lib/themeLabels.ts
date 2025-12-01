export const themeLabels: Record<string, string> = {
    // World Bank codes
    'WB_621_HEALTH_NUTRITION_AND_POPULATION': 'Health & Nutrition',
    'WB_2670_JOBS': 'Employment',
    'WB_507_ENERGY_AND_EXTRACTIVES': 'Energy & Mining',
    'WB_469_EDUCATION': 'Education',
    'WB_1619_WATER': 'Water Resources',
    'WB_1637_AGRICULTURE_AND_FOOD': 'Agriculture & Food',
    'WB_434_TRANSPORT': 'Transportation',
    'WB_2810_CLIMATE_CHANGE': 'Climate Change',
    'WB_1637_URBAN_DEVELOPMENT': 'Urban Development',

    // EPU codes
    'EPU_POLICY': 'Economic Policy',
    'EPU_POLICY_POLICY': 'Economic Policy',
    'EPU_ECONOMY_HISTORIC': 'Economic History',
    'EPUPOLICYPOLICY': 'Economic Policy',
    'EPUECONOMYHISTORIC': 'Economic History',

    // Crisis codes
    'CRISISLEX_CRISISLEXREC': 'Crisis Event',
    'CRISISLEX_C01_RESOURCE': 'Resource Crisis',
    'CRISISLEX_C02_DISASTER': 'Natural Disaster',
    'CRISISLEX_C03_DISEASE': 'Disease Outbreak',

    // Environment codes
    'UNGP_FORESTS_RIVERS_OCEANS': 'Environment',
    'ENV_FOREST': 'Forestry',
    'ENV_OCEAN': 'Ocean & Marine',
    'ENV_CLIMATE': 'Climate',

    // Ethnicity & Culture codes
    'TAX_ETHNICITY': 'Ethnicity',
    'TAX_ETHNICITY_AMERICAN': 'American Culture',
    'TAX_ETHNICITY_FRENCH': 'French Culture',
    'TAX_ETHNICITY_CHINESE': 'Chinese Culture',
    'TAX_ETHNICITY_INDIAN': 'Indian Culture',
    'TAX_WORLDLANGUAGES': 'Languages',

    // US Politics codes
    'USPEC_POLITICS_GENERAL1': 'US Politics',
    'USPEC_POLICY1': 'US Policy',
    'USPEC_POLICY2': 'US Domestic Policy',
    'USPEC_POLICY_ECONOMIC': 'US Economic Policy',

    // General codes
    'GENERAL_GOVERNMENT': 'Government',
    'GENERAL_HEALTH': 'Health',
    'GENERAL_ECONOMY': 'Economy',
    'GENERAL_MILITARY': 'Military',

    // Media codes
    'MEDIA_MSM': 'Mainstream Media',
    'MEDIAMSM': 'Mainstream Media',
    'MEDIA_SOCIAL': 'Social Media',

    // Society codes
    'SOC_POINTSOFINTEREST': 'Points of Interest',
    'SOC_GENERALCRIME': 'Crime',
    'SOC_CRIME': 'Crime',
    'SOC_PROTEST': 'Protests',
    'SOC_UNREST': 'Civil Unrest',

    // Transport codes
    'TRANSPORT': 'Transportation',
    'PUBLICTRANSPORT': 'Public Transport',
    'TRANSPORT_AIR': 'Aviation',
    'TRANSPORT_RAIL': 'Railways',

    // Additional common themes
    'ECON_TRADE': 'International Trade',
    'ECON_INFLATION': 'Inflation',
    'ECON_UNEMPLOYMENT': 'Unemployment',
    'GOV_ELECTION': 'Elections',
    'GOV_LEGISLATION': 'Legislation',
    'TECH_AI': 'Artificial Intelligence',
    'TECH_CYBER': 'Cybersecurity',
    'ENERGY_OIL': 'Oil & Gas',
    'ENERGY_RENEWABLE': 'Renewable Energy'
}

// Improve the fallback function
export function getThemeLabel(code: string): string {
    if (!code) return 'Unknown'

    // Direct match
    const upper = code.toUpperCase()
    if (themeLabels[upper]) return themeLabels[upper]
    if (themeLabels[code]) return themeLabels[code]

    // Try removing prefixes and cleaning
    let cleaned = upper
        .replace(/^WB_\d+_/, '')           // Remove "WB_621_"
        .replace(/^EPU_/, '')               // Remove "EPU_"
        .replace(/^TAX_/, '')               // Remove "TAX_"
        .replace(/^SOC_/, '')               // Remove "SOC_"
        .replace(/^USPEC_/, 'US ')          // "USPEC_" → "US "
        .replace(/^CRISISLEX_/, '')         // Remove "CRISISLEX_"
        .replace(/^UNGP_/, '')              // Remove "UNGP_"
        .replace(/^GENERAL_/, '')           // Remove "GENERAL_"
        .replace(/^MEDIA/, '')              // Remove "MEDIA"
        .replace(/^ENV_/, '')               // Remove "ENV_"
        .replace(/^ECON_/, 'Economic ')     // "ECON_" → "Economic "
        .replace(/^GOV_/, 'Government ')    // "GOV_" → "Government "
        .replace(/^TECH_/, 'Technology ')   // "TECH_" → "Technology "
        .replace(/^ENERGY_/, 'Energy ')     // "ENERGY_" → "Energy "
        .replace(/_AND_/g, ' & ')           // "_AND_" → " & "
        .replace(/_/g, ' ')                 // Underscores → spaces
        .replace(/(\d+)/g, '')              // Remove numbers
        .replace(/\s+/g, ' ')               // Multiple spaces → single
        .trim()

    // If very short or empty, return original
    if (cleaned.length < 3) return code

    // Title case
    return cleaned
        .toLowerCase()
        .split(' ')
        .filter(w => w.length > 0)
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ')
}

// Export getThemeIcon function that was duplicated in ThemeDetail
export function getThemeIcon(theme: string): string {
    const upper = theme.toUpperCase()
    if (upper.includes('ECONOMY') || upper.includes('ECON')) return '💰'
    if (upper.includes('GOVERNMENT') || upper.includes('GOV')) return '🏛️'
    if (upper.includes('MILITARY') || upper.includes('WAR') || upper.includes('CONFLICT')) return '⚔️'
    if (upper.includes('HEALTH') || upper.includes('DISEASE') || upper.includes('NUTRITION')) return '🏥'
    if (upper.includes('ENVIRONMENT') || upper.includes('CLIMATE') || upper.includes('FOREST')) return '🌍'
    if (upper.includes('TECH') || upper.includes('CYBER')) return '💻'
    if (upper.includes('CRIME') || upper.includes('ARREST')) return '🚨'
    if (upper.includes('PROTEST') || upper.includes('UNREST')) return '✊'
    if (upper.includes('ELECTION') || upper.includes('VOTE')) return '🗳️'
    if (upper.includes('ENERGY') || upper.includes('OIL')) return '⚡'
    if (upper.includes('TRANSPORT')) return '🚗'
    if (upper.includes('CRISIS')) return '🔴'
    if (upper.includes('HOLIDAY')) return '🎉'
    if (upper.includes('ETHNICITY') || upper.includes('LANGUAGE')) return '🗣️'
    if (upper.includes('POLICY')) return '📋'
    if (upper.includes('JOB') || upper.includes('EMPLOY')) return '💼'
    if (upper.includes('EDUCATION')) return '📚'
    if (upper.includes('WATER')) return '💧'
    if (upper.includes('AGRICULTURE') || upper.includes('FOOD')) return '🌾'
    return '📰'
}
