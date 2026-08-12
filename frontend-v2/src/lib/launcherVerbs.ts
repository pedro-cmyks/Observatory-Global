export type LauncherKind =
  | 'coverage-gap' | 'gaps-sentence' | 'cross-read-tension' | 'contested-figure'
  | 'semantic-neighbor' | 'connected-thread' | 'lead' | 'isolated-pin'
export type Verb = 'open' | 'fresh-query' | 'corroborate' | 'keep' | 'drop'
export interface LauncherVerb { verb: Verb; label: string; tip: string }

const V = (verb: Verb, label: string, tip: string): LauncherVerb => ({ verb, label, tip })

export function resolveLauncherVerbs(kind: LauncherKind): LauncherVerb[] {
  switch (kind) {
    case 'coverage-gap':
    case 'gaps-sentence':
      return [V('fresh-query', 'Investigate the gap', 'Start a fresh query for this missing coverage')]
    case 'cross-read-tension':
      return [V('corroborate', 'Corroborate', 'Re-run corroboration on this discrepancy')]
    case 'contested-figure':
      return [V('corroborate', 'Corroborate', 'Re-run corroboration on this contested figure')]
    case 'semantic-neighbor':
      return [V('open', 'Open in Atlas', 'Open the nearest-meaning signal in-app'), V('keep', 'Keep', 'Pin it to the investigation')]
    case 'connected-thread':
      return [V('open', 'Open story', 'Open the connected story in-app')]
    case 'lead':
      return [V('open', 'Open story', 'Open the lead\'s story'), V('keep', 'Keep', 'Pin the lead to the investigation')]
    case 'isolated-pin':
      return [V('keep', 'Keep anyway', 'Mark reviewed — keep the pin'), V('drop', 'Drop receipt', 'Remove this unrelated receipt')]
    default:
      return []
  }
}
