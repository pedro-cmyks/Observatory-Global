# Migration 042 proposal — LLM-distilled multilingual lexicon expansion

Schema: `atlas-migration-042-proposal-v1`
Min vocab confidence threshold: 0.85

## Summary

| Metric | Value |
|---|---:|
| Topics covered | 30 |
| Topics with proposed additions | 30 |
| Total new terms proposed | 423 |
| Total negative terms to monitor | 150 |
| Existing terms flagged for removal review | 0 |

## How to use this proposal

1. Read the SQL draft (`migration-042-draft.sql`).
2. For each topic block, drop any term that does not feel safe.
3. Apply via Supabase MCP `apply_migration`.
4. Delete v2 assignments for the touched topics.
5. Re-run `backend/scripts/backfill_lexicon_topics.py` over a recent 24h window.
6. Re-benchmark Atlas v2 with the bootstrap CI tool against existing gold.
7. Compare lift vs prior Wilson CI baseline `[46.50%, 70.46%]`.

## Per-topic detail

### `agriculture-crop-risk`

- LLM-Atlas agreement on reviewed sample: 33.3%
- existing lexicon size: 5
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `crop failure risk` [en] conf=0.93 — Directly signals agricultural production loss due to environmental or disease factors.
  - `harvest threatened by drought` [en] conf=0.95 — Explicitly links crop output to climate-driven agricultural risk.
  - `pest damage to crops` [en] conf=0.91 — Indicates biological threat to agricultural yield.
  - `pérdida de cosecha` [es] conf=0.93 — Spanish phrase for crop loss, a core agriculture risk signal.
  - `sequía amenaza cultivos` [es] conf=0.94 — Drought threatening crops is a primary agriculture risk headline pattern.
  - `plaga agrícola` [es] conf=0.90 — Agricultural plague/pest directly indicates crop risk topic.
  - `perda de safra` [pt] conf=0.93 — Portuguese for harvest/crop loss, central to agriculture risk reporting.
  - `seca prejudica lavoura` [pt] conf=0.94 — Drought harming crops is a direct agriculture risk indicator in Brazilian news.
  - `geada danifica plantação` [pt] conf=0.91 — Frost damaging plantation is a specific crop risk event phrase.
  - `raccolto a rischio` [it] conf=0.93 — Italian for 'harvest at risk', directly signals crop risk topic.
  - `siccità danneggia colture` [it] conf=0.94 — Drought damaging crops is a primary agriculture risk phrase in Italian.
  - `récolte menacée par la sécheresse` [fr] conf=0.95 — Harvest threatened by drought is a direct crop risk signal in French headlines.
  - `risque pour les cultures` [fr] conf=0.90 — Risk to crops is a clear agriculture risk topic marker in French.
  - `ernteverlust durch dürre` [de] conf=0.94 — Harvest loss due to drought is a direct crop risk phrase in German.
  - `schädlingsbefall landwirtschaft` [de] conf=0.91 — Pest infestation in agriculture directly signals crop risk in German news.
- negative monitors (5):
  - `food prices` [en] — Usually signals economics or inflation stories rather than on-farm crop risk events.
  - `farm subsidies` [en] — Primarily indicates agricultural policy or budget news, not crop risk itself.
  - `drought relief fund` [en] — Focuses on government financial aid response, not the crop risk event itself.
  - `agricultural exports` [en] — Typically signals trade and economics stories, not crop vulnerability or loss.
  - `campo de cultivo` [es] — Generic term for crop field used in many non-risk contexts including tourism and education.

### `armed-conflict-escalation`

- LLM-Atlas agreement on reviewed sample: 62.5%
- existing lexicon size: 48
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `military offensive launched` [en] conf=0.93 — Directly signals the start of armed escalation in a conflict zone.
  - `airstrikes intensify` [en] conf=0.91 — Indicates escalating aerial bombardment in an active conflict.
  - `ground invasion begins` [en] conf=0.95 — Unambiguously marks a major escalation of armed conflict.
  - `ofensiva militar` [es] conf=0.92 — Spanish phrase directly indicating a military offensive operation.
  - `escalada de violencia` [es] conf=0.90 — Spanish term for escalation of violence in conflict contexts.
  - `bombardeos intensos` [es] conf=0.89 — Refers to intense bombing campaigns signaling conflict escalation.
  - `ofensiva militar intensifica` [pt] conf=0.91 — Portuguese phrase indicating intensifying military offensive.
  - `ataques aéreos aumentam` [pt] conf=0.90 — Portuguese for increasing airstrikes, a clear escalation indicator.
  - `escalade militaire` [fr] conf=0.92 — French term directly describing military escalation.
  - `offensive terrestre` [fr] conf=0.91 — French for ground offensive, indicating armed conflict escalation.
  - `escalation militare` [it] conf=0.92 — Italian term directly describing military escalation in a conflict.
  - `bombardamenti intensificati` [it] conf=0.89 — Italian for intensified bombardments, a clear conflict escalation signal.
  - `militäroffensive gestartet` [de] conf=0.93 — German for military offensive launched, directly indicating escalation.
  - `luftangriffe eskalieren` [de] conf=0.91 — German for escalating airstrikes, a strong armed conflict indicator.
  - `heavy shelling reported` [en] conf=0.90 — Indicates active artillery bombardment signaling conflict escalation.
- negative monitors (5):
  - `war on drugs` [en] — Refers to law enforcement policy, not armed interstate or insurgent conflict escalation.
  - `trade war escalates` [en] — Economic/tariff disputes use 'war' metaphorically, not literal armed conflict.
  - `culture war` [en] — Political/social debate framing, not armed conflict.
  - `price war` [en] — Business competition terminology, unrelated to armed conflict escalation.
  - `guerra comercial` [es] — Spanish for trade war; uses conflict language but refers to economic disputes only.

### `corruption-investigation`

- LLM-Atlas agreement on reviewed sample: 91.7%
- existing lexicon size: 5
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `corruption probe` [en] conf=0.95 — Directly signals an active investigation into corrupt conduct.
  - `bribery investigation` [en] conf=0.93 — Specific phrase indicating a formal inquiry into bribery.
  - `anticorruption inquiry` [en] conf=0.91 — Explicitly frames the story as an anti-corruption investigation.
  - `investigación por corrupción` [es] conf=0.95 — Spanish phrase directly meaning 'corruption investigation'.
  - `caso de soborno` [es] conf=0.88 — Spanish for 'bribery case', strongly tied to corruption investigations.
  - `investigado por corrupción` [es] conf=0.92 — Indicates a person is under investigation for corruption.
  - `investigação por corrupção` [pt] conf=0.95 — Portuguese phrase directly meaning 'corruption investigation'.
  - `operação anticorrupção` [pt] conf=0.93 — Portuguese for 'anti-corruption operation', signals an active probe.
  - `indagato per corruzione` [it] conf=0.94 — Italian for 'investigated for corruption', core topic signal.
  - `inchiesta per corruzione` [it] conf=0.93 — Italian for 'corruption inquiry', directly on-topic.
  - `enquête pour corruption` [fr] conf=0.94 — French for 'corruption investigation', precise topic match.
  - `mis en examen pour corruption` [fr] conf=0.92 — French legal phrase meaning formally placed under corruption investigation.
  - `korruptionsermittlung` [de] conf=0.95 — German compound noun meaning 'corruption investigation', highly specific.
  - `bestechungsvorwürfe` [de] conf=0.90 — German for 'bribery allegations', strongly associated with corruption probes.
  - `ermittlungen wegen korruption` [de] conf=0.93 — German phrase meaning 'investigations due to corruption', direct topic signal.
- negative monitors (5):
  - `corruption index` [en] — Refers to rankings like Transparency International's CPI, not an active investigation.
  - `anti-corruption law` [en] — Signals legislative or policy stories, not an ongoing investigation.
  - `corruption perception` [en] — Associated with survey or report stories about perceived corruption levels, not probes.
  - `lucha contra la corrupción` [es] — Broad political rhetoric about fighting corruption, not a specific investigation.
  - `corruption scandal` [en] — Often refers to political fallout or opinion pieces rather than an active legal investigation.

### `cyberattack-infrastructure`

- LLM-Atlas agreement on reviewed sample: 28.6%
- existing lexicon size: 5
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `cyberattack on power grid` [en] conf=0.97 — Directly describes a cyberattack targeting electrical infrastructure.
  - `ransomware hits water utility` [en] conf=0.96 — Ransomware attack on a water utility is a clear infrastructure cyberattack.
  - `critical infrastructure hacked` [en] conf=0.95 — Hacking of critical infrastructure is the core topic.
  - `ataque cibernético infraestructura` [es] conf=0.95 — Spanish phrase directly linking cyberattack to infrastructure.
  - `hackers atacan red eléctrica` [es] conf=0.94 — Describes hackers attacking the electrical grid in Spanish.
  - `ciberataque oleoducto` [es] conf=0.93 — Cyberattack on a pipeline, a key infrastructure target.
  - `ataque hacker infraestrutura` [pt] conf=0.95 — Portuguese phrase for hacker attack on infrastructure.
  - `ransomware sistema elétrico` [pt] conf=0.94 — Ransomware targeting the electrical system in Portuguese.
  - `ciberataque rede de água` [pt] conf=0.93 — Cyberattack on water network, a critical infrastructure sector.
  - `attacco informatico infrastrutture` [it] conf=0.95 — Italian phrase for cyberattack on infrastructure.
  - `hacker colpisce rete elettrica` [it] conf=0.93 — Hacker hits electrical grid in Italian context.
  - `cyberattaque réseau électrique` [fr] conf=0.96 — French term for cyberattack on the electrical network.
  - `attaque informatique infrastructure critique` [fr] conf=0.95 — French phrase targeting critical infrastructure cyberattack.
  - `cyberangriff auf stromnetz` [de] conf=0.96 — German for cyberattack on the power grid.
  - `hackerangriff kritische infrastruktur` [de] conf=0.95 — German phrase for hacker attack on critical infrastructure.
- negative monitors (5):
  - `infrastructure bill` [en] — Refers to legislative spending on physical infrastructure, not cyberattacks.
  - `network outage` [en] — Outages are often caused by technical failures, not cyberattacks specifically.
  - `cyber security budget` [en] — Covers funding and policy discussions, not an active attack event.
  - `infrastructure investment` [en] — Economic or political topic about spending, unrelated to cyberattacks.
  - `power grid upgrade` [en] — Refers to modernization projects, not attacks on the grid.

### `energy-grid-instability`

- existing lexicon size: 5
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `power grid failure` [en] conf=0.95 — Directly describes electrical grid breakdown events.
  - `blackout risk` [en] conf=0.88 — Signals threat of widespread power loss due to grid stress.
  - `grid instability` [en] conf=0.97 — Exact phrase for unstable electricity transmission networks.
  - `apagón eléctrico` [es] conf=0.92 — Spanish term for electrical blackout, core grid instability event.
  - `colapso de la red eléctrica` [es] conf=0.95 — Describes collapse of the electrical grid in Spanish headlines.
  - `inestabilidad energética` [es] conf=0.87 — Directly translates energy instability in Spanish context.
  - `falha na rede elétrica` [pt] conf=0.94 — Portuguese phrase for electrical grid failure.
  - `apagão elétrico` [pt] conf=0.91 — Portuguese term for large-scale power blackout.
  - `instabilidade da rede` [pt] conf=0.88 — Refers to grid network instability in Portuguese.
  - `blackout elettrico` [it] conf=0.93 — Italian term for electrical blackout indicating grid failure.
  - `instabilità della rete elettrica` [it] conf=0.95 — Precise Italian phrase for electrical grid instability.
  - `panne du réseau électrique` [fr] conf=0.94 — French phrase for electrical grid breakdown.
  - `instabilité du réseau énergétique` [fr] conf=0.92 — Directly describes energy network instability in French.
  - `stromausfall netzinstabilität` [de] conf=0.93 — German compound covering power outage and grid instability.
  - `stromnetz zusammenbruch` [de] conf=0.91 — German phrase for electricity network collapse.
- negative monitors (5):
  - `energy drink` [en] — Contains 'energy' but refers to beverage industry, not power grids.
  - `political instability` [en] — Contains 'instability' but refers to governance crises, not energy infrastructure.
  - `power struggle` [en] — Often means political or corporate conflict, not electrical grid issues.
  - `renewable energy investment` [en] — Covers clean energy finance, not grid failure or instability events.
  - `gas prices` [en] — Relates to fuel cost reporting, not electricity grid stability problems.

### `flood-landslide-disaster`

- existing lexicon size: 5
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `flash flood kills` [en] conf=0.95 — Directly signals a deadly flood disaster event in headlines.
  - `landslide buries` [en] conf=0.95 — Specific phrase indicating a landslide disaster causing casualties or destruction.
  - `flood evacuations` [en] conf=0.85 — Indicates active flood emergency requiring population displacement.
  - `inundaciones dejan muertos` [es] conf=0.95 — Spanish phrase meaning floods leave dead, directly signals flood disaster.
  - `deslizamiento de tierra` [es] conf=0.92 — Standard Spanish term for landslide disaster events.
  - `enchentes deixam vítimas` [pt] conf=0.95 — Portuguese phrase meaning floods leave victims, directly signals disaster.
  - `deslizamento de terra mata` [pt] conf=0.95 — Portuguese for landslide kills, clearly indicates a deadly landslide event.
  - `alluvione travolge` [it] conf=0.93 — Italian for flood sweeps away, strongly signals a flood disaster headline.
  - `frana uccide` [it] conf=0.94 — Italian for landslide kills, directly indicates a deadly landslide event.
  - `inondations meurtrières` [fr] conf=0.94 — French for deadly floods, a strong indicator of flood disaster coverage.
  - `glissement de terrain` [fr] conf=0.92 — Standard French term for landslide, commonly used in disaster headlines.
  - `hochwasser reißt häuser` [de] conf=0.94 — German for floodwater tears away houses, directly signals flood disaster.
  - `erdrutsch begräbt` [de] conf=0.95 — German for landslide buries, strongly indicates a landslide disaster event.
  - `überschwemmungen fordern tote` [de] conf=0.95 — German for floods claim deaths, directly signals a deadly flood disaster.
  - `mudslide sweeps away` [en] conf=0.94 — Specific phrase indicating a destructive mudslide disaster in headlines.
- negative monitors (5):
  - `flood of criticism` [en] — Metaphorical use of flood refers to political or social backlash, not a natural disaster.
  - `flood of migrants` [en] — Uses flood figuratively to describe migration flows, unrelated to natural disaster.
  - `landslide victory` [en] — Landslide in electoral context means overwhelming win, not a geological event.
  - `inondation de données` [fr] — French metaphor for data overflow in tech contexts, not a flood disaster.
  - `erdrutschsieg` [de] — German compound meaning landslide victory in elections, not a natural disaster.

### `fuel-subsidy-unrest`

- existing lexicon size: 36
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `fuel subsidy protest` [en] conf=0.95 — Directly signals unrest over fuel subsidy cuts or changes.
  - `fuel price riots` [en] conf=0.93 — Riots triggered by fuel price hikes linked to subsidy removal.
  - `petrol subsidy unrest` [en] conf=0.92 — UK/Commonwealth English variant directly matching the topic.
  - `protestas subsidio combustible` [es] conf=0.94 — Spanish for protests over fuel subsidy, highly specific to this topic.
  - `disturbios precio gasolina` [es] conf=0.91 — Spanish for unrest over gasoline prices, typically subsidy-related.
  - `protestos subsídio combustível` [pt] conf=0.94 — Portuguese for fuel subsidy protests, directly on-topic.
  - `revolta preço combustível` [pt] conf=0.91 — Portuguese for revolt over fuel prices, common in subsidy-cut coverage.
  - `proteste sussidio carburante` [it] conf=0.93 — Italian for fuel subsidy protests, specific to this topic.
  - `rivolte prezzo benzina` [it] conf=0.90 — Italian for gasoline price riots, typically subsidy-removal driven.
  - `manifestations subvention carburant` [fr] conf=0.94 — French for fuel subsidy demonstrations, directly on-topic.
  - `émeutes prix carburant` [fr] conf=0.92 — French for fuel price riots, strongly associated with subsidy unrest.
  - `kraftstoffsubvention proteste` [de] conf=0.93 — German for fuel subsidy protests, highly specific compound term.
  - `benzinpreisunruhen` [de] conf=0.90 — German compound for gasoline price unrest, directly matches topic.
  - `subvención gasolina disturbios` [es] conf=0.89 — Spanish phrase linking gasoline subsidy to civil disturbances.
  - `spritpreisproteste` [de] conf=0.88 — German colloquial compound for fuel price protests, topic-specific.
- negative monitors (5):
  - `fuel efficiency` [en] — Matches 'fuel' but refers to vehicle/energy technology, not subsidies or unrest.
  - `energy subsidy reform` [en] — Broad policy/legislative framing, usually covers electricity or general energy, not street unrest.
  - `gilets jaunes` [fr] — Yellow Vest movement is often fuel-price-related but has become a broader social movement label.
  - `gas prices surge` [en] — Covers market price movements, not necessarily subsidy removal or civil unrest.
  - `oil price crisis` [en] — Refers to global commodity markets or economic crises, not domestic subsidy-driven protests.

### `gang-control-urban-security`

- existing lexicon size: 5
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `gang control neighborhood` [en] conf=0.88 — Directly describes gangs asserting territorial dominance in urban areas.
  - `urban gang crackdown` [en] conf=0.90 — Signals law enforcement action against gangs in city contexts.
  - `street gang violence city` [en] conf=0.87 — Combines gang violence with urban setting as primary subject.
  - `control territorial pandillas` [es] conf=0.89 — Pandillas (gangs) controlling territory is a core gang-urban-security phrase in Spanish.
  - `seguridad urbana pandillas` [es] conf=0.88 — Directly links urban security to gang activity in Spanish-language headlines.
  - `maras controlan barrios` [es] conf=0.91 — Maras are Central American gangs; controlling barrios is a hallmark gang-territory story.
  - `gangues controlam favela` [pt] conf=0.92 — Gangs controlling favelas is a quintessential Brazilian urban-security headline.
  - `segurança urbana tráfico` [pt] conf=0.85 — Urban security linked to drug trafficking gangs in Portuguese-language news.
  - `operação contra gangues` [pt] conf=0.87 — Police operations against gangs in urban Brazil/Portugal are a primary topic signal.
  - `bande criminali quartiere` [it] conf=0.86 — Criminal gangs in neighborhoods is a direct Italian urban-security phrase.
  - `sicurezza urbana gang` [it] conf=0.88 — Urban security and gangs combined in Italian headlines signals this topic clearly.
  - `bandes urbaines sécurité` [fr] conf=0.87 — Urban gangs and security is a direct French-language topic indicator.
  - `quartiers contrôlés par gangs` [fr] conf=0.90 — Neighborhoods controlled by gangs is a precise French urban-security phrase.
  - `bandenkriminalität stadtgebiet` [de] conf=0.88 — Gang criminality in urban areas is a direct German topic signal.
  - `jugendbanden stadtviertel kontrolle` [de] conf=0.86 — Youth gangs controlling city districts is a specific German urban-security phrase.
- negative monitors (5):
  - `gang rape` [en] — Uses 'gang' but refers to sexual violence crimes, not territorial gang control or urban security.
  - `gang of thieves arrested` [en] — Refers to generic criminal groups rather than organized street gangs and urban territorial control.
  - `gang plank` [en] — Nautical term unrelated to criminal gangs or urban security.
  - `pandilla deportiva` [es] — 'Pandilla' can colloquially mean a sports fan group in some contexts, not criminal gangs.
  - `bande dessinée` [fr] — Means 'comic strip' in French; 'bande' matches gang terms but topic is entertainment, not security.

### `heat-health-risk`

- existing lexicon size: 15
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `heat-related illness` [en] conf=0.95 — Directly signals health harm caused by high temperatures.
  - `extreme heat warning` [en] conf=0.90 — Public health alert specifically tied to dangerous heat conditions.
  - `heatstroke deaths` [en] conf=0.95 — Fatalities from heat exposure are a core heat-health risk story.
  - `golpe de calor` [es] conf=0.95 — Spanish term for heatstroke, directly indicating heat-health risk.
  - `ola de calor muertes` [es] conf=0.93 — Heat wave deaths in Spanish headlines signals public health emergency.
  - `riesgo sanitario calor` [es] conf=0.88 — Health risk from heat phrasing used in Spanish public health reporting.
  - `mortes por calor` [pt] conf=0.94 — Portuguese phrase for deaths caused by heat, core to this topic.
  - `onda de calor saúde` [pt] conf=0.90 — Heat wave and health combined in Portuguese signals this topic.
  - `risco de insolação` [pt] conf=0.88 — Risk of sunstroke/heatstroke in Portuguese directly matches topic.
  - `colpo di calore` [it] conf=0.95 — Italian term for heatstroke, a primary heat-health risk indicator.
  - `ondata di calore vittime` [it] conf=0.92 — Heat wave victims in Italian headlines signals health emergency.
  - `coup de chaleur` [fr] conf=0.95 — French term for heatstroke, directly tied to heat-health risk topic.
  - `canicule risque sanitaire` [fr] conf=0.92 — Heatwave health risk phrasing used in French public health coverage.
  - `hitzebedingte todesfälle` [de] conf=0.95 — German phrase for heat-related deaths, directly signals this topic.
  - `hitzewelle gesundheitsrisiko` [de] conf=0.91 — Heat wave health risk in German clearly indicates this topic.
- negative monitors (5):
  - `heat pump` [en] — Refers to heating/cooling technology, not public health risk from heat.
  - `calor mercado` [es] — 'Heat market' in Spanish refers to energy or commodity markets, not health.
  - `summer heat records` [en] — Often covers meteorological records without a public health angle.
  - `chaleur économie` [fr] — Heat economy in French typically refers to energy sector, not health risk.
  - `hitze sport` [de] — Heat and sport in German usually covers athletic performance, not public health emergencies.

### `humanitarian-access-conflict`

- existing lexicon size: 9
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `humanitarian corridor blocked` [en] conf=0.93 — Directly signals denial of humanitarian access in a conflict zone.
  - `aid workers denied entry` [en] conf=0.91 — Specific phrase indicating obstruction of humanitarian personnel in conflict areas.
  - `relief convoy attacked` [en] conf=0.89 — Describes direct violence against humanitarian supply lines in conflict.
  - `corredor humanitario bloqueado` [es] conf=0.93 — Spanish equivalent of blocked humanitarian corridor, highly specific to this topic.
  - `acceso humanitario restringido` [es] conf=0.90 — Directly states restricted humanitarian access in Spanish-language headlines.
  - `acesso humanitário bloqueado` [pt] conf=0.92 — Portuguese phrase for blocked humanitarian access, topic-specific.
  - `trabalhadores humanitários impedidos` [pt] conf=0.88 — Describes humanitarian workers being prevented from operating in conflict zones.
  - `corridoio umanitario` [it] conf=0.91 — Italian term for humanitarian corridor, strongly associated with conflict access issues.
  - `aiuti umanitari bloccati` [it] conf=0.90 — Italian phrase for blocked humanitarian aid, directly on-topic.
  - `couloir humanitaire fermé` [fr] conf=0.92 — French phrase for closed humanitarian corridor in conflict contexts.
  - `accès humanitaire entravé` [fr] conf=0.90 — Directly describes obstructed humanitarian access in French headlines.
  - `humanitäre hilfe blockiert` [de] conf=0.91 — German phrase for blocked humanitarian aid, specific to conflict access topic.
  - `humanitärer korridor gesperrt` [de] conf=0.92 — German for closed humanitarian corridor, highly specific to this topic.
  - `siege blocks aid delivery` [en] conf=0.88 — Describes how military sieges cut off humanitarian supply in conflict zones.
  - `ong expulsées zone de guerre` [fr] conf=0.87 — Describes NGOs expelled from war zones, directly indicating humanitarian access denial.
- negative monitors (5):
  - `humanitarian award` [en] — Matches 'humanitarian' but refers to prize ceremonies, not conflict access.
  - `foreign aid budget` [en] — Concerns government funding debates, not operational access in conflict zones.
  - `refugee resettlement` [en] — Covers refugee policy and integration, not frontline humanitarian access under fire.
  - `ayuda humanitaria acuerdo` [es] — Diplomatic aid agreements may not involve active conflict access obstruction.
  - `hilfslieferung naturkatastrophe` [de] — Aid delivery in natural disasters shares vocabulary but is a distinct topic from conflict access.

### `migration-border-pressure`

- existing lexicon size: 10
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `border crossings surge` [en] conf=0.93 — Directly signals increased irregular migration at a border.
  - `asylum seekers detained` [en] conf=0.91 — Specifically describes migrants seeking refuge being held at borders.
  - `migrantes en la frontera` [es] conf=0.94 — Directly translates to migrants at the border, core topic phrase.
  - `crisis migratoria` [es] conf=0.90 — Spanish term for migration crisis, strongly tied to border pressure narratives.
  - `travessia irregular` [pt] conf=0.92 — Portuguese for irregular crossing, directly indicates undocumented border migration.
  - `fluxo migratório` [pt] conf=0.88 — Portuguese for migratory flow, commonly used in border pressure headlines.
  - `sbarchi migranti` [it] conf=0.95 — Italian term for migrant landings, specifically tied to sea border arrivals.
  - `flussi migratori irregolari` [it] conf=0.92 — Italian phrase for irregular migratory flows, directly on-topic.
  - `afflux de migrants` [fr] conf=0.93 — French for influx of migrants, signals border pressure as primary subject.
  - `traversée clandestine` [fr] conf=0.91 — French for clandestine crossing, directly indicates irregular border migration.
  - `illegale migration` [de] conf=0.90 — German term for illegal migration, commonly headlines border pressure stories.
  - `grenzschutz flüchtlinge` [de] conf=0.89 — German compound linking border protection and refugees, on-topic signal.
  - `irregular migration spike` [en] conf=0.92 — Signals a sudden increase in undocumented border crossings.
  - `presión migratoria frontera` [es] conf=0.94 — Spanish for migratory pressure at the border, exact topic phrase.
  - `migranten an der grenze` [de] conf=0.93 — German for migrants at the border, directly on-topic.
- negative monitors (5):
  - `migration policy reform` [en] — Often refers to legislative or political debates, not active border pressure events.
  - `bird migration` [en] — Refers to animal migration patterns, completely unrelated to human border crossings.
  - `data migration` [en] — IT/technology term for moving data between systems, not human migration.
  - `frontera comercial` [es] — Spanish for trade border, typically refers to trade disputes not migrant crossings.
  - `grenze deutschland` [de] — Generic German border reference often appears in trade, sports, or travel headlines unrelated to migration pressure.

### `mining-royalty-risk`

- existing lexicon size: 34
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `mine collapse deaths` [en] conf=0.93 — Directly signals a fatal mining safety incident.
  - `mining accident fatalities` [en] conf=0.91 — Explicitly links mining operations to deadly accidents.
  - `trapped miners rescue` [en] conf=0.95 — Classic headline phrase for underground mining emergencies.
  - `accidente minero muertos` [es] conf=0.94 — Spanish phrase for deadly mining accident, highly specific.
  - `derrumbe en mina` [es] conf=0.92 — Spanish for mine collapse, directly indicates mining safety crisis.
  - `mineros atrapados rescate` [es] conf=0.93 — Spanish equivalent of trapped miners rescue scenario.
  - `acidente em mina` [pt] conf=0.92 — Portuguese for mine accident, core topic signal.
  - `mineiros presos soterrados` [pt] conf=0.94 — Portuguese phrase for miners buried/trapped underground.
  - `desastre mineração vítimas` [pt] conf=0.90 — Portuguese for mining disaster with victims, strong topic match.
  - `crollo miniera vittime` [it] conf=0.93 — Italian for mine collapse with victims, precise topic indicator.
  - `minatori intrappolati galleria` [it] conf=0.91 — Italian for miners trapped in a tunnel, clear safety crisis signal.
  - `effondrement mine victimes` [fr] conf=0.93 — French for mine collapse with victims, directly on-topic.
  - `mineurs piégés secours` [fr] conf=0.92 — French for trapped miners rescue, strong topic match.
  - `grubenunglück tote` [de] conf=0.94 — German for mine disaster with fatalities, highly specific.
  - `bergwerksunfall eingeschlossen` [de] conf=0.91 — German for mining accident with trapped workers, precise signal.
- negative monitors (5):
  - `royalty payments mining` [en] — Mining royalties refer to financial/fiscal policy, not safety crises.
  - `gold mining stocks` [en] — Matches mining sector but indicates financial markets, not safety events.
  - `data mining privacy` [en] — 'Mining' here refers to data extraction, completely unrelated to resource safety.
  - `minería inversión` [es] — Spanish mining investment headlines are about economics, not safety crises.
  - `crypto mining energy` [en] — Cryptocurrency mining matches 'mining' substring but is entirely unrelated to resource safety.

### `oil-gas-supply-risk`

- existing lexicon size: 5
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `gas supply disruption` [en] conf=0.93 — Directly signals a threat to natural gas availability in headlines.
  - `oil supply shock` [en] conf=0.92 — Classic phrase for sudden crude oil availability risk events.
  - `pipeline outage` [en] conf=0.88 — Refers to infrastructure failure causing supply interruption for oil or gas.
  - `suministro de gas en riesgo` [es] conf=0.91 — Spanish phrase explicitly framing gas supply as at risk.
  - `corte de suministro energético` [es] conf=0.87 — Spanish term for energy supply cut, commonly used for oil/gas disruptions.
  - `interrupção no fornecimento de gás` [pt] conf=0.92 — Portuguese phrase for gas supply interruption, directly on-topic.
  - `risco de abastecimento de petróleo` [pt] conf=0.90 — Portuguese for oil supply risk, unambiguously on-topic.
  - `fornitura di gas a rischio` [it] conf=0.91 — Italian phrase meaning gas supply at risk, directly matches topic.
  - `interruzione forniture petrolio` [it] conf=0.89 — Italian for oil supply interruption, clearly signals supply risk.
  - `risque d'approvisionnement en gaz` [fr] conf=0.92 — French phrase for gas supply risk, precisely on-topic.
  - `rupture d'approvisionnement pétrolier` [fr] conf=0.90 — French for oil supply rupture, directly indicates supply risk.
  - `gasversorgung gefährdet` [de] conf=0.91 — German phrase meaning gas supply endangered, clearly on-topic.
  - `ölversorgungsrisiko` [de] conf=0.90 — German compound noun for oil supply risk, unambiguous topic signal.
  - `lng supply crunch` [en] conf=0.88 — LNG-specific supply tightening phrase used in energy risk headlines.
  - `lieferstopp erdgas` [de] conf=0.92 — German for natural gas delivery halt, directly signals supply disruption.
- negative monitors (5):
  - `gas prices rise` [en] — Often refers to retail gasoline price increases unrelated to supply risk narratives.
  - `oil company profits` [en] — Matches oil sector headlines about earnings, not supply disruption risk.
  - `energy transition` [en] — Primarily covers renewable shift policy, not oil/gas supply risk events.
  - `gasolinera` [es] — Spanish for gas station; matches retail fuel stories, not supply risk.
  - `pétrole en bourse` [fr] — French for oil on the stock exchange; matches financial market stories, not supply disruption.

### `sanctions-diplomatic-pressure`

- existing lexicon size: 5
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `economic sanctions imposed` [en] conf=0.93 — Directly signals a sanctions action as the headline's main subject.
  - `sanctions package against` [en] conf=0.91 — Specific phrase indicating a new round of sanctions targeting a country or entity.
  - `diplomatic pressure on` [en] conf=0.88 — Explicitly frames diplomatic coercion as the story's core topic.
  - `sanciones económicas` [es] conf=0.92 — Spanish equivalent of economic sanctions, highly specific to this topic.
  - `presión diplomática sobre` [es] conf=0.89 — Spanish phrase for diplomatic pressure targeting a specific actor.
  - `sanções econômicas` [pt] conf=0.92 — Portuguese term for economic sanctions, directly on-topic.
  - `pressão diplomática` [pt] conf=0.87 — Portuguese phrase for diplomatic pressure, strongly tied to this topic.
  - `sanzioni economiche` [it] conf=0.92 — Italian term for economic sanctions, unambiguous topic signal.
  - `pressione diplomatica` [it] conf=0.88 — Italian phrase for diplomatic pressure as a policy tool.
  - `sanctions diplomatiques` [fr] conf=0.91 — French term combining sanctions and diplomacy, highly specific.
  - `pression diplomatique sur` [fr] conf=0.88 — French phrase indicating diplomatic coercion against a named party.
  - `wirtschaftssanktionen gegen` [de] conf=0.93 — German phrase for economic sanctions against a target, very specific.
  - `diplomatischer druck auf` [de] conf=0.89 — German phrase for diplomatic pressure on a specific actor.
  - `sanctions regime tightened` [en] conf=0.90 — Signals escalation of an existing sanctions framework as the main story.
  - `neue sanktionen verhängt` [de] conf=0.91 — German for 'new sanctions imposed', directly indicates this topic.
- negative monitors (5):
  - `sanction` [en] — Single word also means official approval or authorization in non-geopolitical contexts.
  - `pressure` [en] — Extremely generic; matches sports, weather, medical, and political stories unrelated to diplomacy.
  - `embargo` [en] — Often refers to media embargoes or trade embargoes in historical/economic contexts unrelated to current sanctions.
  - `presión` [es] — Generic Spanish word for pressure; matches sports, medical, and social stories far more often than diplomacy.
  - `isolation` [en] — Frequently used in public health, psychology, and social contexts rather than geopolitical isolation.

### `transport-corridor-disruption`

- existing lexicon size: 16
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `rail corridor blocked` [en] conf=0.92 — Directly signals a transport corridor disruption on rail infrastructure.
  - `shipping lane disrupted` [en] conf=0.90 — Indicates disruption to a maritime transport corridor.
  - `highway closure disrupts freight` [en] conf=0.88 — Freight highway closure is a core transport corridor disruption event.
  - `corredor de transporte bloqueado` [es] conf=0.91 — Spanish phrase directly describing a blocked transport corridor.
  - `cierre de autopista interrumpe` [es] conf=0.87 — Highway closure interrupting traffic signals corridor disruption in Spanish.
  - `corredor logístico cortado` [es] conf=0.89 — Cut logistics corridor is a precise transport disruption indicator in Spanish.
  - `corredor de transporte interrompido` [pt] conf=0.91 — Portuguese phrase directly describing an interrupted transport corridor.
  - `bloqueio na rodovia federal` [pt] conf=0.86 — Federal highway blockage in Portuguese signals major corridor disruption.
  - `interrupção na ferrovia` [pt] conf=0.88 — Railway interruption in Portuguese is a clear transport corridor disruption signal.
  - `corridoio ferroviario interrotto` [it] conf=0.92 — Italian phrase for interrupted railway corridor directly matches the topic.
  - `blocco autostradale` [it] conf=0.87 — Italian motorway blockage term strongly indicates transport corridor disruption.
  - `corridor de transport perturbé` [fr] conf=0.91 — French phrase directly describing a disrupted transport corridor.
  - `fermeture de l'axe routier` [fr] conf=0.86 — Road axis closure in French signals a transport corridor disruption event.
  - `verkehrskorridor gesperrt` [de] conf=0.93 — German phrase for a blocked transport corridor is a direct topic match.
  - `autobahn gesperrt güterverkehr` [de] conf=0.88 — Motorway closure affecting freight traffic signals corridor disruption in German.
- negative monitors (5):
  - `corridor` [en] — Too generic; frequently appears in political, architectural, or humanitarian contexts unrelated to transport.
  - `disruption` [en] — Extremely broad term matching tech, business, and political disruption stories far more often than transport corridors.
  - `road closed` [en] — Often refers to local street closures for events or construction rather than strategic transport corridor disruptions.
  - `bloqueo` [es] — In Spanish headlines frequently refers to political blockades or internet blocks, not transport corridors.
  - `sperrung` [de] — German term for closure is used broadly for building closures, border closures, and event perimeters, not specifically transport corridors.

### `water-stress-drought`

- existing lexicon size: 5
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 15
  - `water stress` [en] conf=0.95 — Direct technical term for insufficient water supply relative to demand.
  - `drought emergency` [en] conf=0.93 — Signals an official crisis declaration due to prolonged dry conditions.
  - `sequía severa` [es] conf=0.94 — Severe drought in Spanish, directly signals water scarcity crisis.
  - `escasez de agua` [es] conf=0.92 — Water scarcity in Spanish, primary indicator of water stress topic.
  - `seca prolongada` [pt] conf=0.93 — Prolonged drought in Portuguese, clearly signals water stress conditions.
  - `crise hídrica` [pt] conf=0.94 — Water crisis in Portuguese, directly indicates severe water stress.
  - `siccità grave` [it] conf=0.93 — Severe drought in Italian, unambiguously signals this topic.
  - `emergenza idrica` [it] conf=0.92 — Water emergency in Italian, indicates critical water shortage conditions.
  - `sécheresse prolongée` [fr] conf=0.94 — Prolonged drought in French, directly indicates water stress topic.
  - `stress hydrique` [fr] conf=0.95 — Direct French technical term for water stress conditions.
  - `dürre bedroht` [de] conf=0.91 — Drought threatens in German, signals water stress as primary subject.
  - `wasserknappheit` [de] conf=0.94 — Water scarcity in German, directly indicates water stress topic.
  - `aquifer depletion` [en] conf=0.90 — Specific term for groundwater exhaustion, a key water stress indicator.
  - `restricciones de agua` [es] conf=0.89 — Water restrictions in Spanish, typically imposed during drought conditions.
  - `dürreperiode` [de] conf=0.92 — Drought period in German, unambiguously signals prolonged dry conditions.
- negative monitors (5):
  - `water polo` [en] — Contains 'water' but refers to a sport, not water scarcity.
  - `dry run` [en] — Idiomatic phrase meaning a rehearsal, not related to drought conditions.
  - `drought beer` [en] — Brand or product name that may appear in headlines unrelated to water stress.
  - `seca de ideias` [pt] — Idiomatic Portuguese phrase meaning lack of ideas, not physical drought.
  - `trockenheit im humor` [de] — German metaphor for dry humor, not related to actual drought conditions.

### `currency-debt-stress`

- LLM-Atlas agreement on reviewed sample: 58.3%
- existing lexicon size: 18
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 14
  - `sovereign debt default` [en] conf=0.97 — Explicitly describes a government failing to meet debt obligations.
  - `debt restructuring talks` [en] conf=0.93 — Indicates a country negotiating to reorganize its debt burden.
  - `peso se desploma` [es] conf=0.94 — Describes a sharp collapse of the peso currency in Spanish headlines.
  - `crisis de deuda soberana` [es] conf=0.96 — Directly names a sovereign debt crisis in Spanish.
  - `reestructuración de deuda` [es] conf=0.92 — Refers to debt restructuring negotiations in Spanish-language news.
  - `crise cambial` [pt] conf=0.94 — Portuguese term for exchange-rate or currency crisis.
  - `dívida soberana em risco` [pt] conf=0.93 — Signals sovereign debt at risk of default in Portuguese.
  - `moratória da dívida` [pt] conf=0.95 — Refers to a debt moratorium or payment suspension in Portuguese.
  - `crisi del debito sovrano` [it] conf=0.95 — Italian phrase directly naming a sovereign debt crisis.
  - `crollo della lira` [it] conf=0.91 — Describes a collapse of a lira-denominated currency in Italian headlines.
  - `crise de la dette` [fr] conf=0.94 — French phrase for debt crisis, commonly used in financial headlines.
  - `dépréciation monétaire` [fr] conf=0.92 — Refers to currency depreciation stress in French-language news.
  - `staatsschuldenkrise` [de] conf=0.96 — German compound noun directly meaning sovereign debt crisis.
  - `währungsverfall` [de] conf=0.93 — German term for currency collapse or severe depreciation.
- negative monitors (5):
  - `interest rate hike` [en] — Usually signals central bank monetary policy decisions, not debt stress per se.
  - `budget deficit` [en] — Refers to fiscal planning shortfalls, not necessarily acute debt or currency stress.
  - `inflation rate` [en] — Primarily signals price-level reporting, not currency or debt crisis events.
  - `bond yield` [en] — Often appears in routine market-data headlines rather than crisis coverage.
  - `deuda educativa` [es] — Uses 'deuda' but refers to educational debt or obligations, not sovereign finance.

### `disinformation-influence-operation`

- existing lexicon size: 9
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 14
  - `disinformation campaign` [en] conf=0.95 — Specific phrase for organized spread of false information.
  - `coordinated inauthentic behavior` [en] conf=0.97 — Platform-specific term for detected influence operations.
  - `campaña de desinformación` [es] conf=0.95 — Spanish equivalent of disinformation campaign, highly specific.
  - `operación de influencia` [es] conf=0.93 — Spanish term for influence operation targeting public opinion.
  - `campanha de desinformação` [pt] conf=0.95 — Portuguese phrase directly describing disinformation campaigns.
  - `operação de influência` [pt] conf=0.93 — Portuguese term for coordinated influence operations.
  - `campagna di disinformazione` [it] conf=0.95 — Italian phrase for organized disinformation efforts.
  - `operazione di influenza` [it] conf=0.90 — Italian term for influence operations targeting narratives.
  - `campagne de désinformation` [fr] conf=0.95 — French phrase for disinformation campaigns, highly specific.
  - `opération d'influence` [fr] conf=0.93 — French term for state-linked or covert influence operations.
  - `desinformationskampagne` [de] conf=0.95 — German compound noun directly describing disinformation campaigns.
  - `einflussoperation` [de] conf=0.92 — German term for coordinated influence operations.
  - `fake news network` [en] conf=0.88 — Refers to organized infrastructure for spreading fabricated stories.
  - `manipulation de l'information` [fr] conf=0.90 — French phrase for deliberate information manipulation operations.
- negative monitors (5):
  - `influencer` [en] — Usually refers to social media content creators, not influence operations.
  - `fake news` [en] — Overused phrase often applied to political disputes rather than documented disinformation operations.
  - `propaganda` [en] — Broad term frequently used in historical, advertising, or general political contexts unrelated to specific operations.
  - `misinformation` [en] — Often covers accidental false information spread, not coordinated influence operations.
  - `noticias falsas` [es] — Spanish 'fake news' is frequently used in partisan political rhetoric rather than reporting on actual operations.

### `housing-cost-pressure`

- existing lexicon size: 28
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 14
  - `rent affordability crisis` [en] conf=0.95 — Directly signals housing cost pressure as the primary subject.
  - `housing costs soar` [en] conf=0.93 — Explicitly describes rising housing expenses in headlines.
  - `mortgage burden` [en] conf=0.88 — Refers specifically to financial strain from home loan costs.
  - `alquiler inasequible` [es] conf=0.92 — Spanish for 'unaffordable rent', directly signals housing cost pressure.
  - `precio de la vivienda sube` [es] conf=0.91 — Describes rising housing prices as the main subject in Spanish headlines.
  - `crise do arrendamento` [pt] conf=0.93 — Portuguese for 'rental crisis', a direct indicator of housing cost pressure.
  - `custo da habitação` [pt] conf=0.90 — Portuguese phrase meaning 'housing cost', central to this topic.
  - `affitti insostenibili` [it] conf=0.92 — Italian for 'unsustainable rents', directly signals housing affordability strain.
  - `caro affitti` [it] conf=0.89 — Italian colloquial phrase for expensive rents, common in housing-cost headlines.
  - `crise du logement` [fr] conf=0.93 — French for 'housing crisis', a primary indicator of this topic.
  - `loyers en hausse` [fr] conf=0.91 — French phrase meaning 'rising rents', directly signals housing cost pressure.
  - `mietpreise steigen` [de] conf=0.93 — German for 'rental prices rising', a direct housing cost pressure signal.
  - `wohnkosten explodieren` [de] conf=0.92 — German for 'housing costs exploding', strongly indicates this topic.
  - `wohnungsnot` [de] conf=0.88 — German term for housing shortage/distress, closely tied to cost pressure coverage.
- negative monitors (5):
  - `housing market` [en] — Too broad; often refers to investment trends, sales volumes, or construction activity rather than cost pressure.
  - `real estate boom` [en] — Usually signals investor or economic growth stories, not affordability hardship.
  - `vivienda social` [es] — Refers to social/public housing policy, not necessarily cost pressure on renters or buyers.
  - `immobilier` [fr] — Generic French real-estate term; matches investment, luxury, and commercial property stories unrelated to cost pressure.
  - `hypothèque` [fr] — French for 'mortgage' in a legal/financial context; often appears in banking or fraud stories rather than housing cost pressure.

### `labor-strike-disruption`

- existing lexicon size: 24
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 14
  - `workers go on strike` [en] conf=0.95 — Directly signals a labor strike action in a headline.
  - `strike disrupts service` [en] conf=0.93 — Combines strike action with its disruptive consequence.
  - `union walkout` [en] conf=0.90 — Specific labor action term indicating workers leaving their posts.
  - `huelga general` [es] conf=0.95 — General strike in Spanish, a primary labor disruption signal.
  - `trabajadores en huelga` [es] conf=0.92 — Workers on strike in Spanish, directly indicates labor stoppage.
  - `greve dos trabalhadores` [pt] conf=0.94 — Workers' strike in Portuguese, directly signals labor disruption.
  - `paralisação geral` [pt] conf=0.91 — General work stoppage in Portuguese, indicates widespread strike.
  - `sciopero generale` [it] conf=0.95 — General strike in Italian, a strong primary topic indicator.
  - `lavoratori in sciopero` [it] conf=0.92 — Workers on strike in Italian, directly signals labor action.
  - `grève des travailleurs` [fr] conf=0.94 — Workers' strike in French, directly indicates labor disruption.
  - `mouvement de grève` [fr] conf=0.90 — Strike movement in French, specific to organized labor action.
  - `streik legt betrieb lahm` [de] conf=0.93 — Strike shuts down operations in German, signals disruption clearly.
  - `warnstreik` [de] conf=0.89 — Warning strike in German, a specific labor action term.
  - `gewerkschaft streik` [de] conf=0.88 — Union strike in German, directly ties labor organization to action.
- negative monitors (5):
  - `hunger strike` [en] — Refers to a protest fast, not a labor work stoppage.
  - `bowling strike` [en] — Sports term unrelated to labor action.
  - `airstrike` [en] — Military attack term that matches 'strike' but is entirely unrelated to labor.
  - `huelga de hambre` [es] — Hunger strike in Spanish refers to a protest fast, not a labor walkout.
  - `sciopero della fame` [it] — Hunger strike in Italian, not a labor work disruption event.

### `press-freedom-crackdown`

- existing lexicon size: 15
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 14
  - `press freedom crackdown` [en] conf=0.98 — Exact label phrase; unambiguously marks this topic.
  - `reporter jailed` [en] conf=0.91 — Imprisonment of a journalist is a primary indicator of press suppression.
  - `periodista detenido` [es] conf=0.93 — Spanish for 'journalist detained', directly signals press-freedom crackdown.
  - `libertad de prensa` [es] conf=0.88 — Spanish phrase for 'press freedom', commonly used in headlines about media repression.
  - `censura a medios` [es] conf=0.90 — Spanish for 'media censorship', strongly tied to press-freedom crackdown stories.
  - `jornalista preso` [pt] conf=0.93 — Portuguese for 'journalist imprisoned', a direct indicator of press suppression.
  - `liberdade de imprensa ameaçada` [pt] conf=0.91 — Portuguese phrase meaning 'press freedom threatened', specific to this topic.
  - `censura à imprensa` [pt] conf=0.90 — Portuguese for 'press censorship', closely tied to crackdown on media.
  - `giornalista arrestato` [it] conf=0.93 — Italian for 'journalist arrested', a direct signal of press-freedom crackdown.
  - `libertà di stampa` [it] conf=0.88 — Italian for 'freedom of the press', frequently used in crackdown headlines.
  - `liberté de la presse` [fr] conf=0.88 — French for 'freedom of the press', a standard phrase in media-repression headlines.
  - `journaliste emprisonné` [fr] conf=0.93 — French for 'journalist imprisoned', directly marks press-freedom crackdown events.
  - `pressefreiheit eingeschränkt` [de] conf=0.92 — German for 'press freedom restricted', a precise indicator of this topic.
  - `journalist verhaftet` [de] conf=0.93 — German for 'journalist arrested', strongly signals a press-freedom crackdown story.
- negative monitors (5):
  - `freedom of speech` [en] — Broad civil-liberties phrase that more often covers political protests or social-media bans, not specifically press crackdowns.
  - `media bias` [en] — Usually refers to editorial slant debates, not government suppression of journalists.
  - `fake news` [en] — Predominantly used in misinformation or political rhetoric contexts, not press-freedom crackdowns.
  - `censura` [es] — Single generic word matches internet censorship, film censorship, and many unrelated content-moderation stories.
  - `medienrecht` [de] — German for 'media law' covers routine regulatory and copyright stories, not specifically crackdowns on press freedom.

### `student-youth-protest`

- existing lexicon size: 15
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 14
  - `campus walkout` [en] conf=0.92 — Specific student protest tactic on university or school grounds.
  - `youth demonstration` [en] conf=0.88 — Explicitly links young people to street protest activity.
  - `protesta estudiantil` [es] conf=0.95 — Direct Spanish equivalent of student protest, highly specific.
  - `marcha universitaria` [es] conf=0.90 — University march is a common framing for student protest in Spanish-language headlines.
  - `huelga estudiantil` [es] conf=0.92 — Student strike is a core youth protest action in Spanish-speaking contexts.
  - `protesto estudantil` [pt] conf=0.95 — Direct Portuguese equivalent of student protest.
  - `greve dos estudantes` [pt] conf=0.91 — Students' strike is a frequent framing in Brazilian and Portuguese news.
  - `manifestação jovens` [pt] conf=0.87 — Youth demonstration phrasing common in Portuguese-language headlines.
  - `protesta studentesca` [it] conf=0.93 — Standard Italian phrase for student protest in news headlines.
  - `corteo studentesco` [it] conf=0.90 — Student march/procession is a typical Italian headline term for youth protest.
  - `manifestation lycéens` [fr] conf=0.92 — High-school student demonstration is a classic French protest framing.
  - `grève étudiante` [fr] conf=0.93 — Student strike is a well-established French headline phrase for youth protest.
  - `studentenprotest` [de] conf=0.94 — Compound German noun directly denoting student protest events.
  - `schülerstreik` [de] conf=0.91 — Pupil/school-student strike, common in German coverage of youth climate and political protests.
- negative monitors (5):
  - `student loan` [en] — Matches 'student' but refers to financial policy, not protest activity.
  - `youth unemployment` [en] — Concerns young people but is an economic indicator story, not a protest event.
  - `campus shooting` [en] — Occurs on campus and may involve students but is a crime/violence story, not protest.
  - `jugend festival` [de] — Youth festival matches 'youth' but indicates a cultural event, not a protest.
  - `bourse étudiante` [fr] — Student scholarship/grant story matches 'étudiant' context but is an education-finance topic, not protest.

### `trade-export-restriction`

- existing lexicon size: 5
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 14
  - `trade embargo` [en] conf=0.92 — Specific term for a formal trade restriction between countries.
  - `export controls tightened` [en] conf=0.91 — Signals regulatory tightening of export licensing rules.
  - `restricciones a la exportación` [es] conf=0.93 — Spanish phrase directly meaning export restrictions.
  - `veda de exportaciones` [es] conf=0.90 — Spanish term for an export ban or prohibition.
  - `restrições às exportações` [pt] conf=0.93 — Portuguese phrase directly meaning export restrictions.
  - `proibição de exportação` [pt] conf=0.91 — Portuguese term for an export prohibition or ban.
  - `restrizioni all'esportazione` [it] conf=0.93 — Italian phrase directly meaning export restrictions.
  - `divieto di esportazione` [it] conf=0.91 — Italian term for an export ban or prohibition.
  - `restrictions aux exportations` [fr] conf=0.93 — French phrase directly meaning export restrictions.
  - `embargo commercial` [fr] conf=0.90 — French term for a trade embargo between parties.
  - `exportbeschränkungen` [de] conf=0.93 — German compound noun directly meaning export restrictions.
  - `ausfuhrverbot` [de] conf=0.91 — German term for an export ban or prohibition.
  - `tariff barriers imposed` [en] conf=0.88 — Signals imposition of trade-restricting tariff barriers.
  - `handelsbeschränkungen verhängt` [de] conf=0.90 — German phrase meaning trade restrictions imposed, directly on-topic.
- negative monitors (5):
  - `export growth` [en] — Refers to positive trade performance, not restrictions.
  - `free trade agreement` [en] — Signals trade liberalisation, the opposite of restrictions.
  - `export promotion` [en] — Refers to government efforts to boost exports, not restrict them.
  - `trade deal signed` [en] — Indicates a new trade agreement, not a restriction or ban.
  - `embargo artístico` [es] — Embargo in Spanish cultural contexts refers to media holds or artistic embargoes, not trade policy.

### `disease-outbreak`

- existing lexicon size: 16
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 13
  - `epidemic spreads` [en] conf=0.92 — Signals active spread of a disease in news context.
  - `cases of infection` [en] conf=0.85 — Commonly used in outbreak reporting to quantify spread.
  - `brote de enfermedad` [es] conf=0.95 — Direct Spanish equivalent of 'disease outbreak'.
  - `epidemia de` [es] conf=0.90 — Spanish term for epidemic, strongly tied to disease outbreak stories.
  - `surto de doença` [pt] conf=0.95 — Portuguese phrase directly meaning 'disease outbreak'.
  - `casos confirmados de` [pt] conf=0.85 — Used in Portuguese outbreak reporting to confirm infection cases.
  - `focolaio di` [it] conf=0.93 — Italian word for outbreak/cluster, standard in disease reporting.
  - `epidemia in corso` [it] conf=0.90 — Italian phrase meaning 'ongoing epidemic', specific to outbreak news.
  - `épidémie de` [fr] conf=0.93 — French term for epidemic, directly signals disease outbreak topic.
  - `foyer épidémique` [fr] conf=0.88 — French phrase for epidemic focus/cluster, specific to outbreak reporting.
  - `ausbruch der krankheit` [de] conf=0.93 — German phrase meaning 'disease outbreak', highly specific.
  - `infektionswelle` [de] conf=0.88 — German term for 'wave of infection', used in outbreak coverage.
  - `seuchenausbruch` [de] conf=0.91 — German compound noun specifically meaning epidemic/plague outbreak.
- negative monitors (5):
  - `outbreak of violence` [en] — 'Outbreak' here refers to conflict, not disease, causing false positives.
  - `virus informatique` [fr] — 'Virus' in French tech headlines refers to computer viruses, not biological ones.
  - `epidemia de corrupción` [es] — Metaphorical use of 'epidemia' for corruption, not a disease outbreak.
  - `fever pitch` [en] — Idiomatic English phrase meaning intense excitement, unrelated to disease.
  - `contagio político` [es] — Metaphorical use of 'contagio' for political spread, not a health outbreak.
- rejected below confidence threshold (1):
  - `alerte sanitaire` [fr] conf=0.84

### `forced-displacement`

- existing lexicon size: 17
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 13
  - `internally displaced persons` [en] conf=0.93 — Specific UN term for people displaced within their own country.
  - `desplazamiento forzado` [es] conf=0.95 — Standard Spanish term for forced displacement used in Latin American and Spanish news.
  - `desplazados internos` [es] conf=0.90 — Spanish equivalent of internally displaced persons, directly signals the topic.
  - `deslocamento forçado` [pt] conf=0.95 — Portuguese direct translation of forced displacement used in Brazilian and Portuguese media.
  - `deslocados internos` [pt] conf=0.90 — Portuguese term for internally displaced persons, specific to this topic.
  - `sfollati interni` [it] conf=0.92 — Italian term for internally displaced persons, strongly tied to this topic.
  - `sfollamento forzato` [it] conf=0.93 — Italian phrase for forced displacement, directly identifies the topic.
  - `déplacement forcé` [fr] conf=0.95 — Standard French term for forced displacement in humanitarian contexts.
  - `déplacés internes` [fr] conf=0.91 — French equivalent of IDPs, commonly used in francophone humanitarian reporting.
  - `zwangsvertreibung` [de] conf=0.93 — German term for forced expulsion/displacement, directly signals the topic.
  - `binnenvertriebene` [de] conf=0.92 — German word for internally displaced persons, specific to this humanitarian topic.
  - `mass displacement crisis` [en] conf=0.88 — Phrase used in headlines about large-scale forced population movements.
  - `vertreibung von zivilisten` [de] conf=0.87 — German phrase for expulsion of civilians, strongly associated with forced displacement events.
- negative monitors (5):
  - `refugee resettlement` [en] — Refers to the legal resettlement process for recognized refugees, not the act of displacement itself.
  - `migration policy` [en] — Usually covers border and immigration law debates, not forced displacement events.
  - `asylum seekers` [en] — Primarily signals legal status and asylum processes rather than the displacement event itself.
  - `evacuación voluntaria` [es] — Voluntary evacuation is distinct from forced displacement and often covers disaster preparedness stories.
  - `relocation program` [en] — Typically refers to planned government or corporate relocation schemes, not forced displacement.
- rejected below confidence threshold (1):
  - `population déracinée` [fr] conf=0.82

### `constitutional-institutional-crisis`

- LLM-Atlas agreement on reviewed sample: 62.5%
- existing lexicon size: 18
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 12
  - `impeachment proceedings` [en] conf=0.87 — Signals a formal institutional challenge to executive authority.
  - `crise constitutionnelle` [fr] conf=0.95 — French direct equivalent of constitutional crisis.
  - `dissolution du parlement` [fr] conf=0.85 — Parliamentary dissolution is a key marker of institutional crisis.
  - `crisis constitucional` [es] conf=0.95 — Spanish direct equivalent of constitutional crisis.
  - `golpe institucional` [es] conf=0.88 — Institutional coup signals a breakdown of constitutional order in Spanish-language headlines.
  - `crise institucional` [pt] conf=0.93 — Portuguese phrase directly indicating an institutional crisis.
  - `ruptura constitucional` [pt] conf=0.90 — Constitutional rupture signals a severe breakdown of legal-political order.
  - `crisi istituzionale` [it] conf=0.93 — Italian direct equivalent of institutional crisis.
  - `crisi costituzionale` [it] conf=0.95 — Italian direct equivalent of constitutional crisis.
  - `verfassungskrise` [de] conf=0.95 — German compound noun directly meaning constitutional crisis.
  - `staatskrise` [de] conf=0.88 — German term for a state-level political crisis threatening institutions.
  - `destitución presidencial` [es] conf=0.86 — Presidential removal signals a major constitutional confrontation.
