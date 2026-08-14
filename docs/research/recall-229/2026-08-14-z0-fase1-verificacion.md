# Z0 · Fase 1 — verificación del centroide: **REFUTADO**

> **VEREDICTO (regla de kill congelada, honrada): REFUTADO.** La mediana de
> `cos(centroide_incremental, media-corrida-verdadera)` es **0.9916 ≥ 0.98**, la
> barra que el pre-registro fijó como kill. El mecanismo de aliasing **existe y
> quedó confirmado byte a byte** — pero la predicción que lo hacía importar
> (rebuild e incremental deben discrepar sistemáticamente) es **falsa**: el
> centroide "roto" y la media verdadera son el mismo punto a 0.008 de coseno.
> **El arco Z0 se cierra sin tocar código.**

**Fecha:** 2026-08-14 · **Estado:** READ-ONLY. **Nada se escribió.** Solo
SELECT (acotados, `SET LOCAL statement_timeout` dentro de transacción, fetch por
chunks, `taskpolicy -b`). Ni prod, ni tabla sombra, ni migración, ni flag.
**No se corrió `--rebuild` contra prod** (§2.2 explica por qué la réplica offline
es el mismo test y es estrictamente más limpia).

Pre-registro: `docs/superpowers/specs/2026-08-14-centroid-z0-preregistration.md`
Diagnóstico origen: `docs/research/recall-229/2026-08-14-centroid-not-a-running-mean.md`

---

## 1. Las tres distribuciones (la tabla del pre-registro, respondida)

n = 504 topics `active`, no-umbrella, ≥3 clusters miembros vivos (muestra
aleatoria semilla 20260814 sobre los 2,735 elegibles = 18.4%; 5,577 clusters
leídos). Los 5 testigos no-umbrella entraron forzados a la muestra.

| Medida | Predicción si CIERTA | Predicción si FALSA | **MEDIDO (mediana)** | Lado |
|---|---|---|---|---|
| cos(incremental, media verdadera) | bajo y disperso | ≈1.0 | **0.9916** | **FALSA** |
| cos(incremental, último cluster) | ≈1.0 en ~99% | disperso | **1.0000** (98.6% md5-idéntico) | CIERTA |
| cos(media verdadera, último cluster) | disperso | ≈1.0 | **0.9915** | FALSA |

La fila 2 confirma el mecanismo. Las filas 1 y 3 lo desactivan: **la media
corrida verdadera también está pegada al último cluster.** No porque el replay
esté mal, sino porque los clusters miembros de un topic son casi copias entre sí
en este espacio — promediarlos 10 o 37 veces no mueve el punto.

### Histogramas

```
cos(incremental, media verdadera)          n=504   mediana 0.9916  min 0.9339
  [0.93,0.94)    3   0.6% #
  [0.94,0.95)    3   0.6% #
  [0.95,0.96)   24   4.8% ###
  [0.96,0.97)   34   6.7% #####
  [0.97,0.98)   66  13.1% #########
  [0.98,0.99)  109  21.6% ###############
  [0.99,1.00)  219  43.5% ##############################
      =1.0000   46   9.1% ######
                              ^ 74.2% ya está por encima de 0.98

cos(incremental, último cluster)           n=504   mediana 1.0000  min 0.9885
  [0.98,0.99)    2   0.4% #
  [0.99,1.00)    5   1.0% #
      =1.0000  497  98.6% #####################################################################

cos(media verdadera, último cluster)       n=504   mediana 0.9915  min 0.9339
  [0.93,0.94)    3   0.6% #
  [0.94,0.95)    3   0.6% #
  [0.95,0.96)   24   4.8% ###
  [0.96,0.97)   35   6.9% #####
  [0.97,0.98)   68  13.5% #########
  [0.98,0.99)  107  21.2% ###############
  [0.99,1.00)  218  43.3% ##############################
      =1.0000   46   9.1% ######
```

Las distribuciones 1 y 3 son **la misma curva** (difieren en ≤2 topics por bin).
Eso es la refutación en una imagen: si el centroide servido ≡ último cluster
(fila 2), entonces "incremental vs media" y "media vs último" tienen que
coincidir — y coinciden. La pregunta se reduce a **cuánto se aleja la media de
su propio último miembro**, y la respuesta medida es: 0.0085.

