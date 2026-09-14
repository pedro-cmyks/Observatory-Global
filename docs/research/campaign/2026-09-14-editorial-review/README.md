# Revisión editorial independiente — lo que saldría del kit LinkedIn (2026-09-14)

**Pedido de Pedro**: entrar a Atlas, sacar 3 temas, descargarlos, leerlos con
rigor, evaluarlos; buscar los mismos temas en internet y comparar actualidad,
ángulos y voces (múltiples lugares = la tesis de Atlas); calificar; decir
qué cambiaría.

**Método**: (1) payload prod `GET /api/v2/theme/{id}?hours=168` de 3
historias con perfil distinto → `dt-*.payload.json` + `dt-*.receipts.tsv`
(200 recibos c/u); (2) lectura del pool completo y del corte que el kit
ofrece (los 30 más recientes); (3) generación REAL del kit contra prod
(endpoint editorial + traducción + misma lógica de caption) → `kit-*.json`;
(4) tres investigaciones web independientes (agentes con WebSearch/
WebFetch, solo páginas de septiembre 2026, fuentes listadas en cada brief);
(5) contraste y nota 1-10 en seis ejes. **Lo que NO hice**: no toqué el
motor ni las etiquetas; no edité ningún lede a mano.

**Contexto que condiciona todo lo medido**: DeepSeek se quedó sin saldo el
**sáb 13-sep 07:01 UTC** (~5.000 llamadas/día, 7.600 de `typing` en 3 días).
El nocturno del 13→14 corrió sin LLM (sin court, sin relabel). Pedro cargó
$20 el 14-sep ~15:00 UTC; los ledes de abajo se regeneraron después.

---

## 0 · Veredicto en una tabla

| eje (1-10) | Ceuta (dt-18062) | Netanyahu/Gaza (dt-277) | Irán (dt-20497) |
|---|:-:|:-:|:-:|
| **Actualidad** (¿lo más fresco del mundo está?) | 6 | 3 | 5 |
| **Ángulos** (¿múltiples lugares/voces vs el mundo?) | 6 | 3 | 7 |
| **Pureza del pool del kit** (% on-story de los 30 que ofrece) | **2** (20%) | 4 (40%) | 5 (50%) |
| **Etiqueta** (¿describe lo que hay dentro HOY?) | 7 | **1** | **2** |
| **Editorial** (lede/caption: calidad + honestidad) | 5 | 4 | 6 |
| **Publicable mañana tal cual** | 4 | 1 | 3 |
| **Global** | **5.0** | **2.7** | **4.7** |

**Lectura corta**: Atlas TIENE la cobertura (en Ceuta, 104 recibos on-story
en 6 idiomas; en Irán, 30/200 recibos de prensa estatal medidos) pero **la
sirve mal en tres puntos**: (a) el corte de 30 recientes del kit está lleno
de basura de umbrella/grab-bag; (b) dos de tres etiquetas son de otra
semana (o de otro mes); (c) una traducción convirtió tiendas de campaña en
comercios y el quote gate la dejó pasar. Con curación humana y etiqueta
correcta, Ceuta e Irán son publicables y buenos; Gaza no bajo esta etiqueta.

---

## 1 · Ceuta Migrant Crisis (dt-18062)