- negative monitors (5):
  - `crisis económica` [es] — Economic crisis headlines dominate this phrase, not constitutional or institutional crises.
  - `government shutdown` [en] — Usually refers to budget/funding disputes rather than a constitutional breakdown.
  - `political scandal` [en] — Scandals are common and often unrelated to constitutional or institutional crises.
  - `regierungskrise` [de] — Government crisis in German often refers to coalition collapses, not constitutional crises specifically.
  - `crise politique` [fr] — Generic political crisis in French covers many unrelated governance disputes beyond constitutional issues.
- rejected below confidence threshold (2):
  - `checks and balances undermined` [en] conf=0.82
  - `dissolution of parliament` [en] conf=0.84

### `election-legitimacy-dispute`

- existing lexicon size: 43
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 12
  - `election fraud claims` [en] conf=0.93 — Directly signals disputed election legitimacy via fraud allegations.
  - `stolen election` [en] conf=0.91 — Core phrase used when a candidate or party contests election results.
  - `disputed election results` [en] conf=0.94 — Explicitly describes a legitimacy challenge to electoral outcomes.
  - `resultados impugnados` [es] conf=0.90 — Means 'contested results', directly indicating an election legitimacy dispute.
  - `elección ilegítima` [es] conf=0.88 — Phrase explicitly labeling an election as illegitimate.
  - `fraude nas eleições` [pt] conf=0.92 — Portuguese phrase for electoral fraud, core to legitimacy disputes.
  - `resultado eleitoral contestado` [pt] conf=0.91 — Directly describes a contested electoral result in Portuguese.
  - `risultati contestati elezioni` [it] conf=0.90 — Italian phrase for contested election results.
  - `résultats électoraux contestés` [fr] conf=0.91 — French phrase explicitly describing disputed election results.
  - `wahlfälschung` [de] conf=0.93 — German word for election fraud, core indicator of legitimacy disputes.
  - `wahlergebnis angefochten` [de] conf=0.91 — German phrase meaning 'election result challenged', directly on-topic.
  - `wahlbetrug vorwürfe` [de] conf=0.90 — German for 'election fraud allegations', strongly tied to legitimacy disputes.
- negative monitors (5):
  - `election campaign` [en] — Refers to pre-election campaigning, not a legitimacy dispute after voting.
  - `voter turnout` [en] — Describes participation rates, not a challenge to election legitimacy.
  - `election day` [en] — Refers to the voting event itself, not a post-election legitimacy contest.
  - `fraude fiscal` [es] — 'Fraude fiscal' means tax fraud in Spanish, unrelated to elections despite containing 'fraude'.
  - `wahlrecht` [de] — Means 'voting rights' or 'electoral law' in German, not a legitimacy dispute.

### `food-price-stress`

- existing lexicon size: 26
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 12
  - `food prices surge` [en] conf=0.93 — Directly signals rising food costs as the headline subject.
  - `grocery bills rising` [en] conf=0.91 — Specifically captures consumer stress from supermarket price increases.
  - `cost of food soars` [en] conf=0.90 — Unambiguously describes escalating food expenditure pressure.
  - `cesta de la compra cara` [es] conf=0.88 — Refers to expensive shopping basket, a direct food-cost stress indicator in Spanish media.
  - `preços dos alimentos sobem` [pt] conf=0.91 — Portuguese phrase for rising food prices, primary topic signal.
  - `custo da alimentação` [pt] conf=0.87 — Cost of food/nutrition in Portuguese, directly relevant.
  - `caro fare la spesa` [it] conf=0.88 — Italian phrase meaning expensive grocery shopping, clear food-price stress signal.
  - `prezzi alimentari aumentano` [it] conf=0.90 — Italian for rising food prices, unambiguous topic match.
  - `hausse des prix alimentaires` [fr] conf=0.92 — French for rise in food prices, directly indicates this topic.
  - `lebensmittelpreise steigen` [de] conf=0.92 — German for rising food prices, a direct and specific topic signal.
  - `teurer einkaufen` [de] conf=0.86 — German phrase meaning more expensive shopping, signals consumer food-cost stress.
  - `nahrungsmittelpreise erhöhen` [de] conf=0.89 — German for increasing food/nutrition prices, clearly on-topic.
- negative monitors (5):
  - `food festival` [en] — Matches 'food' but refers to cultural events, not price stress.
  - `restaurant prices` [en] — Often covers dining-out trends or reviews rather than household food-cost stress.
  - `oil prices` [en] — Could co-occur with food topics but primarily signals energy/fuel market stories.
  - `precio del petróleo` [es] — Spanish for oil price; shares 'precio' with food-price terms but covers energy markets.
  - `prix du marché` [fr] — French for market prices; too generic and frequently refers to financial markets, not food.

### `telecom-internet-shutdown`

- existing lexicon size: 17
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 12
  - `telecom blackout` [en] conf=0.91 — Refers specifically to telecommunications service cutoffs.
  - `corte de internet` [es] conf=0.95 — Spanish phrase for internet shutdown used in Latin American and Spanish news.
  - `apagón de internet` [es] conf=0.94 — Spanish 'internet blackout' term widely used for connectivity shutdowns.
  - `bloqueo de telecomunicaciones` [es] conf=0.89 — Refers to telecom blocking actions by authorities in Spanish-language headlines.
  - `bloqueio de internet` [pt] conf=0.93 — Portuguese term for internet blocking, commonly used in shutdown coverage.
  - `apagão de telecomunicações` [pt] conf=0.88 — Portuguese 'telecom blackout' phrase indicating service disruption by authorities.
  - `interruzione internet` [it] conf=0.93 — Italian phrase for internet interruption or shutdown.
  - `blackout delle telecomunicazioni` [it] conf=0.90 — Italian term for telecom blackout events.
  - `coupure internet` [fr] conf=0.94 — French term for internet cutoff, used in shutdown reporting.
  - `coupure des télécommunications` [fr] conf=0.91 — French phrase for telecom service cutoff by authorities.
  - `internetsperre` [de] conf=0.93 — German compound word specifically meaning internet blockade or shutdown.
  - `internet abgeschaltet` [de] conf=0.90 — German phrase meaning 'internet switched off', used in shutdown headlines.
- negative monitors (5):
  - `power outage` [en] — Refers to electrical blackouts, not telecom/internet shutdowns specifically.
  - `network upgrade` [en] — Describes planned infrastructure improvements, not politically motivated shutdowns.
  - `streaming outage` [en] — Usually refers to platform-specific service disruptions like Netflix, not government shutdowns.
  - `apagón eléctrico` [es] — Spanish for electrical blackout, not a telecom or internet shutdown.
  - `panne de réseau` [fr] — French for generic network failure, often technical/accidental rather than a deliberate shutdown.

### `gender-violence-rights`

- existing lexicon size: 18
- vocab mining proposed: 15 positive, 5 negative
- terms to add (high-confidence, not yet in lexicon): 11
  - `violência doméstica` [pt] conf=0.95 — Portuguese term for domestic violence, strongly tied to gender-violence reporting.
  - `violência contra a mulher` [pt] conf=0.97 — Direct Portuguese phrase meaning violence against women, unambiguously on-topic.
  - `violenza di genere` [it] conf=0.96 — Italian equivalent of gender-based violence, primary subject indicator in Italian headlines.
  - `femminicidio` [it] conf=0.96 — Italian term for femicide, directly signals gender-violence topic.
  - `violences conjugales` [fr] conf=0.95 — French phrase for spousal/domestic violence, strongly on-topic in French news.
  - `féminicide` [fr] conf=0.97 — French term for femicide, unambiguously signals gender-violence reporting.
  - `häusliche gewalt` [de] conf=0.95 — German phrase for domestic violence, primary indicator of this topic in German headlines.
  - `geschlechtsbezogene gewalt` [de] conf=0.94 — German phrase for gender-based violence, directly on-topic.
  - `domestic abuse conviction` [en] conf=0.93 — Specific English phrase tying legal outcomes to domestic/gender violence cases.
  - `femicide rate` [en] conf=0.95 — English phrase about femicide statistics, directly on-topic.
  - `restraining order domestic` [en] conf=0.88 — Signals domestic violence legal proceedings in English headlines.
- negative monitors (5):
  - `gender pay gap` [en] — Relates to economic inequality, not violence or rights abuses; would false-positive on gender topic.
  - `domestic policy` [en] — 'Domestic' here means national/internal policy, not domestic violence.
  - `violencia callejera` [es] — Refers to street crime in general, not specifically gender-based violence.
  - `droits de l'homme` [fr] — Means 'human rights' broadly, not specifically gender violence or women's rights.
  - `gewalt im sport` [de] — Refers to violence in sports contexts, not gender-based violence.
