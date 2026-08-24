# Atlas English style — ASD-STE100, adapted (directiva de Pedro, 2026-08-24)

**Rule of the house**: all reader-facing English in Atlas follows Simplified
Technical English (ASD-STE100), adapted for a news product. The product says
"measured, not editorialized" — the language must be as controlled as the
numbers. This document is the reference for ALL new copy (UI, captions,
share posts, auth pages, Landing) and the target for the migration of
existing copy.

## 1 · Core rules (from STE, kept as-is)

1. One sentence = one idea. Maximum 20 words per sentence (25 for
   descriptive text).
2. Active voice. "Atlas measures the coverage", never "the coverage is
   measured by Atlas".
3. Simple tenses only: present, past, future. No perfect tenses where a
   simple tense works.
4. One word = one meaning, one meaning = one word. No synonym drift (see
   the term table).
5. No idioms, no metaphors, no marketing words (seamless, robust,
   leverage, insights, empower).
6. Noun clusters: maximum 3 nouns together.
7. Instructions use the imperative: "Copy the caption." — one instruction
   per sentence.
8. Use articles (a, the) explicitly. Do not drop them for style.
9. Warnings and empty states state the condition first, then the action:
   "Clipboard blocked — select and copy the caption below."

## 2 · House rules (Atlas additions to STE)

- Every number states its base and window ("48 signals · latest pass
  Aug 23, 7d window"). A number without a base does not print.
- Honest absence: if a field is not measured, the sentence does not exist.
  Never write around a missing number.
- State media is always named: "state media". Never "official sources",
  never unlabeled.
- Uncertainty is declared with the measured word: "unverified", "partial",
  "below the bar" — never softened ("may", "possibly") and never hidden.

## 3 · Term table (one concept, one word — reader surfaces)

| concept | approved | banned variants |
|---|---|---|
| una historia agrupada | story | thread, topic, narrative (solo en superficies de analista/console donde ya son contrato) |
| una fila de datos de prensa | signal | article, item, mention |
| evidencia citable | receipt | proof, evidence sample (en prosa) |
| medio emisor | outlet | publisher, source (source = solo en "sources" como conteo de outlets, con base declarada) |
| medido por el motor | measured | detected, computed, calculated |
| pasó el gate | verified | confirmed, validated |
| prensa estatal | state media | government media, official press |
| lo que falta | gap / what is missing | blind spot, silence |
| la edición diaria | edition | issue, daily, digest |
| sellado | sealed | frozen, locked (frozen se reserva para snapshots técnicos) |

## 4 · Scope and rollout

- **Applies now**: all NEW English copy. The LinkedIn kit v2 caption
  generator MUST produce STE (spec de campaña, pieza A).
- **Migration order**: (1) kit/share captions + standfirst del Brief +
  auth pages + Landing CTA (hecho en el pase 2026-08-24); (2) Brief
  completo (empty states, banners, hints); (3) console L2 (chips,
  tooltips, guías); (4) Docs.
- **Does not apply**: identifiers de código, comentarios, docs internos en
  español, y los artefactos de research.
- Test de aceptación por superficie: cada string nueva pasa un checklist
  (≤20 palabras/frase, voz activa, términos de la tabla, base declarada).

## 5 · Example (before → after)

- Before: "Most news products tell you what to think. I've been building
  one that tells you what's actually being covered — and what isn't."
- After (STE): "Most news feeds give you opinions. Atlas gives you
  measurements. Atlas shows what the world's press covers — and what it
  does not cover."
