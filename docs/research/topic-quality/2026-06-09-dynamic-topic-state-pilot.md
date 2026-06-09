# Dynamic Topic State Pilot

**Model:** `kalman-state-v0-readonly`
**Mode:** read-only; no lifecycle/classification writes.

| topic | lifecycle | trend | velocity | surprise | uncertainty | recommendation |
|---|---|---:|---:|---:|---:|---|
| Greek News Roundup | candidate | cooling | -0.1622 | 1.3044 | 0.6859 | do_not_promote_roundup |
| Brazil News Roundup | candidate | surging | 0.3969 | 1.6813 | 0.5045 | do_not_promote_roundup |
| Romanian News Roundup | candidate | stable | -0.0017 | 1.4398 | 0.6318 | do_not_promote_roundup |
| Mixed News Headlines | candidate | stable | -0.0436 | 0.9993 | 0.4744 | do_not_promote_roundup |
| Turkey News Roundup | candidate | cooling | -0.2104 | 1.0154 | 0.5818 | do_not_promote_roundup |
| Russia-Ukraine War Updates | active | cooling | -0.3224 | 1.0426 | 0.4823 | watch_decay |
| Indonesian News Roundup | candidate | cooling | -0.2733 | 0.8844 | 0.4711 | do_not_promote_roundup |
| Agostina Vega Found Dead | candidate | accelerating | 0.1472 | 0.7389 | 0.6267 | do_not_promote_high_noise |
| Noticias Regionales Variadas | active | stable | -0.0390 | 0.5633 | 0.5340 | keep_current_lifecycle |
| Death of Indio Solari | active | accelerating | 0.1417 | 0.7117 | 0.6319 | watch_acceleration |
| Stock Price Movements | active | surging | 0.1411 | 1.4688 | 0.4744 | watch_acceleration |
| New World Screwworm in Texas | active | cooling | -0.2725 | 1.0631 | 0.4502 | watch_decay |

Interpretation: this report estimates movement state only. It should be used
to prioritize review or monitoring, not to promote/suppress semantic topics.