Percentiles completos:

| medida | min | p05 | p25 | mediana | p75 | p95 | max | media |
|---|---|---|---|---|---|---|---|---|
| cos(inc, media verdadera) | 0.9339 | 0.9577 | 0.9792 | **0.9916** | 0.9992 | 1.0000 | 1.0000 | 0.9870 |
| cos(inc, último cluster) | 0.9885 | 1.0000 | 1.0000 | **1.0000** | 1.0000 | 1.0000 | 1.0000 | 0.9999 |
| cos(media verdadera, último) | 0.9339 | 0.9577 | 0.9790 | **0.9915** | 0.9992 | 1.0000 | 1.0000 | 0.9869 |
| cos(inc, media de la última pasada) | 0.9885 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9999 |
| cos(inc, PRIMER cluster / ancla) | 0.9302 | 0.9334 | 0.9455 | 0.9661 | 0.9973 | 1.0000 | 1.0000 | 0.9691 |

---

## 2. Método

### 2.1 Qué es cada vector

- **(a) incremental / servido** — `dynamic_topics.centroid_vec` tal como se sirve.
- **(b) media corrida verdadera** — recomputada **offline** replicando
  `hydrate_topics()` (`project_dynamic_topics.py:1234-1246`): `Topic(primer
  cluster vivo)` y luego `attach()` de cada miembro posterior en orden de
  `snapshot_at`, con `running_mean(old,k,new)=(old*k+new)/(k+1)` y `k =
  len(members)` — que en el replay **sí** crece. Miembros filtrados a los que
  siguen vivos en `emergent_clusters`, que es exactamente el filtro de `:1191`.
  Verificado empíricamente que ese replay es idéntico a la media simple:
  `max|replay − mean| = 4.4e-16` sobre 200 topics sintéticos.
- **(c) último cluster** — `DISTINCT ON (dynamic_topic_id) … ORDER BY
  snapshot_at DESC, emergent_cluster_id DESC`. Se midió además **(c′)** la media
  de todos los clusters de la ÚLTIMA snapshot del topic (la predicción exacta
  del mecanismo cuando una pasada absorbe ≥2).

### 2.2 Por qué no se corrió `--rebuild`

Un `--rebuild` real no solo recomputa el centroide: **vuelve a decidir qué
cluster va a qué identidad** desde cero. Su diff mezclaría dos efectos (la
aritmética del promedio + un re-matching distinto) y no aislaría la hipótesis.
El replay offline **congela la membresía persistida** y cambia **solo** la
aritmética — es el test de la hipótesis, sin ruido y sin riesgo de escritura.
Además `--rebuild` contra prod TRUNCA/reescribe identidades, que es exactamente
lo que el pre-registro prohíbe en Fase 1. **No se escribió una sola fila.**

---

## 3. El mecanismo SÍ existe (confirmado, byte a byte)

Esto no está en duda; lo que se refutó es su consecuencia.

**Escaneo de población (md5 sobre `centroid_vec::text`, hoy):**

| estado | topics con centroide | último miembro vivo | `centroid_vec` == ese cluster |
|---|---|---|---|
| active | 3,088 | 3,088 | **3,065 (99.3%)** |
| candidate | 4,956 | 4,678 | **4,655 (99.5%)** |

Reproduce exactamente el número del diagnóstico.

**Prueba de sufijo (la más nítida).** Para cada topic se buscó el sufijo más
corto de sus miembros (ordenados por snapshot) cuya media reproduce el centroide
servido:

| longitud del sufijo | topics | lectura |
|---|---|---|
| **m = 1** | **497 / 504 (98.6%)** | el centroide servido ES el último cluster |
| m = 2 | 7 / 504 (1.4%) | la última pasada absorbió 2 clusters → media de esos 2 |
| m ≥ 3 | **0** | ningún topic promedia su historia |

Ninguno de los 504 topics — con 3 a 46 miembros, hasta 36 snapshots — tiene un
centroide que promedie más que su última pasada. Los 7 con m=2 son exactamente la
clase de las "23 excepciones activas" que el diagnóstico ya había nombrado.
`cos(inc, media-de-la-última-pasada)` = 1.0000 mediana, ≥0.999 en 98.8%.

**Los 15 grupos duplicados quedan explicados al 100%.** En los 15 (30 topics: 3
active⟷active, 5 active⟷candidate, 7 candidate⟷candidate), **los dos miembros de
cada par tienen `centroid_vec` == el md5 de SU PROPIO último cluster**
(`members_eq_own_last = 2/2` en los 15), y esos últimos clusters son **ids
distintos con contenido idéntico** (gemelos re-emitidos). No hay ningún par cuyo
duplicado se explique por membresía compartida. El mecanismo es la causa
completa de los duplicados.

---

## 4. Cuánto se aleja el centroide servido de sus propios miembros

El proxy pedido de "qué tan mal ancla para el matching": coseno medio del
centroide contra cada uno de sus clusters miembros.

| | mediana | p25 | p05 | min | <0.93 |
|---|---|---|---|---|---|
| centroide **servido** ↔ sus miembros | 0.9793 | 0.9616 | 0.9419 | 0.9127 | 9 topics (1.8%) |
| **media verdadera** ↔ sus miembros | 0.9902 | 0.9829 | 0.9752 | 0.9684 | **0** |

```
cos medio(servido, miembros)               n=504   mediana 0.9793
  [0.91,0.92)    3  0.6% #
  [0.92,0.93)    6  1.2% #          <- 1.8% por debajo de ANCHOR_THRESHOLD 0.93
  [0.93,0.94)   15  3.0% ##
  [0.94,0.95)   38  7.5% #####
  [0.95,0.96)   48  9.5% #######
  [0.96,0.97)   77 15.3% ###########
  [0.97,0.98)   70 13.9% ##########
  [0.98,0.99)   50  9.9% #######
  [0.99,1.00)  152 30.2% #####################
      =1.0000   45  8.9% ######
```

**Lectura honesta:** el arreglo mejoraría el anclaje en **+0.011 de coseno
mediano** y sacaría a 9 topics (1.8%) de debajo de 0.93. Pero el umbral que
decide el matching es `MATCH_THRESHOLD = 0.88` (`:42`) y los miembros ya puntúan
0.9793 contra el centroide roto — **muy por encima**. Es decir: el defecto **no
está mordiendo** el matching por esta vía. Ese es el corazón de la refutación —
no que el defecto no exista, sino que no llega a la palanca.

Nota lateral: `cos(servido, PRIMER cluster)` mediana 0.9661 con p25 0.9455
muestra que el centroide servido tampoco es el ancla; `anchor_centroid` es una
variable en memoria aparte (`:464`), reconstruida del miembro vivo más antiguo, y
esta medición no la toca.

---

## 5. Testigos — el terremoto de Colombia, medidos uno a uno

| topic | miembros | snaps | cos(inc, media verd.) | cos(inc, último) | md5 == último | sufijo | cos(servido, miembros) | cos(media, miembros) | label_status |
|---|---|---|---|---|---|---|---|---|---|
| **dt-242** | 17 | 17 | **0.9483** | 1.0000 | sí | 1 | 0.9193 | 0.9694 | entailed |
| **dt-244** | 26 | 26 | **0.9822** | 1.0000 | sí | 1 | 0.9616 | 0.9790 | partial |
| **dt-248** | 37 | 36 | **0.9633** | 1.0000 | sí | 1 | 0.9472 | 0.9832 | entailed |
| **dt-510** | 24 | 24 | **0.9730** | 1.0000 | sí | 1 | 0.9531 | 0.9796 | entailed |
| **dt-517** | 23 | 23 | **0.9699** | 1.0000 | sí | 1 | 0.9515 | 0.9811 | entailed |
| dt-12910 | *(umbrella, 2 hijos: 244+248)* | — | — | — | — | — | — | — | entailed |
| dt-12928 | *(umbrella, 17 hijos)* | — | — | — | — | — | — | — | failed |

Etiquetas servidas: dt-242 "7.4-Magnitude Earthquake Kills Dozens in Colombia" ·
dt-244 "…Death Toll Rises Past 132" · dt-248 "…Past 130" · dt-510 "Magnitude 7.4
Earthquake Strikes Colombia" · dt-517 "…Rises to 132". Sus últimos clusters:
79099 "Colombia Earthquake Devastation", 79737 "Earthquake Death Tolls", 79155
"Colombia Earthquake Casualties", 79175 "Earthquake Strikes Colombia", 79153
"Colombia Earthquake Death Toll". **Cinco identidades activas para un solo
terremoto** — la dispersión sigue ahí, intacta y medida.

**dt-12910 y dt-12928 quedan FUERA del mecanismo:** son `is_umbrella=true`, las
escribe `build_umbrella_topics.py:211`, y `hydrate_topics` las salta explícitamente
(`:1188`). Su centroide es centroide-de-hijos, así que heredan lo que traigan los
hijos, pero el aliasing de `attach()` no las toca. Medirlas con esta vara sería
mezclar dos escritores. (Dato de paso: dt-12910 tiene 2 hijos = dt-244 y dt-248;
dt-12928 tiene 17 hijos y **ninguno** de los cinco testigos — dos paraguas
distintos sobre el mismo terremoto.)

### 5.1 Residuo honesto — los testigos son la cola, no la mediana

Los 5 testigos caen entre 0.948 y 0.982, **todos por debajo de la mediana 0.9916**,
tres de ellos por debajo de la barra 0.98. Es un patrón, no ruido: la discrepancia
crece con la vida del topic.

| miembros vivos | n | mediana cos(inc, media verd.) | p25 | min |
|---|---|---|---|---|
| 3-4 | 101 | 0.9996 | 0.9964 | 0.9608 |
| 5-9 | 192 | 0.9969 | 0.9839 | 0.9339 |
| 10-19 | 127 | **0.9821** | 0.9709 | 0.9349 |
| 20+ | 84 | **0.9836** | 0.9769 | 0.9428 |

130 de 504 (25.8%) quedan bajo 0.98; su mediana de miembros es 12.5 contra 6.0 de
los que la superan.

Y sobre los testigos específicamente, la geometría **sí** cambiaría (coseno par a
par entre las 5 identidades):

| | media par a par | pares ≥ MATCH 0.88 | pares ≥ MERGE 0.90 |
|---|---|---|---|
| centroides **servidos** (hoy) | 0.8863 | **6 / 10** | **2 / 10** |
| **medias verdaderas** | 0.9209 (**+0.035**) | **10 / 10** | **9 / 10** |

Con la media verdadera las cinco identidades del terremoto se ven entre sí por
encima del umbral de match, y nueve de diez pares también por encima del de merge.

**Esto NO resucita la hipótesis.** La regla de kill se congeló sobre la **mediana
de una muestra de ≥200**, se midió 0.9916, y la regla se honra. Un subgrupo
elegido después de ver los datos no puede mover una barra pre-registrada — esa es
precisamente la disciplina que este proyecto lleva nueve gates sosteniendo. Lo que
esta sub-medición sí hace es **definir la hipótesis siguiente**, que necesitaría su
propio pre-registro con su propia barra congelada antes de correrse.

---

## 6. Qué tendría que cambiar la Fase 2 (y por qué hoy no procede)

**Hoy no procede.** El pre-registro dice, literal: *"si cos(incremental, rebuild)
≥0.98 mediano, el diagnóstico está mal y este arco se cierra sin tocar código."*
0.9916 ≥ 0.98. **Fase 2 y el gate Z0 quedan cancelados.**

Queda escrito lo que habría que cambiar, para que nadie lo re-descubra:

1. **El fix mecánico sigue siendo correcto como higiene** (no como palanca):
   separar las dos responsabilidades de `Topic.members` — cola de INSERT vs peso
   `k` — con un contador propio usado en `running_mean` (`:548`) y en `absorb`
   (`:568-574`, hoy degenerado: tras hydrate ambos lados tienen 0 miembros y el
   centroide de la víctima se descarta en silencio). Medido: mueve el centroide
   0.008 de coseno mediano. **Es un bugfix de limpieza, no un cambio de
   comportamiento** — y aun así toca identidad, así que si algún día se hace,
   se hace con gate.
2. **Las cuatro barras del gate Z0 quedan sin sujeto.** G-ANCLA pedía que
   `cos(centroide_nuevo, último cluster)` cayera por debajo de 0.95: la media
   verdadera da **0.9915**, así que G-ANCLA **fallaría por construcción** — el fix
   correcto no puede pasar su propia barra, porque la barra asumía que la media
   estaba lejos del último cluster y no lo está. Si se re-pre-registra, esa barra
   hay que re-derivarla de una medición, no de la intuición.
3. **La palanca de la dispersión está en otra parte.** El campo mide
   `cos(miembros, centroide)` ≈ 0.98 y `cos(identidad, identidad)` ≈ 0.89 sobre la
   MISMA historia: el problema no es dónde está parado el ancla, es que
   `MATCH_THRESHOLD 0.88` / `ANCHOR_THRESHOLD 0.93` sobre un espacio comprimido no
   distingue "mismo terremoto" de "otra cosa", y cinco identidades del mismo evento
   conviven sin verse. Eso es la dispersión de argmax nombrada el 2026-07-30, y Z0
   no la tocaba.
4. **Lo que sí sobrevive intacto del diagnóstico** y no depende de esta hipótesis:
   el desempate silencioso en `build_unified_topics.py:261-263` (`sims.argmax`) y
   en `match_snapshot`'s `pairs.sort` (`:841`). Con 15 pares de centroides
   byte-idénticos vivos, cada señal de esos pares se rutea siempre al id que
   ordena primero, por índice, sin registro. Hacer explícito ese empate (logearlo,
   o negarse a asignar en un 1.0 entre dos identidades) es barato, es independiente
   de este gate, y sigue siendo la recomendación.

---

## 7. Reproducción

Harness read-only en el scratchpad de la sesión
(`z0_probe.py`, `z0_fase1.py`, `z0_witness.py`; resultados completos por topic en
`z0_fase1_result.json`). Los dos SQL que sostienen §3 corren en ~1 min:

```sql
-- 99.3% (poblacional, sin transferir vectores)
WITH t AS (SELECT id, state, md5(centroid_vec::text) th FROM dynamic_topics
           WHERE centroid_vec IS NOT NULL AND NOT is_umbrella
             AND state IN ('active','candidate')),
lastm AS (SELECT DISTINCT ON (dynamic_topic_id) dynamic_topic_id tid,
                 emergent_cluster_id cid
          FROM dynamic_topic_members
          ORDER BY dynamic_topic_id, snapshot_at DESC, emergent_cluster_id DESC)
SELECT t.state, count(*) topics, count(ec.id) last_cluster_live,
       count(*) FILTER (WHERE md5(ec.centroid_vec::text) = t.th) AS eq_last
FROM t LEFT JOIN lastm ON lastm.tid = t.id
       LEFT JOIN emergent_clusters ec ON ec.id = lastm.cid
GROUP BY 1;
```

La media verdadera de un topic = media simple de los `centroid_vec` de sus
`dynamic_topic_members` que sigan vivos en `emergent_clusters` (identidad con el
replay de `hydrate_topics` verificada a 4.4e-16).

---

## 8. Cierre

El mecanismo era real y quedó probado byte a byte: **el centroide servido es una
copia del último cluster absorbido en el 99.3% de los activos, y ningún topic
promedia más allá de su última pasada.** La hipótesis de que eso importa —
que rebuild e incremental discrepan sistemáticamente — **se murió en su propia
barra**: 0.9916 contra un kill de 0.98. La media corrida verdadera vive a 0.0085
de coseno del último cluster, porque los clusters miembros de una historia son
casi copias entre sí.

Un defecto real que no mueve nada medible sigue siendo un defecto que no mueve
nada medible. **Z0 cerrado. Décima barra honrada.**
