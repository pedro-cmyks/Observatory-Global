# Post #1 — Ceuta Migrant Crisis · borrador de FORMA (generado 2026-09-11)

**No publicar este texto.** Es la salida real del kit v2.1 contra prod el
09-11 para revisar la forma. El martes 09-15 se regenera desde el kit: los
números (73 señales, pase Sep 10) serán otros y el lede se genera sobre los
recibos de ese día. Lo que sí queda: la curación elegida (3 outlets, 3
idiomas, uno de ellos negando desde Marruecos), el formato portrait y la
pregunta de cierre.

## Curación usada (dt-18062, pool de 30)

- elpais.com (es) — "Al menos 40 tiendas de migrantes incendiadas en las Naves del Tarajal"
- aljazeera.com (en) — "Morocco denies involvement in migrant surge into Spain's Ceuta"
- yle.fi (fi) — "Espanjassa kiistellään siitä, varoitettiinko hallitusta Ceutaan saapuvista tulijoista etukäteen"

Descartados los 2 default (Houthis/ruta petrolera nos.nl; coches
autónomos shafaqna.com) — off-story, la enfermedad M1 en vivo.

## Caption (tal cual salió — hook-first, sin link)

```
At least 40 migrant shops were burned in the Naves del Tarajal, according to El País. Morocco denies involvement in the migrant surge into Spain's Ceuta, Al Jazeera reports. In Spain there is disagreement over whether the government was warned in advance about those arriving in Ceuta, according to Yle.

Measured: The sampled receipts span 11 languages; 3 of 200 sampled receipts are from state-media outlets.

Measured coverage: 73 signals (latest clustering pass Sep 10, 7d window) · 10 countries · 83 sources (distinct outlets in the sampled receipts).

Receipts — the lede above is synthesized only from these, quote-checked:
• "At least 40 migrant shops burned in the Naves del Tarajal" — elpais.com (translated from es)
• "Morocco denies involvement in migrant surge into Spain's Ceuta | Migration News" — aljazeera.com (en)
• "In Spain, there is a dispute over whether the government was warned in advance about arrivals coming to Ceuta" — yle.fi (translated from fi)

Story on Atlas: Ceuta Migrant Crisis — measurement, not opinion.

Three outlets, three languages, one border. Which account would you trust first — and what would make you change your mind?
```

1.166 caracteres. Hook visible en móvil: "At least 40 migrant shops were
burned in the Naves del Tarajal, according to El País." (85 chars).

Hashtags sugeridos (al final, ≤3): `#OSINT #MediaAnalysis #Ceuta`

## Primer comentario (arm A — post impar)

```
Read the full measured story on Atlas (free): https://observatory-global.vercel.app/app?theme=dynamic-topic-18062&entry=linkedin&utm_source=linkedin&utm_medium=organic&utm_campaign=sow-2026-w38&utm_content=dynamic-topic-18062
```

(El kit lo genera con el tag de la semana en curso — el martes saldrá
`sow-2026-w38` solo.)

## Imagen

Card **portrait 1080×1350** — botón "Download card PNG" del kit. Lleva:
masthead ATLAS · label · lede (3 frases) · MEASURED · 3 recibos con outlet,
"translated from", chip de tier · vitals · pie.

## Día 7 (09-22)

```bash
cd backend && python scripts/campaign_acquisition_report.py --days 8 --campaign sow-2026-w38
```

y llenar la fila #1 de la bitácora (`../2026-09-linkedin-calendar.md` §5)
con LinkedIn analytics + esa salida.
