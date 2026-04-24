import React from 'react';
import {
    Briefcase, Landmark, Swords, Stethoscope, Laptop, Siren,
    HandMetal, Vote, Zap, Waves, Languages, FileText, User, Newspaper,
    Leaf, Users
} from 'lucide-react';

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
    'WB_696_PUBLIC_SECTOR_MANAGEMENT': 'Public Sector',
    'WB_2432_FRAGILITY_CONFLICT_AND_VIOLENCE': 'Conflict & Violence',
    'WB_678_DIGITAL_GOVERNMENT': 'Digital Government',
    'WB_133_INFORMATION_AND_COMMUNICATION_TECHNOLOGIES': 'Technology & Communications',

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
    'CRISISLEX_T11_UPDATESSYMPATHY': 'Crisis Updates',
    'CRISISLEX_C07_SAFETY': 'Public Safety',

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
    'TAX_ECON_PRICE': 'Pricing & Markets',
    'TAX_FNCACT_PRESIDENT': 'Presidential Actions',
    'TAX_FNCACT_GOVERNMENT': 'Government Actions',

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
    'LEADER': 'Leadership',
    'MEDICAL': 'Medical',
    'EDUCATION': 'Education',
    'MANMADE_DISASTER_IMPLIED': 'Man-Made Disaster',

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

export function getThemeLabel(code: string): string {
    if (!code) return 'Unknown'

    const upper = code.toUpperCase()

    // Check explicit mapping first
    if (themeLabels[upper]) return themeLabels[upper]
    if (themeLabels[code]) return themeLabels[code]

    // Clean up common GDELT prefixes
    return code
        .replace(/^WB_\d+_/, 'World Bank: ')
        .replace(/^WB_/, 'World Bank: ')
        .replace(/^UNGP_/, 'UN: ')
        .replace(/^TAX_FNCACT_/, '')
        .replace(/^TAX_ETHNICITY_/, 'Ethnicity: ')
        .replace(/^TAX_WORLDLANGUAGES_/, 'Language: ')
        .replace(/^WORLDLANGUAGES_/, 'Language: ')
        .replace(/^TAX_/, '')
        .replace(/^EPU_/, 'Policy: ')
        .replace(/^CRISISLEX_/, 'Crisis: ')
        .replace(/^USPEC_/, '')
        .replace(/^SOC_/, '')
        .replace(/^GENERAL_/, '')
        .replace(/^MEDIA_?/, '')
        .replace(/^ENV_/, '')
        .replace(/^ECON_/, 'Economic: ')
        .replace(/^GOV_/, 'Government: ')
        .replace(/^TECH_/, 'Technology: ')
        .replace(/^ENERGY_/, 'Energy: ')
        .replace(/_AND_/g, ' & ')
        .replace(/_/g, ' ')
        .replace(/\s+/g, ' ')
        .toLowerCase()
        .replace(/\b\w/g, c => c.toUpperCase())
        .replace('Un: ', 'UN: ')
        .replace('Us: ', 'US: ')
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