### Qué sirve Atlas
- `currentTotal` 114 · 13 países · 6 idiomas (en 65 · es 53 · it 22 · de 17
  · id 6) · 200 recibos (35 archivados) · rango 05-sep 14:54 → **14-sep
  08:14** · `firstSeen` 01-jul · **umbrella desde anoche** (`is_umbrella`,
  sin court) · `coherence 0.44 loose / grab_bag` ("likely conflates
  unrelated stories").
- Top outlets: elpais 28 · **antaranews 19** · repubblica 17 · lavanguardia
  11 · elmundo 9 · zeit 8 · **mia.mk 8** · spiegel 5 · moroccoworldnews 5.
- **Pool del kit (30 más recientes): 6/30 on-story.** Los otros 24:
  **7 de Mundial de baloncesto femenino** (zeit/spiegel/faz/sportschau),
  6 de Trump en Irlanda (mia.mk en cirílico), 5 Houthis/Yemen (Antara),
  Culiacán, profesores italianos, Home Office UK… Al volverse umbrella, el
  pool = unión de hijos que no son Ceuta.
- **Pool completo: 104/200 on-story (52%)** y RICO: CNI desclasifica 40
  documentos · Feijóo/Vox vs Sánchez · Page "segunda gran mentira"/11-M ·
  Robles "unidad del Gobierno" · Rey + cúpula militar · colegios de El
  Príncipe ("estamos abandonados") · Marruecos rechaza/chivo expiatorio ·
  MWN "Spain fails to secure EU sanctions" · Mundial 2030 · nacionalidad
  saharaui · AfD (Von Storch) · Al Jazeera ×4 · **5 topics Ceuta distintos**
  coexisten (18062, 1508, 9903, 5004, 8438 — fragmentación de identidad).

### Salida real del kit
**A — con el pool que el kit permite hoy** (MWN, myjoyonline, 20minutos):
lede de 2 frases (1 dropeada por el gate), ambas del lado marroquí; caption
plano. **No publicable**: sin El País, sin Al Jazeera, sin política española
— los 30 recientes no los traen.

**B — curación sobre el pool completo** (El País PSOE #39 · MWN UE #19 · Al
Jazeera CNI #90), lede real (deepseek, dropped 0):

> Spain's spy agency warned of mass crossings into Ceuta before the border
> crisis, according to Al Jazeera. Spain failed to secure EU sanctions
> against Morocco over the Ceuta border entry, Morocco World News reported.
> Within the PSOE, the political handling of the Ceuta crisis has produced
> disarray, El Pais reported: "Si intentábamos salir de esta, nos hemos
> embarrado más".

Tres ángulos reales (inteligencia / UE-Marruecos / política interna). Nits:
cita en español dentro del lede inglés (el gate la exige verbatim);
"Morocco World News" atribuido sin marcar que es prensa marroquí pro-oficial
(no es state media en nuestra lista — pero SÍ es el único lado marroquí que
tenemos).

### El mundo (brief web, 45 páginas, 14-sep)
- **Corrección de marco**: el salto masivo fue **30-31 de julio** (70-80k).
  Septiembre es el *aftermath*: retornos (5.321 al 13-sep), escándalo del
  aviso del CNI, primera reacción oficial marroquí (10-sep vía MAP),
  incendio del Tarajal (10→11-sep: **42 chabolas**), segunda convocatoria
  viral para el **23-sep = elecciones marroquíes** (Gen.Z.212, 91.600
  miembros), Marlaska 14-sep 13:30: 300 expulsiones judiciales.
- **Ángulos del mundo**: política española/CNI · posición marroquí (Le360,
  Hespress, Alyaoum24, TelQuel — **unánimes en "Sebta ocupada"**) · UE/Frontex
  (Euronews 14-sep: endurecer política) · humanitario (eldiario, Il Post:
  ~20 casos de violencia sexual, 9.000 comidas/día Cruz Roja) · ultraderecha
  · soberanía (Sáhara 2022, visita a Argel 20-jul) · local (El Faro) · voces
  de migrantes (3 citas en 45 páginas) · LatAm (EFE/AFP sin ángulo propio).
- **Estatal**: RT Francés corre el comunicado marroquí sin lado español; Al
  Jazeera lo equilibra con los documentos del CNI el mismo día.

### Contraste
| | Atlas | Mundo |
|---|---|---|
| Recibo más fresco on-story | 13-sep 06:30 (20minutos) / 12-sep 20:15 (MWN) | 14-sep 13:30 (Marlaska), 13-sep (5.321 retornos) |
| Política española | ✅ abundante (El País, LV, El Mundo) | ✅ |
| Marruecos | ⚠️ solo MWN (en) + reacciones vía AJ/El País | Le360/Hespress/TelQuel/MAP en fr/ar — **cero en Atlas** |
| "Sebta ocupada" (marco marroquí) | ❌ 0 | dominante en prensa marroquí |
| Retornos/expulsiones (5.321 / 300) | ❌ 0 | número central del fin de semana |
| Gen.Z.212 / 23-S | ⚠️ 1 (20minutos elecciones) | ✅ |
| Local (El Faro) | ❌ 0 | ✅ |
| Humanitario / voces migrantes | ⚠️ colegios El Príncipe | ✅ |
| UE/Frontex | ⚠️ MWN "EU sanctions" | Euronews 14-sep |
| Países medidos "13" | incluye ID/YE/MK por basura de umbrella | — |

### **Hallazgo grave: la traducción mintió y el gate la dejó pasar**
Titular de El País del viernes: *"Al menos 40 tiendas de migrantes
incendiadas en las Naves del Tarajal"*. `tiendas` = tiendas de campaña
(chabolas, confirmado por El Faro/EFE/eldiario: 42 chabolas). Ambos lanes
de traducción de prod devuelven **"At least 40 migrant shops burned"** (y
está cacheado en `signal_translations`). El lede del viernes decía *"At
least 40 migrant shops were burned"*. El quote gate valida la cita contra el
ESPAÑOL (correcta, verbatim); el guard de números pasa (40); la semántica
inglesa la puso el modelo. **Habríamos publicado un hecho falso con recibo
correcto.** La web confirma: "No 'shops burned' found anywhere".

**Nota Ceuta**: 5.0. Con curación B + traducción corregida: 7.

---

## 2 · "Netanyahu Rejects Trump Gaza Plan" (dt-277)

### Qué sirve Atlas
- `currentTotal` **10** · 12 países · 200 recibos de los que **163
  archivados** · `snapshots` 47 (identidad desde 01-jul) · rango 03-ago →
  14-sep · coherence 0.639 *tight* (¡sobre 29 miembros!).
- **Pool del kit (30 recientes): 18 son Trump vs regulación de la IA**
  ("fuerzas negativas", 13-14 sep, Clarín/El Tiempo/France24/G1) — nada que
  ver con Gaza. Los 12 restantes: **Haaretz revela que EAU avisó a Netanyahu
  antes del 7-O + Netanyahu demanda a Haaretz** (8-10 sep; es/fr/it/ro/pt).
- Pool completo: 64/200 on-story (32%); 109 con "IA". Recibo on-story más
  fresco: **10-sep 23:56**. Nada después.
- Idiomas: `?` 163 (archivados sin lang) · es 28 · pt 3 · it 3 · **en 1**.
  Cero prensa israelí, cero árabe, cero palestina en el pool.

### Salida real del kit
Lede (deepseek, 1 dropeada):
> The denial follows a Haaretz revelation that Netanyahu knew about 7
> October and was warned by the Emirates, according to Repubblica. After the
> Haaretz revelations, Netanyahu's party accused a Palestinian of
> interference, according to RFI.

**Defecto del gate**: dropeó la frase 1 (France24 "Netanyahu niega…") y la
2 quedó abriendo con "**The denial** follows…" — anáfora sin antecedente. El
gate garantiza que cada frase cite; no garantiza que el texto resultante
sea legible. Caption: **"10 signals · 12 countries · 85 sources"** — tres
números que no pueden convivir en un card (10 señales en el último pase vs
200 recibos cumulativos).

### El mundo (brief web, 14-sep)
- **"Netanyahu rejects Trump's Gaza plan" fue noticia el 9 de agosto**
  (CNN/WaPo/NPR/NBC/AJ: rechazo del documento de 15 puntos). No es titular
  de esta semana en ninguna página.
- Lo vivo 7-14 sep: **UK + 12 estados sancionan bienes de asentamientos
  (8-sep); Israel cierra el consulado británico en Jerusalén Este (9-sep)**;
  parálisis del "fase 2" por elecciones israelíes del 27-oct; Haaretz/MBZ
  (8-sep) y demanda; Kushner vs Netanyahu por Doha (13-sep); asesinato del
  comandante de Khan Younis (10-11); 73.786 muertos (MoH 14-sep).
- Voces: prensa israelí (ToI/JPost/Haaretz) domina el detalle; Al Jazeera
  "genocidal war" con comillas en "ceasefire"; Press TV/TRT omiten el plan
  Trump; LatAm vía EFE/EuropaPress.

### Contraste
| | Atlas dt-277 | Mundo |
|---|---|---|
| Etiqueta | rechazo del plan (9-ago) | sanciones UK / parálisis electoral / Haaretz |
| Haaretz–MBZ | ✅ 17 recibos, 5 idiomas | ✅ |
| Sanciones UK / consulado | **❌ 0** | titular de la semana |
| Kushner/Doha | ❌ 0 | 13-sep |
| Prensa israelí / árabe / palestina | ❌ 0 / 0 / 0 | dominantes |
| Contaminación | 109/200 "IA" (Trump absorbe por nombre) | — |

Lo que hay dentro sí existe en Atlas, pero en OTROS topics: `dt-20919
"Sanctions on Israeli Settlements"`, `dt-10599/9691 "Gaza Ceasefire…"`,
`dt-11775 "Kushner Gaza Diplomacy"`. **Ningún topic Gaza/Israel aparece en
el top-60 de `/threads?hours=168`.** La historia más grande del Medio
Oriente esta semana no tiene una identidad que la nombre.

**Nota Gaza**: 2.7. La sub-historia Haaretz/demanda (12 recibos, 5 idiomas)
sería un post honesto de 6-7 **si se llamara así**.

---

## 3 · "Trump Halts Iran Strikes" (dt-20497)

### Qué sirve Atlas
- `currentTotal` 33 · 10 países (IR 165 señales) · 8 idiomas (en 162 · ar 24
  · tr 5 · fa 4) · 200 recibos, 0 archivados · rango 09-sep → **13-sep
  15:17** · `firstSeen` 01-jun · coherence 0.439 *loose / grab_bag*.
- Top outlets: **arabic.rt.com 16** · royanews 9 · jpost 9 · mia.mk 7 · MEE
  6 · INN 6 · globalsecurity 5 · aa.com.tr 5 · aljazeera 4 · irna 4.
- **Pool del kit: 15/30 on-story (50%)**. Contaminación: **5 de Putin/
  Lituania (RT árabe)**, Corea del Norte/IAEA, EU-Ucrania (aktuality.sk),
  oro en Arabia. **Bug de metadatos**: royanews.tv marcado `lang=en` con
  titulares en árabe (9 filas).
- Lo que SÍ está: día 197-198 de la guerra (Roya), Baréin se retira de la
  reunión de Ormuz, Tasnim "el acuerdo con Omán no reabre Ormuz", 7
  condiciones (RT), Trump "la guerra acaba tras las midterms" (26 ecos),
  IAEA/Pickaxe Mountain + remisión al CSNU (13), ataques a la base de
  Jordania (32), petroleros (7).
- **Hallazgo medido real: 30 de 200 recibos son prensa estatal** (RT árabe,
  IRNA, Anadolu…). Es el número que el card imprime — y es verdad.

### Salida real del kit
Lede (deepseek, dropped 0):
> Trump reiterated that he sees the Iran war ending after US midterm
> elections, according to Middle East Eye. An Iranian source disclosed
> details of an understanding with Oman involving 7 conditions in exchange
> for opening the Strait of Hormuz, according to RT.

Correcto, RT nombrado (regla state-media), números del titular. Le falta la
tercera pata (Baréin/AJ — el modelo escribió 2 frases). Caption: "8
languages; 30 of 200 state-media" = el mejor gancho de las tres historias.

### El mundo (brief web, 14-sep)
- **Mes siete de una guerra caliente** (Jamenei muerto 28-feb; alto el fuego
  8-abr; colapso 8-jul; hostilidades desde 1-sep). "Trump halts strikes"
  fue titular el **1-2 de agosto** (y 7 veces antes, AP/PBS).
- Semana 8-14: CENTCOM hunde **5 petroleros** iraníes (8-9); Jordania
  intercepta 18/20; **IAEA remite a Irán al CSNU 23-3-8** (9-sep, primera vez
  en 20 años); **drones desde Irak cierran el oleoducto Este-Oeste saudí**
  (10-11); Tasnim: reapertura de Ormuz depende de EE.UU. (12); Baréin se
  retira (12); barco iraní alcanzado en Qeshm, 1 muerto (13); **Omán aplaza
  Salalah "por consenso"** (13); Brent **$108** (13); Irán culpa a "objeción
  saudí" (14); tránsitos por Ormuz en dígitos simples (14).
- Voces: Fox "US hammers minelayers"; Press TV atribuye a EE.UU. el ataque
  de Qeshm; RT "Trump floats oil takeover"; Xinhua "US-Israeli strikes";
  Anadolu/TRT fijan origen EE.UU.-Israel; AJ "US-Israel war on Iran".

### Contraste
| | Atlas | Mundo |
|---|---|---|
| Etiqueta | halt (1-ago) | guerra de petroleros + diplomacia de Ormuz sin EE.UU. |
| Aplazamiento de Salalah (13-sep) | **❌ 0** | el hecho del fin de semana |
| Oleoducto saudí cerrado (10-11) | **❌ 0** | segundo cuello de botella |
| Petroleros hundidos | ⚠️ 7 | ✅ |
| IAEA → CSNU | ✅ 13 | ✅ |
| Baréin / Tasnim / 7 condiciones | ✅ | ✅ |
| Prensa estatal medida | ✅ RT-ar, IRNA, AA; **Press TV/Mehr/Xinhua 0** | Press TV, Mehr, Xinhua, RT-en |
| Houthis / Bab al-Mandeb | ❌ 0 | ✅ |

**Nota Irán**: 4.7. Con etiqueta "US–Iran war, day 198: Hormuz talks
collapse" y el pool limpio: 7.5 — es la historia más "Atlas" de las tres
(voces estatales medibles, 8 idiomas, disputa sobre el mismo hecho).

---

## 4 · Defectos transversales (ordenados por daño) y qué cambiaría

| # | defecto | evidencia | dueño | cambio |
|---|---|---|---|---|
| 1 | **Traducción semántica errónea pasa el quote gate** | tiendas→shops, cacheado, en lede del viernes | kit + translate | Pasar **contexto** al traductor (label de la historia + outlet + país: "Ceuta migrant camp fire" desambigua *tiendas*). Prompt del lede: si el recibo está traducido, el modelo debe razonar sobre el ORIGINAL y el label. Invalidar caché de traducciones cuando cambie el prompt (`model` versionado). |
| 2 | **Pool del kit = 30 más recientes** → 20-50% on-story | Ceuta 6/30, baloncesto | kit | Pool ordenado por **relevancia al label** (tokens del label + hijos con court entailed primero; junk lanes al final) + **buscador/filtro** en la lista + pool 60. Recencia como desempate, no como criterio. |
| 3 | **Etiquetas de otra semana / otro mes** | dt-277 (9-ago), dt-20497 (1-ago) | motor (M1/court) | El selector debe exigir `label` re-juzgada sobre miembros de los últimos 7 días (hoy exige `entailed` histórico). El kit debe mostrar **"label last judged: <fecha>"** y avisar si > 7 días. |
| 4 | **Umbrella sin court + hijos basura** | Ceuta umbrella anoche: pool con Yemen/Irlanda/baloncesto | motor (R2) | Umbrella hereda el court de sus hijos; hijos sin entailment no entran al pool de recibos de la umbrella. Selector: admitir umbrellas con ≥1 hijo entailed. |
| 5 | **Anáfora huérfana tras drop del gate** | "The denial follows…" | kit (story_editorial) | Regla en prompt: "cada frase debe sostenerse sola, sin pronombres/artículos que apunten a otra frase". Gate: si se dropea la frase i, dropear i+1 cuando empieza con `The <sustantivo>/This/That/He/She/It/They/Such`. Re-ask una vez si queda < 2 frases. |
| 6 | **Números incompatibles en el card** | "10 signals · 12 countries · 85 sources" | kit | Si `currentTotal` < `sourceCount`, imprimir el **tamaño del sample** ("200 sampled receipts") en vez de "signals"; nunca dos bases distintas en la misma línea. |
| 7 | **Metadatos de idioma falsos** | royanews `en` con árabe (9); 163 `?` en dt-277 | ingesta/archivo | Detectar script del titular al ingerir (ya existe la lógica de script en silent-risk); archivados deberían conservar `source_lang`. |
| 8 | **Voz marroquí/iraní/china ausente donde el mundo la tiene** | 0 Le360/Hespress/MAP; 0 Press TV/Mehr/Xinhua | feeds (#235) | Añadir Hespress (ar), Le360 (fr), MAP (fr/ar), Press TV (en), Mehr (en), Xinhua (en). Es exactamente la promesa "múltiples lugares". |
| 9 | **Sufijo de sección en titulares** | "… \| Humanitarian Crises News" | kit | Strip de ` \| <sección>` al final del titular en el card/caption. |
| 10 | **Sin alerta de saldo LLM** | 13-sep 07:01 → 14-sep 15:00 a oscuras | ops | Check diario de `/user/balance` en el weekly-read/watchdog: < $3 → línea en el ledger de fiabilidad + aviso. |

Lo que **no** cambiaría: el quote gate (hizo su trabajo: 3 frases dropeadas
en 4 corridas, todas justificadas), la atribución obligatoria de state
media (RT nombrado en las 2 corridas donde entró), el hallazgo medido (el
"30 de 200 state media" de Irán es el mejor titular de la semana y es
matemática, no prosa), y la curación humana como paso obligatorio (sin ella
las tres historias son impublicables; con ella dos son buenas).

## 5 · ¿Qué publicar mañana?

**Ceuta, curación B, con dos condiciones**: (1) no usar el recibo "tiendas"
(o corregir la traducción a "tents" antes — la caché la va a servir mal
hasta que se invalide); (2) pregunta de cierre que abra el marco que Atlas
NO tiene: *"La prensa marroquí llama a esto 'Sebta ocupada'. ¿Qué cambia
cuando el mismo hecho tiene dos nombres?"* — honesto, porque el post muestra
lo que medimos y nombra lo que no.

Alternativa más fuerte si el fix #2 (pool por relevancia) entra hoy:
**Irán**, relabelada a mano en la pregunta de cierre, con el card diciendo
"30 of 200 sampled receipts are state media" — nadie más en LinkedIn puede
publicar ese número.

## Artefactos
`dt-*.payload.json` (payloads prod) · `dt-*.receipts.tsv` (200 recibos c/u)
· `kit-*.json` (salida real: recibos elegidos, frases + quotes, lede,
caption, finding) · briefs web: en los transcripts de los tres agentes
(URLs listadas al final de cada brief; ~45 / ~40 / ~45 páginas fetched;
El País/El Mundo/Le Monde/Reuters/Guardian bloqueadas al crawler — cubiertas
vía sindicación).
