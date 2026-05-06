import React from 'react';
import {
    Briefcase, Landmark, Swords, Stethoscope, Laptop, Siren,
    HandMetal, Vote, Zap, Waves, Languages, FileText, User, Newspaper,
    Leaf, Users
} from 'lucide-react';

export const themeLabels: Record<string, string> = {
    // World Bank — governance & institutions
    'WB_696_PUBLIC_SECTOR_MANAGEMENT': 'Public Sector',
    'WB_678_DIGITAL_GOVERNMENT': 'Digital Government',
    'WB_2432_FRAGILITY_CONFLICT_AND_VIOLENCE': 'Conflict & Violence',
    'WB_133_INFORMATION_AND_COMMUNICATION_TECHNOLOGIES': 'Technology',
    'WB_621_HEALTH_NUTRITION_AND_POPULATION': 'Health & Nutrition',
    'WB_2670_JOBS': 'Employment',
    'WB_507_ENERGY_AND_EXTRACTIVES': 'Energy & Mining',
    'WB_469_EDUCATION': 'Education',
    'WB_1619_WATER': 'Water Resources',
    'WB_1637_AGRICULTURE_AND_FOOD': 'Agriculture & Food',
    'WB_434_TRANSPORT': 'Transportation',
    'WB_2810_CLIMATE_CHANGE': 'Climate Change',
    'WB_1637_URBAN_DEVELOPMENT': 'Urban Development',

    // World Bank — justice & rule of law (common in GDELT)
    'WB_NEGOTIATION': 'Negotiations',
    'WB_DISPUTE_RESOLUTION': 'Dispute Resolution',
    'WB_ALTERNATIVE_DISPUTE_RESOLUTION': 'Mediation',
    'WB_CONFLICT_AND_VIOLENCE': 'Conflict & Violence',
    'WB_ANTI_CORRUPTION': 'Anti-Corruption',
    'WB_JUSTICE': 'Justice',
    'WB_GOVERNANCE': 'Governance',
    'WB_RULE_OF_LAW': 'Rule of Law',
    'WB_ACCOUNTABILITY': 'Accountability',
    'WB_TRANSPARENCY': 'Transparency',
    'WB_HUMAN_RIGHTS': 'Human Rights',
    'WB_GENDER': 'Gender & Equality',
    'WB_POVERTY': 'Poverty',
    'WB_SOCIAL_PROTECTION': 'Social Safety Nets',
    'WB_FINANCIAL_SECTOR': 'Financial System',
    'WB_MACROECONOMIC_VULNERABILITY_AND_DEBT': 'Economic Debt',
    'WB_OIL_AND_GAS_POLICY_STRATEGY_AND_INSTITUTIONS': 'Oil & Gas Policy',
    'WB_IMMIGRATION': 'Immigration',
    'WB_WAGES': 'Wages & Labor',
    'WB_ICT_APPLICATIONS': 'Digital Applications',
    'WB_TRADE_POLICY': 'Trade Policy',
    'WB_INVESTMENT': 'Investment',
    'WB_TAXATION': 'Taxation',
    'WB_BANKING': 'Banking',
    'WB_INSURANCE': 'Insurance',
    'WB_INFRASTRUCTURE': 'Infrastructure',
    'WB_PRIVATE_SECTOR': 'Private Sector',
    'WB_COMPETITIVENESS': 'Economic Competition',
    'WB_INNOVATION': 'Innovation',
    'WB_DECENTRALIZATION': 'Local Government',
    'WB_FEDERALISM': 'Federal Structure',
    'WB_ELECTIONS': 'Elections',
    'WB_PARLIAMENT': 'Parliament',
    'WB_CONSTITUTION': 'Constitutional Affairs',
    'WB_SECURITY_SECTOR': 'Security Forces',
    'WB_MILITARY': 'Military',
    'WB_PEACEKEEPING': 'Peacekeeping',
    'WB_DIPLOMACY': 'Diplomacy',
    'WB_SANCTIONS': 'Sanctions',
    'WB_NUCLEAR': 'Nuclear Affairs',
    'WB_TERRORISM': 'Terrorism',
    'WB_ORGANIZED_CRIME': 'Organized Crime',
    'WB_DRUG_TRAFFICKING': 'Drug Trafficking',
    'WB_REFUGEE': 'Refugees',
    'WB_DISPLACEMENT': 'Displacement',
    'WB_HUMANITARIAN': 'Humanitarian Aid',
    'WB_FOOD_SECURITY': 'Food Security',
    'WB_WATER_AND_SANITATION': 'Water & Sanitation',
    'WB_DISEASE': 'Disease',
    'WB_PANDEMIC': 'Pandemic',
    'WB_MENTAL_HEALTH': 'Mental Health',
    'WB_EDUCATION_QUALITY': 'Education Quality',
    'WB_YOUTH': 'Youth',
    'WB_URBANIZATION': 'Urbanization',
    'WB_HOUSING': 'Housing',
    'WB_LAND': 'Land Rights',
    'WB_ENVIRONMENT': 'Environment',
    'WB_BIODIVERSITY': 'Biodiversity',
    'WB_POLLUTION': 'Pollution',
    'WB_RENEWABLE_ENERGY': 'Renewable Energy',
    'WB_COAL': 'Coal',

    // EPU — economic policy uncertainty
    'EPU_POLICY': 'Policy Uncertainty',
    'EPU_POLICY_POLICY': 'Policy Uncertainty',
    'EPU_ECONOMY_HISTORIC': 'Economic History',
    'EPU_POLICY_CATS_TAXES': 'Tax Policy',
    'EPU_POLICY_CATS_MIGRATION_FEAR_MIGRATION': 'Migration',
    'EPU_POLICY_CATS_NATIONAL_SECURITY': 'National Security',
    'EPUPOLICYPOLICY': 'Policy Uncertainty',
    'EPUECONOMYHISTORIC': 'Economic History',

    // Crisis
    'CRISISLEX_CRISISLEXREC': 'Crisis Event',
    'CRISISLEX_C01_RESOURCE': 'Resource Crisis',
    'CRISISLEX_C02_DISASTER': 'Natural Disaster',
    'CRISISLEX_C03_DISEASE': 'Disease Outbreak',
    'CRISISLEX_C03_WELLBEING_HEALTH': 'Public Health',
    'CRISISLEX_T11_UPDATESSYMPATHY': 'Crisis Response',
    'CRISISLEX_C07_SAFETY': 'Public Safety',

    // Environment
    'UNGP_FORESTS_RIVERS_OCEANS': 'Environment',
    'ENV_FOREST': 'Forestry',
    'ENV_OCEAN': 'Oceans',
    'ENV_CLIMATE': 'Climate',

    // Ethnicity & culture
    'TAX_ETHNICITY': 'Ethnicity',
    'TAX_ETHNICITY_AMERICAN': 'American Culture',
    'TAX_ETHNICITY_FRENCH': 'French Culture',
    'TAX_ETHNICITY_CHINESE': 'Chinese Culture',
    'TAX_ETHNICITY_INDIAN': 'Indian Culture',
    'TAX_ETHNICITY_IRANIAN': 'Iranian Culture',
    'TAX_WORLDLANGUAGES': 'Languages',
    'TAX_ECON_PRICE': 'Prices & Markets',
    'TAX_FNCACT_PRESIDENT': 'Presidential Actions',
    'TAX_FNCACT_GOVERNMENT': 'Government',
    'TAX_FNCACT_COMMANDER': 'Military Command',
    'TAX_FNCACT_NEGOTIATOR': 'Negotiations',
    'TAX_FNCACT_DIRECTOR': 'Leadership',
    'TAX_FNCACT_MILITARY_TITLE_OFFICER': 'Military Officers',

    // US politics
    'USPEC_POLITICS_GENERAL1': 'US Politics',
    'USPEC_POLICY1': 'US Policy',
    'USPEC_POLICY2': 'US Domestic Policy',
    'USPEC_POLICY_ECONOMIC': 'US Economic Policy',

    // General
    'GENERAL_GOVERNMENT': 'Government',
    'GENERAL_HEALTH': 'Health',
    'GENERAL_ECONOMY': 'Economy',
    'GENERAL_MILITARY': 'Military',
    'LEADER': 'Leadership',
    'MEDICAL': 'Medical',
    'EDUCATION': 'Education',
    'MANMADE_DISASTER_IMPLIED': 'Industrial Disaster',
    'UNGP_ECONOMIC_ESC_RIGHTS': 'Economic Rights',
    'WORLDMAMMALS_LION': 'Wildlife',

    // Media
    'MEDIA_MSM': 'News Coverage',
    'MEDIAMSM': 'News Coverage',
    'MEDIA_SOCIAL': 'Social Media',

    // Society
    'SOC_POINTSOFINTEREST': 'Notable Events',
    'SOC_GENERALCRIME': 'Crime',
    'SOC_CRIME': 'Crime',
    'SOC_PROTEST': 'Protests',
    'SOC_UNREST': 'Civil Unrest',

    // Transport
    'TRANSPORT': 'Transportation',
    'PUBLICTRANSPORT': 'Public Transport',
    'TRANSPORT_AIR': 'Aviation',
    'TRANSPORT_RAIL': 'Railways',

    // Economy
    'ECON_TRADE': 'International Trade',
    'ECON_INFLATION': 'Inflation',
    'ECON_UNEMPLOYMENT': 'Unemployment',
    'ECON_OILPRICE': 'Oil Prices',
    'ECON_GASOLINEPRICE': 'Fuel Prices',
    'ECON_HEATINGOIL': 'Energy Prices',

    // Governance
    'GOV_ELECTION': 'Elections',
    'GOV_LEGISLATION': 'Legislation',

    // Tech
    'TECH_AI': 'Artificial Intelligence',
    'TECH_CYBER': 'Cybersecurity',

    // Energy
    'ENERGY_OIL': 'Oil & Gas',
    'ENERGY_RENEWABLE': 'Renewable Energy',

    // Spy / intelligence
    'SPY': 'Intelligence & Espionage',
}

