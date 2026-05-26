# Atlas V2 Batch 02 Human Review Packet

This packet is for human review/adjudication. Assistant-pilot labels are
suggestions only; they are not paper-grade gold labels until reviewed.

## Review Rules

- Judge whether the assigned Atlas topic is supported by the headline evidence.
- Prefer precise child-thread labels when the row is specific.
- Mark broad but relevant context as `parent_thread` or `context_signal`.
- Mark unsupported or misleading rows as `noise` or `incorrect`.
- Keep reviewer notes short and evidence-based.

## Rows

## 1. Signal 4486065

**Headline:** Trump now clashing with a Supreme Court that usually gives him what he wants

| Field | Value |
|---|---|
| Assigned topic | Constitutional or institutional crisis |
| Topic slug | `constitutional-institutional-crisis` |
| Country | `US` |
| Source | alternet.org |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["supreme court"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: parent_thread
- `evidence_role`: analysis
- `error_type`: -
- `parent_thread`: us-executive-judiciary-institutional-friction
- `child_thread`: trump-supreme-court-friction
- `supported_questions`: related_thread, evidence_support
- `notes`: Assistant pilot label: Supreme Court/executive friction can support a US institutional crisis parent thread.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 2. Signal 4543811

**Headline:** Peter Murrell expected in court on embezzlement charges

| Field | Value |
|---|---|
| Assigned topic | Corruption investigation |
| Topic slug | `corruption-investigation` |
| Country | `GB` |
| Source | cotswoldjournal.co.uk |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["embezzlement"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=2; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: followup
- `error_type`: -
- `parent_thread`: scottish-political-corruption-investigation
- `child_thread`: peter-murrell-embezzlement-court-case
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: court appearance on embezzlement charges is direct corruption-investigation evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 3. Signal 4543809

**Headline:** Peter Murrell expected in court on embezzlement charges

| Field | Value |
|---|---|
| Assigned topic | Corruption investigation |
| Topic slug | `corruption-investigation` |
| Country | `GB` |
| Source | richmondandtwickenhamtimes.co.uk |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["embezzlement"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=2; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: followup
- `error_type`: -
- `parent_thread`: scottish-political-corruption-investigation
- `child_thread`: peter-murrell-embezzlement-court-case
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: duplicated/syndicated court appearance item remains direct corruption-investigation evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 4. Signal 4535658

**Headline:** Peter Murrell expected in court on embezzlement charges

| Field | Value |
|---|---|
| Assigned topic | Corruption investigation |
| Topic slug | `corruption-investigation` |
| Country | `GB` |
| Source | cravenherald.co.uk |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["embezzlement"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=2; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: followup
- `error_type`: -
- `parent_thread`: scottish-political-corruption-investigation
- `child_thread`: peter-murrell-embezzlement-court-case
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: duplicated/syndicated court appearance item remains direct corruption-investigation evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 5. Signal 4544053

**Headline:** Peter Murrell expected in court on embezzlement charges

| Field | Value |
|---|---|
| Assigned topic | Corruption investigation |
| Topic slug | `corruption-investigation` |
| Country | `GB` |
| Source | dumbartonreporter.co.uk |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["embezzlement"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=2; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: followup
- `error_type`: -
- `parent_thread`: scottish-political-corruption-investigation
- `child_thread`: peter-murrell-embezzlement-court-case
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: duplicated/syndicated court appearance item remains direct corruption-investigation evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 6. Signal 4577853

**Headline:** Early resignation of chief rocks corruption watchdog

| Field | Value |
|---|---|
| Assigned topic | Corruption investigation |
| Topic slug | `corruption-investigation` |
| Country | `AU` |
| Source | manningrivertimes.com.au |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["corruption"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: parent_thread
- `evidence_role`: reaction
- `error_type`: -
- `parent_thread`: australia-anti-corruption-watchdog-integrity
- `child_thread`: australia-corruption-watchdog-chief-resignation
- `supported_questions`: what_changed, related_thread
- `notes`: Assistant pilot label: anti-corruption watchdog leadership resignation is governance/corruption oversight evidence, but not a specific corruption case.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 7. Signal 4554085

**Headline:** Federal anti-corruption boss resigns two years early

| Field | Value |
|---|---|
| Assigned topic | Corruption investigation |
| Topic slug | `corruption-investigation` |
| Country | `AU` |
| Source | mudgeeguardian.com.au |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["corruption"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: parent_thread
- `evidence_role`: reaction
- `error_type`: -
- `parent_thread`: australia-anti-corruption-watchdog-integrity
- `child_thread`: australia-corruption-watchdog-chief-resignation
- `supported_questions`: what_changed, related_thread
- `notes`: Assistant pilot label: early resignation of anti-corruption boss supports a watchdog-integrity parent thread.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 8. Signal 4575098

**Headline:** Early resignation of chief rocks corruption watchdog

| Field | Value |
|---|---|
| Assigned topic | Corruption investigation |
| Topic slug | `corruption-investigation` |
| Country | `AU` |
| Source | theadvocate.com.au |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["corruption"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: parent_thread
- `evidence_role`: reaction
- `error_type`: -
- `parent_thread`: australia-anti-corruption-watchdog-integrity
- `child_thread`: australia-corruption-watchdog-chief-resignation
- `supported_questions`: what_changed, related_thread
- `notes`: Assistant pilot label: duplicated/syndicated watchdog resignation item supports corruption oversight, not a direct corruption allegation.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 9. Signal 4556366

**Headline:** Federal anti-corruption boss resigns two years early

| Field | Value |
|---|---|
| Assigned topic | Corruption investigation |
| Topic slug | `corruption-investigation` |
| Country | `AU` |
| Source | examiner.com.au |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["corruption"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: parent_thread
- `evidence_role`: reaction
- `error_type`: -
- `parent_thread`: australia-anti-corruption-watchdog-integrity
- `child_thread`: australia-corruption-watchdog-chief-resignation
- `supported_questions`: what_changed, related_thread
- `notes`: Assistant pilot label: duplicated/syndicated watchdog resignation item supports corruption oversight, not a direct corruption allegation.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 10. Signal 4614976

**Headline:** "Plag&#xEB; q&#xEB; na i ka l&#xEB;n&#xEB; korrupsioni", Kurti: Byroja p&#xEB;r Konfiskimin e Pasuris&#xEB; do ta ndreq shum&#xEB; Kosov&#xEB;n &#x2013; Lajmi.net

| Field | Value |
|---|---|
| Assigned topic | Corruption investigation |
| Topic slug | `corruption-investigation` |
| Country | `KV` |
| Source | lajmi.net |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: parent_thread
- `evidence_role`: reaction
- `error_type`: -
- `parent_thread`: kosovo-anti-corruption-reform
- `child_thread`: kosovo-asset-confiscation-bureau
- `supported_questions`: why_moving, related_thread
- `notes`: Assistant pilot label: Kurti/asset-confiscation bureau item is anti-corruption reform evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 11. Signal 4607603

**Headline:** Capturan en zona 1 a presunto extorsionista con nueve &#xF3;rdenes de aprehensi&#xF3;n

| Field | Value |
|---|---|
| Assigned topic | Corruption investigation |
| Topic slug | `corruption-investigation` |
| Country | `GT` |
| Source | prensalibre.com |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: noise
- `evidence_role`: not_evidence
- `error_type`: off_topic
- `parent_thread`: guatemala-extortion-arrest
- `child_thread`: -
- `supported_questions`: -
- `notes`: Assistant pilot label: extortion arrest is criminal enforcement, not corruption investigation evidence from the headline.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 12. Signal 4614982

**Headline:** Kurti paralajm&#xEB;ron "goditjen e madhe" ndaj korrupsionit: Byroja p&#xEB;r konfiskimin e pasuris&#xEB;, prioritet i mandatit t&#xEB; ri

| Field | Value |
|---|---|
| Assigned topic | Corruption investigation |
| Topic slug | `corruption-investigation` |
| Country | `KV` |
| Source | botasot.info |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: parent_thread
- `evidence_role`: primary_event
- `error_type`: -
- `parent_thread`: kosovo-anti-corruption-reform
- `child_thread`: kosovo-asset-confiscation-bureau
- `supported_questions`: why_moving, evidence_support, related_thread
- `notes`: Assistant pilot label: anti-corruption bureau/confiscation priority is direct anti-corruption reform evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 13. Signal 4506995

**Headline:** Alleged defamation: El-Rufai's wife files N2bn suit against ICPC - Latest News In Nigeria, Nigeria News Today, Your Online Nigerian Newspaper

| Field | Value |
|---|---|
| Assigned topic | Corruption investigation |
| Topic slug | `corruption-investigation` |
| Country | `NG` |
| Source | nigerianeye.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: context_signal
- `evidence_role`: background
- `error_type`: primary_context_mismatch
- `parent_thread`: nigeria-anti-corruption-agency-litigation
- `child_thread`: el-rufai-wife-defamation-suit-against-icpc
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: ICPC is present, but the main story is defamation litigation rather than a corruption investigation.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 14. Signal 4521891

**Headline:** Sri Lanka's exchange rate dilemma: Don't blame toothless Central Bank

| Field | Value |
|---|---|
| Assigned topic | Currency and debt stress |
| Topic slug | `currency-debt-stress` |
| Country | `LK` |
| Source | ft.lk |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["central bank", "exchange rate"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=2; theme=1; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: parent_thread
- `evidence_role`: analysis
- `error_type`: -
- `parent_thread`: sri-lanka-currency-stability-pressure
- `child_thread`: sri-lanka-exchange-rate-dilemma
- `supported_questions`: why_moving, related_thread
- `notes`: Assistant pilot label: exchange-rate dilemma and central bank discussion support currency stress analysis.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 15. Signal 4574777

**Headline:** Romanian Senate backs bill requiring euro invoices to use central bank exchange rate

| Field | Value |
|---|---|
| Assigned topic | Currency and debt stress |
| Topic slug | `currency-debt-stress` |
| Country | `RO` |
| Source | romania-insider.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.75` |
| Matched terms | `["central bank", "exchange rate"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=2; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: context_signal
- `evidence_role`: background
- `error_type`: scope_mismatch
- `parent_thread`: romania-currency-invoice-policy
- `child_thread`: romania-euro-invoice-exchange-rate-bill
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: exchange-rate policy is related but not clear currency/debt stress evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 16. Signal 4521961

**Headline:** Sri Lanka's exchange rate dilemma: Don't blame toothless Central Bank

| Field | Value |
|---|---|
| Assigned topic | Currency and debt stress |
| Topic slug | `currency-debt-stress` |
| Country | `LK` |
| Source | ft.lk |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["central bank", "exchange rate"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=2; theme=1; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: parent_thread
- `evidence_role`: analysis
- `error_type`: -
- `parent_thread`: sri-lanka-currency-stability-pressure
- `child_thread`: sri-lanka-exchange-rate-dilemma
- `supported_questions`: why_moving, related_thread
- `notes`: Assistant pilot label: duplicate Sri Lanka exchange-rate dilemma item supports currency stress analysis.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 17. Signal 4479801

**Headline:** Gelombang PHK Massal, KSPI Ungkap Imbas Inflasi Harga Minyak dan Rupiah Melemah  : Okezone Economy

| Field | Value |
|---|---|
| Assigned topic | Currency and debt stress |
| Topic slug | `currency-debt-stress` |
| Country | `ID` |
| Source | okezone.com |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `lex_high_conf` |
| Confidence | `0.8` |
| Matched terms | `["rupiah"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=2; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: child_thread
- `evidence_role`: analysis
- `error_type`: -
- `parent_thread`: indonesia-currency-inflation-labor-pressure
- `child_thread`: indonesia-rupiah-oil-inflation-layoff-pressure
- `supported_questions`: why_moving, evidence_support
- `notes`: Assistant pilot label: weak rupiah, oil inflation, and layoffs connect currency pressure to economic stress.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 18. Signal 4563415

**Headline:** This must be our last IMF bailout - President Mahama

| Field | Value |
|---|---|
| Assigned topic | Currency and debt stress |
| Topic slug | `currency-debt-stress` |
| Country | `GH` |
| Source | ghanaiantimes.com.gh |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["imf bailout"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: parent_thread
- `evidence_role`: reaction
- `error_type`: -
- `parent_thread`: ghana-imf-debt-program-pressure
- `child_thread`: ghana-imf-bailout-exit-claim
- `supported_questions`: why_moving, related_thread
- `notes`: Assistant pilot label: presidential statement on IMF bailout is debt-stress/program evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 19. Signal 4552542

**Headline:** Ini Dugaan Awal Penyebab Blackout Aliran Listrik Sumatera Menurut Bareskrim Polri

| Field | Value |
|---|---|
| Assigned topic | Currency and debt stress |
| Topic slug | `currency-debt-stress` |
| Country | `ID` |
| Source | republika.co.id |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["lira"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: noise
- `evidence_role`: not_evidence
- `error_type`: substring_noise
- `parent_thread`: sumatra-electricity-blackout
- `child_thread`: -
- `supported_questions`: -
- `notes`: Assistant pilot label: lira appears to be a substring artifact in Indonesian text, not currency stress evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 20. Signal 4565835

**Headline:** La Costumbre del Poder: El valor del peso no est&#xE1; en la paridad, sino en el poder adquisitivo I/III

| Field | Value |
|---|---|
| Assigned topic | Currency and debt stress |
| Topic slug | `currency-debt-stress` |
| Country | `SE` |
| Source | almomento.mx |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["peso"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: context_signal
- `evidence_role`: analysis
- `error_type`: -
- `parent_thread`: mexico-peso-purchasing-power-pressure
- `child_thread`: peso-purchasing-power-column
- `supported_questions`: why_moving, related_thread
- `notes`: Assistant pilot label: peso purchasing-power analysis is currency-stress context, though not a direct crisis event.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 21. Signal 4525331

**Headline:** Ruth desvi&#xF3; m&#xE1;s de 900 mil pesos del ISSSTE a una cuenta ajena al instituto y ahora no podr&#xE1; ser funcionaria por al menos 10 a&#xF1;os

| Field | Value |
|---|---|
| Assigned topic | Currency and debt stress |
| Topic slug | `currency-debt-stress` |
| Country | `MX` |
| Source | elimparcial.com |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["peso"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: noise
- `evidence_role`: not_evidence
- `error_type`: primary_context_mismatch
- `parent_thread`: issste-funds-diversion-case
- `child_thread`: -
- `supported_questions`: -
- `notes`: Assistant pilot label: pesos are only an amount in an alleged diversion/corruption story, not currency stress evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 22. Signal 4576880

**Headline:** Stournaras'tan ECB'ye uyar&#x131;: A&#x15F;&#x131;r&#x131; s&#x131;k&#x131; para politikas&#x131; ekonomiyi zay&#x131;flatabilir

| Field | Value |
|---|---|
| Assigned topic | Currency and debt stress |
| Topic slug | `currency-debt-stress` |
| Country | `IR` |
| Source | sabah.com.tr |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: context_signal
- `evidence_role`: analysis
- `error_type`: -
- `parent_thread`: eurozone-monetary-tightening-growth-risk
- `child_thread`: ecb-tight-policy-growth-warning
- `supported_questions`: why_moving, related_thread
- `notes`: Assistant pilot label: ECB tight-policy warning is monetary stress context.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 23. Signal 4537928

**Headline:** &#x623;&#x631;&#x642;&#x627;&#x645; : &#x645;&#x639;&#x644;&#x648;&#x645;&#x627;&#x62A; &#x627;&#x644;&#x634;&#x631;&#x643;&#x629;  - &#x643;&#x64A;&#x627;&#x646; &#x627;&#x644;&#x633;&#x639;&#x648;&#x62F;&#x64A;&#x629;

| Field | Value |
|---|---|
| Assigned topic | Currency and debt stress |
| Topic slug | `currency-debt-stress` |
| Country | `SA` |
| Source | argaam.com |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: unclear
- `scope`: noise
- `evidence_role`: not_evidence
- `error_type`: insufficient_context
- `parent_thread`: -
- `child_thread`: -
- `supported_questions`: -
- `notes`: Assistant pilot label: headline is too thin/encoded to determine currency or debt stress.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 24. Signal 4489113

**Headline:** Fisco | 120mila pignoramenti sui conti focus su Lombardia e Lazio

| Field | Value |
|---|---|
| Assigned topic | Currency and debt stress |
| Topic slug | `currency-debt-stress` |
| Country | `IT` |
| Source | zazoom.it |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: correct
- `scope`: context_signal
- `evidence_role`: primary_event
- `error_type`: -
- `parent_thread`: italy-tax-debt-enforcement-pressure
- `child_thread`: italy-account-garnishment-tax-pressure
- `supported_questions`: where_concentrated, evidence_support
- `notes`: Assistant pilot label: account garnishments can support debt/tax enforcement pressure, though scope is narrower than sovereign stress.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 25. Signal 4564854

**Headline:** &#x420;&#x43E;&#x441;&#x442; &#x446;&#x435;&#x43D; &#x43D;&#x430; &#x43F;&#x440;&#x43E;&#x43C;&#x44B;&#x448;&#x43B;&#x435;&#x43D;&#x43D;&#x443;&#x44E; &#x43F;&#x440;&#x43E;&#x434;&#x443;&#x43A;&#x446;&#x438;&#x44E; &#x437;&#x430;&#x444;&#x438;&#x43A;&#x441;&#x438;&#x440;&#x43E;&#x432;&#x430;&#x43B;&#x438; &#x432; &#x413;&#x440;&#x443;&#x437;&#x438;&#x438;

| Field | Value |
|---|---|
| Assigned topic | Currency and debt stress |
| Topic slug | `currency-debt-stress` |
| Country | `US` |
| Source | vestikavkaza.ru |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=3` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: context_signal
- `evidence_role`: background
- `error_type`: scope_mismatch
- `parent_thread`: georgia-industrial-price-inflation
- `child_thread`: -
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: producer price growth is inflation context, not direct currency/debt stress evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 26. Signal 4566704

**Headline:** Africa's AI ambitions face critical infrastructure questions

| Field | Value |
|---|---|
| Assigned topic | Cyberattack on infrastructure |
| Topic slug | `cyberattack-infrastructure` |
| Country | `ZA` |
| Source | it-online.co.za |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["critical infrastructure"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: context_signal
- `evidence_role`: analysis
- `error_type`: primary_context_mismatch
- `parent_thread`: africa-ai-infrastructure-capacity
- `child_thread`: -
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: critical infrastructure is present, but the story is AI/infrastructure capacity, not cyberattack.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 27. Signal 4538209

**Headline:** London iPhone Theft Leads to China Threats; Hackers Stop After Apple ID Removal

| Field | Value |
|---|---|
| Assigned topic | Cyberattack on infrastructure |
| Topic slug | `cyberattack-infrastructure` |
| Country | `GB` |
| Source | bhaskar.com |
| Source family | `gdelt` |
| Source language | `xx` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.65` |
| Matched terms | `["hackers"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=0; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: noise
- `evidence_role`: not_evidence
- `error_type`: scope_mismatch
- `parent_thread`: consumer-device-cybercrime
- `child_thread`: iphone-theft-hackers-apple-id-removal
- `supported_questions`: -
- `notes`: Assistant pilot label: hackers appear in a consumer-device theft story, not infrastructure cyberattack evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 28. Signal 4610012

**Headline:** Krispy Kreme data breach lawsuit settlement claim deadline nears &#x2013; NBC Connecticut

| Field | Value |
|---|---|
| Assigned topic | Cyberattack on infrastructure |
| Topic slug | `cyberattack-infrastructure` |
| Country | `US` |
| Source | nbcconnecticut.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.7` |
| Matched terms | `["data breach"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=1; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: context_signal
- `evidence_role`: background
- `error_type`: scope_mismatch
- `parent_thread`: consumer-data-breach-litigation
- `child_thread`: krispy-kreme-data-breach-settlement
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: data breach litigation is cyber context but not infrastructure attack evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 29. Signal 4523286

**Headline:** Kash Patel's "Based Apparel" E-Commerce Website Taken Offline After Targeted Malware Cyberattack

| Field | Value |
|---|---|
| Assigned topic | Cyberattack on infrastructure |
| Topic slug | `cyberattack-infrastructure` |
| Country | `IR` |
| Source | techstory.in |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `lex_low_conf` |
| Confidence | `0.7` |
| Matched terms | `["cyberattack"]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=1; theme=1; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: child_thread
- `evidence_role`: primary_event
- `error_type`: scope_mismatch
- `parent_thread`: website-malware-attack
- `child_thread`: kash-patel-ecommerce-malware-attack
- `supported_questions`: evidence_support
- `notes`: Assistant pilot label: targeted malware attack is cyber evidence, but not infrastructure-focused.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 30. Signal 4505431

**Headline:** SEC and PNP join forces to combat online investment scams in Central Luzon

| Field | Value |
|---|---|
| Assigned topic | Cyberattack on infrastructure |
| Topic slug | `cyberattack-infrastructure` |
| Country | `RP` |
| Source | manilatimes.net |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: noise
- `evidence_role`: not_evidence
- `error_type`: off_topic
- `parent_thread`: online-investment-scam-enforcement
- `child_thread`: -
- `supported_questions`: -
- `notes`: Assistant pilot label: online investment scams are fraud enforcement, not infrastructure cyberattack.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 31. Signal 4553970

**Headline:** Sad authorities haven't learnt lesson: Supreme Court in NEET-UG Paper leak case | Legal News

| Field | Value |
|---|---|
| Assigned topic | Cyberattack on infrastructure |
| Topic slug | `cyberattack-infrastructure` |
| Country | `IN` |
| Source | indianexpress.com |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: noise
- `evidence_role`: not_evidence
- `error_type`: off_topic
- `parent_thread`: neet-paper-leak-legal-case
- `child_thread`: -
- `supported_questions`: -
- `notes`: Assistant pilot label: exam paper leak/Supreme Court item is not cyberattack infrastructure evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:


## 32. Signal 4605853

**Headline:** "We are switching you to 5G, type a command": IDBank warns about  fraud disguised as "network update"

| Field | Value |
|---|---|
| Assigned topic | Cyberattack on infrastructure |
| Topic slug | `cyberattack-infrastructure` |
| Country | `AM` |
| Source | panarmenian.net |
| Source family | `gdelt` |
| Source language | `en` |
| Sample bucket | `theme_low_conf` |
| Confidence | `0.65` |
| Matched terms | `[]` |
| Evidence formula | `theme-hint-lex-v2` |
| Lex/theme/hint counts | `lex=0; theme=2; hint=4` |

### Assistant-Pilot Suggestion

- `decision`: incorrect
- `scope`: context_signal
- `evidence_role`: reaction
- `error_type`: scope_mismatch
- `parent_thread`: banking-social-engineering-fraud
- `child_thread`: idbank-network-update-fraud-warning
- `supported_questions`: related_thread
- `notes`: Assistant pilot label: bank fraud warning is cyber/social-engineering context, not infrastructure attack evidence.

### Reviewer Adjudication

- `accept_assistant_label`:
- `reviewer_decision`:
- `reviewer_scope`:
- `reviewer_evidence_role`:
- `reviewer_error_type`:
- `reviewer_parent_thread`:
- `reviewer_child_thread`:
- `reviewer_supported_questions`:
- `reviewer_notes`:
