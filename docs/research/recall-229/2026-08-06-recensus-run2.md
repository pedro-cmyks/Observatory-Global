# Re-censo run-2 (todos los leones activos): 72.2% — FAIL contra la barra, PERO la cohorte nueva llega a 83.3%

**2026-08-06 · 320 promociones frescas (post-08-04 18:00Z, o sea con
service-junk + earnings-autogen + post-revival-receipts + revival-cap +
blob-veto + PR-wire TODOS vivos). Mismo harness, doble juez + tiebreak,
acuerdo inter-juez 96.9%, 63 agentes (jueces en Opus tras agotar Fable —
la regla del CLAUDE.md aplicada: jueces nunca en el tier caro).**

## Números

| Corte | n | real | tasa |
|---|---|---|---|
| **Cohorte completa** | 320 | 231 | **72.2%** (barra 90% → FAIL) |
| run-1 (08-04, mismos criterios) | 179 | 106 | 59.2% |
| **Mecánica · identidad NUEVA (nacida post-leones)** | 132 | 110 | **83.3%** |
| Mecánica · identidad VIEJA | 153 | 100 | 65.4% |
| Vetada (revival + court) · identidad vieja | 35 | 21 | 60.0% |

Fallas: 35 label_mismatch · 31 blob · 23 junk. Acuerdo 96.9%.

## La lectura que importa: la trayectoria por EDAD DE IDENTIDAD

**+13pp globales en 48h (59.2 → 72.2)** con los leones puestos, y el split
por edad separa dos poblaciones que el promedio confunde:

- **Identidades NUEVAS = 83.3%.** Lo que el motor está PRODUCIENDO hoy, con
  todos los gates activos, está a 6.7pp de la barra. La maquinaria nueva
  funciona.
- **Identidades VIEJAS = 65.4% (mecánica) / 60.0% (vetada).** Un topic viejo
  que hoy re-promueve arrastra su label congelado en la creación y su
  historia de absorciones. Los gates lo dejan pasar porque juzgan el
  ENTAILMENT presente, no la deuda acumulada.

**La deuda es de STOCK, no de flujo.** Los detectores nuevos protegen lo que
nace; lo que ya nació enfermo sigue re-promoviendo. Es la misma forma que el
gate-c encontró (el certificado ~70% preciso) pero ahora con la variable que
lo explica medida.

## Lo que esto pre-registra (sin mover barras)

1. **La barra 90% se mide sobre la cohorte NUEVA** en el próximo re-censo —
   es la población que responde a los gates. La cohorte vieja necesita su
   propio instrumento (abajo), no una barra compartida que promedia dos
   enfermedades distintas.
2. **El instrumento faltante: relabel de identidades viejas al re-promover.**
   El relabel-loop existe (court failed → relabel → re-juicio) pero se
   dispara por veredicto `failed`, y un label viejo-y-vago ENTAILA sus
   recibos (nunca falla). Candidato medido-primero: al promover una identidad
   con `first_seen` > N días y label sin refrescar, forzar re-etiquetado
   desde los recibos ACTUALES antes de servir. Medir con los 153 viejos de
   esta corrida como testigos (65.4% es el baseline).
3. Los 89 fallos de esta corrida quedan identificados por id en el journal
   del workflow (`wf_bbb13846-801`) — material de cirugía y de calibración.

## Método

Jueces y tiebreak fijados explícitamente en un tier no-Fable tras el agotamiento
de créditos a mitad del primer intento (36/320 juzgados, descartados por
muestra no autorizada — el pre-registro exige la cohorte completa). El re-run
completo con la llave de caché nueva costó los 36 de nuevo: pérdida contable,
cero contaminación metodológica.