export function getThemeLabel(code: string): string {
    if (!code) return 'Unknown'

    const upper = code.toUpperCase()

    // Check explicit mapping first
    if (themeLabels[upper]) return themeLabels[upper]
    if (themeLabels[code]) return themeLabels[code]

    if (upper.startsWith('WB_')) {
        return `${formatThemeWords(upper.replace(/^WB_(?:\d+_)?/, ''))} (World Bank)`
    }

    if (upper.startsWith('USPEC_POLICY_ECONOMIC')) return 'US Economic Policy'
    if (upper.startsWith('USPEC_POLICY')) return 'US Policy'
    if (upper.startsWith('USPEC_POLITICS')) return 'US Politics'
    if (upper.startsWith('USPEC_')) return `US ${formatThemeWords(upper.replace(/^USPEC_/, ''))}`

    if (upper.startsWith('EPU_')) return `Policy: ${formatThemeWords(upper.replace(/^EPU_/, ''))}`
    if (upper.startsWith('CRISISLEX_')) {
        return `Crisis: ${formatThemeWords(upper.replace(/^CRISISLEX_(?:C\d+_)?/, ''))}`
    }
    if (upper.startsWith('UNGP_')) return `UN: ${formatThemeWords(upper.replace(/^UNGP_/, ''))}`

    const prefixRules: Array<[RegExp, string]> = [
        [/^TAX_FNCACT_/, ''],
        [/^TAX_ETHNICITY_/, 'Ethnicity: '],
        [/^TAX_WORLDLANGUAGES_/, 'Language: '],
        [/^WORLDLANGUAGES_/, 'Language: '],
        [/^TAX_/, ''],
        [/^SOC_/, ''],
        [/^GENERAL_/, ''],
        [/^MEDIA_?/, ''],
        [/^ENV_/, ''],
        [/^ECON_/, 'Economic: '],
        [/^GOV_/, 'Government: '],
        [/^TECH_/, 'Technology: '],
        [/^ENERGY_/, 'Energy: '],
    ]

    for (const [pattern, labelPrefix] of prefixRules) {
        if (pattern.test(upper)) return `${labelPrefix}${formatThemeWords(upper.replace(pattern, ''))}`
    }

    return formatThemeWords(upper)
}

