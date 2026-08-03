# Pre-registro: consolidación + shared-country con IDENTITY-LANDING como métrica primaria

**2026-08-03 · Congelado ANTES de extender el harness o correr nada (aprobado
por Pedro: "de una"). Gates escritos aquí primero; movimiento post-resultados
= inválido. Séptimo gate pre-registrado del programa de identidad.**

## La regla bajo prueba (heredada, no nueva)

Grafo de consolidación intra-snapshot:
```
cos(centroid_a, centroid_b) >= 0.90
AND labels_compatible(label_a, label_b)     # producción, verbatim
AND countries_share(a, b)                   # el conjunct D3, verbatim
```
Componentes conexos = UN super-cluster = UN pick contra el pool. La condición
shared-country fue medida post-hoc en el run 5 (§11.1) — este run la
pre-registra como primaria, que es exactamente lo que ese artefacto exigió.

## Las dos diferencias de terreno vs el run 5

1. **Pool limpio**: el downstream corre contra el estado de HOY de
   `dynamic_topics` (TF-3b + court + blob-veto + junk operando desde 08-01;
   el run 5 midió contra el campo de julio pre-limpieza).
2. **Landing con sesgo a fundar (arm B)**: dos arms de landing por
   super-cluster —
   - **Arm A (producción)**: join si best-cos ≥ MATCH_THRESHOLD (semántica
     actual, `used_t` intacto).
   - **Arm B (found-biased)**: join SOLO si best-cos ≥ MATCH_THRESHOLD **y**
     `labels_compatible(label_supercluster, label_target)`; si no, FUNDA
     identidad nueva. (Fundar es barato — el lifecycle retira duplicados;
     unirse mal es el black-hole.)

## Gates congelados (todos deben sostenerse para GO; cualquiera falla → KILL, se documenta y se para)

| Gate | Barra | Fuente |
|---|---|---|
| **G-K2** | mayor componente ≤ 2% de los clusters de su snapshot, en ≥14 de 15 noches etiquetadas | heredado run 5 (medido 14/15 con la condición) |
| **G-784** | componentes con ≥3 países primarios Y par de labels incompatible = **0** en 15 noches | heredado run 5 (medido 0) |
| **G-LANDING (la primaria)** | en las familias testigo scorables, el arm B aterriza el evento en identidad CORRECTA (label describe el mismo evento, juzgado con recibos) en **≥4 de 6** familias — Y estrictamente más familias correctas que el arm A | nueva; el run 5 midió 2/6 en su downstream |
| **G-COBERTURA (secundaria)** | cobertura de familia ≥ la del RAW arm; nunca se reporta sola | run 5 §11.2 |
| **G-FUNDACIÓN** | el arm B no infla el pool: fundaciones nuevas ≤ 15% de los super-clusters que aterrizan (fundar-todo = esconder el problema) | nueva, anti-trivialización |
| **G-FALSOS** | 0/1200 pares falsos admitidos por noche (protocolo del run 2) | heredado |

Exclusiones por construcción: las 5 noches blackout (07-23→07-27, labels
100% NULL) no pueden portar la regla; se reportan como no-scorables, jamás
como éxito. Familias testigo: las 6 del run 5 (caspian, berlin-pride,
us-strikes-iran, paris-knife, kyiv-strikes, wildfires-fr-es) con sus
definiciones importadas verbatim; si el campo de hoy deja alguna no-scorable
se reporta y el denominador de G-LANDING baja con ella (barra se mantiene
proporcional: ≥⌈⅔·scorables⌉).

## Método (fidelidad heredada del run 5)

Harness = extensión de `measure_cluster_consolidation.py` (todo importado de
producción, nada re-implementado; checks de fidelidad del run 5 se re-corren
y deben reproducir). Landing-judgment: por familia, el topic destino se
juzga con sus recibos (juez LLM con quote-gate + spot-check humano de los 6
— población chica, se puede a mano). Read-only sobre prod; M1 **mindful
SIEMPRE** (taskpolicy -b — Pedro en la máquina); artefacto
`2026-08-03-consolidation-landing.{md,json}`.

## Qué compra un GO

El paso de consolidación+landing entra al pipeline nocturno (flag-gateado,
reversible) → los fragmentos de un evento entran como UNA identidad bien
aterrizada → NAV-LOSS re-gate del story lens → `STORY_LENS_AUTO=on` si pasa.
Un KILL deja el instrumento de landing y el siguiente lead honesto.
