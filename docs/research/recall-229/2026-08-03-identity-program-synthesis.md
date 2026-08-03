# El programa de identidad tras 6 refutaciones — síntesis y el próximo run pre-registrable

**2026-08-03 · Documento de síntesis (no de medición). Junta los veredictos de
los 6 gates pre-registrados de la capa de identidad con lo que el arco de
lifecycle (TF-3b + court + blob-veto + junk-gates) cambió del terreno, y
propone EL run que la evidencia señala. Nada aquí se ejecutó; es el menú.**

## Las 6 refutaciones, en una línea cada una

1. **Whitening en identidad** (07-28): destruye el alineamiento cross-lingüe
   — separa pares que el motor nunca confundió.
2. **Merge-gate por solape de evidencia** (07-29): la DENSIDAD del grafo
   manda, no la precisión pairwise (1.4% falso ⇒ componente del 96.2%).
   Rehabilitó la regla SHIPPING (cos≥0.90 AND label≥0.80, K2-safe).
3. **Juez DeepSeek como confirmador de merges**: muerto por volumen
   (2.4×–1117× el presupuesto nocturno).
4. **Quitar `used_t`** (07-30): 2,247 absorciones falsas; y el hallazgo
   decisivo — **los fragmentos de un mismo evento NO comparten argmax**
   (43/54 Berlin-Pride sin el target en su top-12). La dispersión argmax es
   LA enfermedad.
5. **Consolidación cluster-level** (07-30): el recall funciona
   espectacularmente (23→3 topics, cobertura 0.93-1.00) pero **aterriza
   eventos enteros en la identidad EQUIVOCADA** (Kyiv-atacada → topic de
   Moscú-atacada, 4 de 6 familias testigo). "El argmax está mal, y hacerle
   una mejor pregunta no arregla su respuesta."
6. **Bake-off de embeddings v2** (07-31): NINGÚN espacio cura la dispersión;
   el espacio no es el cuello — la capa de identidad lo es.

## Lo que el arco de lifecycle cambió del terreno (y las refutaciones no vieron)

Todas las mediciones de identidad corrieron sobre el campo de JULIO: pool de
topics con ~61% is_blob, labels congelados, revividos sin vetting. Desde
entonces: TF-3b (revival→candidate + promoción exige court `entailed`),
censo gate-c + cirugía (footprint revivido 100% verificado), blob-veto
persistido (mig 095), junk-gate PR-wire, relabel-loop cerrando mismatches.
**El POOL de targets — la mitad del problema del landing — está en proceso
de limpieza continua por primera vez.** Señal temprana: gold día-4 marcó la
primera persistencia 3/3 de la serie y 4 identidades sobreviviendo
día-a-día (el día 3 tenía cero).

## Dónde apunta la evidencia — el run que se pre-registra solo

La consolidación (refutación 5) dejó sus DOS kills cerrables con una
condición ya medida (`+ countries_share`: 784-class 0/15 noches, K2 14/15,
5/6 familias testigo intactas; costo estructural conocido: historias
bilaterales no mergean — Caspian 4→5). Lo que le faltó fue el LANDING:
sobre qué identidad aterriza el super-cluster.

**El próximo run (cuando se decida):** consolidación + shared-country, con
**identity-landing como métrica de primera clase** (no cobertura sola), y
dos diferencias de terreno que ninguna medición previa tuvo:
- correr sobre el POOL LIMPIO (semanas de court/blob/junk trabajando — el
  target equivocado cercano tiene cada vez más probabilidad de estar
  retired/candidate, no active);
- una regla de landing con sesgo a FUNDAR: en banda gris de score o labels
  incoherentes con el candidato, el super-cluster funda identidad nueva en
  vez de unirse a una vieja — anti-black-hole por construcción (la
  fundación es barata y el lifecycle ya sabe retirar duplicados; unirse mal
  es lo caro e irreversible-en-serving).

Gates a congelar antes de correr: K2 ≤2% + 784-class = 0 (ya medidos con la
condición), **landing-correcto ≥ X% en familias testigo** (X a fijar ANTES,
sugerido ≥4/6), cobertura como métrica secundaria nunca sola, y las noches
blackout excluidas por construcción.

## Qué NO hacer (ya refutado, no re-investigar)

Whitening en identidad · umbral df de "token distintivo" (anti-correlacionado
con las familias grandes que debe preservar — medido) · juez LLM por par a
volumen · cambiar de espacio de embeddings · quitar used_t sin sustituto.

## Estado del story lens

Sigue honesto en DARK (su K1: no servir recibos sobre vecinos falsos). Su
re-gate depende exactamente del landing-correcto de arriba — no de más
lifecycle. Cuando el run de consolidación+landing pase sus gates, el lens es
una línea (`STORY_LENS_AUTO=on`) y una re-corrida de NAV-LOSS.
