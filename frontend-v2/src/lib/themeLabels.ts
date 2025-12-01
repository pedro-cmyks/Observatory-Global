// GDELT Theme Code to Human-Readable Label mapping
export const themeLabels: Record<string, string> = {
    // Crisis & Emergency
    'CRISISLEX_CRISISLEXREC': 'Crisis Event',
    'CRISISLEX_C01_CASUALTIES': 'Casualties',
    'CRISISLEX_C02_INFRASTRUCTURE': 'Infrastructure Damage',
    'CRISISLEX_C03_SUPPLIES': 'Supply Issues',
    'CRISISLEX_C04_SERVICES': 'Service Disruption',
    'CRISISLEX_T01_CAUTION': 'Caution Advisory',
    'CRISISLEX_T02_EMERGINGTHREATS': 'Emerging Threats',
    'CRISISLEX_T03_DEAD': 'Casualties',
    'CRISISLEX_T04_DISPLACED': 'Displaced Persons',
    'CRISISLEX_T05_INJURED': 'Injured',
    'CRISISLEX_T06_MISSING': 'Missing',
    'CRISISLEX_T07_FOUND': 'Found',
    'CRISISLEX_T08_DISEASEOUTBREAK': 'Disease Outbreak',
    'CRISISLEX_T09_QUARANTINE': 'Quarantine',
    'CRISISLEX_T10_DISASTERRESCUE': 'Disaster Rescue',
    'CRISISLEX_T11_UPDATESSYMPATHY': 'Updates & Sympathy',

    // Environment
    'UNGP_FORESTS_RIVERS_OCEANS': 'Environment',
    'ENV_CLIMATECHANGE': 'Climate Change',
    'ENV_DEFORESTATION': 'Deforestation',
    'ENV_WATERWAYS': 'Waterways',
    'ENV_NATURALGAS': 'Natural Gas',

    // Politics
    'USPEC_POLITICS_GENERAL1': 'US Politics',
    'GOV_LEADER': 'Government Leader',
    'GOV_ELECTION': 'Election',
    'GOV_MILITARY': 'Military',
    'POL_PROTEST': 'Protest',
    'GENERAL_GOVERNMENT': 'Government',

    // Economy
    'ECON_BANKRUPTCY': 'Bankruptcy',
    'ECON_STOCKMARKET': 'Stock Market',
    'ECON_INFLATION': 'Inflation',
    'ECON_UNEMPLOYMENT': 'Unemployment',

    // Social
    'SOC_GENERALCRIME': 'Crime',
    'SOC_POINTSOFINTEREST_JAIL': 'Incarceration',
    'TAX_ETHNICITY': 'Ethnicity',
    'TAX_ETHNICITY_AMERICAN': 'American Ethnicity',

    // Health
    'HEALTH_PANDEMIC': 'Pandemic',
    'HEALTH_DISEASE': 'Disease',
    'HEALTH_VACCINATION': 'Vaccination',
    'WB_1305_HEALTH_SERVICES_DELIVERY': 'Health Services',
    'GENERAL_HEALTH': 'Health',
    'MEDICAL': 'Medical',

    // General Actions
    'GEN_HOLIDAY': 'Holiday',
    'ARREST': 'Arrest',
    'KILL': 'Violence',
    'SEIZE': 'Seizure',
    'WOUNDED': 'Injured',

    // Security
    'SECURITY_SERVICES': 'Security Services',
    'TAX_FNCACT': 'Functional Actor',
    'TAX_FNCACT_CHILDREN': 'Children',

    // Transport
    'WB_135_TRANSPORT': 'Transportation',
    'MARITIME': 'Maritime',

    // Ideology
    'IDEOLOGY': 'Ideology',
};

export function getThemeLabel(code: string): string {
    // Direct match
    if (themeLabels[code]) {
        return themeLabels[code];
    }

    // Try uppercase
    const upper = code.toUpperCase();
    if (themeLabels[upper]) {
        return themeLabels[upper];
    }

    // Try partial match
    for (const [key, label] of Object.entries(themeLabels)) {
        if (upper.includes(key) || key.includes(upper)) {
            return label;
        }
    }

    // Clean up unknown codes
    return code
        .replace(/^(CRISISLEX_|UNGP_|USPEC_|TAX_|SOC_|ENV_|GOV_|ECON_|GEN_|WB_)/i, '')
        .replace(/_/g, ' ')
        .replace(/([A-Z])/g, ' $1')
        .trim()
        .split(' ')
        .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
        .join(' ');
}
