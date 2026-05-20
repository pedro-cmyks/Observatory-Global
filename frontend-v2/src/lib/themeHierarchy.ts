import { getThemeLabel } from './themeLabels'

export interface ThemeCluster {
  id: string
  label: string
  codes: string[]
}

export interface GroupedThemeTopic<T> {
  cluster: ThemeCluster
  items: T[]
}

export const OTHER_THEME_CLUSTER: ThemeCluster = {
  id: 'other',
  label: 'Other Signals',
  codes: [],
}

export const THEME_CLUSTERS: Record<string, ThemeCluster> = {
  conflict_security: {
    id: 'conflict_security',
    label: 'Conflict and Security',
    codes: [
      'ARMEDCONFLICT',
      'MILITARY',
      'TERROR',
      'TAX_TERROR_GROUP',
      'TAX_FNCACT_INSURGENT',
      'TAX_FNCACT_TERRORIST',
      'TAX_FNCACT_MILITARY',
      'TAX_FNCACT_POLICE',
      'TAX_FNCACT_REBEL',
      'TAX_FNCACT_MILITANT',
      'WEAPONS',
      'WEA_MASS_DESTRUCTION',
      'CRISISLEX_C07_SAFETY',
      'SECURITY_SERVICES',
    ],
  },
  politics_governance: {
    id: 'politics_governance',
    label: 'Politics and Governance',
    codes: [
      'USPEC_POLITICS_GENERAL1',
      'USPEC_POLICY1',
      'USPEC_POLICY2',
      'WB_696_PUBLIC_SECTOR_MANAGEMENT',
      'WB_698_PUBLIC_ADMINISTRATION',
      'WB_678_DIGITAL_GOVERNMENT',
      'WB_133_INFORMATION_AND_COMMUNICATION_TECHNOLOGIES',
      'ELECTION',
      'DEMOCRACY',
      'CORRUPTION',
      'TAX_FNCACT_GOVERNMENT',
      'TAX_FNCACT_PRESIDENT',
    ],
  },
  diplomacy_law: {
    id: 'diplomacy_law',
    label: 'Diplomacy and Law',
    codes: [
      'DIPLOMACY',
      'GOV_FOREIGN_AID',
      'GOV_CEASEFIRE',
      'SANCTIONS',
      'NEGOTIATIONS',
      'TAX_FNCACT_DIPLOMAT',
      'TAX_FNCACT_AMBASSADOR',
      'TAX_FNCACT_JUDGE',
      'TAX_FNCACT_LAWYER',
      'JUSTICE',
      'LEGAL',
    ],
  },
  economy_trade: {
    id: 'economy_trade',
    label: 'Economy and Trade',
    codes: [
      'ECON',
      'ECON_COST_OF_LIVING',
      'ECON_COST_BENEFITS',
      'ECON_TAXATION',
      'ECON_STOCKMARKET',
      'WB_507_ENERGY_AND_EXTRACTIVES',
      'WB_1103_INFRASTRUCTURE',
      'WB_1332_TRADE',
      'WB_2165_FOOD_SECURITY',
      'TAX_FNCACT_BUSINESSMAN',
      'TAX_FNCACT_INVESTOR',
    ],
  },
  humanitarian_health: {
    id: 'humanitarian_health',
    label: 'Humanitarian and Health',
    codes: [
      'CRISISLEX_CRISISLEXREC',
      'CRISISLEX_C03_DISEASE',
      'CRISISLEX_C04_SECURITY',
      'CRISISLEX_T01_CAUTION_ADVICE',
      'HEALTH',
      'MEDICAL',
      'PANDEMIC',
      'REFUGEES',
      'DISPLACED',
      'HUMAN_RIGHTS',
      'TAX_FNCACT_REFUGEE',
      'TAX_FNCACT_DOCTOR',
    ],
  },
  environment_climate: {
    id: 'environment_climate',
    label: 'Environment and Climate',
    codes: [
      'ENV',
      'ENV_CLIMATECHANGE',
      'ENV_WATER',
      'ENV_NATURALDISASTER',
      'NATURAL_DISASTER',
      'WB_567_ENVIRONMENT',
      'WB_621_CLIMATE_CHANGE',
      'WB_1785_WATER',
      'WB_430_AGRICULTURE',
    ],
  },
  technology_media: {
    id: 'technology_media',
    label: 'Technology and Media',
    codes: [
      'CYBER_ATTACK',
      'TAX_FNCACT_HACKER',
      'TAX_FNCACT_PROGRAMMER',
      'MEDIA_MSM',
      'MEDIA_SOCIAL',
      'TAX_FNCACT_JOURNALIST',
      'TAX_FNCACT_BROADCASTER',
      'INTERNET',
      'SURVEILLANCE',
      'ARTIFICIAL_INTELLIGENCE',
    ],
  },
}

const CLUSTER_BY_CODE = new Map<string, ThemeCluster>(
  Object.values(THEME_CLUSTERS).flatMap(cluster => cluster.codes.map(code => [code, cluster] as const)),
)

export function getThemeCluster(themeCode: string): ThemeCluster {
  return CLUSTER_BY_CODE.get(themeCode) ?? OTHER_THEME_CLUSTER
}

export function groupThemeTopics<T extends { topic: string; count?: number }>(topics: T[]): GroupedThemeTopic<T>[] {
  const groups = new Map<string, GroupedThemeTopic<T>>()

  for (const topic of topics) {
    const cluster = getThemeCluster(topic.topic)
    const existing = groups.get(cluster.id)
    if (existing) {
      existing.items.push(topic)
    } else {
      groups.set(cluster.id, { cluster, items: [topic] })
    }
  }

  return [...groups.values()]
    .map(group => ({
      ...group,
      items: [...group.items].sort((a, b) => (b.count ?? 0) - (a.count ?? 0) || getThemeLabel(a.topic).localeCompare(getThemeLabel(b.topic))),
    }))
    .sort((a, b) => {
      if (a.cluster.id === OTHER_THEME_CLUSTER.id) return 1
      if (b.cluster.id === OTHER_THEME_CLUSTER.id) return -1
      const aTotal = a.items.reduce((sum, item) => sum + (item.count ?? 0), 0)
      const bTotal = b.items.reduce((sum, item) => sum + (item.count ?? 0), 0)
      return bTotal - aTotal || a.cluster.label.localeCompare(b.cluster.label)
    })
}