function formatThemeWords(value: string): string {
    return value
        .replace(/_AND_/g, ' & ')
        .replace(/_/g, ' ')
        .replace(/\b([A-Z]+)\d+\b/g, '$1')
        .replace(/\s+/g, ' ')
        .toLowerCase()
        .replace(/\b\w/g, c => c.toUpperCase())
        .replace(/\bAnti Corruption\b/g, 'Anti-Corruption')
        .replace(/\bNondefense\b/g, 'Non-Defense')
        .replace(/\bNon Defense\b/g, 'Non-Defense')
        .replace(/\bUn\b/g, 'UN')
        .replace(/\bUs\b/g, 'US')
        .trim()
}

// Theme icon function - returns Lucide icon component
export function getThemeIcon(theme: string): React.ReactNode {
    const upper = theme.toUpperCase()
    const size = 14;

    if (upper.includes('ECONOMY') || upper.includes('ECON') || upper.includes('TRADE') || upper.includes('MARKET')) return <Briefcase size={size} />
    if (upper.includes('GOVERNMENT') || upper.includes('GOV') || upper.includes('POLICY')) return <Landmark size={size} />
    if (upper.includes('MILITARY') || upper.includes('WAR') || upper.includes('SECURITY')) return <Swords size={size} />
    if (upper.includes('HEALTH') || upper.includes('DISEASE') || upper.includes('MEDICAL')) return <Stethoscope size={size} />
    if (upper.includes('ENVIRONMENT') || upper.includes('CLIMATE') || upper.includes('NATURE')) return <Leaf size={size} />
    if (upper.includes('TECH') || upper.includes('CYBER') || upper.includes('DIGITAL')) return <Laptop size={size} />
    if (upper.includes('CRIME') || upper.includes('ARREST') || upper.includes('LAW')) return <Siren size={size} />
    if (upper.includes('PROTEST') || upper.includes('UNREST') || upper.includes('SOCIAL')) return <HandMetal size={size} />
    if (upper.includes('ELECTION') || upper.includes('VOTE')) return <Vote size={size} />
    if (upper.includes('ENERGY') || upper.includes('OIL') || upper.includes('POWER')) return <Zap size={size} />
    if (upper.includes('FOREST') || upper.includes('OCEAN') || upper.includes('WATER')) return <Waves size={size} />
    if (upper.includes('ETHNICITY') || upper.includes('LANGUAGE') || upper.includes('CULTURE')) return <Languages size={size} />
    if (upper.includes('JOB') || upper.includes('EMPLOY') || upper.includes('LABOR')) return <Users size={size} />
    if (upper.includes('EDUCATION') || upper.includes('SCHOOL')) return <FileText size={size} />
    if (upper.includes('LEADER') || upper.includes('PRESIDENT')) return <User size={size} />

    return <Newspaper size={size} />
}
