# Atlas V2 Batch 01 Human Review Packet

This packet is for human review/adjudication. Assistant-pilot labels are
suggestions only; they are not paper-grade gold labels until reviewed.

## Review Rules

- Judge whether the assigned Atlas topic is supported by the headline evidence.
- Prefer precise child-thread labels when the row is specific.
- Mark broad but relevant context as `parent_thread` or `context_signal`.
- Mark unsupported or misleading rows as `noise` or `incorrect`.
- Keep reviewer notes short and evidence-based.

## Rows

## 1. Signal 4510843

**Headline:** Farmers harvest hope through community Agribusiness advisors

| Field | Value |
|---|---|
| Assigned topic | Agriculture and crop risk |
| Topic slug | `agriculture-crop-risk` |
| Country | `MW` |
| Source | malawi24.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["harvest", "farmers"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=2; theme=1; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: parent_thread
- `evidence_role`: background
- `error_type`: scope_mismatch
- `parent_thread`: agriculture-development
- `child_thread`: -
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: agriculture development/support, not direct crop-risk evidence.

### Reviewer Adjudication

- `accept_assistant_label`: false
- `reviewer_decision`: incorrect
- `reviewer_scope`: child_thread
- `reviewer_evidence_role`: background
- `reviewer_error_type`: substring_noise
- `reviewer_parent_thread`: Community advisory , community, agriculture, agriculture community. agriculture bussines
- `reviewer_child_thread`: -
- `reviewer_supported_questions`: related_thread
- `reviewer_notes`:  headline more inclined towards the business side of things, more than the farmer's, even though the farmer sector is mentioned.


## 2. Signal 4617019

**Headline:** Farmers did not get much help from 2026 Legislature

| Field | Value |
|---|---|
| Assigned topic | Agriculture and crop risk |
| Topic slug | `agriculture-crop-risk` |
| Country | `US` |
| Source | willmarradio.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["farmers"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: parent_thread
- `evidence_role`: reaction
- `error_type`: -
- `parent_thread`: farmer-policy-support
- `child_thread`: -
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: policy support complaint can support an agriculture stress parent thread.

### Reviewer Adjudication

- `accept_assistant_label`:false
- `reviewer_decision`: correct
- `reviewer_scope`: parent_thread
- `reviewer_evidence_role`: reaction
- `reviewer_error_type`: -
- `reviewer_parent_thread`: -
- `reviewer_child_thread`: farmer-policy-support
- `reviewer_supported_questions`: evidence_support
- `reviewer_notes`:


## 3. Signal 4498053

**Headline:** &#xC30;&#xC3E;&#xC37;&#xC4D;&#xC1F;&#xC4D;&#xC30;&#xC02;&#xC32;&#xC4B; &#xC07;&#xC2C;&#xC4D;&#xC2C;&#xC02;&#xC26;&#xC3F; &#xC2A;&#xC21;&#xC41;&#xC24;&#xC41;&#xC28;&#xC4D;&#xC28; &#xC30;&#xC48;&#xC24;&#xC41;&#xC32;&#xC41; : &#xC0E;&#xC02;&#xC2A;&#xC40; &#xC15;&#xC4A;&#xC02;&#xC21;&#xC3E; &#xC35;&#xC3F;&#xC36;&#xC4D;&#xC35;&#xC47;&#xC36;&#xC4D;&#xC35;&#xC30;&#xC4D; &#xC30;&#xC46;&#xC21;&#xC4D;&#xC21;&#xC3F; | BJP Slams Telangana Congress Over Paddy Procurement Crisis, Konda Vishweshwar Reddy Announces Farmers Protest Yatra VVNP

| Field | Value |
|---|---|
| Assigned topic | Agriculture and crop risk |
| Topic slug | `agriculture-crop-risk` |
| Country | `IN` |
| Source | andhrajyothy.com |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["farmers"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: primary_event
- `error_type`: -
- `parent_thread`: agriculture-procurement-pressure
- `child_thread`: telangana-paddy-procurement-farmer-protest
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: visible English text indicates paddy procurement crisis and farmer protest.

### Reviewer Adjudication

- `accept_assistant_label`: false
- `reviewer_decision`: unclear
- `reviewer_scope`: context_signal
- `reviewer_evidence_role`: reaction, background
- `reviewer_error_type`: primary_context_mismatch
- `reviewer_parent_thread`: Indian congress , farmer protest, agriculture-crop-risk
- `reviewer_child_thread`:  telangana-paddy-procurement-farmer-protest
- `reviewer_supported_questions`: where_concentrated, evidence_support
- `reviewer_notes`: matching only one word cannot determine the outcome. It doesn't give enough context.


## 4. Signal 4582545

**Headline:** Fuel, fertilizer, and forex are the biggest challenges, says FM Sitharaman

| Field | Value |
|---|---|
| Assigned topic | Agriculture and crop risk |
| Topic slug | `agriculture-crop-risk` |
| Country | `IN` |
| Source | calcuttanews.net |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["fertilizer"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: context_signal
- `evidence_role`: analysis
- `error_type`: -
- `parent_thread`: agriculture-input-cost-pressure
- `child_thread`: -
- `supported_questions`: why_moving, related_thread
- `notes`: Assistant pilot label: fertilizer/fuel/forex challenges are agriculture input-cost context.

### Reviewer Adjudication

- `accept_assistant_label`: false
- `reviewer_decision`: incorrect
- `reviewer_scope`: context_signal, entity_thread
- `reviewer_evidence_role`: analysis, primary_event
- `reviewer_error_type`: primary_context_mismatch
- `reviewer_parent_thread`: Indian Finance Ministery, agriculture , oil and gas, foreing exchange
- `reviewer_child_thread`: Nirmala Sitharaman
- `reviewer_supported_questions`:related_thread
- `reviewer_notes`: There's a mismatch on acronyms and contractions. For instance, in this case, FN refers to Finance Minister, and Forex refers to Foreign Exchange.


## 5. Signal 4494624

**Headline:** Esplanade Gersik weekly farmers market should be revived, says deputy minister

| Field | Value |
|---|---|
| Assigned topic | Agriculture and crop risk |
| Topic slug | `agriculture-crop-risk` |
| Country | `MY` |
| Source | theborneopost.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.7` |
| Matched terms | `["farmers"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=1; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: parent_thread
- `evidence_role`: background
- `error_type`: scope_mismatch
- `parent_thread`: local-farmers-market
- `child_thread`: -
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: farmers market is agriculture-adjacent but not crop-risk/stress evidence.

### Reviewer Adjudication

- `accept_assistant_label`: false
- `reviewer_decision`: incorrect
- `reviewer_scope`: child_thread
- `reviewer_evidence_role`: reaction, background
- `reviewer_error_type`: scope_mismatch
- `reviewer_parent_thread`: local-farmers-market
- `reviewer_child_thread`: -
- `reviewer_supported_questions`: related_thread
- `reviewer_notes`: farmers market is agriculture-adjacent but not crop-risk/stress evidence.


## 6. Signal 4510678

**Headline:** How Smart Irrigation in Morocco is Changing Agriculture

| Field | Value |
|---|---|
| Assigned topic | Agriculture and crop risk |
| Topic slug | `agriculture-crop-risk` |
| Country | `MA` |
| Source | borgenproject.org |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: context_signal
- `evidence_role`: background
- `error_type`: -
- `parent_thread`: agriculture-water-adaptation
- `child_thread`: morocco-smart-irrigation
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: irrigation is relevant agriculture adaptation context, not an acute event.

### Reviewer Adjudication

- `accept_assistant_label`: false
- `reviewer_decision`: correct
- `reviewer_scope`: child_thread
- `reviewer_evidence_role`: background
- `reviewer_error_type`: -
- `reviewer_parent_thread`: agriculture tecnology
- `reviewer_child_thread`: smart irrigation
- `reviewer_supported_questions`:related_thread , evidence_support
- `reviewer_notes`:


## 7. Signal 4492910

**Headline:** Why Farmer Governor Mohammed Umaru Bago's Track Record Justifies a Second Term -By Abdulfatah Adam Suleja

| Field | Value |
|---|---|
| Assigned topic | Agriculture and crop risk |
| Topic slug | `agriculture-crop-risk` |
| Country | `NG` |
| Source | opinionnigeria.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: noise
- `evidence_role`: not_evidence
- `error_type`: off_topic
- `parent_thread`: -
- `child_thread`: -
- `supported_questions`: -
- `notes`: Assistant pilot label: political opinion about a governor, not crop-risk evidence.

### Reviewer Adjudication

- `accept_assistant_label`: false
- `reviewer_decision`: incorrect
- `reviewer_scope`: context_signal
- `reviewer_evidence_role`: analysis
- `reviewer_error_type`: primary_context_mismatch
- `reviewer_parent_thread`: NG elections, farming and agriculture
- `reviewer_child_thread`: Mohammed Umaru Bago
- `reviewer_supported_questions`: evidence_support, related_thread
- `reviewer_notes`: Can a person be a thread? Even though farming is mentioned, farming is not what's driving this headline


## 8. Signal 4522013

**Headline:** RESTORING MANGROVES, SUSTAINING COASTAL LIVELIHOODS &#x2013; Ministry of Defence &#x2013; Kenya

| Field | Value |
|---|---|
| Assigned topic | Agriculture and crop risk |
| Topic slug | `agriculture-crop-risk` |
| Country | `KE` |
| Source | mod.go.ke |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: noise
- `evidence_role`: not_evidence
- `error_type`: off_topic
- `parent_thread`: -
- `child_thread`: -
- `supported_questions`: -
- `notes`: Assistant pilot label: mangrove/coastal livelihoods item is environmental, not agriculture crop-risk evidence.

### Reviewer Adjudication

- `accept_assistant_label`: false
- `reviewer_decision`: incorrect
- `reviewer_scope`: child_thread, context_signal
- `reviewer_evidence_role`:  primary_event
- `reviewer_error_type`: off_topic
- `reviewer_parent_thread`: kenya ministry of defence, enviorment, sutainability
- `reviewer_child_thread`: -
- `reviewer_supported_questions`: related_thread
- `reviewer_notes`: mangrove/coastal livelihoods item is environmental, not agriculture crop-risk evidence.


## 9. Signal 4510751

**Headline:** The Threat this Year of the El Ni&#xF1;o Climate Phenomenon

| Field | Value |
|---|---|
| Assigned topic | Agriculture and crop risk |
| Topic slug | `agriculture-crop-risk` |
| Country | `CU` |
| Source | havanatimes.org |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: context_signal
- `evidence_role`: background
- `error_type`: -
- `parent_thread`: el-nino-agriculture-climate-risk
- `child_thread`: -
- `supported_questions`: why_moving, related_thread
- `notes`: Assistant pilot label: El Nino threat is relevant climate-risk context for agriculture/crops.

### Reviewer Adjudication

- `accept_assistant_label`: false
- `reviewer_decision`: incorrect
- `reviewer_scope`: parent thread
- `reviewer_evidence_role`: primary_event, analysis
- `reviewer_error_type`: off_topic
- `reviewer_parent_thread`: climate risk
- `reviewer_child_thread`: -
- `reviewer_supported_questions`: evidence_support, why_moving
- `reviewer_notes`:The headline is talking about climate phenomena, not agriculture and crop risk, even though they could be related. Climate phenomena could impact the crops, but it's not implied in the headline.


## 10. Signal 4481387

**Headline:** Missile attacks on Ukraine demonstrate Putin's 'weakness', Cooper says

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `RU` |
| Source | basingstokegazette.co.uk |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["missile attack", "missile attacks"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=2; theme=1; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: analysis
- `error_type`: -
- `parent_thread`: russia-ukraine-war-escalation
- `child_thread`: ukraine-missile-attacks
- `supported_questions`: where_concentrated, evidence_support, related_thread
- `notes`: Assistant pilot label: missile attacks on Ukraine support armed conflict escalation.

### Reviewer Adjudication

- `accept_assistant_label`: true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 11. Signal 4598592

**Headline:** Eyal Zamir calls to strike Beirut over Hezbollah's drone attacks

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `IL` |
| Source | jpost.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["drone attack", "drone attacks"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=2; theme=1; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: reaction
- `error_type`: -
- `parent_thread`: israel-hezbollah-escalation
- `child_thread`: hezbollah-drone-attacks-beirut-strike-calls
- `supported_questions`: what_changed, related_thread, evidence_support
- `notes`: Assistant pilot label: call to strike Beirut in response to drone attacks supports escalation thread.

### Reviewer Adjudication

- `accept_assistant_label`: true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 12. Signal 4480654

**Headline:** Missile attacks on Ukraine demonstrate Putin's 'weakness', Cooper says

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `UA` |
| Source | thetelegraphandargus.co.uk |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["missile attack", "missile attacks"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=2; theme=1; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: analysis
- `error_type`: -
- `parent_thread`: russia-ukraine-war-escalation
- `child_thread`: ukraine-missile-attacks
- `supported_questions`: where_concentrated, evidence_support, related_thread
- `notes`: Assistant pilot label: duplicate missile-attacks row supports Ukraine conflict escalation.

### Reviewer Adjudication

- `accept_assistant_label`: true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 13. Signal 4474418

**Headline:** Parents and infant killed in Israeli airstrike in Gaza

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `IL` |
| Source | wn.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["airstrike"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=2; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: primary_event
- `error_type`: -
- `parent_thread`: gaza-war-civilian-casualties
- `child_thread`: israeli-airstrike-gaza-family-killed
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: civilian deaths in airstrike are direct armed-conflict evidence.

### Reviewer Adjudication

- `accept_assistant_label`: true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 14. Signal 4505201

**Headline:** DR Congo Ebola cases rise amid distrust, armed conflict zone

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `CD` |
| Source | wyomingpublicmedia.org |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["armed conflict"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: context_signal
- `evidence_role`: background
- `error_type`: primary_context_mismatch
- `parent_thread`: drc-ebola-outbreak
- `child_thread`: -
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: primary story is Ebola; armed conflict is context.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 15. Signal 4498744

**Headline:** Cuatro muertos y casi 100 heridos en un bombardeo ruso a Ucrania

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `RU` |
| Source | heraldo.es |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["bombardeo"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: primary_event
- `error_type`: -
- `parent_thread`: russia-ukraine-war-escalation
- `child_thread`: russian-bombardment-ukraine-casualties
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: bombing with casualties is direct conflict evidence.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 16. Signal 4496783

**Headline:** Russia pounds Kyiv in powerful drone and missile attack

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `UA` |
| Source | knpr.org |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.7` |
| Matched terms | `["missile attack"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=1; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: primary_event
- `error_type`: -
- `parent_thread`: russia-ukraine-war-escalation
- `child_thread`: kyiv-drone-missile-attack
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: drone/missile attack on Kyiv is direct conflict evidence.

### Reviewer Adjudication

- `accept_assistant_label`: true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 17. Signal 4606349

**Headline:** 3 AIADMK MLAs' resignations accepted while EPS alleges 'horse-trading' by Vijay's TVK: What next for the rebels?

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `IN` |
| Source | hindustantimes.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.7` |
| Matched terms | `["rebels"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=1; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: noise
- `evidence_role`: not_evidence
- `error_type`: substring_noise
- `parent_thread`: -
- `child_thread`: -
- `supported_questions`: -
- `notes`: Assistant pilot label: political rebel usage, not armed conflict.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 18. Signal 4495116

**Headline:** As&#xED; suena 'Shine', el nuevo &#xE1;lbum de Fito P&#xE1;ez

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `IT` |
| Source | diariodelsur.com.co |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `theme_high_conf` |
| Confidence | `0.75` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=4; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: noise
- `evidence_role`: not_evidence
- `error_type`: off_topic
- `parent_thread`: -
- `child_thread`: -
- `supported_questions`: -
- `notes`: Assistant pilot label: music/album story, not armed conflict.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 19. Signal 4582736

**Headline:** WATCH: Four Hezbollah terrorists killed in IDF strikes

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `IL` |
| Source | clevelandjewishnews.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `theme_high_conf` |
| Confidence | `0.75` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=4; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: primary_event
- `error_type`: -
- `parent_thread`: israel-hezbollah-escalation
- `child_thread`: idf-strikes-kill-hezbollah-members
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: IDF strike killing Hezbollah members is direct conflict evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`: true
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 20. Signal 4479742

**Headline:** &#x412;&#x456;&#x439;&#x43D;&#x430; &#x432; &#x423;&#x43A;&#x440;&#x430;&#x457;&#x43D;&#x456; - &#x423;&#x434;&#x430;&#x440; &#x43F;&#x43E; &#x41A;&#x438;&#x454;&#x432;&#x443; &#x43F;&#x43E;&#x448;&#x43A;&#x43E;&#x434;&#x438;&#x432; &#x436;&#x438;&#x442;&#x43B;&#x43E; &#x43F;&#x43E;&#x441;&#x43B;&#x430; &#x410;&#x43B;&#x431;&#x430;&#x43D;&#x456;&#x457;

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `UA` |
| Source | unian.ua |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `theme_high_conf` |
| Confidence | `0.75` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=4; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: primary_event
- `error_type`: -
- `parent_thread`: russia-ukraine-war-escalation
- `child_thread`: kyiv-strike-damages-diplomatic-housing
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: visible translated fragments indicate war/strike on Kyiv damage.

### Reviewer Adjudication

- `accept_assistant_label`: true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 21. Signal 4493319

**Headline:** &#x5EA;&#x5D9;&#x5E2;&#x5D5;&#x5D3; &#x5D3;&#x5E8;&#x5DE;&#x5D8;&#x5D9; &#x5DE;&#x5D4;&#x5DC;&#x5D7;&#x5D9;&#x5DE;&#x5D4; &#x5D1;&#x5DC;&#x5D1;&#x5E0;&#x5D5;&#x5DF;. &#x5E6;&#x5E4;&#x5D5;

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `LS` |
| Source | srugim.co.il |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `theme_high_conf` |
| Confidence | `0.75` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=4; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: primary_event
- `error_type`: -
- `parent_thread`: israel-hezbollah-escalation
- `child_thread`: lebanon-fighting-footage
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: visible Hebrew fragments indicate fighting in Lebanon.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 22. Signal 4581717

**Headline:** No final US-Iran deal yet, Tehran says after talks

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `IR` |
| Source | news.az |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: context_signal
- `evidence_role`: background
- `error_type`: primary_context_mismatch
- `parent_thread`: us-iran-diplomatic-pressure
- `child_thread`: -
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: diplomacy talks, not direct armed escalation evidence.

### Reviewer Adjudication

- `accept_assistant_label`: true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 23. Signal 4598700

**Headline:** Dialogue, negotiation right path for Iran situation: foreign ministry-Xinhua

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `CN` |
| Source | english.news.cn |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: context_signal
- `evidence_role`: reaction
- `error_type`: primary_context_mismatch
- `parent_thread`: iran-diplomatic-pressure
- `child_thread`: -
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: negotiation/diplomacy framing, not direct armed escalation evidence.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 24. Signal 4531517

**Headline:** "BLA is taking up arms to fight against Pak," says Defence Expert

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `PK` |
| Source | pakistantelegraph.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: analysis
- `error_type`: -
- `parent_thread`: balochistan-insurgency-pakistan
- `child_thread`: bla-armed-struggle-framing
- `supported_questions`: related_thread, evidence_support
- `notes`: Assistant pilot label: taking up arms against Pakistan supports armed-conflict thread, though analytical quote.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 25. Signal 4603780

**Headline:** &#x39C;&#x3AC;&#x3C7;&#x3B7; &#x3B5;&#x3BE;&#x3BF;&#x3C5;&#x3C3;&#x3AF;&#x3B1;&#x3C2; &#x3C3;&#x3C4;&#x3B1; &#x3B8;&#x3B1;&#x3BB;&#x3AC;&#x3C3;&#x3C3;&#x3B9;&#x3B1; &#x3C0;&#x3B5;&#x3C1;&#x3AC;&#x3C3;&#x3BC;&#x3B1;&#x3C4;&#x3B1; &#x3C4;&#x3BF;&#x3C5; &#x3C0;&#x3BB;&#x3B1;&#x3BD;&#x3AE;&#x3C4;&#x3B7;

| Field | Value |
|---|---|
| Assigned topic | Armed conflict escalation |
| Topic slug | `armed-conflict-escalation` |
| Country | `CN` |
| Source | protagon.gr |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=6` |

### Assistant-Pilot Suggestion

- `decision`: unclear
- `scope`: -
- `evidence_role`: -
- `error_type`: insufficient_context
- `parent_thread`: -
- `child_thread`: -
- `supported_questions`: -
- `notes`: Assistant pilot label: translated fragments suggest power struggle over sea passages, but not enough to confirm armed conflict.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 26. Signal 4505533

**Headline:** Impeachment raising PH risks &#x2013; BMI analysts

| Field | Value |
|---|---|
| Assigned topic | Constitutional or institutional crisis |
| Topic slug | `constitutional-institutional-crisis` |
| Country | `RP` |
| Source | manilatimes.net |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.75` |
| Matched terms | `["impeachment", "impeach"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=2; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: parent_thread
- `evidence_role`: analysis
- `error_type`: -
- `parent_thread`: philippines-impeachment-risk
- `child_thread`: -
- `supported_questions`: why_moving, related_thread
- `notes`: Assistant pilot label: impeachment risk supports institutional crisis parent thread.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 27. Signal 4510419

**Headline:** Adiong: No to online participation of Dela Rosa in VP Sara's impeachment trial

| Field | Value |
|---|---|
| Assigned topic | Constitutional or institutional crisis |
| Topic slug | `constitutional-institutional-crisis` |
| Country | `RP` |
| Source | mindanews.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["impeachment", "impeach"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=2; theme=1; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: followup
- `error_type`: -
- `parent_thread`: philippines-impeachment-crisis
- `child_thread`: vp-sara-impeachment-trial-process
- `supported_questions`: what_changed, evidence_support
- `notes`: Assistant pilot label: procedural dispute in impeachment trial supports institutional crisis.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 28. Signal 4512261

**Headline:** Impeachment Hero and Senate Candidate Alex Vindman Endorses Run Everywhere Project

| Field | Value |
|---|---|
| Assigned topic | Constitutional or institutional crisis |
| Topic slug | `constitutional-institutional-crisis` |
| Country | `US` |
| Source | dailykos.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.75` |
| Matched terms | `["impeachment", "impeach"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=2; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: context_signal
- `evidence_role`: background
- `error_type`: primary_context_mismatch
- `parent_thread`: us-impeachment-political-identity
- `child_thread`: -
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: impeachment is historical identity/context, not a current institutional crisis.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 29. Signal 4550146

**Headline:** MPs scrabble for interim rules to avoid Ramaphosa impeachment inquiry delay

| Field | Value |
|---|---|
| Assigned topic | Constitutional or institutional crisis |
| Topic slug | `constitutional-institutional-crisis` |
| Country | `ZA` |
| Source | timeslive.co.za |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.75` |
| Matched terms | `["impeachment", "impeach"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=2; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: followup
- `error_type`: -
- `parent_thread`: south-africa-impeachment-process
- `child_thread`: ramaphosa-impeachment-inquiry-rules
- `supported_questions`: what_changed, evidence_support
- `notes`: Assistant pilot label: parliamentary rules around impeachment inquiry support institutional crisis.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 30. Signal 4528307

**Headline:** California chemical tank has cracked causing state of emergency, thousands to evacuate

| Field | Value |
|---|---|
| Assigned topic | Constitutional or institutional crisis |
| Topic slug | `constitutional-institutional-crisis` |
| Country | `US` |
| Source | kccu.org |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["state of emergency"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: child_thread
- `evidence_role`: primary_event
- `error_type`: primary_context_mismatch
- `parent_thread`: industrial-chemical-emergency
- `child_thread`: california-chemical-tank-evacuation
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: state of emergency is disaster/industrial emergency, not constitutional crisis.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 31. Signal 4483495

**Headline:** Turkish riot police enter opposition headquarters to evict ousted leadership

| Field | Value |
|---|---|
| Assigned topic | Constitutional or institutional crisis |
| Topic slug | `constitutional-institutional-crisis` |
| Country | `TR` |
| Source | thehindu.com |
| Source family | `independent` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["ousted"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: primary_event
- `error_type`: -
- `parent_thread`: turkey-opposition-institutional-crisis
- `child_thread`: riot-police-evict-ousted-opposition-leadership
- `supported_questions`: where_concentrated, evidence_support, what_changed
- `notes`: Assistant pilot label: riot police entering opposition HQ to evict leadership supports institutional crisis.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 32. Signal 4521953

**Headline:** California chemical tank has cracked causing state of emergency, thousands to evacuate

| Field | Value |
|---|---|
| Assigned topic | Constitutional or institutional crisis |
| Topic slug | `constitutional-institutional-crisis` |
| Country | `US` |
| Source | kpbs.org |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["state of emergency"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: child_thread
- `evidence_role`: primary_event
- `error_type`: primary_context_mismatch
- `parent_thread`: industrial-chemical-emergency
- `child_thread`: california-chemical-tank-evacuation
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: duplicate disaster emergency row, not constitutional crisis.

### Reviewer Adjudication

- `accept_assistant_label`:true
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:

