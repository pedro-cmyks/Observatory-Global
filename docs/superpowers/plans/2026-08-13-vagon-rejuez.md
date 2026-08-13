# Vagón re-juez — la punch list del G-LECTURA PASS — 2026-08-13

**Fuente**: `docs/research/gold/2026-08-13-brief-rejudge.md`. Fuera del vagón,
con dueño: item 1 (edición sellada vacía ← lifecycle congelado) = chip
task_5e3cbb74 CORRIENDO; item 8 (cluster guerra+carreteras) = programa de
landing, reloj de condenación run-4 mañana. Regla: pathspec, TDD,
browser-verify, integro + deploy único.

| # | Item del juez | Fix | Agente |
|---|---|---|---|
| **W1** | Lens móvil brickea (tap directo a Lens: no renderiza + scroll bloqueado, 3× reproducido — el candado tiene un SEGUNDO camino que C5 no cubrió) | reproducir a 375px, cazar el segundo owner/camino del lock, cubrir con el scrollLock suspendible + boundary; verificar TODOS los caminos de entrada al Lens | mobile |
| **W2** | Analysis: "Ungp Forests Rivers Oceans"/"Crisislexrec" como prosa + "−0.48 en la escala −0.48…−0.48" + contradice el chart de categorías de abajo | backend: los theme codes pasan por getThemeLabel-equivalente ANTES del prompt; el template de escala arregla sus cotas (bug: valor en vez de banda); la base del Analysis nombra su taxonomía o usa la del chart | backend |
| **W3** | "Translate all" no-op silencioso (flip a SHOW ORIGINALS, nada se traduce) | trazar el wiring roto (TranslatableSection/pageLanguage/endpoint); si el endpoint falla → estado honesto visible, jamás flip silencioso | translate libs |
| **W4** | Rate-limit matando al lector (Nigeria: "6 stories" → "door did not answer", 429s; el bucket paid 20/300s cubre lecturas baratas) | MEDIR qué endpoints toca una sesión de lectura + su costo real hoy (country-edition ya es lectura de artefacto ~1s); re-bucketizar: paid protege lo que CUESTA (LLM), lecturas de artefacto a un bucket de lectura; límites nuevos justificados por el costo medido | backend rate_limit |
| **W5** | Portada vs console en desacuerdo sobre las historias del día + Culture-vacío vs chart "Sports 1,398" + markets "LAST CLOSE AUG 11" en Ago-13 + score 0.99 en explainer del patrón oro ("precision theatre") | tras W3: diagnosticar cada par (lanes distintas → nombrar base o unificar); el chart junto a una sección vacía declara su base; markets: ¿cron de acumulación vivo?; display de scores under-radar: banda honesta, nunca "0.99" crudo sobre match léxico | Brief (tras W3) |

Al aterrizar: gate integrado + deploy Fly/Vercel. El re-re-juez NO es
automático — la cadencia de jueces la decide Pedro.
