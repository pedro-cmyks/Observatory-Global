# Subject Geography Complete-Universe Report

Generated: `2026-07-13T14:54:15.693270+00:00`

This is a read-only, deterministic Stage 1 report. It makes no LLM calls, does not write lifecycle or serving state, and does not treat coverage geography or archive matches as ground truth.

## Completion receipt

- Complete universe: `true`
- Rows discovered / processed: `1488` / `1488`
- Cursor batches: `30`; last cursor: `2435`
- Failures: `0`

## Summary

- Topics: `1488`
- Inferred / abstained: `169` / `1319`
- Inference rate: `11.4%`
- Proxy disagreement rows: `123`
- Deterministic fixture checks: `2/2`

Proxy disagreement means the deterministic candidate and a non-gold comparison dimension differ. It is a review signal, not a ground-truth error.

## Topic ledger

| ID | State | Topic | Primary | Signals | Lane | Reasons |
|---:|---|---|---|---:|---|---|
| 7 | candidate | Mixed News Headlines | abstain | 12 | abstained | ambiguous_subject_geo |
| 8 | candidate | Greek News Roundup | abstain | 11 | abstained | insufficient_subject_evidence |
| 10 | active | Ukraine War Updates | abstain | 270 | abstained | ambiguous_subject_geo |
| 11 | candidate | Vietnam News Roundup | abstain | 10 | abstained | insufficient_subject_evidence |
| 12 | candidate | Turkey News Roundup | abstain | 8 | abstained | ambiguous_subject_geo |
| 14 | active | Violent Crimes in Uruguay | abstain | 114 | abstained | ambiguous_subject_geo |
| 15 | candidate | Brazil News Roundup | abstain | 19 | abstained | ambiguous_subject_geo |
| 16 | candidate | Stock Price Movements | abstain | 12 | abstained | insufficient_subject_evidence |
| 18 | candidate | Indonesian News Roundup | ID | 13 | inferred | anchor_corroborated_subject_geo |
| 19 | candidate | Noticias Regionales Variadas | abstain | 24 | abstained | insufficient_subject_evidence |
| 20 | active | Israel Lebanon Withdrawal Dispute | abstain | 108 | abstained | ambiguous_subject_geo |
| 21 | active | Cronaca e Incidenti | abstain | 376 | abstained | ambiguous_subject_geo |
| 22 | candidate | Romanian News Roundup | abstain | 8 | abstained | ambiguous_subject_geo |
| 23 | candidate | News Headlines Mix | abstain | 9 | abstained | insufficient_subject_evidence |
| 27 | candidate | Iraqi News and Culture | abstain | 24 | abstained | ambiguous_subject_geo |
| 28 | active | Trump Abandons Weaponization Fund | US | 38 | inferred | headline_geo_consensus |
| 29 | candidate | Saudi Company Information | abstain | 0 | abstained | insufficient_subject_evidence |
| 30 | active | Q2 2026 Earnings Announcements | abstain | 69 | abstained | ambiguous_subject_geo |
| 33 | candidate | Vancouver Real Estate Listings | abstain | 24 | abstained | insufficient_subject_evidence |
| 34 | active | Securities Class Action Lawsuits | abstain | 75 | abstained | ambiguous_subject_geo |
| 37 | active | Major Russian Strikes on Ukraine | abstain | 56 | abstained | ambiguous_subject_geo |
| 38 | candidate | Vietnamese News Headlines | abstain | 10 | abstained | insufficient_subject_evidence |
| 39 | candidate | WH Correspondents Dinner Rescheduled | abstain | 0 | abstained | insufficient_subject_evidence |
| 40 | candidate | Economic and Market Trends | abstain | 9 | abstained | insufficient_subject_evidence |
| 43 | active | Escaped Inmate Found Dead | abstain | 61 | abstained | ambiguous_subject_geo |
| 46 | candidate | Maori Language Waka Tour | abstain | 0 | abstained | insufficient_subject_evidence |
| 49 | active | US Iran Exchange Strikes | IR | 37 | inferred | headline_geo_consensus |
| 50 | active | US Strikes Iran Retaliation | abstain | 35 | abstained | ambiguous_subject_geo |
| 51 | active | 2026 Primary Election Results | abstain | 24 | abstained | ambiguous_subject_geo |
| 52 | active | Cepeda Concedes to De la Espriella | abstain | 659 | abstained | ambiguous_subject_geo |
| 56 | active | Legal and Historical Reflections | abstain | 50 | abstained | ambiguous_subject_geo |
| 66 | active | Cyclosporiasis Outbreak in US | abstain | 54 | abstained | ambiguous_subject_geo |
| 68 | candidate | The Christophers Film Review | abstain | 0 | abstained | insufficient_subject_evidence |
| 71 | candidate | Dominican Republic News | US | 23 | junk | headline_geo_consensus |
| 76 | candidate | Zimbabwe News Roundup | abstain | 8 | abstained | ambiguous_subject_geo |
| 77 | candidate | News from Buryatia | abstain | 14 | abstained | insufficient_subject_evidence |
| 81 | candidate | Negative Gearing Housing Crisis | abstain | 0 | abstained | insufficient_subject_evidence |
| 83 | active | Philippines 7.8 Earthquake Tsunami | abstain | 42 | abstained | ambiguous_subject_geo |
| 84 | candidate | ACT Public Sector Issues | abstain | 15 | junk | ambiguous_subject_geo |
| 90 | active | Trump FIFA World Cup Scandal | abstain | 48 | abstained | ambiguous_subject_geo |
| 92 | candidate | Health Hero Campaign | abstain | 0 | abstained | insufficient_subject_evidence |
| 93 | candidate | LA Mayoral Runoff | abstain | 0 | abstained | insufficient_subject_evidence |
| 96 | active | Côte d'Ivoire Public Service | abstain | 56 | abstained | ambiguous_subject_geo |
| 98 | candidate | Ancestry Reveals Irish Past | abstain | 0 | abstained | insufficient_subject_evidence |
| 104 | active | Maine Senate Primary Results | abstain | 10 | abstained | insufficient_subject_evidence |
| 109 | candidate | New Zealand News Roundup | abstain | 7 | abstained | insufficient_subject_evidence |
| 112 | active | Indian Sailors Killed in US Strikes Off Oman | abstain | 11 | abstained | ambiguous_subject_geo |
| 115 | active | Mundial 2026 Coverage | abstain | 58 | abstained | ambiguous_subject_geo |
| 121 | active | US Bombards Iran Over Ormuz Attack | abstain | 67 | abstained | ambiguous_subject_geo |
| 124 | candidate | iPhone Fertility Link | abstain | 0 | abstained | insufficient_subject_evidence |
| 127 | active | Guo Wengui Sentenced | abstain | 15 | abstained | insufficient_subject_evidence |
| 129 | candidate | David Hockney Death | abstain | 0 | abstained | insufficient_subject_evidence |
| 131 | candidate | Stock Price Moving Average Crossovers | abstain | 11 | abstained | ambiguous_subject_geo |
| 153 | active | Venezuela Earthquake Tragedy | abstain | 52 | abstained | insufficient_subject_evidence |
| 155 | candidate | High Class Canadian Tunes | abstain | 0 | abstained | insufficient_subject_evidence |
| 159 | candidate | Food Product Recalls | abstain | 0 | abstained | insufficient_subject_evidence |
| 164 | candidate | Daily News Roundup | abstain | 9 | abstained | insufficient_subject_evidence |
| 165 | candidate | Venezuela Weather and Dollar | VE | 24 | inferred | headline_geo_consensus |
| 177 | candidate | Manly Sea Eagles Reputation | abstain | 0 | abstained | insufficient_subject_evidence |
| 184 | active | Putin and Philippines at ASEAN | abstain | 126 | abstained | ambiguous_subject_geo |
| 193 | candidate | Whistler Blackcomb Ski Secrets | abstain | 0 | abstained | insufficient_subject_evidence |
| 203 | active | Molotov Attack on Lawyer's Home | abstain | 39 | abstained | ambiguous_subject_geo |
| 205 | candidate | From My Grandmother's Garden | abstain | 0 | abstained | insufficient_subject_evidence |
| 216 | active | Dembele Hat-Trick Powers France | abstain | 18 | abstained | ambiguous_subject_geo |
| 220 | candidate | News Headlines Cluster | abstain | 12 | abstained | insufficient_subject_evidence |
| 223 | candidate | TV Program Listings | abstain | 11 | abstained | ambiguous_subject_geo |
| 224 | active | Тищенко Застава 10 млн | abstain | 95 | abstained | ambiguous_subject_geo |
| 226 | active | Qatargate Immunity Request | abstain | 9 | abstained | insufficient_subject_evidence |
| 227 | active | Ekurhuleni Officials Granted Bail | abstain | 14 | abstained | insufficient_subject_evidence |
| 229 | active | South Korea World Cup Loss | abstain | 128 | abstained | ambiguous_subject_geo |
| 230 | active | FIFA Suspends Balogun Red Card | abstain | 36 | abstained | ambiguous_subject_geo |
| 233 | active | Suiza Elimina a Colombia | abstain | 9 | abstained | ambiguous_subject_geo |
| 235 | active | India-Pakistan UN J&K Dispute | abstain | 50 | abstained | ambiguous_subject_geo |
| 237 | candidate | Lottery Results and Weather | abstain | 13 | abstained | insufficient_subject_evidence |
| 239 | active | First Ebola Case in France | abstain | 16 | abstained | insufficient_subject_evidence |
| 242 | active | Venezuela Earthquakes Cause Collapse | VE | 32 | inferred | headline_geo_consensus |
| 245 | active | Albanian Anti-Government Protests | abstain | 93 | abstained | ambiguous_subject_geo |
| 246 | active | Egypt vs Iran World Cup 2026 | abstain | 25 | abstained | ambiguous_subject_geo |
| 248 | active | Venezuela Earthquake Death Toll | VE | 20 | inferred | anchor_corroborated_subject_geo |
| 250 | candidate | Chris Meledandri Profile | abstain | 0 | abstained | insufficient_subject_evidence |
| 254 | active | EU Extends Russia Sanctions | abstain | 67 | abstained | ambiguous_subject_geo |
| 256 | active | Russian Air Defense Shoots Down Ukrainian Drones | RU | 11 | inferred | anchor_corroborated_subject_geo |
| 258 | active | US Aid to Venezuela | VE | 36 | inferred | headline_geo_consensus |
| 260 | active | Ukraine War Escalation | abstain | 192 | abstained | ambiguous_subject_geo |
| 264 | active | NDC Deregistration Controversy | abstain | 27 | abstained | ambiguous_subject_geo |
| 271 | active | Ranucci Attack Investigation | abstain | 210 | abstained | ambiguous_subject_geo |
| 277 | active | Supreme Court Rulings Against Trump | abstain | 17 | abstained | ambiguous_subject_geo |
| 278 | active | High Temperature Warning | abstain | 14 | abstained | insufficient_subject_evidence |
| 280 | candidate | Colorado Redistricting Ruling | abstain | 0 | abstained | insufficient_subject_evidence |
| 282 | active | Mali Attacks Escalate | abstain | 37 | abstained | ambiguous_subject_geo |
| 283 | candidate | Ja Morant Trade | abstain | 0 | abstained | insufficient_subject_evidence |
| 285 | candidate | San Francisco Archdiocese Abuse Settlement | abstain | 0 | abstained | insufficient_subject_evidence |
| 286 | candidate | NBA Gambling Charges | abstain | 0 | abstained | insufficient_subject_evidence |
| 290 | candidate | Akal Takht Anti-Sacrilege Law Deadline | abstain | 0 | abstained | insufficient_subject_evidence |
| 292 | active | Mumbai Heavy Rain Red Alert | abstain | 51 | abstained | ambiguous_subject_geo |
| 293 | active | Pune Toddler Rape-Murder Death Penalty | abstain | 276 | abstained | ambiguous_subject_geo |
| 295 | active | Bombay HC on Protest Rights | abstain | 30 | abstained | ambiguous_subject_geo |
| 298 | candidate | CBSE Revaluation Dispute | abstain | 0 | abstained | insufficient_subject_evidence |
| 299 | active | Drunk Driver Hits Family in Kaliningrad | abstain | 37 | abstained | ambiguous_subject_geo |
| 300 | active | Ukraine Conflict Escalation | abstain | 92 | abstained | ambiguous_subject_geo |
| 301 | candidate | High Scores on Unified State Exam | abstain | 10 | abstained | ambiguous_subject_geo |
| 302 | active | Ukraine Drone Incident Constanta | abstain | 18 | abstained | insufficient_subject_evidence |
| 303 | candidate | Kyrgyzstan News Roundup | abstain | 19 | abstained | insufficient_subject_evidence |
| 304 | active | Russia Ukraine Conflict Narratives | abstain | 284 | abstained | ambiguous_subject_geo |
| 306 | candidate | First LGBT Verdict | abstain | 0 | abstained | insufficient_subject_evidence |
| 307 | active | Drone Attacks on Moscow | RU | 101 | inferred | headline_geo_consensus |
| 308 | active | Russia Preparing Massive Strike | abstain | 17 | abstained | insufficient_subject_evidence |
| 309 | active | Attack on Traffic Police in Moscow | abstain | 22 | abstained | ambiguous_subject_geo |
| 310 | candidate | Alaska Ballot Name Ruling | abstain | 0 | abstained | insufficient_subject_evidence |
| 311 | active | Germany Denies Taurus to Ukraine | abstain | 105 | abstained | ambiguous_subject_geo |
| 312 | active | Syria US Terror List | abstain | 62 | abstained | ambiguous_subject_geo |
| 314 | candidate | Death of Figure Skater Artur Dmitriev | abstain | 0 | abstained | insufficient_subject_evidence |
| 316 | candidate | FAS Cartel in Housing | abstain | 0 | abstained | insufficient_subject_evidence |
| 317 | candidate | FSB Prevents Synagogue Attack | abstain | 0 | abstained | insufficient_subject_evidence |
| 318 | active | Monaco Bombing Suspect | abstain | 18 | abstained | insufficient_subject_evidence |
| 319 | candidate | Cyprus Political Disputes | abstain | 9 | abstained | insufficient_subject_evidence |
| 320 | active | 17-Year-Old British Teen Fall | abstain | 150 | abstained | ambiguous_subject_geo |
| 322 | active | Jeffrey Donaldson Review | abstain | 16 | abstained | insufficient_subject_evidence |
| 324 | candidate | Crime Drama Recommendations | abstain | 9 | abstained | ambiguous_subject_geo |
| 328 | candidate | Microwaved Squishy Toy Burns | abstain | 0 | abstained | insufficient_subject_evidence |
| 329 | candidate | Ben Stokes Retires | abstain | 0 | abstained | insufficient_subject_evidence |
| 330 | candidate | Andy Burnham Number 10 North Plan | abstain | 0 | abstained | insufficient_subject_evidence |
| 331 | candidate | Sainsbury's Lifetime Ban | abstain | 0 | abstained | insufficient_subject_evidence |
| 332 | candidate | Enzo Maresca to Man City | abstain | 0 | abstained | insufficient_subject_evidence |
| 333 | candidate | Aldi Sunscreen Best | abstain | 0 | abstained | insufficient_subject_evidence |
| 335 | candidate | Travel Scam Warnings | abstain | 7 | abstained | insufficient_subject_evidence |
| 336 | candidate | UK Property Listings | abstain | 21 | abstained | insufficient_subject_evidence |
| 337 | active | EU Loan for Ukraine Arms | abstain | 34 | abstained | ambiguous_subject_geo |
| 339 | candidate | Καύσωνας στη Βρετανία | abstain | 0 | abstained | insufficient_subject_evidence |
| 340 | active | France Heatwave Death Toll | DE | 8 | inferred | headline_geo_consensus |
| 342 | active | European Heatwave Deaths | abstain | 22 | abstained | insufficient_subject_evidence |
| 345 | active | Germany Shooting Incident | LB | 28 | inferred |  |
| 347 | active | Heatwave Deaths in Germany | DE | 21 | inferred | headline_geo_consensus |
| 350 | active | Heatwave Impacts and Disasters | abstain | 208 | abstained | ambiguous_subject_geo |
| 351 | candidate | Lena Schätte Wins Bachmann Prize | abstain | 0 | abstained | insufficient_subject_evidence |
| 352 | candidate | Flugzeugabsturz in Frankreich | abstain | 0 | abstained | insufficient_subject_evidence |
| 353 | active | Incêndio Florestal na Espanha | abstain | 16 | abstained | ambiguous_subject_geo |
| 354 | candidate | Stade Shooting | abstain | 0 | abstained | insufficient_subject_evidence |
| 355 | active | Atac Armat în Stade | abstain | 13 | abstained | insufficient_subject_evidence |
| 356 | active | Yellow Alert for Storms | abstain | 58 | abstained | insufficient_subject_evidence |
| 357 | active | Deadly Crash in Mykolaiv | abstain | 97 | abstained | ambiguous_subject_geo |
| 358 | candidate | Deadly Shooting in Stade | abstain | 10 | abstained | ambiguous_subject_geo |
| 360 | active | Depot Store Closures | abstain | 11 | abstained | insufficient_subject_evidence |
| 362 | candidate | Germany Youth Center Shooting | abstain | 0 | abstained | insufficient_subject_evidence |
| 363 | candidate | Germany Heat Records | abstain | 0 | abstained | insufficient_subject_evidence |
| 364 | active | Kitesurfer Body Found in Libya | abstain | 24 | abstained | insufficient_subject_evidence |
| 366 | active | Dayanne Rodrigues Disappearance | abstain | 20 | abstained | insufficient_subject_evidence |
| 367 | active | African Heatwave Italy | abstain | 39 | abstained | insufficient_subject_evidence |
| 368 | active | Football Transfer News | abstain | 70 | abstained | ambiguous_subject_geo |
| 369 | active | Missing 74-Year-Old Found Dead | abstain | 14 | abstained | insufficient_subject_evidence |
| 370 | active | Eleni Menegaki Family Vacation | abstain | 15 | abstained | insufficient_subject_evidence |
| 371 | candidate | Record Heat Wave Europe | abstain | 8 | abstained | insufficient_subject_evidence |
| 372 | active | Trump Attacks Meloni | abstain | 16 | abstained | insufficient_subject_evidence |
| 373 | active | Omicidio a Santadi per Droga | abstain | 82 | abstained | ambiguous_subject_geo |
| 374 | active | Grecia Incendii și Amenzi | abstain | 20 | abstained | insufficient_subject_evidence |
| 375 | active | European Heatwave Crisis | abstain | 22 | abstained | insufficient_subject_evidence |
| 376 | candidate | Bocelli Villa Theft | abstain | 0 | abstained | insufficient_subject_evidence |
| 377 | candidate | Vespa 80th Anniversary Parade | abstain | 0 | abstained | insufficient_subject_evidence |
| 378 | active | Zelenskyy Talks with Trump and Macron | abstain | 15 | abstained | ambiguous_subject_geo |
| 379 | active | Ali Hamaney Cenaze Töreni | abstain | 17 | abstained | ambiguous_subject_geo |
| 381 | candidate | Jean Hanlon Murder Verdict | abstain | 17 | abstained | insufficient_subject_evidence |
| 382 | active | Deniz Göktaş Arrest | abstain | 73 | abstained | ambiguous_subject_geo |
| 383 | active | Romania Demands Drone Reprogramming | abstain | 37 | abstained | ambiguous_subject_geo |
| 384 | active | İstanbul Su Kesintileri | TR | 13 | inferred | headline_geo_consensus |
| 385 | active | Accidents and Tragedies | abstain | 82 | abstained | ambiguous_subject_geo |
| 386 | active | Akaryakıt ve Döviz Fiyatları | abstain | 27 | abstained | ambiguous_subject_geo |
| 387 | active | Ukraine Germany Men Return | abstain | 9 | abstained | insufficient_subject_evidence |
| 388 | candidate | Daily Horoscope Predictions | abstain | 10 | abstained | insufficient_subject_evidence |
| 390 | active | NATO Summit Ankara | TR | 28 | inferred |  |
| 391 | candidate | Daily Horoscope Predictions | abstain | 12 | abstained | insufficient_subject_evidence |
| 392 | active | Turkey S-400 Resale Talks | abstain | 35 | abstained | ambiguous_subject_geo |
| 393 | candidate | OPEKEPE Sentencing | abstain | 0 | abstained | insufficient_subject_evidence |
| 395 | active | Nancy Plane Crash | FR | 13 | inferred | headline_geo_consensus |
| 397 | active | Father Dies Saving Children | abstain | 27 | abstained | insufficient_subject_evidence |
| 398 | candidate | France Skydiving Plane Crash | abstain | 0 | abstained | insufficient_subject_evidence |
| 400 | active | France Heat Wave Deaths | abstain | 9 | abstained | ambiguous_subject_geo |
| 402 | active | Waldbrände in Südfrankreich | abstain | 34 | abstained | ambiguous_subject_geo |
| 403 | active | Heatwave Drownings in France | abstain | 49 | abstained | insufficient_subject_evidence |
| 404 | candidate | China Shoe Factory Fire | abstain | 14 | abstained | insufficient_subject_evidence |
| 405 | active | June Heatwave Death Toll | abstain | 9 | abstained | ambiguous_subject_geo |
| 406 | candidate | Paris Heatwave Mortuaries | abstain | 0 | abstained | insufficient_subject_evidence |
| 407 | active | Canicule Vigilance Orange | abstain | 59 | abstained | ambiguous_subject_geo |
| 409 | candidate | World Cup 2026 Round of 32 | abstain | 10 | abstained | ambiguous_subject_geo |
| 410 | active | Venezuela Earthquake Rescues | abstain | 11 | abstained | insufficient_subject_evidence |
| 411 | candidate | Plane Crash in France | abstain | 0 | abstained | insufficient_subject_evidence |
| 412 | candidate | Tour de France 2026 Coverage | FR | 9 | inferred | headline_geo_consensus |
| 413 | candidate | Paris Diamond League Highlights | abstain | 0 | abstained | insufficient_subject_evidence |
| 415 | active | France Heatwave and Violence | abstain | 41 | abstained | ambiguous_subject_geo |
| 417 | active | Sports and Politics Mix | abstain | 87 | abstained | ambiguous_subject_geo |
| 419 | active | GDP Growth Forecast Raised | abstain | 26 | abstained | ambiguous_subject_geo |
| 420 | active | Zamora River Flooding | abstain | 71 | abstained | ambiguous_subject_geo |
| 421 | candidate | Celebrity Emotional Statements | abstain | 14 | junk | ambiguous_subject_geo |
| 422 | active | Feijóo Absentismo Laboral Polémica | abstain | 79 | abstained | ambiguous_subject_geo |
| 424 | active | Venezuela Earthquake Aftermath | abstain | 11 | abstained | insufficient_subject_evidence |
| 425 | candidate | Stade Massacre Turkish Fugitive | abstain | 13 | abstained | insufficient_subject_evidence |
| 426 | active | Aldo Montano Anaphylactic Shock | abstain | 45 | abstained | ambiguous_subject_geo |
| 427 | active | Isaac Del Toro Wins Tour de France Stage | abstain | 11 | abstained | insufficient_subject_evidence |
| 428 | candidate | Mafia Capo Arrested in Soria | abstain | 0 | abstained | insufficient_subject_evidence |
| 429 | active | PP-Vox Pact in Andalusia | abstain | 61 | abstained | ambiguous_subject_geo |
| 432 | active | Russia Imports Aviation Fuel | abstain | 127 | abstained | ambiguous_subject_geo |
| 433 | candidate | Church Holidays July 5 | abstain | 22 | junk | insufficient_subject_evidence |
| 435 | candidate | Daily Combat Reports | abstain | 19 | junk | insufficient_subject_evidence |
| 436 | active | Russia-Ukraine Military Escalation | KW | 22 | inferred |  |
| 439 | active | Ukraine War Escalation | abstain | 40 | abstained | ambiguous_subject_geo |
| 442 | candidate | Israel News Roundup | abstain | 16 | abstained | ambiguous_subject_geo |
| 443 | active | Russian Attacks on Zaporizhzhia | abstain | 22 | abstained | insufficient_subject_evidence |
| 445 | active | SBU Thwarts Sabotage in Lviv | abstain | 22 | abstained | ambiguous_subject_geo |
| 446 | active | Russia Captures Bogodarovka | abstain | 9 | abstained | ambiguous_subject_geo |
| 447 | active | Power Outage Updates Ukraine | abstain | 40 | abstained | ambiguous_subject_geo |
| 448 | active | Russian Attacks on Ukraine | abstain | 35 | abstained | insufficient_subject_evidence |
| 449 | active | Monaco Assassination Attempt | abstain | 55 | abstained | ambiguous_subject_geo |
| 450 | active | Power Outages June 30 | abstain | 24 | abstained | ambiguous_subject_geo |
| 451 | candidate | Dasha Kvitkova Wedding | abstain | 0 | abstained | insufficient_subject_evidence |
| 452 | active | Ukraine War Updates | abstain | 37 | abstained | ambiguous_subject_geo |
| 453 | active | Monaco Oligarch Attack | abstain | 25 | abstained | insufficient_subject_evidence |
| 454 | active | Russian Fuel Shortages | abstain | 14 | abstained | insufficient_subject_evidence |
| 455 | active | Ukraine Conflict Escalation | abstain | 46 | abstained | ambiguous_subject_geo |
| 456 | active | Допрос Павла Дурова во Франции | abstain | 18 | abstained | ambiguous_subject_geo |
| 457 | active | Ukraine Conflict Casualties | abstain | 197 | abstained | ambiguous_subject_geo |
| 458 | active | Wildfire Outbreak in Greece | abstain | 67 | abstained | insufficient_subject_evidence |
| 459 | candidate | Kissamos Ship Grounding | abstain | 0 | abstained | insufficient_subject_evidence |
| 460 | active | Tasoulas Letter to Trump | abstain | 25 | abstained | insufficient_subject_evidence |
| 461 | candidate | Russian Prank on Greek Advisor | abstain | 12 | abstained | insufficient_subject_evidence |
| 463 | candidate | Widow Pensions Reform | abstain | 12 | abstained | insufficient_subject_evidence |
| 465 | candidate | Metro Line 3 Schedule Changes | abstain | 0 | abstained | insufficient_subject_evidence |
| 466 | active | Heraklion Child Attack | abstain | 15 | abstained | insufficient_subject_evidence |
| 467 | active | MRB Poll: ND Leads ELAS | abstain | 13 | abstained | insufficient_subject_evidence |
| 468 | active | Chinese Translator Disappearance | abstain | 10 | abstained | insufficient_subject_evidence |
| 470 | candidate | Fire in Spathovouni Corinth | abstain | 0 | abstained | insufficient_subject_evidence |
| 471 | candidate | Athens Stock Exchange Rally | abstain | 18 | abstained | insufficient_subject_evidence |
| 472 | candidate | Mitsotakis Inaugurates ESY Upgrades | abstain | 40 | abstained | insufficient_subject_evidence |
| 473 | candidate | 15-Year-Old Catches 158 Toxic Fish | abstain | 0 | abstained | insufficient_subject_evidence |
| 474 | candidate | Daily Events and Name Days | abstain | 25 | junk | insufficient_subject_evidence |
| 475 | candidate | Earthquakes in Lakonia | abstain | 0 | abstained | insufficient_subject_evidence |
| 476 | active | Petralona Building Collapse | abstain | 42 | abstained | insufficient_subject_evidence |
| 477 | active | Dog Dies After Eating Pufferfish | abstain | 22 | abstained | insufficient_subject_evidence |
| 478 | active | Oraiokastro Fire Arrest | abstain | 30 | abstained | insufficient_subject_evidence |
| 479 | candidate | Speedboat Fire in Vouliagmeni | abstain | 15 | abstained | insufficient_subject_evidence |
| 480 | active | Rhodes Fire Atavyros | abstain | 30 | abstained | insufficient_subject_evidence |
| 481 | candidate | Lifeguard Tower Collapse Kavala | abstain | 0 | abstained | insufficient_subject_evidence |
| 482 | candidate | Teen Saved by Mother CPR | abstain | 12 | abstained | insufficient_subject_evidence |
| 484 | active | Μουντιάλ 2026 Προκρίσεις | abstain | 12 | abstained | insufficient_subject_evidence |
| 497 | active | Turkey Offers Mediation | abstain | 13 | abstained | insufficient_subject_evidence |
| 499 | active | World Cup 2026 Quarterfinals | abstain | 43 | abstained | ambiguous_subject_geo |
| 500 | active | Floods and Wildfires in Manitoba and Alberta | abstain | 8 | abstained | insufficient_subject_evidence |
| 501 | candidate | Ontario Child Rabies Death | abstain | 0 | abstained | insufficient_subject_evidence |
| 502 | candidate | Ex-Husband Guilty of Murder | abstain | 0 | abstained | insufficient_subject_evidence |
| 503 | active | Health and Lifestyle Tips | abstain | 8 | abstained | insufficient_subject_evidence |
| 504 | candidate | Drake Janice Apology Parties | abstain | 0 | abstained | insufficient_subject_evidence |
| 506 | candidate | Horoscopes Weekly Predictions | abstain | 8 | abstained | insufficient_subject_evidence |
| 507 | active | China Disasters and Tensions | CN | 48 | inferred | headline_geo_consensus |
| 508 | candidate | Cina News Multitematiche | abstain | 12 | junk | insufficient_subject_evidence |
| 509 | candidate | Shio Keberuntungan dan Rezeki | abstain | 12 | junk | ambiguous_subject_geo |
| 513 | active | Venezuela Earthquake Disaster | abstain | 21 | abstained | ambiguous_subject_geo |
| 516 | active | Venezuela Earthquake Death Toll | VE | 44 | inferred | anchor_corroborated_subject_geo |
| 517 | active | Venezuela Earthquake Death Toll | VE | 17 | inferred | headline_geo_consensus |
| 518 | candidate | Venezuela Earthquake Death Toll | abstain | 0 | abstained | insufficient_subject_evidence |
| 519 | active | Tentato Omicidio a Ivrea | abstain | 83 | abstained | ambiguous_subject_geo |
| 523 | active | Spanish Deaths in Venezuela Earthquakes | VE | 46 | inferred | anchor_corroborated_subject_geo |
| 524 | active | Venezuela Survival Miracle | abstain | 12 | abstained | insufficient_subject_evidence |
| 525 | active | El Niño Threatens Peru | abstain | 24 | abstained | ambiguous_subject_geo |
| 526 | candidate | Venezuela Earthquake Death Toll | abstain | 0 | abstained | insufficient_subject_evidence |
| 528 | active | Venezuela Earthquake Death Toll | abstain | 27 | abstained | insufficient_subject_evidence |
| 530 | candidate | Mother Survives Rubble with Baby | abstain | 0 | abstained | insufficient_subject_evidence |
| 531 | active | Venezuela Earthquake Death Toll | VE | 9 | inferred | anchor_corroborated_subject_geo |
| 532 | active | England vs Mexico World Cup | abstain | 18 | abstained | ambiguous_subject_geo |
| 534 | active | Mundial 2026 Dieciseisavos | abstain | 98 | abstained | ambiguous_subject_geo |
| 535 | active | Roxana Guzmán Murder | abstain | 9 | abstained | insufficient_subject_evidence |
| 536 | candidate | Mundial 2026 Partidos | abstain | 24 | abstained | ambiguous_subject_geo |
| 537 | active | World Cup 2026 Results | abstain | 24 | abstained | ambiguous_subject_geo |
| 539 | active | Brazil vs Norway World Cup | abstain | 27 | abstained | ambiguous_subject_geo |
| 540 | active | Olympiacos Transfers and World Cup 2026 | abstain | 8 | abstained | insufficient_subject_evidence |
| 542 | candidate | Noticias del Edoméx | abstain | 22 | junk | ambiguous_subject_geo |
| 543 | candidate | El Chavo Félix Pleads Guilty | abstain | 0 | abstained | insufficient_subject_evidence |
| 544 | candidate | Mexican Batman Vigilante | abstain | 0 | abstained | insufficient_subject_evidence |
| 545 | candidate | Mexican Officials as US Informants | abstain | 0 | abstained | insufficient_subject_evidence |
| 546 | active | Hoy No Circula July 2026 | abstain | 11 | abstained | insufficient_subject_evidence |
| 547 | active | Sheinbaum Denies Political Motive | MX | 9 | inferred | headline_geo_consensus |
| 548 | active | World Cup 2026 Match Previews | abstain | 53 | abstained | ambiguous_subject_geo |
| 550 | active | Celebrity Reappearances and Rumors | abstain | 31 | abstained | ambiguous_subject_geo |
| 551 | active | Moto Bandera Marruecos Accidente | abstain | 106 | abstained | ambiguous_subject_geo |
| 553 | active | Violent Deaths and Crimes | abstain | 42 | abstained | insufficient_subject_evidence |
| 554 | active | Suiza Elimina a Colombia | abstain | 41 | abstained | ambiguous_subject_geo |
| 555 | candidate | Mega-Sena Lottery Results | abstain | 11 | abstained | insufficient_subject_evidence |
| 557 | active | Brazil Beats Japan | abstain | 18 | abstained | insufficient_subject_evidence |
| 558 | active | Egypt vs Australia World Cup | EG | 38 | inferred | anchor_corroborated_subject_geo |
| 559 | active | Weather Alerts in Brazil | abstain | 27 | abstained | ambiguous_subject_geo |
| 560 | candidate | Brazil Advances Past Japan | abstain | 0 | abstained | insufficient_subject_evidence |
| 564 | active | Anvisa Atualiza Vacinas Covid | abstain | 11 | abstained | insufficient_subject_evidence |
| 565 | active | Job and Course Openings | abstain | 50 | abstained | ambiguous_subject_geo |
| 566 | active | Crime and Corruption Investigations | abstain | 60 | abstained | ambiguous_subject_geo |
| 567 | active | Brasil vs Norwegia Piala Dunia 2026 | abstain | 25 | abstained | ambiguous_subject_geo |
| 568 | active | Iran Attacks on Bahrain and Kuwait | abstain | 18 | abstained | ambiguous_subject_geo |
| 569 | active | Strait of Hormuz Tensions | abstain | 140 | abstained | ambiguous_subject_geo |
| 572 | candidate | US-Iran Hostilities Paused | abstain | 0 | abstained | insufficient_subject_evidence |
| 573 | candidate | Trump Accuses Iran of Ceasefire Violation | abstain | 11 | abstained | insufficient_subject_evidence |
| 575 | active | US-Iran Ceasefire Tensions | abstain | 30 | abstained | ambiguous_subject_geo |
| 576 | active | Gold Drops Oil Rises | abstain | 8 | abstained | insufficient_subject_evidence |
| 578 | candidate | Oinoi Fire Emergency | abstain | 16 | abstained | insufficient_subject_evidence |
| 579 | candidate | US-Iran Strikes Exchange | abstain | 0 | abstained | insufficient_subject_evidence |
| 580 | candidate | Iran Regional Tensions | abstain | 0 | abstained | insufficient_subject_evidence |
| 581 | active | US-Iran Ceasefire Agreement | abstain | 13 | abstained | ambiguous_subject_geo |
| 582 | active | US-Iran Conflict Escalates | abstain | 10 | abstained | insufficient_subject_evidence |
| 583 | active | US-Iran Military Strikes | IR | 56 | inferred |  |
| 584 | active | Hezbollah Rejects Israel-Lebanon Deal | abstain | 12 | abstained | insufficient_subject_evidence |
| 585 | active | US Strikes Near Bushehr | abstain | 87 | abstained | ambiguous_subject_geo |
| 586 | active | Iran vs Egypt World Cup Draw | abstain | 38 | abstained | ambiguous_subject_geo |
| 590 | candidate | World Cup 2026 Knockout Stage | abstain | 6 | abstained | insufficient_subject_evidence |
| 592 | active | H5N1 Bird Flu in NSW | abstain | 22 | abstained | ambiguous_subject_geo |
| 593 | candidate | Bowan Park Horse Cruelty | abstain | 0 | abstained | insufficient_subject_evidence |
| 595 | candidate | Cliftleigh Home Invasion Stabbing | abstain | 0 | abstained | insufficient_subject_evidence |
| 596 | candidate | Bradman Best Blues Recall | abstain | 0 | abstained | insufficient_subject_evidence |
| 597 | candidate | Calvary Mater Hospital Legal Costs | abstain | 0 | abstained | insufficient_subject_evidence |
| 598 | active | Australia Social Media Penalties | abstain | 55 | abstained | ambiguous_subject_geo |
| 600 | candidate | Australian Farm Cost Changes | abstain | 0 | abstained | insufficient_subject_evidence |
| 601 | candidate | Daryl Braithwaite The Horses | abstain | 0 | abstained | insufficient_subject_evidence |
| 602 | candidate | Mid-Season Signings and Rallies | abstain | 0 | abstained | insufficient_subject_evidence |
| 603 | active | Doctor Icha Intimidation Case | abstain | 14 | abstained | ambiguous_subject_geo |
| 604 | active | Earthquake Reports Indonesia | abstain | 8 | abstained | insufficient_subject_evidence |
| 605 | active | Bupati Langkat Corruption Case | abstain | 22 | abstained | insufficient_subject_evidence |
| 606 | active | Piala Dunia 2026 | abstain | 22 | abstained | ambiguous_subject_geo |
| 607 | active | APBD Absorption Low | abstain | 18 | abstained | ambiguous_subject_geo |
| 608 | active | Three Police Killed in Drug Raid | abstain | 22 | abstained | ambiguous_subject_geo |
| 609 | candidate | Daily Updates July 3 2026 | abstain | 11 | junk | ambiguous_subject_geo |
| 610 | active | Jadwal Transportasi Jogja Juli 2026 | abstain | 56 | abstained | ambiguous_subject_geo |
| 611 | active | KPK OTT Bupati Langkat | abstain | 34 | abstained | ambiguous_subject_geo |
| 612 | active | TPA Jatiwaringin Fire Response | abstain | 81 | abstained | ambiguous_subject_geo |
| 613 | active | Sentul Raid Seizes Gold and Cash | abstain | 30 | abstained | insufficient_subject_evidence |
| 614 | active | IHSG Anjlok dan Aksi Jual Asing | abstain | 19 | abstained | ambiguous_subject_geo |
| 615 | active | DIY Home Decor Ideas | abstain | 9 | abstained | ambiguous_subject_geo |
| 616 | active | Nadiem Makarim Sentenced 10 Years | abstain | 17 | abstained | insufficient_subject_evidence |
| 617 | active | Peluncuran Program B50 | abstain | 24 | abstained | ambiguous_subject_geo |
| 618 | candidate | Indonesian News Headlines | abstain | 9 | abstained | ambiguous_subject_geo |
| 619 | candidate | GoCar Cancellation Fee Rp3,000 | abstain | 0 | abstained | insufficient_subject_evidence |
| 620 | candidate | Summer Heat and Storms | abstain | 8 | junk | insufficient_subject_evidence |
| 621 | candidate | South Korea News Roundup | abstain | 0 | abstained | insufficient_subject_evidence |
| 624 | candidate | July 3 Anniversary | abstain | 0 | junk | insufficient_subject_evidence |
| 625 | active | Egypt vs Australia World Cup | EG | 53 | inferred | headline_geo_consensus |
| 627 | active | Heatwave and Humidity Warning | abstain | 23 | abstained | ambiguous_subject_geo |
| 628 | active | Gold Prices in Egypt | EG | 22 | inferred | headline_geo_consensus |
| 629 | candidate | Fire in Kalochori Thessaloniki | abstain | 14 | abstained | insufficient_subject_evidence |
| 630 | candidate | Egyptian Pound Exchange Rates | abstain | 19 | abstained | ambiguous_subject_geo |
| 633 | candidate | Egyptian Pound Exchange Rates | abstain | 0 | abstained | insufficient_subject_evidence |
| 636 | active | Egypt's UN Stance on Sudan | SD | 22 | inferred | headline_geo_consensus |
| 637 | active | Tribal Mobilization Against Aggression | abstain | 20 | abstained | insufficient_subject_evidence |
| 639 | active | World Cup 2026 Updates | abstain | 14 | abstained | insufficient_subject_evidence |
| 640 | candidate | Weather Forecast July 5 | abstain | 0 | abstained | insufficient_subject_evidence |
| 642 | active | Weather Alerts Argentina | abstain | 18 | abstained | ambiguous_subject_geo |
| 643 | active | Libra Case Querellantes Removed | abstain | 24 | abstained | ambiguous_subject_geo |
| 644 | active | Argentina vs Cabo Verde World Cup 2026 | abstain | 22 | abstained | insufficient_subject_evidence |
| 646 | active | Karina Milei Reelección 2027 | AR | 44 | inferred | headline_geo_consensus |
| 647 | active | Dawlat Al-Tilawa Season 2 Launch | abstain | 9 | abstained | insufficient_subject_evidence |
| 649 | candidate | Daily Horoscopes | abstain | 0 | abstained | insufficient_subject_evidence |
| 650 | candidate | Daily Horoscope Predictions | abstain | 22 | abstained | insufficient_subject_evidence |
| 651 | candidate | New Hantavirus Variant in Argentina | abstain | 0 | abstained | insufficient_subject_evidence |
| 652 | candidate | Weather Forecasts June 29 | abstain | 0 | abstained | insufficient_subject_evidence |
| 653 | active | Sudan Conflict Updates | SD | 18 | inferred | headline_geo_consensus |
| 656 | active | Netanyahu Trial and Political Crisis | abstain | 138 | abstained | insufficient_subject_evidence |
| 659 | active | Israeli Airstrikes Kill Palestinians | abstain | 46 | abstained | ambiguous_subject_geo |
| 661 | candidate | Israel-Lebanon Agreement Rejection | abstain | 8 | abstained | insufficient_subject_evidence |
| 662 | active | PNL Congress Suspension | abstain | 17 | abstained | insufficient_subject_evidence |
| 663 | active | Gaza Casualty Toll Update | abstain | 8 | abstained | ambiguous_subject_geo |
| 664 | active | Israeli Attacks in Gaza | PS | 11 | inferred | headline_geo_consensus |
| 665 | candidate | Turkey Reacts to Israel's Armenian Genocide Recognition | abstain | 0 | abstained | insufficient_subject_evidence |
| 666 | active | Netanyahu Responds to Erdogan Threats | abstain | 13 | abstained | insufficient_subject_evidence |
| 667 | active | Poland Declassifies Military Aid to Ukraine | abstain | 159 | abstained | ambiguous_subject_geo |
| 668 | active | World Cup 2026 and Heatwave | abstain | 8 | abstained | insufficient_subject_evidence |
| 670 | candidate | Tour de France 2026 | abstain | 9 | abstained | insufficient_subject_evidence |
| 671 | candidate | Poland Lightning Strikes Fountain | abstain | 0 | abstained | insufficient_subject_evidence |
| 672 | active | Poland Demands Nazi Compensation | abstain | 23 | abstained | ambiguous_subject_geo |
| 673 | active | GNR Operations and Incidents | abstain | 150 | abstained | ambiguous_subject_geo |
| 675 | candidate | Colombia vs Portugal Match | abstain | 0 | abstained | insufficient_subject_evidence |
| 676 | active | Beşiktaş Transfer News | abstain | 31 | abstained | ambiguous_subject_geo |
| 677 | active | Portuguese Deaths in Venezuela Earthquake | VE | 10 | inferred | headline_geo_consensus |
| 678 | active | Brasil vs Japón Copa 2026 | abstain | 53 | abstained | ambiguous_subject_geo |
| 683 | candidate | Manga Volume & Cover News | abstain | 112 | junk | insufficient_subject_evidence |
| 686 | active | Wildfire in Nea Kallikrateia | abstain | 24 | abstained | insufficient_subject_evidence |
| 688 | active | Gasoline Price Drop | abstain | 18 | abstained | ambiguous_subject_geo |
| 689 | active | Hanoi Adjacent House Fire | abstain | 17 | abstained | insufficient_subject_evidence |
| 690 | active | Bão Số 1 Maysak | abstain | 9 | abstained | insufficient_subject_evidence |
| 691 | active | Gold Price Fluctuations | abstain | 23 | abstained | ambiguous_subject_geo |
| 692 | candidate | World Cup 2026 Coverage | abstain | 8 | abstained | ambiguous_subject_geo |
| 695 | candidate | France-Paraguay Match Controversy | FR | 18 | inferred | headline_geo_consensus |
| 699 | active | Financial and Legal Advice | abstain | 132 | abstained | ambiguous_subject_geo |
| 700 | active | ADC 2027 Election Alarms | abstain | 24 | abstained | ambiguous_subject_geo |
| 703 | active | Peter Obi 2027 Ambition | NG | 17 | inferred | headline_geo_consensus |
| 706 | active | Oyo Pupils Rescue Update | abstain | 66 | abstained | ambiguous_subject_geo |
| 708 | active | Ex-Navy Chief Arrested | abstain | 71 | abstained | ambiguous_subject_geo |
| 710 | active | Emefiele Fraud Trial | abstain | 23 | abstained | ambiguous_subject_geo |
| 711 | candidate | Terrorists Arrested After Hajj | abstain | 0 | abstained | insufficient_subject_evidence |
| 713 | active | Demisia Premierului Munteanu | abstain | 15 | abstained | insufficient_subject_evidence |
| 714 | active | Political Blocaj Continues | abstain | 15 | abstained | insufficient_subject_evidence |
| 715 | active | Bacalaureat Fraud Investigation | abstain | 10 | abstained | insufficient_subject_evidence |
| 716 | candidate | World Cup 2026 Results | abstain | 0 | abstained | insufficient_subject_evidence |
| 717 | active | Καύσωνας και Καιρός | abstain | 538 | abstained | ambiguous_subject_geo |
| 721 | candidate | Instructor Salta de Avión | abstain | 10 | junk | ambiguous_subject_geo |
| 722 | candidate | Lena Schätte Wins Bachmann Prize | abstain | 40 | junk | ambiguous_subject_geo |
| 725 | candidate | Argentina vs Suiza Cuartos | AR | 41 | inferred | headline_geo_consensus |
| 727 | active | Colombia World Cup 2026 | abstain | 8 | abstained | insufficient_subject_evidence |
| 728 | candidate | Ξυλοδαρμός 14χρονου στην Αχαΐα | abstain | 24 | abstained | insufficient_subject_evidence |
| 729 | candidate | Colombia News July 2026 | abstain | 9 | abstained | ambiguous_subject_geo |
| 731 | active | Canicule en Belgique | abstain | 259 | abstained | ambiguous_subject_geo |
| 732 | active | Germany Policy Changes | abstain | 26 | abstained | ambiguous_subject_geo |
| 733 | active | World Cup 2026 Matches | abstain | 48 | abstained | ambiguous_subject_geo |
| 734 | active | Pope's Message on Immigration | abstain | 40 | abstained | ambiguous_subject_geo |
| 736 | active | NATO Zirvesi ve Trump Netanyahu Görüşmesi | TR | 44 | inferred |  |
| 737 | active | Morocco World Cup 2026 | MA | 25 | inferred | anchor_corroborated_subject_geo |
| 739 | active | Fas Hollanda'yı Eledi | abstain | 141 | abstained | ambiguous_subject_geo |
| 740 | active | World Cup 2026 Updates | abstain | 8 | abstained | insufficient_subject_evidence |
| 741 | candidate | 2026 World Cup Updates | abstain | 5 | abstained | ambiguous_subject_geo |
| 742 | candidate | Japan News and Culture | abstain | 88 | abstained | ambiguous_subject_geo |
| 743 | candidate | Cody Gakpo Family Tragedy | abstain | 0 | abstained | insufficient_subject_evidence |
| 744 | active | Justice and Violence Protests | abstain | 15 | abstained | ambiguous_subject_geo |
| 745 | active | Yemen Conflict Analysis | abstain | 58 | abstained | ambiguous_subject_geo |
| 747 | candidate | US-Iran Conflict Escalation | abstain | 24 | abstained | insufficient_subject_evidence |
| 749 | candidate | Punjabi Tribune Authors | abstain | 5 | abstained | insufficient_subject_evidence |
| 751 | candidate | Pakistan Security Attacks | abstain | 0 | abstained | insufficient_subject_evidence |
| 753 | active | Strait of Hormuz Tanker Attacks | abstain | 159 | abstained | ambiguous_subject_geo |
| 755 | active | NATO Summit in Ankara | abstain | 74 | abstained | ambiguous_subject_geo |
| 756 | candidate | Casa di Silvia Inauguration | abstain | 10 | junk | insufficient_subject_evidence |
| 757 | candidate | European Heatwave Records | abstain | 9 | abstained | insufficient_subject_evidence |
| 759 | active | Heatwave and Green Initiatives | abstain | 84 | abstained | ambiguous_subject_geo |
| 760 | active | Khamenei Funeral Sons Absent | abstain | 29 | abstained | insufficient_subject_evidence |
| 761 | active | Bulgaria Political and Economic News | abstain | 49 | abstained | ambiguous_subject_geo |
| 762 | candidate | BNT News Broadcasts | abstain | 13 | junk | insufficient_subject_evidence |
| 766 | candidate | Charleen Murphy Love Island | abstain | 11 | junk | insufficient_subject_evidence |
| 769 | candidate | Algérie Qualification Coupe du Monde 2026 | abstain | 2 | abstained | ambiguous_subject_geo |
| 771 | active | Saudi Aramco Helicopter Crash | abstain | 12 | abstained | insufficient_subject_evidence |
| 773 | candidate | Saudi Helicopter Crash | abstain | 0 | abstained | insufficient_subject_evidence |
| 777 | active | Israel-Lebanon Framework Agreement | abstain | 9 | abstained | ambiguous_subject_geo |
| 778 | candidate | Christian Villages Annexation Claim | abstain | 8 | abstained | ambiguous_subject_geo |
| 783 | active | World Cup 2026 Matches | abstain | 17 | abstained | ambiguous_subject_geo |
| 784 | candidate | Cabo Verde Captain Rape Allegations | abstain | 0 | abstained | insufficient_subject_evidence |
| 785 | active | Black Caps vs England Test Series | abstain | 68 | abstained | ambiguous_subject_geo |
| 786 | active | Anti-Immigrant Violence in South Africa | ZA | 29 | inferred | headline_geo_consensus |
| 787 | active | Marruecos Golea a Canadá | abstain | 28 | abstained | ambiguous_subject_geo |
| 789 | candidate | Μουντιάλ 2026: Μεξικό vs Αγγλία | abstain | 14 | abstained | insufficient_subject_evidence |
| 791 | candidate | World Cup 2026 Match Schedules | abstain | 12 | junk | ambiguous_subject_geo |
| 793 | candidate | Celebrity Personal Struggles | abstain | 23 | junk | insufficient_subject_evidence |
| 794 | active | Service Disruptions in Lima | abstain | 25 | abstained | ambiguous_subject_geo |
| 795 | candidate | Serbia President Resigns | abstain | 0 | abstained | insufficient_subject_evidence |
| 797 | candidate | Thailand Suitcase Murder | abstain | 0 | abstained | insufficient_subject_evidence |
| 798 | candidate | Thai News Roundup | abstain | 7 | abstained | insufficient_subject_evidence |
| 801 | candidate | World Cup 2026 Round of 16 | FR | 9 | inferred | headline_geo_consensus |
| 802 | candidate | Iran Threatens US Over Hormuz | abstain | 3 | abstained | insufficient_subject_evidence |
| 804 | candidate | News Headlines Variety | abstain | 24 | abstained | insufficient_subject_evidence |
| 806 | active | Brasil vs Noruega Mundial 2026 | abstain | 101 | abstained | ambiguous_subject_geo |
| 807 | active | NATO Summit Preparations | abstain | 14 | abstained | insufficient_subject_evidence |
| 808 | active | Electoral Code Dispute | abstain | 54 | abstained | ambiguous_subject_geo |
| 810 | candidate | Pilot Suicide Mid-Flight | abstain | 12 | abstained | insufficient_subject_evidence |
| 812 | candidate | Sevgül Uludağ Death | abstain | 0 | abstained | insufficient_subject_evidence |
| 813 | candidate | Cyprus Child Deaths in Car | abstain | 0 | abstained | insufficient_subject_evidence |
| 814 | candidate | Hungarian News Roundup | abstain | 20 | abstained | insufficient_subject_evidence |
| 815 | candidate | European Heatwave Crisis | abstain | 13 | abstained | insufficient_subject_evidence |
| 816 | active | Ukraine EU Membership Tensions | abstain | 23 | abstained | ambiguous_subject_geo |
| 818 | candidate | Trump Iran Meeting Doha | abstain | 0 | abstained | insufficient_subject_evidence |
| 819 | active | Croacia vs Ghana Mundial 2026 | GB | 9 | inferred | headline_geo_consensus |
| 820 | candidate | Croatia News Roundup | abstain | 17 | abstained | insufficient_subject_evidence |
| 822 | active | Morocco Economy and Tourism | abstain | 44 | abstained | ambiguous_subject_geo |
| 823 | candidate | Morocco News Roundup | EG | 10 | inferred | headline_geo_consensus |
| 824 | active | Fadl Shaker Health Deterioration | abstain | 15 | abstained | ambiguous_subject_geo |
| 825 | candidate | Egypt World Cup Controversy | abstain | 24 | abstained | insufficient_subject_evidence |
| 826 | active | Reactions to Incidents | abstain | 9 | abstained | insufficient_subject_evidence |
| 827 | active | Deadly Accidents on Kyiv-Odesa Highway | abstain | 22 | abstained | insufficient_subject_evidence |
| 828 | active | Switzerland Advances to Quarterfinals | abstain | 48 | abstained | ambiguous_subject_geo |
| 829 | candidate | Currency Exchange Rates | abstain | 0 | abstained | insufficient_subject_evidence |
| 832 | active | Ola de Calor en EE.UU. | abstain | 30 | abstained | ambiguous_subject_geo |
| 833 | active | Senator Calisto Fraud Case | EC | 13 | inferred | headline_geo_consensus |
| 835 | candidate | European Heatwave Deaths | abstain | 8 | abstained | insufficient_subject_evidence |
| 836 | candidate | Czech News Roundup | abstain | 24 | abstained | insufficient_subject_evidence |
| 837 | active | Senegal Political Turmoil | abstain | 32 | abstained | ambiguous_subject_geo |
| 841 | candidate | Supreme Court TPS Ruling | abstain | 0 | abstained | insufficient_subject_evidence |
| 842 | active | Armenian Constitutional Court Upholds Election Results | RU | 94 | inferred |  |
| 844 | active | Finland Safety and Incidents | abstain | 159 | abstained | ambiguous_subject_geo |
| 845 | active | Missouri Camp Flood Rescue | abstain | 29 | abstained | ambiguous_subject_geo |
| 846 | candidate | World Cup 2026 Group L Matches | MX | 4 | inferred | headline_geo_consensus |
| 847 | active | Putin-Lukashenko Meeting on Valdai | abstain | 22 | abstained | ambiguous_subject_geo |
| 848 | candidate | Spain World Cup Victory | abstain | 8 | abstained | ambiguous_subject_geo |
| 850 | candidate | Messi and Argentina World Cup 2026 | abstain | 16 | abstained | insufficient_subject_evidence |
| 851 | candidate | Dutton Ranch Season 1 Finale | abstain | 360 | junk | ambiguous_subject_geo |
| 852 | active | Mundial 2026 Partidos | abstain | 11 | abstained | ambiguous_subject_geo |
| 853 | active | Piala Dunia 2026 Babak 32 Besar | abstain | 25 | abstained | ambiguous_subject_geo |
| 855 | candidate | Christophe Gleizes Detention | abstain | 0 | abstained | insufficient_subject_evidence |
| 856 | candidate | Paraguay Elimina a Alemania | abstain | 0 | abstained | insufficient_subject_evidence |
| 857 | active | World Cup 2026 Updates | QA | 24 | inferred |  |
| 858 | active | World Cup 2026 Updates | abstain | 55 | abstained | ambiguous_subject_geo |
| 859 | active | Earthquakes and Cross-Border Attacks | abstain | 10 | abstained | insufficient_subject_evidence |
| 860 | candidate | Afghanistan Earthquake | abstain | 0 | abstained | insufficient_subject_evidence |
| 861 | active | Pakistan Airstrikes in Afghanistan | abstain | 28 | abstained | ambiguous_subject_geo |
| 863 | active | Anti-Corruption Campaign in Iraq | abstain | 37 | abstained | ambiguous_subject_geo |
| 864 | candidate | Mauritius Budget and Policy Debates | abstain | 11 | abstained | ambiguous_subject_geo |
| 865 | candidate | Strait of Hormuz De-mining | abstain | 0 | abstained | insufficient_subject_evidence |
| 866 | active | Libya Economic and Cyber News | abstain | 94 | abstained | ambiguous_subject_geo |
| 867 | active | Iran Military Posturing | abstain | 68 | abstained | ambiguous_subject_geo |
| 869 | active | Accidents and Fires in Egypt | abstain | 36 | abstained | ambiguous_subject_geo |
| 870 | active | Sri Lanka Dengue Crisis | abstain | 17 | abstained | ambiguous_subject_geo |
| 872 | active | McGregor vs Holloway 2 | abstain | 34 | abstained | ambiguous_subject_geo |
| 873 | candidate | Oil Tanker Drift Incident | abstain | 0 | abstained | insufficient_subject_evidence |
| 874 | active | Ebola Outbreak and Security Issues | abstain | 44 | abstained | ambiguous_subject_geo |
| 876 | active | Crisis in DR Congo | abstain | 40 | abstained | ambiguous_subject_geo |
| 878 | candidate | Tour de France 2026 Updates | FR | 6 | inferred | anchor_corroborated_subject_geo |
| 880 | candidate | Bahrain News Highlights | abstain | 24 | junk | ambiguous_subject_geo |
| 881 | active | Bahrain Accuses Iran of Drone Attack | abstain | 57 | abstained | ambiguous_subject_geo |
| 882 | active | Iranian Aggression Condemned | abstain | 13 | abstained | ambiguous_subject_geo |
| 883 | active | Ukraine Refuses Bodies in Kostiantynivka | abstain | 79 | abstained | ambiguous_subject_geo |
| 888 | active | Yemen Conflict Escalation | abstain | 52 | abstained | ambiguous_subject_geo |
| 889 | candidate | Haiti News Roundup | HT | 12 | inferred | headline_geo_consensus |
| 890 | candidate | Supreme Court TPS Ruling | abstain | 0 | abstained | insufficient_subject_evidence |
| 891 | candidate | Tunisia News Roundup | abstain | 9 | abstained | ambiguous_subject_geo |
| 892 | active | SEPI President Implicated | abstain | 9 | abstained | insufficient_subject_evidence |
| 893 | active | Dr. Hussam Abu Safiya in Danger | abstain | 25 | abstained | ambiguous_subject_geo |
| 894 | candidate | Senegal 2026 World Cup | abstain | 3 | abstained | ambiguous_subject_geo |
| 895 | active | General Strike July 10 | abstain | 12 | abstained | insufficient_subject_evidence |
| 896 | active | FIFA Suspends Balogun Red Card | abstain | 73 | abstained | ambiguous_subject_geo |
| 898 | active | DR Congo Ebola Outbreak | CD | 24 | inferred | anchor_corroborated_subject_geo |
| 899 | candidate | Fiji Budget Criticism | abstain | 46 | abstained | ambiguous_subject_geo |
| 900 | active | Ebola Outbreak Congo | abstain | 10 | abstained | ambiguous_subject_geo |
| 901 | candidate | Colombia vs Portugal World Cup 2026 | abstain | 11 | abstained | insufficient_subject_evidence |
| 902 | active | Lebanon Displacement and Reconstruction | abstain | 28 | abstained | ambiguous_subject_geo |
| 903 | active | Gaza Conflict Casualties | abstain | 28 | abstained | ambiguous_subject_geo |
| 904 | active | Syria Security Incidents | IQ | 26 | inferred | headline_geo_consensus |
| 905 | active | Ébola en RD Congo | abstain | 16 | abstained | ambiguous_subject_geo |
| 906 | active | Burkina Faso News | BF | 24 | inferred | anchor_corroborated_subject_geo |
| 907 | candidate | Various News Headlines | EG | 24 | inferred | headline_geo_consensus |
| 1111 | candidate | Ohio Children Rescue | abstain | 0 | abstained | insufficient_subject_evidence |
| 1112 | candidate | Danny Glover Alzheimer's Diagnosis | abstain | 0 | abstained | insufficient_subject_evidence |
| 1113 | candidate | Taylor Swift Travis Kelce Wedding | abstain | 12 | junk | ambiguous_subject_geo |
| 1116 | active | McConnell Health Incident | abstain | 14 | abstained | insufficient_subject_evidence |
| 1117 | candidate | Empire State Building Banner Arrest | abstain | 0 | abstained | insufficient_subject_evidence |
| 1118 | candidate | Monthly Dividend Announcements | abstain | 0 | abstained | insufficient_subject_evidence |
| 1119 | candidate | John Brennan Sues Trump Admin | abstain | 0 | abstained | insufficient_subject_evidence |
| 1120 | candidate | Calais Campbell Mother Murder | abstain | 0 | abstained | insufficient_subject_evidence |
| 1121 | candidate | Jamaica News Roundup | abstain | 9 | abstained | insufficient_subject_evidence |
| 1122 | candidate | Dave Roberts 1,000 Wins | abstain | 0 | abstained | insufficient_subject_evidence |
| 1123 | candidate | Housing Crisis Debt | abstain | 0 | abstained | insufficient_subject_evidence |
| 1124 | active | Denmark Rejects Trump Greenland | US | 27 | inferred | anchor_corroborated_subject_geo |
| 1125 | candidate | Student Loan Changes July 1 | abstain | 0 | abstained | insufficient_subject_evidence |
| 1126 | active | Indian Sailor Organs Missing | abstain | 11 | abstained | insufficient_subject_evidence |
| 1127 | candidate | June GST Collections Rise | abstain | 0 | abstained | insufficient_subject_evidence |
| 1128 | candidate | Tamil Nadu Challenges Cow Slaughter Ban | abstain | 0 | abstained | insufficient_subject_evidence |
| 1129 | candidate | Syama Prasad Mookerjee Tribute | IN | 12 | junk | headline_geo_consensus |
| 1130 | candidate | PM CM Removal Bill | abstain | 2 | abstained | insufficient_subject_evidence |
| 1132 | candidate | Egg Attack Allegations | abstain | 0 | abstained | insufficient_subject_evidence |
| 1133 | active | Ram Temple Donation Probe | abstain | 47 | abstained | ambiguous_subject_geo |
| 1134 | candidate | US Lifts Sanctions on Indian Firms | abstain | 0 | abstained | insufficient_subject_evidence |
| 1135 | candidate | Tamil Nadu Horse-Trading Allegations | abstain | 0 | abstained | insufficient_subject_evidence |
| 1136 | candidate | Exam Results 2026 | abstain | 14 | junk | insufficient_subject_evidence |
| 1137 | candidate | Salman Khan Kala Hiran Case | abstain | 0 | abstained | insufficient_subject_evidence |
| 1138 | candidate | Cabinet Approves Highway Projects | abstain | 0 | abstained | insufficient_subject_evidence |
| 1139 | active | Mankhurd Chawl Collapse | abstain | 34 | abstained | ambiguous_subject_geo |
| 1140 | candidate | Japan PM Takaichi India Visit | abstain | 0 | abstained | insufficient_subject_evidence |
| 1141 | candidate | BJP vs Revanth Reddy | abstain | 0 | abstained | insufficient_subject_evidence |
| 1142 | candidate | Bosco Martis Health Scare | abstain | 0 | abstained | insufficient_subject_evidence |
| 1143 | candidate | Neha Dhupia Slams Paparazzi | abstain | 0 | abstained | insufficient_subject_evidence |
| 1146 | active | Health Risks in Hot Weather | RU | 86 | inferred | headline_geo_consensus |
| 1147 | candidate | Health Discoveries and Risks | abstain | 0 | abstained | insufficient_subject_evidence |
| 1150 | active | Russian Fuel Deficit After Drone Attacks | abstain | 70 | abstained | ambiguous_subject_geo |
| 1151 | candidate | Кокаин в Тунце Порт СПб | abstain | 0 | abstained | insufficient_subject_evidence |
| 1152 | candidate | Police Misconduct Probe | abstain | 0 | abstained | insufficient_subject_evidence |
| 1153 | candidate | Albanese Hack Expose | abstain | 0 | abstained | insufficient_subject_evidence |
| 1154 | candidate | Teacher Rebuilds Life | abstain | 0 | abstained | insufficient_subject_evidence |
| 1155 | candidate | England vs DR Congo World Cup | abstain | 0 | abstained | insufficient_subject_evidence |
| 1156 | active | Western Europe Hottest June | abstain | 17 | abstained | ambiguous_subject_geo |
| 1157 | candidate | Fatal Ongar Plane Crash | abstain | 0 | abstained | insufficient_subject_evidence |
| 1158 | candidate | Wimbledon and F1 Updates | abstain | 9 | abstained | insufficient_subject_evidence |
| 1159 | candidate | TG Jones Store Closures | abstain | 0 | abstained | insufficient_subject_evidence |
| 1160 | candidate | Essex Plane Crash Kills Two | abstain | 0 | abstained | insufficient_subject_evidence |
| 1161 | candidate | Teen Rapists Sentencing Review | abstain | 0 | abstained | insufficient_subject_evidence |
| 1162 | candidate | TV Show Listings | abstain | 11 | abstained | insufficient_subject_evidence |
| 1163 | candidate | A12 Disruption and Power Outage | abstain | 0 | abstained | insufficient_subject_evidence |
| 1164 | candidate | Halifax Brand Disappearance | abstain | 0 | abstained | insufficient_subject_evidence |
| 1165 | candidate | PGR Defends Bolsonaro House Arrest | abstain | 0 | abstained | insufficient_subject_evidence |
| 1166 | candidate | Fermanagh News Roundup | abstain | 8 | abstained | insufficient_subject_evidence |
| 1167 | candidate | Prince William Jokes About England Win | abstain | 0 | abstained | insufficient_subject_evidence |
| 1168 | candidate | UK House Prices June | abstain | 0 | abstained | insufficient_subject_evidence |
| 1169 | active | Polymarket Blocked in Italy | abstain | 8 | abstained | insufficient_subject_evidence |
| 1171 | candidate | Europe UK Heatwave Tips | abstain | 0 | abstained | insufficient_subject_evidence |
| 1172 | candidate | Scooter Chase Fatality | abstain | 0 | abstained | insufficient_subject_evidence |
| 1173 | active | Rome Traffic Updates | abstain | 8 | abstained | insufficient_subject_evidence |
| 1174 | candidate | Meloni Meets Astronaut Parmitano | abstain | 0 | abstained | insufficient_subject_evidence |
| 1175 | candidate | Rome Lazio Traffic Updates | abstain | 9 | junk | insufficient_subject_evidence |
| 1176 | candidate | Vaccines for Elderly | abstain | 0 | abstained | insufficient_subject_evidence |
| 1178 | candidate | Rally Roma Capitale Health Screening | abstain | 0 | abstained | insufficient_subject_evidence |
| 1179 | candidate | Silverstone 2026 F1 Results | abstain | 4 | abstained | insufficient_subject_evidence |
| 1180 | candidate | EU Funds Misappropriation Raids | abstain | 0 | abstained | insufficient_subject_evidence |
| 1181 | active | Извержение Вулкана Этна | abstain | 8 | abstained | insufficient_subject_evidence |
| 1182 | candidate | David Bowie Archive Tour | abstain | 0 | abstained | insufficient_subject_evidence |
| 1183 | candidate | WM 2026 Live Streams | abstain | 0 | junk | insufficient_subject_evidence |
| 1184 | candidate | Bronze Pushkin Statue Stolen in Germany | abstain | 0 | abstained | insufficient_subject_evidence |
| 1186 | candidate | Harry Kane Saves England | abstain | 0 | abstained | insufficient_subject_evidence |
| 1187 | active | New Heating Law Changes | abstain | 63 | abstained | ambiguous_subject_geo |
| 1189 | candidate | BMW X5 and Volkswagen Crisis | abstain | 8 | abstained | insufficient_subject_evidence |
| 1190 | candidate | Jerman Tersingkir Piala Dunia 2026 | abstain | 8 | abstained | ambiguous_subject_geo |
| 1192 | candidate | Minimum Pension Announcement | abstain | 0 | abstained | insufficient_subject_evidence |
| 1193 | candidate | Political Tensions in Turkey | abstain | 0 | abstained | insufficient_subject_evidence |
| 1195 | candidate | Turkish Company Disclosures | abstain | 0 | abstained | insufficient_subject_evidence |
| 1196 | active | Czech NATO Summit Dispute | abstain | 158 | abstained | ambiguous_subject_geo |
| 1197 | candidate | İmamoğlu Criticizes Government | abstain | 0 | abstained | insufficient_subject_evidence |
| 1198 | candidate | Turkish Companies Special Disclosures | abstain | 0 | abstained | insufficient_subject_evidence |
| 1199 | candidate | Suçlu İadeleri | abstain | 0 | abstained | insufficient_subject_evidence |
| 1200 | active | CHP Party Purge | abstain | 18 | abstained | ambiguous_subject_geo |
| 1201 | candidate | Interest-Bearing Capital Market Instruments | abstain | 0 | abstained | insufficient_subject_evidence |
| 1202 | candidate | Beşiktaş Transfer News | abstain | 9 | abstained | ambiguous_subject_geo |
| 1203 | candidate | Turkish Fund Documents | abstain | 12 | abstained | insufficient_subject_evidence |
| 1204 | candidate | Turkey's Strategic Regional Role | abstain | 0 | abstained | insufficient_subject_evidence |
| 1205 | candidate | Professor Arrested for Bribery | abstain | 0 | abstained | insufficient_subject_evidence |
| 1208 | candidate | French Politics and Events | FR | 21 | inferred | anchor_corroborated_subject_geo |
| 1209 | candidate | French Presidential Election Dates | abstain | 0 | abstained | insufficient_subject_evidence |
| 1210 | candidate | Isabelle Adjani Tax Evasion | abstain | 0 | abstained | insufficient_subject_evidence |
| 1211 | candidate | Librairies Furet du Nord et Decitre Fermetures | abstain | 0 | abstained | insufficient_subject_evidence |
| 1212 | candidate | Emmanouil Karalis Sworn In | abstain | 0 | abstained | insufficient_subject_evidence |
| 1213 | candidate | Liverpool Signs Jeremy Jacquet | abstain | 0 | abstained | insufficient_subject_evidence |
| 1214 | active | Costa Brava Wildfire | abstain | 36 | abstained | ambiguous_subject_geo |
| 1215 | candidate | Mehdi Kessaci Arrests | abstain | 0 | abstained | insufficient_subject_evidence |
| 1216 | candidate | Aide à Mourir Approuvée | abstain | 0 | abstained | insufficient_subject_evidence |
| 1217 | candidate | July 4th Meaning Debate | abstain | 0 | abstained | insufficient_subject_evidence |
| 1218 | candidate | Isabelle Adjani Fraud Sentence | abstain | 0 | abstained | insufficient_subject_evidence |
| 1219 | candidate | Angelina Jolie No Dating Since Divorce | abstain | 0 | abstained | insufficient_subject_evidence |
| 1220 | active | Ola de Calor en España | abstain | 55 | abstained | ambiguous_subject_geo |
| 1223 | candidate | Weather Forecasts by AEMET | abstain | 0 | abstained | insufficient_subject_evidence |
| 1224 | active | Double Murder in Mijas | abstain | 31 | abstained | insufficient_subject_evidence |
| 1225 | candidate | Tour de Francia 2026 Etapas | abstain | 6 | abstained | insufficient_subject_evidence |
| 1226 | active | Crimea-Congo Hemorrhagic Fever Death | CD | 14 | inferred | headline_geo_consensus |
| 1227 | candidate | Sahrawi Nationality Law Advances | abstain | 0 | abstained | insufficient_subject_evidence |
| 1229 | active | Incendios Forestales en Europa | abstain | 45 | abstained | ambiguous_subject_geo |
| 1231 | candidate | Marbella Mayor's Stepson Sentenced | abstain | 0 | abstained | insufficient_subject_evidence |
| 1232 | candidate | Frigiliana Corruption Investigation | abstain | 0 | abstained | insufficient_subject_evidence |
| 1233 | candidate | III Premios Academia de la Moda | abstain | 0 | abstained | insufficient_subject_evidence |
| 1234 | candidate | Xabier Ron Sentenced | abstain | 0 | abstained | insufficient_subject_evidence |
| 1235 | candidate | Monaco Explosion Targets Ukrainian Oligarch | abstain | 0 | abstained | insufficient_subject_evidence |
| 1239 | candidate | England Advances Past Congo | abstain | 0 | abstained | insufficient_subject_evidence |
| 1240 | active | Balogun Red Card Controversy | abstain | 23 | abstained | ambiguous_subject_geo |
| 1241 | active | Lotería Navidad 2026 Sale | abstain | 30 | abstained | insufficient_subject_evidence |
| 1242 | candidate | Mexico World Cup Deaths | abstain | 0 | abstained | insufficient_subject_evidence |
| 1243 | candidate | Guardia Nacional Anniversary Recognition | abstain | 0 | abstained | insufficient_subject_evidence |
| 1244 | candidate | T-MEC Extension Dispute | abstain | 0 | abstained | insufficient_subject_evidence |
| 1245 | candidate | Marruecos Elimina a Países Bajos | abstain | 0 | abstained | insufficient_subject_evidence |
| 1246 | active | Peso Mexicano y Dólar | abstain | 26 | abstained | ambiguous_subject_geo |
| 1247 | candidate | CDMX Traffic and Weather | abstain | 20 | junk | ambiguous_subject_geo |
| 1249 | candidate | USMCA Renewal Refused | abstain | 0 | abstained | insufficient_subject_evidence |
| 1250 | active | Public Infrastructure Investment | AR | 36 | inferred | headline_geo_consensus |
| 1251 | active | El Chapo Lawsuit Dismissed | abstain | 86 | abstained | ambiguous_subject_geo |
| 1253 | candidate | Argentina Remontada Épica | AR | 14 | junk | anchor_corroborated_subject_geo |
| 1254 | candidate | US Rejects T-MEC Renewal | abstain | 0 | abstained | insufficient_subject_evidence |
| 1255 | active | Mexico Legal Action Against ICE | MX | 24 | inferred | headline_geo_consensus |
| 1256 | candidate | Vassilis Leventis Death | abstain | 0 | abstained | insufficient_subject_evidence |
| 1257 | candidate | New Leadership at Areios Pagos | abstain | 0 | abstained | insufficient_subject_evidence |
| 1258 | candidate | Άρση Ασυλίας Ζωής Κωνσταντοπούλου | abstain | 0 | abstained | insufficient_subject_evidence |
| 1259 | candidate | Athens Municipality Aid | abstain | 0 | abstained | insufficient_subject_evidence |
| 1260 | candidate | Petralona Building Collapse | abstain | 0 | abstained | insufficient_subject_evidence |
| 1261 | candidate | Health and Lifestyle | abstain | 16 | junk | insufficient_subject_evidence |
| 1263 | candidate | Nike Turnaround Amid China Woes | abstain | 0 | abstained | insufficient_subject_evidence |
| 1264 | candidate | Alibaba $600M Settlement | abstain | 0 | abstained | insufficient_subject_evidence |
| 1265 | candidate | Investor Law Firm Deadlines | abstain | 0 | abstained | insufficient_subject_evidence |
| 1266 | candidate | Maior Lote de Restituição do IR | abstain | 0 | abstained | insufficient_subject_evidence |
| 1268 | candidate | São Paulo Toll Increases | abstain | 0 | abstained | insufficient_subject_evidence |
| 1269 | candidate | Henrique Emergency Surgery | abstain | 0 | abstained | insufficient_subject_evidence |
| 1270 | active | PF Investigation into Emendas Pix | abstain | 32 | abstained | ambiguous_subject_geo |
| 1271 | active | Bolsonaro's Seized Shotgun | abstain | 23 | abstained | ambiguous_subject_geo |
| 1273 | active | Bolsonaro Not Indicted for Gun | abstain | 23 | abstained | ambiguous_subject_geo |
| 1274 | candidate | Lottery Results Today | abstain | 9 | abstained | insufficient_subject_evidence |
| 1275 | candidate | Cacique Raoni Hemorragia UTI | abstain | 0 | abstained | insufficient_subject_evidence |
| 1276 | candidate | TV News Broadcasts | abstain | 13 | abstained | insufficient_subject_evidence |
| 1279 | candidate | Blush Pink Styles | abstain | 0 | abstained | insufficient_subject_evidence |
| 1280 | active | Power Outages After Storms | abstain | 34 | abstained | ambiguous_subject_geo |
| 1282 | candidate | Canada GDP Rebounds in April | abstain | 0 | abstained | insufficient_subject_evidence |
| 1283 | candidate | Airdrie Canada Day Events | abstain | 9 | junk | insufficient_subject_evidence |
| 1284 | candidate | USMCA Non-Renewal | abstain | 0 | abstained | insufficient_subject_evidence |
| 1285 | candidate | Canada Day Fireworks Delays | abstain | 12 | junk | insufficient_subject_evidence |
| 1286 | candidate | Vancouver Giants Move to Surrey | abstain | 0 | abstained | insufficient_subject_evidence |
| 1288 | candidate | Coquitlam Real Estate Listings | abstain | 13 | abstained | insufficient_subject_evidence |
| 1289 | candidate | Federal Funding Boosts | abstain | 0 | abstained | insufficient_subject_evidence |
| 1290 | candidate | Chatham-Kent Heat Wave | abstain | 0 | abstained | insufficient_subject_evidence |
| 1291 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1292 | active | Venezuela Earthquake Death Toll | VE | 19 | inferred | anchor_corroborated_subject_geo |
| 1293 | candidate | MLB Donation to Venezuela | abstain | 0 | abstained | insufficient_subject_evidence |
| 1294 | candidate | Venezuela Earthquakes Aftermath | abstain | 0 | abstained | insufficient_subject_evidence |
| 1295 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1296 | active | Weather and Earthquake Updates | abstain | 12 | abstained | insufficient_subject_evidence |
| 1298 | candidate | Ruben Onsu Child Custody Lawsuit | abstain | 11 | junk | insufficient_subject_evidence |
| 1300 | candidate | HUT Bhayangkara ke-80 | abstain | 0 | abstained | insufficient_subject_evidence |
| 1301 | candidate | Bhayangkara Day Commitments | abstain | 0 | abstained | insufficient_subject_evidence |
| 1302 | candidate | Pemakaman Ayatollah Ali Khamenei | abstain | 41 | junk | ambiguous_subject_geo |
| 1303 | candidate | HUT Bhayangkara Ke-80 | abstain | 0 | abstained | insufficient_subject_evidence |
| 1304 | active | Raja Juli Amplop Scandal | abstain | 22 | abstained | ambiguous_subject_geo |
| 1305 | candidate | Nadiem Makarim Sentenced to 10 Years | abstain | 0 | abstained | insufficient_subject_evidence |
| 1306 | candidate | Ship Runs Aground in Strait of Hormuz | abstain | 0 | abstained | insufficient_subject_evidence |
| 1307 | candidate | No Direct US-Iran Talks | abstain | 0 | abstained | insufficient_subject_evidence |
| 1308 | active | Funeral of Ayatollah Khamenei | IR | 28 | inferred | headline_geo_consensus |
| 1311 | candidate | Biography of Ayatollah Khamenei | abstain | 0 | abstained | insufficient_subject_evidence |
| 1312 | candidate | Vanstone Criticizes Hanson | abstain | 0 | abstained | insufficient_subject_evidence |
| 1313 | candidate | Geelong Best Restaurants | abstain | 0 | abstained | insufficient_subject_evidence |
| 1314 | candidate | Dry July Abstinence | abstain | 0 | abstained | insufficient_subject_evidence |
| 1315 | candidate | Catalano Family Violence Case | abstain | 0 | abstained | insufficient_subject_evidence |
| 1316 | candidate | Rabbi's Bondi Beach Legacy | abstain | 0 | abstained | insufficient_subject_evidence |
| 1317 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1318 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1319 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1320 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1321 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1322 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1323 | candidate | (label failed) | abstain | 60 | junk | ambiguous_subject_geo |
| 1324 | active | (label failed) | abstain | 8 | abstained | insufficient_subject_evidence |
| 1325 | candidate | Education Grant Reform Debate | abstain | 9 | abstained | insufficient_subject_evidence |
| 1326 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1327 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1329 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1330 | active | Wildfires in Castellón and Huesca | AR | 16 | inferred | headline_geo_consensus |
| 1331 | candidate | Hijo de Diomedes Díaz Prisión Domiciliaria | abstain | 11 | junk | ambiguous_subject_geo |
| 1332 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1333 | candidate | School Shooting in Neuquén | abstain | 0 | abstained | insufficient_subject_evidence |
| 1334 | active | Dólar Hoy Cotizaciones | abstain | 18 | abstained | ambiguous_subject_geo |
| 1335 | candidate | Egypt FIFA Complaint | AR | 24 | junk | headline_geo_consensus |
| 1336 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1337 | candidate | Colombia Inflation and Water Bills | CO | 28 | junk | headline_geo_consensus |
| 1338 | active | Milei Shutdown Proposal | AR | 14 | inferred | anchor_corroborated_subject_geo |
| 1339 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1340 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1341 | active | CABA Inflation June 1.8% | abstain | 11 | abstained | ambiguous_subject_geo |
| 1342 | candidate | Quiniela Lottery Results | abstain | 21 | abstained | insufficient_subject_evidence |
| 1343 | active | Violent Crimes and Incidents | abstain | 314 | abstained | ambiguous_subject_geo |
| 1344 | candidate | Cabo Verde Scandal and Messi Gift | abstain | 11 | junk | ambiguous_subject_geo |
| 1345 | candidate | Polish Healthcare Crisis | abstain | 13 | abstained | insufficient_subject_evidence |
| 1346 | active | Brazil Inflation Slows in June | abstain | 19 | abstained | ambiguous_subject_geo |
| 1347 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1348 | active | Vouzela Wildfire Crisis | abstain | 12 | abstained | ambiguous_subject_geo |
| 1349 | candidate | GTA 6 60 FPS Rumors | abstain | 0 | abstained | insufficient_subject_evidence |
| 1350 | candidate | Two Towers Investigation Dropped | abstain | 0 | abstained | insufficient_subject_evidence |
| 1352 | active | Moldova Political Crisis | abstain | 68 | abstained | ambiguous_subject_geo |
| 1353 | candidate | Basic Law Torah Study Passes | abstain | 0 | abstained | insufficient_subject_evidence |
| 1354 | active | Wave of Murders in Arab Society | abstain | 47 | abstained | insufficient_subject_evidence |
| 1355 | candidate | Canada Joins Eurovision 2027 | abstain | 0 | abstained | insufficient_subject_evidence |
| 1356 | candidate | Woman Charged with Funding Palestinian Terror | abstain | 0 | abstained | insufficient_subject_evidence |
| 1357 | candidate | Scott Wiener Harassment Incident | abstain | 0 | abstained | insufficient_subject_evidence |
| 1359 | candidate | Israeli Knesset Restricts Adhan | abstain | 0 | abstained | insufficient_subject_evidence |
| 1360 | candidate | Secondary School Admission 2026 | abstain | 8 | junk | insufficient_subject_evidence |
| 1361 | candidate | X-Men '97 Season 2 | abstain | 0 | abstained | insufficient_subject_evidence |
| 1363 | candidate | Egyptian Stock Exchange Weekly Gains | abstain | 0 | abstained | insufficient_subject_evidence |
| 1365 | active | Etna Eruption Disrupts Catania Airport | TR | 10 | inferred | headline_geo_consensus |
| 1366 | candidate | IMF Seventh Review Agreement | abstain | 0 | abstained | insufficient_subject_evidence |
| 1367 | candidate | Manshiet Nasser Fire Tragedy | abstain | 0 | abstained | insufficient_subject_evidence |
| 1368 | active | Viet Duc Hospital Ninh Binh Opens | abstain | 12 | abstained | insufficient_subject_evidence |
| 1369 | active | Assault with High-Pressure Water Hose | abstain | 32 | abstained | insufficient_subject_evidence |
| 1370 | candidate | Heart Attacks During Childcare | abstain | 0 | abstained | insufficient_subject_evidence |
| 1371 | candidate | University Admission Thresholds 2026 | abstain | 35 | junk | insufficient_subject_evidence |
| 1372 | candidate | Hợp Đồng Kỳ Nghỉ Lừa Đảo | abstain | 4 | junk | insufficient_subject_evidence |
| 1373 | candidate | Search for War Remains | abstain | 18 | junk | insufficient_subject_evidence |
| 1375 | candidate | Yen Falls to 40-Year Low | abstain | 0 | abstained | insufficient_subject_evidence |
| 1376 | candidate | (label failed) | abstain | 48 | junk | ambiguous_subject_geo |
| 1377 | candidate | Japanese Entertainment News | abstain | 10 | abstained | ambiguous_subject_geo |
| 1378 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1379 | candidate | Wimbledon 2026 Italian Players | abstain | 18 | abstained | ambiguous_subject_geo |
| 1380 | candidate | (label failed) | abstain | 9 | junk | insufficient_subject_evidence |
| 1381 | candidate | Fiscalía vs Juez Peinado | abstain | 37 | junk | ambiguous_subject_geo |
| 1382 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1383 | candidate | Adorni Credit Card Scandal | abstain | 0 | abstained | insufficient_subject_evidence |
| 1384 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1385 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1386 | candidate | ASF Denuncias por Daño al Erario | abstain | 0 | abstained | insufficient_subject_evidence |
| 1387 | candidate | Weather Forecasts | abstain | 8 | abstained | insufficient_subject_evidence |
| 1388 | active | Viorel Pașca Case Adjourned | abstain | 11 | abstained | insufficient_subject_evidence |
| 1389 | candidate | PNRR Laws Adopted | abstain | 0 | abstained | insufficient_subject_evidence |
| 1390 | active | Raed Arafat Asset Seizure | abstain | 14 | abstained | insufficient_subject_evidence |
| 1391 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1392 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1394 | active | PNL Congress Decisions Suspended | abstain | 9 | abstained | insufficient_subject_evidence |
| 1395 | candidate | National Exam 2026 Results | abstain | 0 | abstained | insufficient_subject_evidence |
| 1396 | candidate | CBN Revokes 46 Microfinance Bank Licenses | abstain | 0 | abstained | insufficient_subject_evidence |
| 1397 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1399 | active | Lagos Flooding Crisis | abstain | 58 | abstained | ambiguous_subject_geo |
| 1400 | candidate | 2027 Election Nomination Updates | abstain | 0 | abstained | insufficient_subject_evidence |
| 1401 | active | Demands for Release of Detainees | abstain | 78 | abstained | ambiguous_subject_geo |
| 1402 | candidate | ADC Uploads Atiku Amaechi | abstain | 0 | abstained | insufficient_subject_evidence |
| 1403 | candidate | ADA INEC Access Code Dispute | abstain | 0 | abstained | insufficient_subject_evidence |
| 1404 | candidate | Cabinet Reshuffles in Oyo and Ebonyi | abstain | 0 | abstained | insufficient_subject_evidence |
| 1405 | candidate | Borno School Attack Missing Students | abstain | 0 | abstained | insufficient_subject_evidence |
| 1407 | active | Amotekun Arrests Kidnapping Family | abstain | 9 | abstained | ambiguous_subject_geo |
| 1408 | candidate | Carter Efe Certificate Controversy | abstain | 0 | abstained | insufficient_subject_evidence |
| 1409 | candidate | (label failed) | abstain | 0 | abstained | insufficient_subject_evidence |
| 1410 | candidate | Antwerp Apartment Fire | abstain | 0 | abstained | insufficient_subject_evidence |
| 1411 | candidate | Belgium Epic Comeback vs Senegal | abstain | 0 | abstained | insufficient_subject_evidence |
| 1412 | active | Belgium vs Senegal World Cup | abstain | 91 | abstained | ambiguous_subject_geo |
| 1413 | active | Incendio en Amberes | TH | 8 | inferred | headline_geo_consensus |
| 1414 | active | Mesir Protes Wasit Argentina | AR | 40 | inferred |  |
| 1415 | candidate | Belgium vs Senegal 2026 | abstain | 0 | abstained | insufficient_subject_evidence |
| 1416 | active | Antwerp Building Fire | abstain | 50 | abstained | ambiguous_subject_geo |
| 1417 | candidate | World Cup 2026 Schedules | abstain | 0 | abstained | insufficient_subject_evidence |
| 1419 | active | Keiko Fujimori Proclamation | abstain | 33 | abstained | ambiguous_subject_geo |
| 1420 | candidate | Presidential Transition Process | abstain | 0 | abstained | insufficient_subject_evidence |
| 1421 | candidate | Natalia Villalba Autopsy Results | abstain | 0 | abstained | insufficient_subject_evidence |
| 1422 | candidate | Colombian Lottery Results | CO | 24 | inferred | anchor_corroborated_subject_geo |
| 1423 | candidate | US Travel Experiences | abstain | 0 | abstained | insufficient_subject_evidence |
| 1424 | candidate | Canada Eurovision 2027 | abstain | 0 | abstained | insufficient_subject_evidence |
| 1425 | candidate | SSPX Defies Pope | abstain | 0 | abstained | insufficient_subject_evidence |
| 1426 | candidate | Dutch News Highlights | abstain | 5 | abstained | insufficient_subject_evidence |
| 1427 | candidate | New Zealand Rate Hike | abstain | 8 | junk | insufficient_subject_evidence |
| 1429 | candidate | Bouchaker Guilty Verdict | abstain | 0 | abstained | insufficient_subject_evidence |
| 1430 | active | Russia Minaccia Polonia | abstain | 111 | abstained | ambiguous_subject_geo |
| 1431 | candidate | Eva Green Injured on Set | abstain | 0 | abstained | insufficient_subject_evidence |
| 1433 | candidate | India Rejects Pakistan Allegations | abstain | 0 | abstained | insufficient_subject_evidence |
| 1435 | candidate | Pakistan Tutoring Centre Roof Collapse | abstain | 0 | abstained | insufficient_subject_evidence |
| 1436 | candidate | Pakistan Coaching Center Roof Collapse | abstain | 0 | abstained | insufficient_subject_evidence |
| 1437 | candidate | Pakistan Dershane Çatı Çökmesi | abstain | 0 | abstained | insufficient_subject_evidence |
| 1438 | candidate | Prisoner Escape from Van | abstain | 0 | abstained | insufficient_subject_evidence |
| 1439 | candidate | Pakistan Gurdwara Demolition Condemned | abstain | 0 | abstained | insufficient_subject_evidence |
| 1440 | candidate | Anti-Immigrant Protests in South Africa | abstain | 0 | abstained | insufficient_subject_evidence |
| 1441 | candidate | Best of George Awards | abstain | 0 | abstained | insufficient_subject_evidence |
| 1442 | active | Ebola Outbreak in DRC | abstain | 12 | abstained | ambiguous_subject_geo |
| 1443 | candidate | Limpopo Repatriation Bus Crash | abstain | 0 | abstained | insufficient_subject_evidence |
| 1445 | candidate | South Africa Anti-Migrant Protests | abstain | 0 | abstained | insufficient_subject_evidence |
| 1446 | candidate | CSD Cologne Flirty Flamingo | abstain | 18 | junk | insufficient_subject_evidence |
| 1447 | candidate | Peruvian News Live Streams | abstain | 13 | abstained | insufficient_subject_evidence |
| 1448 | active | Peru Election Results Proclamation | abstain | 50 | abstained | ambiguous_subject_geo |
| 1449 | candidate | Roxy Murdoch's Return to Elite League | abstain | 0 | abstained | insufficient_subject_evidence |
| 1450 | active | Typhoon Bavi Disrupts Travel | abstain | 24 | abstained | ambiguous_subject_geo |
| 1451 | candidate | Strait of Hormuz Incidents | abstain | 0 | abstained | insufficient_subject_evidence |
| 1452 | candidate | Iran Nuclear Talks Progress | abstain | 0 | abstained | insufficient_subject_evidence |
| 1453 | candidate | US-Iran Talks Progress | abstain | 0 | abstained | insufficient_subject_evidence |
| 1454 | candidate | US-Iran Talks in Pakistan | abstain | 3 | abstained | ambiguous_subject_geo |
| 1455 | candidate | US-Iran Talks in Doha | abstain | 0 | abstained | insufficient_subject_evidence |
| 1456 | candidate | Wildfire Updates Macedonia | abstain | 0 | abstained | insufficient_subject_evidence |
| 1457 | candidate | Power Outages in Skopje | abstain | 0 | abstained | insufficient_subject_evidence |
| 1458 | candidate | Death of Vlado Janevski | abstain | 0 | abstained | insufficient_subject_evidence |
| 1459 | candidate | World Cup 2026 Reactions | abstain | 15 | abstained | insufficient_subject_evidence |
| 1460 | candidate | Belgrade Radio Programs | abstain | 0 | abstained | insufficient_subject_evidence |
| 1461 | active | Russian Arrested in Murder Case | abstain | 76 | abstained | ambiguous_subject_geo |
| 1463 | candidate | Czech News Briefs | abstain | 0 | abstained | insufficient_subject_evidence |
| 1464 | candidate | Bouřky a škody v Česku | abstain | 0 | abstained | insufficient_subject_evidence |
| 1465 | candidate | Czech Proposal to Strip Zelenskyy of Order | abstain | 0 | abstained | insufficient_subject_evidence |
| 1466 | candidate | World Cup 2026 Fallout | abstain | 0 | abstained | insufficient_subject_evidence |
| 1468 | candidate | Spain vs Belgium World Cup Quarterfinal | abstain | 24 | abstained | insufficient_subject_evidence |
| 1469 | candidate | Lyhanna Case Protests | abstain | 9 | abstained | ambiguous_subject_geo |
| 1470 | candidate | Chile Weather Forecasts | abstain | 24 | abstained | ambiguous_subject_geo |
| 1471 | candidate | Algerian National Memory | abstain | 193 | abstained | ambiguous_subject_geo |
| 1472 | active | Maroc Croissance Économique | abstain | 58 | abstained | ambiguous_subject_geo |
| 1473 | candidate | Resistance and Sovereignty in Lebanon | abstain | 0 | abstained | insufficient_subject_evidence |
| 1474 | active | Aquiles Alvarez Medical Transfer | abstain | 15 | abstained | ambiguous_subject_geo |
| 1475 | active | Fatal Celebrations in Mexico | AR | 69 | inferred | headline_geo_consensus |
| 1476 | active | Severe Weather Warnings Serbia | abstain | 11 | abstained | insufficient_subject_evidence |
| 1479 | active | Legal Cases and Appeals | abstain | 8 | abstained | ambiguous_subject_geo |
| 1481 | candidate | Ship Runs Aground in Strait of Hormuz | abstain | 0 | abstained | insufficient_subject_evidence |
| 1482 | candidate | Lucie en Thaïlande | abstain | 0 | abstained | insufficient_subject_evidence |
| 1483 | active | Armenian Political Turmoil | abstain | 8 | abstained | insufficient_subject_evidence |
| 1484 | candidate | Lukashenko Pardons Prisoners | abstain | 0 | abstained | insufficient_subject_evidence |
| 1485 | active | Ghana Floods Death Toll | abstain | 62 | abstained | ambiguous_subject_geo |
| 1487 | candidate | Ghana Flood Relief Package | abstain | 0 | abstained | insufficient_subject_evidence |
| 1488 | active | Negombo Prison Deaths Probe | abstain | 31 | abstained | ambiguous_subject_geo |
| 1489 | candidate | Ghana US Deportation Lawsuit | abstain | 0 | abstained | insufficient_subject_evidence |
| 1490 | candidate | MoldATSA Corruption Scandal | abstain | 0 | abstained | insufficient_subject_evidence |
| 1491 | active | Severe Weather Alerts Romania | abstain | 13 | abstained | insufficient_subject_evidence |
| 1492 | candidate | Escrocherii și Infracțiuni în Chișinău | abstain | 0 | abstained | insufficient_subject_evidence |
| 1493 | candidate | Weather Forecast Updates | abstain | 0 | abstained | insufficient_subject_evidence |
| 1494 | candidate | Mauritius News Roundup | abstain | 24 | abstained | ambiguous_subject_geo |
| 1495 | candidate | Kenya Protests Over Abductions | abstain | 0 | abstained | insufficient_subject_evidence |
| 1497 | active | Severe Thunderstorm Warnings | abstain | 21 | abstained | ambiguous_subject_geo |
| 1498 | active | Pantai Gading vs Norwegia Piala Dunia 2026 | abstain | 33 | abstained | ambiguous_subject_geo |
| 1499 | active | Floods in Ivory Coast and Ghana | CN | 36 | inferred | headline_geo_consensus |
| 1500 | candidate | Pakistan-Afghanistan Border Clashes | abstain | 0 | abstained | insufficient_subject_evidence |
| 1501 | candidate | Ugunsgrēks Ulmaņa Gatvē | abstain | 0 | abstained | insufficient_subject_evidence |
| 1502 | active | Luxembourg Economic Challenges | abstain | 205 | abstained | ambiguous_subject_geo |
| 1503 | candidate | Congo Bans Gatherings Over Ebola | abstain | 0 | abstained | insufficient_subject_evidence |
| 1504 | candidate | Congo News Roundup | CM | 8 | inferred | headline_geo_consensus |
| 1505 | active | Ebola Center Attack | abstain | 14 | abstained | ambiguous_subject_geo |
| 1506 | candidate | Inggris vs RD Kongo Piala Dunia 2026 | abstain | 17 | abstained | ambiguous_subject_geo |
| 1507 | candidate | Walter Mazariegos Usac Rector | abstain | 0 | abstained | insufficient_subject_evidence |
| 1508 | candidate | Government Supports SEPI President | abstain | 0 | abstained | insufficient_subject_evidence |
| 1509 | active | UN Genocide Findings Sudan | SD | 11 | inferred | headline_geo_consensus |
| 1510 | candidate | Ebola Economic Impact | abstain | 0 | abstained | insufficient_subject_evidence |
| 1511 | active | Ol Kalou By-Election Crisis | abstain | 43 | abstained | ambiguous_subject_geo |
| 1512 | candidate | Fiji Military Commander Term | abstain | 0 | abstained | insufficient_subject_evidence |
| 1513 | candidate | Monaco Explosion Ukraine | abstain | 0 | abstained | insufficient_subject_evidence |
| 1514 | active | Coordinated Attacks in Mali | abstain | 64 | abstained | ambiguous_subject_geo |
| 1515 | candidate | Haverhill Sewage Spill | abstain | 0 | abstained | insufficient_subject_evidence |
| 1516 | candidate | Albanese Hack Expose | abstain | 0 | abstained | insufficient_subject_evidence |
| 1517 | candidate | Enola Holmes 3 Reviews | abstain | 0 | abstained | insufficient_subject_evidence |
| 1518 | candidate | Yorgen Fenech Trial Begins | abstain | 0 | abstained | insufficient_subject_evidence |
| 1519 | candidate | Malta News Roundup | abstain | 15 | abstained | insufficient_subject_evidence |
| 1520 | active | Cameroun Economic and Social Issues | abstain | 35 | abstained | ambiguous_subject_geo |
| 1522 | candidate | Process Aoun Implementation | abstain | 0 | abstained | insufficient_subject_evidence |
| 1523 | candidate | Mauritanian President Engages Diplomats | abstain | 0 | abstained | insufficient_subject_evidence |
| 1524 | candidate | Mauritania News Roundup | abstain | 0 | abstained | insufficient_subject_evidence |
| 1525 | active | China Shoe Factory Fire | TH | 39 | inferred |  |
| 1526 | candidate | Myanmar Conflict Death Toll | abstain | 0 | abstained | insufficient_subject_evidence |
| 1529 | candidate | FBI Georgia Election Probe | abstain | 0 | abstained | insufficient_subject_evidence |
| 1531 | candidate | America at 250 Reflections | abstain | 0 | abstained | insufficient_subject_evidence |
| 1533 | candidate | Taylor Swift and Travis Kelce Wedding | abstain | 5 | junk | insufficient_subject_evidence |
| 1534 | candidate | Ballot Measure Signature Campaigns | abstain | 0 | abstained | insufficient_subject_evidence |
| 1535 | candidate | Secret Service Radio Failures | abstain | 0 | abstained | insufficient_subject_evidence |
| 1536 | candidate | MLB Brawl Suspensions | abstain | 0 | abstained | insufficient_subject_evidence |
| 1538 | candidate | Trump Approves Disaster Declarations | abstain | 0 | abstained | insufficient_subject_evidence |
| 1539 | candidate | Hottest Julys by State | abstain | 0 | abstained | insufficient_subject_evidence |
| 1540 | candidate | Married At First Sight Arrest | abstain | 0 | abstained | insufficient_subject_evidence |
| 1541 | candidate | Stock Price Movements | abstain | 14 | abstained | insufficient_subject_evidence |
| 1542 | candidate | Global Drug-Facilitated Sexual Assault Ring | abstain | 0 | abstained | insufficient_subject_evidence |
| 1543 | active | ЧМ-2026 Четвертьфиналисты | abstain | 17 | abstained | insufficient_subject_evidence |
| 1544 | candidate | US Seizes 138 Weapons Bound for Mexico | abstain | 0 | abstained | insufficient_subject_evidence |
| 1545 | candidate | Mariana Bernal Suspension | abstain | 0 | abstained | insufficient_subject_evidence |
| 1546 | candidate | Trump's $46B Smart Wall | abstain | 0 | abstained | insufficient_subject_evidence |
| 1550 | candidate | Ford Raptors Dodge Rams Blight | abstain | 0 | abstained | insufficient_subject_evidence |
| 1553 | candidate | Arthur Boyd Tapestries Revealed | abstain | 0 | abstained | insufficient_subject_evidence |
| 1556 | candidate | Regional Infrastructure Upgrades | abstain | 0 | abstained | insufficient_subject_evidence |
| 1558 | candidate | Nuclear Reactor Investment | abstain | 0 | abstained | insufficient_subject_evidence |
| 1559 | candidate | Soarin' Ride Comparison | abstain | 0 | abstained | insufficient_subject_evidence |
| 1560 | active | Iran Accepts US Demands | abstain | 18 | abstained | ambiguous_subject_geo |
| 1561 | candidate | Israel Gedenkt Hamas-Überfall | abstain | 0 | abstained | insufficient_subject_evidence |
| 1562 | candidate | Swiss History Milestones | abstain | 0 | abstained | insufficient_subject_evidence |
| 1563 | candidate | EU Approves Spain Payment | abstain | 0 | abstained | insufficient_subject_evidence |
| 1564 | candidate | Patrick Bruel Sexual Assault Allegations | abstain | 0 | abstained | insufficient_subject_evidence |
| 1565 | active | Damascus Cafe Bombing Condemned | abstain | 9 | abstained | ambiguous_subject_geo |
| 1574 | candidate | Fourth of July 2026 | abstain | 0 | abstained | insufficient_subject_evidence |
| 1575 | candidate | Skydiving Plane Crash Investigation | abstain | 0 | abstained | insufficient_subject_evidence |
| 1576 | candidate | Local News and Events | abstain | 0 | abstained | insufficient_subject_evidence |
| 1580 | active | Bengaluru Daycare Abuse Case | abstain | 48 | abstained | ambiguous_subject_geo |
| 1581 | candidate | Jaish-e-Mohammed Suspects Arrested | abstain | 0 | abstained | insufficient_subject_evidence |
| 1582 | candidate | Sonam Raghuvanshi Bail Upheld | abstain | 0 | abstained | insufficient_subject_evidence |
| 1584 | candidate | Royal Family Rift | abstain | 10 | junk | insufficient_subject_evidence |
| 1585 | candidate | Driving Fines Warnings | abstain | 10 | junk | insufficient_subject_evidence |
| 1586 | candidate | Celebrities Emotional Over Family | abstain | 0 | abstained | insufficient_subject_evidence |
| 1587 | active | Ospedale Omicidio-Suicidio | abstain | 12 | abstained | insufficient_subject_evidence |
| 1588 | candidate | German Securities Act Disclosures | abstain | 0 | abstained | insufficient_subject_evidence |
| 1590 | candidate | Frankfurt-Mannheim Rail Milestone | abstain | 1 | abstained | insufficient_subject_evidence |
| 1593 | candidate | Funeral de Ali Jamenei | abstain | 50 | junk | ambiguous_subject_geo |
| 1594 | active | Israel Plot to Kill Iran Negotiators | abstain | 49 | abstained | ambiguous_subject_geo |
| 1595 | candidate | Norfolk Council Approvals | abstain | 0 | junk | insufficient_subject_evidence |
| 1598 | candidate | Swedish Recipes | MA | 24 | inferred | headline_geo_consensus |
| 1601 | active | PFIPC Scandal Demands | abstain | 25 | abstained | ambiguous_subject_geo |
| 1603 | candidate | Arrestime në Protesta dhe Skema Mashtrimi | abstain | 0 | abstained | insufficient_subject_evidence |
| 1604 | active | Moldova PM Resigns | UA | 11 | inferred | headline_geo_consensus |
| 1615 | candidate | Mixed: Economic and Regional Updates | abstain | 22 | junk | ambiguous_subject_geo |
| 1616 | candidate | Mixed: International News | abstain | 0 | junk | insufficient_subject_evidence |
| 1617 | candidate | Japanese Stocks Gap Down | abstain | 22 | junk | insufficient_subject_evidence |
| 1618 | candidate | Emerging: Canadian Stocks Advance As US Fed Rate-Hike Concerns Begin To Ease | abstain | 25 | abstained | ambiguous_subject_geo |
| 1619 | candidate | Emerging: Kim Jong Un seen observing weapons tests from new North Korean naval destroyer | abstain | 3 | abstained | ambiguous_subject_geo |
| 1620 | candidate | Emerging: تمهیدات مقامات عراقی برای برگزاری مراسم تشییع پیکر مطهر رهبر شهید انقلاب | abstain | 0 | junk | insufficient_subject_evidence |
| 1621 | candidate | Emerging: Hunter region records NSW's first H5N1 bird flu case \| Newcastle Herald | abstain | 2 | abstained | insufficient_subject_evidence |
| 1622 | active | Killarney Murder Investigation | abstain | 34 | abstained | insufficient_subject_evidence |
| 1623 | candidate | Dhamaal 4 Box Office | abstain | 15 | junk | ambiguous_subject_geo |
| 1625 | candidate | Emerging: Investigators find no evidence of engine failure in fiery crash of skydiving pla | abstain | 0 | abstained | insufficient_subject_evidence |
| 1626 | candidate | Emerging: Class Action Alert: Levi & Korsinsky Reminds Futu Holdings Limited ... | abstain | 66 | abstained | ambiguous_subject_geo |
| 1627 | active | Irishman Jailed for Murder of American Nurse in Hungary | abstain | 15 | abstained | ambiguous_subject_geo |
| 1628 | active | Kawhi Leonard Trade Halted | abstain | 20 | abstained | insufficient_subject_evidence |
| 1629 | active | Impaired Driving and Assault Charges | abstain | 101 | abstained | insufficient_subject_evidence |
| 1630 | active | Windstorm Devastation in Nigeria | abstain | 16 | abstained | ambiguous_subject_geo |
| 1631 | candidate | Emerging: Brandon Marsh, Cristopher S&#xE1;nchez highlight 5 Phillies in All-Star Game | abstain | 205 | abstained | ambiguous_subject_geo |
| 1632 | candidate | Emerging: Live MLB on TNT Sports 1 HD: full details and when it's on | abstain | 29 | abstained | insufficient_subject_evidence |
| 1633 | candidate | Emerging: Indian PM Modi to visit Australia, Indonesia and NZ | IN | 28 | inferred | headline_geo_consensus |
| 1634 | candidate | Emerging: Reports: England-Mexico start time Sunday moving due to storm risk | abstain | 5 | abstained | ambiguous_subject_geo |
| 1636 | candidate | Emerging: K&#xF6;ln: Handy am Beckenrand? Bademeister ermahnen Eltern | abstain | 9 | junk | insufficient_subject_evidence |
| 1637 | candidate | Emerging: Aksaray'da Yolcu Otob&#xFC;s&#xFC;n&#xFC;n &#x15E;arampole D&#xFC;&#x15F;mesi So | abstain | 169 | abstained | ambiguous_subject_geo |
| 1638 | active | Palermo Stabbing Barricade | abstain | 9 | abstained | insufficient_subject_evidence |
| 1639 | active | 보완수사권 논쟁 | abstain | 92 | abstained | ambiguous_subject_geo |
| 1640 | candidate | Emerging: Fallece a los 71 a&#xF1;os Fernando Kliche, &#xED;cono de la televisi&#xF3;n chi | abstain | 7 | abstained | insufficient_subject_evidence |
| 1641 | candidate | Emerging: Fire breaks out on Brooklyn Bridge during 4th of July fireworks show | abstain | 0 | abstained | insufficient_subject_evidence |
| 1642 | active | Northern Vietnam Weather | abstain | 20 | abstained | insufficient_subject_evidence |
| 1643 | candidate | Emerging: Fireworks, heat and politics: America celebrates its 250th birthday | abstain | 8 | abstained | ambiguous_subject_geo |
| 1644 | candidate | Emerging: Evacuation ordered at National Mall as storms gather ahead of Trump's July 4 spe | abstain | 0 | abstained | insufficient_subject_evidence |
| 1645 | candidate | Lottery Results Daily | abstain | 10 | abstained | insufficient_subject_evidence |
| 1646 | candidate | Emerging: Keiko Fujimori es proclamada oficialmente como presidenta electa de Perú por el | abstain | 4 | abstained | insufficient_subject_evidence |
| 1647 | active | Emerging: Misi&#xF3;n humanitaria en Venezuela: el Gobierno anunci&#xF3; el env&#xED;o de | VE | 127 | inferred | headline_geo_consensus |
| 1648 | candidate | FBI Role in El Mayo Capture | MX | 10 | junk | headline_geo_consensus |
| 1649 | active | Francia Semifinalista Mundial 2026 | abstain | 28 | abstained | insufficient_subject_evidence |
| 1650 | active | Protestos Contra AfD na Alemanha | abstain | 66 | abstained | ambiguous_subject_geo |
| 1653 | candidate | Trump Pardons Emissions Violators | abstain | 0 | abstained | insufficient_subject_evidence |
| 1660 | candidate | Emerging: &#xE2A;&#xE38;&#xE14;&#xE2A;&#xE25;&#xE14;&#xE43;&#xE08; '&#xE1C;&#xE31;&#xE27;- | abstain | 20 | abstained | insufficient_subject_evidence |
| 1661 | candidate | Emerging: Ongar camping barbecue sparks fast spreading grassland fire \| Maldon and Burnham | abstain | 135 | abstained | ambiguous_subject_geo |
| 1662 | candidate | Emerging: Altrincham care home raises hundreds for stroke survivors | abstain | 74 | abstained | ambiguous_subject_geo |
| 1663 | candidate | Emerging: Gulf Coast marks Fourth of July with fireworks, concerts | abstain | 26 | abstained | ambiguous_subject_geo |
| 1665 | active | Invasive Caterpillar Spread | abstain | 152 | abstained | ambiguous_subject_geo |
| 1666 | candidate | Daily News Roundup | abstain | 8 | junk | insufficient_subject_evidence |
| 1667 | candidate | Emerging: Off the wire \| The Arkansas Democrat-Gazette - Arkansas' Best News Source | abstain | 47 | abstained | ambiguous_subject_geo |
| 1668 | active | Ukraine War Escalation | abstain | 194 | abstained | ambiguous_subject_geo |
| 1669 | candidate | Emerging: Govt issues notice to Meta over Child Sexual Exploitative Material in Instagram | abstain | 17 | abstained | insufficient_subject_evidence |
| 1670 | active | Emerging: Will work with allies for 2027 UP polls, confident of NDA's return with huge maj | abstain | 72 | abstained | ambiguous_subject_geo |
| 1671 | active | BCCI Review After T20I Loss | IN | 38 | inferred | headline_geo_consensus |
| 1673 | candidate | Emerging: China, Russia to hold joint naval exercise, maritime patrol-Xinhua | abstain | 3 | abstained | ambiguous_subject_geo |
| 1674 | candidate | Emerging: &#x392;&#x3B1;&#x3C1;&#x3CC;&#x3BC;&#x3B5;&#x3C4;&#x3C1;&#x3BF; &#x3B3;&#x3B9;&# | abstain | 5 | junk | insufficient_subject_evidence |
| 1676 | candidate | Emerging: Peste 4.500 tone de miere, exportate &#xEE;n 2025 c&#x103;tre consumatorii din U | abstain | 223 | abstained | ambiguous_subject_geo |
| 1677 | active | KPK Investigation Raja Juli | abstain | 40 | abstained | ambiguous_subject_geo |
| 1678 | candidate | Emerging: La ni&#xF1;ez palestina masacrada | abstain | 1701 | abstained | ambiguous_subject_geo |
| 1680 | candidate | Emerging: 'Minions & Monsters' debuts at $61.4 million, tops weekend box office | abstain | 6 | abstained | insufficient_subject_evidence |
| 1681 | candidate | Emerging: &#x9B8;&#x9CD;&#x9AC;&#x9BE;&#x9AE;&#x9C0;&#x9B0; &#x9A6;&#x9C7;&#x9DF;&#x9BE; & | abstain | 720 | abstained | ambiguous_subject_geo |
| 1682 | candidate | Emerging: Delta flight 'felt a big bang' after apparently being hit by firework while land | abstain | 3 | abstained | insufficient_subject_evidence |
| 1683 | candidate | Emerging: Cargo ship attacked off Yemen coast in Red Sea, British military says | IN | 10 | inferred | headline_geo_consensus |
| 1684 | candidate | Emerging: Jewellery worth millions of euros stolen in French museum burglary | abstain | 2 | abstained | insufficient_subject_evidence |
| 1685 | candidate | Emerging: Princess Kate shares heartwarming family photos after Three Peaks Challenge | abstain | 5 | abstained | ambiguous_subject_geo |
| 1687 | active | Amnesty War Crimes Probe | abstain | 16 | abstained | ambiguous_subject_geo |
| 1689 | candidate | Emerging: This is some serious boomer humor but damn if I didn't nose exhale | abstain | 0 | junk | insufficient_subject_evidence |
| 1690 | candidate | TV Program Listings | abstain | 55 | abstained | ambiguous_subject_geo |
| 1691 | candidate | Emerging: Masterpiece BBC period drama based on book is 'best of all time' | abstain | 31 | abstained | insufficient_subject_evidence |
| 1692 | active | Leclerc Wins Silverstone GP | abstain | 35 | abstained | ambiguous_subject_geo |
| 1693 | active | Wimbledon Quarterfinalists | GB | 110 | inferred | headline_geo_consensus |
| 1694 | candidate | Emerging: Democrat Mallory McMorrow suspends her Michigan Senate campaign | abstain | 11 | abstained | insufficient_subject_evidence |
| 1695 | active | France vs Morocco Quarterfinal | abstain | 34 | abstained | ambiguous_subject_geo |
| 1701 | candidate | Joys of Joyscrolling | abstain | 24 | abstained | insufficient_subject_evidence |
| 1702 | candidate | Arkansas Democrat-Gazette Sections | abstain | 3 | abstained | insufficient_subject_evidence |
| 1704 | candidate | Emerging: &#x627;&#x644;&#x645;&#x635;&#x631;&#x641; &#x64A;&#x634;&#x62C;&#x639; &#x639;& | abstain | 122 | abstained | ambiguous_subject_geo |
| 1705 | candidate | Emerging: Australian PM Apologises For Kylie Minogue "Shagging" Comment | abstain | 3 | abstained | insufficient_subject_evidence |
| 1706 | candidate | Celebrity Health Struggles | abstain | 38 | abstained | ambiguous_subject_geo |
| 1707 | candidate | Emerging: artfight attack to @voidnovaa.bsky.social 

#digitalart #artfight #artfight2026 | abstain | 2 | abstained | insufficient_subject_evidence |
| 1708 | candidate | Emerging: いろいろ出来るかもしれんね
間にｷｯｶｧｺｰｼﾞ入れたら最高やん
内向けの振りして外向けに投げかける感じでね
いつもののせやんけわーーー！っはっはっ！ | abstain | 0 | junk | insufficient_subject_evidence |
| 1710 | candidate | Emerging: &#x41D;&#x43E;&#x440;&#x432;&#x435;&#x433;&#x438;&#x44F; &#x43E;&#x431;&#x44B;&# | abstain | 3 | abstained | insufficient_subject_evidence |
| 1712 | candidate | Emerging: If England can shithouse their way out of Mexico with the win like this, I think | abstain | 0 | abstained | insufficient_subject_evidence |
| 1713 | candidate | Emerging: Impeachment trial of Philippine's Duterte to open in divided Senate | abstain | 13 | abstained | ambiguous_subject_geo |
| 1714 | active | Trump Balogun FIFA Controversy | abstain | 63 | abstained | ambiguous_subject_geo |
| 1716 | active | Otago Snow Closures | abstain | 143 | abstained | ambiguous_subject_geo |
| 1717 | candidate | Emerging: Australia, Fiji sign mutual defence pact to boost Pacific security | abstain | 37 | abstained | ambiguous_subject_geo |
| 1718 | candidate | Emerging: Cooper: World cannot wait for 'AI Hiroshima' before acting on safety concerns \| | abstain | 28 | abstained | ambiguous_subject_geo |
| 1720 | active | Super Typhoon Bavi | CN | 24 | inferred | headline_geo_consensus |
| 1721 | candidate | Delta Flight Hit by Firework | abstain | 12 | abstained | insufficient_subject_evidence |
| 1723 | candidate | July 4th Storm Power Outages | abstain | 10 | abstained | ambiguous_subject_geo |
| 1724 | candidate | White House vs Smithsonian | abstain | 9 | abstained | insufficient_subject_evidence |
| 1725 | candidate | Royals vs Phillies Series | abstain | 10 | abstained | insufficient_subject_evidence |
| 1726 | candidate | Fireworks Hit Chicago Plane | US | 10 | inferred | headline_geo_consensus |
| 1727 | candidate | Trump Intervenes in Balogun Red Card | US | 10 | inferred | anchor_corroborated_subject_geo |
| 1728 | candidate | Solo Row Record | abstain | 9 | abstained | ambiguous_subject_geo |
| 1729 | active | Charlie Kirk Murder Case | abstain | 28 | abstained | ambiguous_subject_geo |
| 1730 | candidate | DC Air Quality After Fireworks | abstain | 8 | abstained | ambiguous_subject_geo |
| 1731 | candidate | Trump Elevates Debates at 250th | US | 8 | inferred | headline_geo_consensus |
| 1736 | candidate | Alpha Box Office Performance | abstain | 13 | junk | ambiguous_subject_geo |
| 1738 | candidate | Odisha Voter List Deletions | abstain | 11 | abstained | ambiguous_subject_geo |
| 1739 | candidate | Fishermen Missing Off Visakhapatnam | abstain | 6 | abstained | insufficient_subject_evidence |
| 1740 | candidate | Mumbai Tree Collapse Deaths | IN | 10 | inferred | headline_geo_consensus |
| 1742 | candidate | Ram Temple Trust Meeting | abstain | 9 | abstained | insufficient_subject_evidence |
| 1743 | candidate | CJP Protest Day 16 | abstain | 11 | abstained | insufficient_subject_evidence |
| 1744 | active | J&K Book Controversy Suspensions | abstain | 9 | abstained | insufficient_subject_evidence |
| 1747 | candidate | Serena Williams Wimbledon Doubles Withdrawal | abstain | 1 | abstained | ambiguous_subject_geo |
| 1748 | candidate | Wimbledon Match Previews | abstain | 1 | abstained | ambiguous_subject_geo |
| 1749 | candidate | Blair Warns Burnham on Tax | abstain | 2 | abstained | insufficient_subject_evidence |
| 1750 | candidate | Women's Voices and Independence | abstain | 3 | abstained | insufficient_subject_evidence |
| 1751 | active | Ukrainian Drone Attack on St. Petersburg Oil Terminal | abstain | 14 | abstained | ambiguous_subject_geo |
| 1752 | candidate | Phone Calls Between Trump, Putin, Zelensky | abstain | 2 | abstained | ambiguous_subject_geo |
| 1753 | candidate | Regional Issues and Incidents | abstain | 6 | abstained | insufficient_subject_evidence |
| 1754 | candidate | Four-Day Work Week in Russia | RU | 4 | inferred | headline_geo_consensus |
| 1755 | candidate | Самое Длинное Слово | abstain | 3 | abstained | insufficient_subject_evidence |
| 1756 | candidate | Ukraine Denies Russian Capture Claims | abstain | 3 | abstained | ambiguous_subject_geo |
| 1757 | candidate | Bacon Cooking Recipes | abstain | 21 | abstained | insufficient_subject_evidence |
| 1758 | candidate | Francesca Vecchioni Wedding | abstain | 5 | abstained | insufficient_subject_evidence |
| 1760 | candidate | Erdoğan Phone Calls with Leaders | abstain | 0 | abstained | insufficient_subject_evidence |
| 1761 | candidate | Veli Ağbaba's Nephew Detained | abstain | 0 | abstained | insufficient_subject_evidence |
| 1763 | candidate | German Protests Against AfD | abstain | 0 | abstained | insufficient_subject_evidence |
| 1764 | candidate | Weather Warnings Germany | abstain | 2 | abstained | insufficient_subject_evidence |
| 1765 | candidate | Pogacar Gifts Stage Win | FR | 11 | inferred | headline_geo_consensus |
| 1766 | candidate | Costa Brava Wildfire | abstain | 0 | abstained | insufficient_subject_evidence |
| 1769 | candidate | Body Found in Canal Saint-Martin | FR | 2 | inferred | headline_geo_consensus |
| 1770 | candidate | Le Pen Presidential Bid | FR | 7 | inferred | headline_geo_consensus |
| 1771 | candidate | Bernard Arnault Tax Adjustment | abstain | 0 | abstained | insufficient_subject_evidence |
| 1777 | candidate | Trump 250 Aniversario EE.UU. | US | 5 | inferred | headline_geo_consensus |
| 1779 | candidate | Zoologin Lydia Möcklinghoff Tod | abstain | 8 | junk | insufficient_subject_evidence |
| 1787 | active | Venezuela Earthquake Death Toll | VE | 20 | inferred | anchor_corroborated_subject_geo |
| 1788 | active | Venezuela Quake Death Toll | VE | 26 | inferred | headline_geo_consensus |
| 1801 | active | Police Arrest Suspected Cultists | NG | 26 | inferred | headline_geo_consensus |
| 1806 | candidate | Anh hùng Ngô Thị Tuyển qua đời | abstain | 1 | junk | insufficient_subject_evidence |
| 1807 | active | Super Typhoon Bavi | abstain | 11 | abstained | ambiguous_subject_geo |
| 1810 | active | Dublin Assault Incidents | abstain | 106 | abstained | ambiguous_subject_geo |
| 1811 | active | Motorcycle Crash Fatalities | abstain | 9 | abstained | insufficient_subject_evidence |
| 1814 | active | Sara Duterte Impeachment Trial | PH | 12 | inferred | headline_geo_consensus |
| 1817 | active | Sri Lanka Prison Riot | abstain | 41 | abstained | ambiguous_subject_geo |
| 1832 | candidate | Emerging: ITV agrees to sell broadcasting arm to Sky for up to &#xA3;1.6bn | abstain | 4 | abstained | ambiguous_subject_geo |
| 1834 | candidate | Emerging: Oil slips after OPEC+ agrees to raise output targets | abstain | 45 | abstained | ambiguous_subject_geo |
| 1836 | candidate | Emerging: Merchantwise Bolsters Team With Senior Licensing Hires | abstain | 261 | abstained | ambiguous_subject_geo |
| 1877 | candidate | China Missile Test Reactions | CN | 17 | junk | headline_geo_consensus |
| 1878 | candidate | Emerging: Who is Ser Torrhen Manderly? Dan Fogler's new House of the Dragon character expl | abstain | 10 | junk | insufficient_subject_evidence |
| 1879 | candidate | Emerging: Rocky, Rambo, Action, Gehstock: Sylvester Stallone wird 80 | abstain | 50 | abstained | ambiguous_subject_geo |
| 1880 | candidate | Emerging: China's Tianwen-2 probe reaches target asteroid, starts scientific exploration-- | abstain | 105 | abstained | ambiguous_subject_geo |
| 1881 | candidate | Portugal World Cup Exit | abstain | 9 | junk | insufficient_subject_evidence |
| 1882 | candidate | Pahalgam Attack Chargesheet | abstain | 11 | abstained | ambiguous_subject_geo |
| 1883 | candidate | Coney Island July 4th Shooting | abstain | 10 | abstained | insufficient_subject_evidence |
| 1884 | candidate | Harry's Solo London Visit | GB | 4 | inferred | headline_geo_consensus |
| 1885 | candidate | TV Schedule Listings | GB | 13 | junk | headline_geo_consensus |
| 1886 | candidate | August Pension Increases | RU | 2 | inferred | headline_geo_consensus |
| 1887 | candidate | Comedian Detained for Insulting Erdogan | abstain | 0 | abstained | insufficient_subject_evidence |
| 1888 | active | Erdogan Insults and Warnings | abstain | 8 | abstained | ambiguous_subject_geo |
| 1889 | candidate | Germany's Social and Policy Issues | DE | 3 | inferred | anchor_corroborated_subject_geo |
| 1891 | active | San Luis Potosí News | abstain | 8 | abstained | insufficient_subject_evidence |
| 1892 | candidate | England Beats Mexico | MX | 8 | inferred | anchor_corroborated_subject_geo |
| 1897 | active | Demands for Release of Gaza Doctor | abstain | 22 | abstained | ambiguous_subject_geo |
| 1912 | active | ISWAP Attacks and Security Responses | abstain | 49 | abstained | ambiguous_subject_geo |
| 1913 | active | Marine Le Pen 2027 Candidacy | abstain | 21 | abstained | ambiguous_subject_geo |
| 1914 | candidate | Emerging: Why some African nations are turning down Trump aid money | abstain | 133 | abstained | ambiguous_subject_geo |
| 1915 | candidate | Emerging: Global ageing: 1.6 billion seniors need more protein by 2050 \| Port Stephens Exa | abstain | 10 | abstained | insufficient_subject_evidence |
| 1916 | candidate | Emerging: CentralAsia: &#x412; &#x440;&#x435;&#x437;&#x443;&#x43B;&#x44C;&#x442;&#x430;&#x | abstain | 6 | junk | insufficient_subject_evidence |
| 1918 | candidate | Emerging: &#x5F37;&#x98B1;&#x5DF4;&#x5A01;&#x903C;&#x8FD1;&#xFF01;&#x6C88;&#x4F2F;&#x6D0B; | abstain | 266 | abstained | ambiguous_subject_geo |
| 1919 | candidate | Mixed: Business and Real Estate Updates | abstain | 0 | junk | insufficient_subject_evidence |
| 1920 | candidate | UK heatwave DIY air con tips | abstain | 408 | abstained | ambiguous_subject_geo |
| 1921 | candidate | India EV and Tourism Growth Updates | abstain | 42 | abstained | ambiguous_subject_geo |
| 1922 | candidate | Canadian Social and Immigration Issues | abstain | 3 | abstained | insufficient_subject_evidence |
| 1924 | candidate | NCERT textbook revisions and tax updates | abstain | 37 | abstained | ambiguous_subject_geo |
| 1925 | candidate | Cancer detection and treatment research | abstain | 45 | abstained | ambiguous_subject_geo |
| 1926 | candidate | Australian Inflation and Supply Shocks | abstain | 11 | junk | insufficient_subject_evidence |
| 1927 | candidate | Supreme Court rulings on consumer protection, abortion | abstain | 68 | abstained | ambiguous_subject_geo |
| 1928 | active | Le Pen 2027 Presidential Bid | FR | 12 | inferred | headline_geo_consensus |
| 1929 | active | China Storm Rescues | abstain | 26 | abstained | ambiguous_subject_geo |
| 1930 | candidate | NYC high-rise structural issues and evacuations | abstain | 104 | abstained | ambiguous_subject_geo |
| 1931 | active | Missing Cargo Plane Off Karachi | PK | 22 | inferred | anchor_corroborated_subject_geo |
| 1932 | active | UNIOSUN Soldier Assault Allegations | abstain | 19 | abstained | ambiguous_subject_geo |
| 1934 | active | Iran Strikes US Bases in Bahrain and Kuwait | IR | 28 | inferred | headline_geo_consensus |
| 1935 | candidate | K92 Mining, Endeavour Silver, Ivanhoe Mines Q2 2026 Production Results | abstain | 1 | abstained | insufficient_subject_evidence |
| 1936 | candidate | NWS Weather Warnings July 8 | abstain | 2 | abstained | insufficient_subject_evidence |
| 1937 | candidate | Mixed: Wildlife and Fisheries Updates | abstain | 0 | junk | insufficient_subject_evidence |
| 1938 | candidate | Assassin's Creed Black Flag Resynced reviews and pre-orders | abstain | 4 | abstained | insufficient_subject_evidence |
| 1939 | candidate | Mixed: Personal Updates and Random Thoughts | abstain | 0 | junk | insufficient_subject_evidence |
| 1940 | candidate | AI actress Tilly Norwood cast in feature film | abstain | 6 | abstained | ambiguous_subject_geo |
| 1941 | candidate | Paris Couture Week 2025 highlights | abstain | 25 | abstained | ambiguous_subject_geo |
| 1943 | candidate | Arsenal transfer targets Morgan Rogers, Gilberto Mora | abstain | 98 | abstained | ambiguous_subject_geo |
| 1944 | candidate | Mixed: NHL and Wordle Updates | abstain | 0 | junk | insufficient_subject_evidence |
| 1945 | candidate | SpaceX joins Nasdaq-100 stock drops | abstain | 28 | abstained | insufficient_subject_evidence |
| 1946 | candidate | Mariska Hargitay to host 2026 Emmy Awards | abstain | 8 | junk | insufficient_subject_evidence |
| 1947 | candidate | Mixed: Pharma and Biotech Updates | abstain | 0 | junk | insufficient_subject_evidence |
| 1948 | candidate | 2026 Awards and Achievements Roundup | abstain | 36 | abstained | ambiguous_subject_geo |
| 1949 | candidate | Q1 2026 Earnings Season Preview | abstain | 26 | abstained | ambiguous_subject_geo |
| 1950 | candidate | Rajkummar Rao as Sourav Ganguly in Dada biopic | abstain | 0 | abstained | insufficient_subject_evidence |
| 1953 | candidate | Celebrity Deaths: Lauren Bennett, Louise Lasser | abstain | 12 | junk | insufficient_subject_evidence |
| 1954 | candidate | NATO summit in Ankara, Turkey | abstain | 20 | abstained | ambiguous_subject_geo |
| 1955 | candidate | Samsung Galaxy Unpacked July 22 foldables | abstain | 29 | abstained | ambiguous_subject_geo |
| 1956 | candidate | Summer entertainment and activities roundup | abstain | 25 | abstained | ambiguous_subject_geo |
| 1957 | active | Switzerland Beats Colombia on Penalties | CO | 18 | inferred | headline_geo_consensus |
| 1958 | candidate | Iran asserts control of Strait of Hormuz | abstain | 54 | abstained | ambiguous_subject_geo |
| 1959 | candidate | Mixed: Violent Crimes and Legal Outcomes | abstain | 8 | junk | insufficient_subject_evidence |
| 1961 | active | Canada Denies Indian Link in Nijjar Killing | IN | 19 | inferred | headline_geo_consensus |
| 1962 | candidate | Mixed: Macedonian political and economic updates | abstain | 0 | junk | insufficient_subject_evidence |
| 1963 | candidate | Data center concerns spark community meetings | abstain | 84 | abstained | ambiguous_subject_geo |
| 1964 | active | Mitch McConnell and Wife News | abstain | 103 | abstained | ambiguous_subject_geo |
| 1965 | candidate | PM Modi visits Prambanan Temple in Indonesia | abstain | 0 | abstained | insufficient_subject_evidence |
| 1966 | active | US Attacks Iran Despite Ceasefire | abstain | 10 | abstained | ambiguous_subject_geo |
| 1967 | active | Iran Missile Attack on Jordan | IR | 119 | inferred |  |
| 1968 | candidate | Mesa Verde Wildfire Closure | abstain | 10 | abstained | insufficient_subject_evidence |
| 1969 | candidate | KNON Radio Shows | abstain | 9 | abstained | insufficient_subject_evidence |
| 1970 | candidate | US Charges Bishnoi Brar | abstain | 8 | abstained | insufficient_subject_evidence |
| 1971 | candidate | Ohtani Hits 300th Homer | abstain | 8 | abstained | ambiguous_subject_geo |
| 1972 | candidate | Mumbai Runway Near-Collision | IN | 12 | inferred | anchor_corroborated_subject_geo |
| 1973 | candidate | Himachal Pradesh Mountains and Peaks | abstain | 11 | abstained | insufficient_subject_evidence |
| 1974 | candidate | NIA Raids Terror Radicalisation | abstain | 10 | abstained | ambiguous_subject_geo |
| 1976 | candidate | UK Speeding Warnings | abstain | 17 | abstained | insufficient_subject_evidence |
| 1977 | candidate | Essex Neo-Nazi Jailed | abstain | 11 | abstained | insufficient_subject_evidence |
| 1978 | candidate | UK Crime Files Series | abstain | 10 | abstained | insufficient_subject_evidence |
| 1979 | candidate | UK Defense Documents Leak | abstain | 10 | abstained | insufficient_subject_evidence |
| 1980 | candidate | IOC Lifts Russia Ban | RU | 24 | inferred | headline_geo_consensus |
| 1982 | candidate | Milano Metro Attacks | abstain | 17 | abstained | insufficient_subject_evidence |
| 1983 | candidate | Rocks Thrown from Muro Torto | abstain | 8 | abstained | insufficient_subject_evidence |
| 1984 | candidate | Kırkpınar Yağlı Güreşleri | abstain | 9 | abstained | insufficient_subject_evidence |
| 1985 | candidate | Starmer Urges NATO Unity | abstain | 10 | abstained | ambiguous_subject_geo |
| 1986 | candidate | Trump Ankara Görüşmeleri | abstain | 7 | abstained | ambiguous_subject_geo |
| 1987 | candidate | NATO Chief Backs US Iran Strikes | IR | 19 | inferred | headline_geo_consensus |
| 1988 | active | US Attacks Iran Retaliation | abstain | 47 | abstained | ambiguous_subject_geo |
| 1989 | candidate | Iran Nuclear Deal Under Pressure | IR | 14 | inferred | headline_geo_consensus |
| 1990 | candidate | USA Attacks Iran | IR | 11 | inferred | headline_geo_consensus |
| 1991 | candidate | EU Advises Avoid Iran Iraq Airspace | abstain | 11 | abstained | ambiguous_subject_geo |
| 1992 | active | US-Iran Talks Continue | abstain | 35 | abstained | ambiguous_subject_geo |
| 1993 | candidate | Le Pen Candidacy Despite Conviction | abstain | 13 | abstained | ambiguous_subject_geo |
| 1994 | candidate | Russian Airstrikes on Ukraine | UA | 15 | inferred | anchor_corroborated_subject_geo |
| 1996 | candidate | Prabowo-Modi Prambanan Conservation | abstain | 9 | abstained | ambiguous_subject_geo |
| 1997 | candidate | Dutton Ranch Season 1 Finale | abstain | 2 | abstained | insufficient_subject_evidence |
| 1998 | active | China Landslide Death Toll | CN | 13 | inferred | anchor_corroborated_subject_geo |
| 1999 | active | Oil Prices Jump After Trump Ends Iran Ceasefire | abstain | 8 | abstained | ambiguous_subject_geo |
| 2000 | candidate | Molly Tea Louis Vuitton Trademark | CN | 7 | inferred | headline_geo_consensus |
| 2001 | active | 정이한 피습 자작극 구속 | abstain | 30 | abstained | ambiguous_subject_geo |
| 2002 | active | Coquitlam House Fire Death | abstain | 26 | abstained | ambiguous_subject_geo |
| 2003 | active | Solo Road Trip Changes Perspective on Chronic Pain | abstain | 24 | abstained | insufficient_subject_evidence |
| 2004 | active | Free Flights to Alice Springs | abstain | 24 | abstained | insufficient_subject_evidence |
| 2005 | active | Thomas Jenkins NRL Immortal Record | abstain | 19 | abstained | insufficient_subject_evidence |
| 2006 | active | Hanson Accelerationism Analysis | abstain | 18 | abstained | insufficient_subject_evidence |
| 2007 | candidate | Helping Adult Kids with Loans | abstain | 10 | abstained | insufficient_subject_evidence |
| 2008 | candidate | Telstra Nationwide Outage | abstain | 10 | abstained | insufficient_subject_evidence |
| 2009 | active | Australian War Memorial Membership | abstain | 10 | abstained | insufficient_subject_evidence |
| 2010 | candidate | Mysterious Space Balls Found | abstain | 7 | abstained | insufficient_subject_evidence |
| 2011 | candidate | Job Offers in Poland | abstain | 8 | abstained | insufficient_subject_evidence |
| 2012 | active | Police Misconduct Sanctions | abstain | 11 | abstained | ambiguous_subject_geo |
| 2013 | candidate | Nigeria Off-Budget Spending Allegations | NG | 6 | inferred | headline_geo_consensus |
| 2014 | candidate | El-Rufai Doctor Arrest | abstain | 8 | abstained | insufficient_subject_evidence |
| 2015 | candidate | Nigeria Condemns South Africa Killings | abstain | 7 | abstained | ambiguous_subject_geo |
| 2016 | candidate | Japan Economic and Tech News | abstain | 8 | abstained | insufficient_subject_evidence |
| 2017 | active | Switzerland Advances to Quarterfinals | abstain | 23 | abstained | ambiguous_subject_geo |
| 2018 | candidate | Violence Against Women | abstain | 8 | abstained | insufficient_subject_evidence |
| 2019 | candidate | Storm and Rain Warnings | abstain | 5 | abstained | insufficient_subject_evidence |
| 2020 | active | Grönland Streit mit Trump | abstain | 61 | abstained | ambiguous_subject_geo |
| 2022 | candidate | Nepal PM's First 100 Days | abstain | 6 | abstained | ambiguous_subject_geo |
| 2023 | candidate | Damascus Cafe Bombing Condemned | abstain | 0 | abstained | insufficient_subject_evidence |
| 2024 | active | Connor Murphy Death | abstain | 20 | abstained | ambiguous_subject_geo |
| 2025 | active | Wimbledon 2026 Upsets | GB | 73 | inferred | headline_geo_consensus |
| 2026 | active | Mnangagwa Term Extension | ZW | 35 | inferred | headline_geo_consensus |
| 2027 | candidate | Stephen Francis Death | abstain | 9 | abstained | insufficient_subject_evidence |
| 2029 | active | Trump FIFA World Cup Scandal | abstain | 138 | abstained | ambiguous_subject_geo |
| 2030 | active | Mundial 2026 Coverage | abstain | 54 | abstained | ambiguous_subject_geo |
| 2036 | active | Sports and Politics Mix | abstain | 195 | abstained | ambiguous_subject_geo |
| 2039 | active | Dayanne Rodrigues Disappearance | abstain | 205 | abstained | ambiguous_subject_geo |
| 2052 | active | Brasil vs Norwegia Piala Dunia 2026 | abstain | 59 | abstained | ambiguous_subject_geo |
| 2069 | candidate | Emerging: Bumper haul of Pacific bluefin tuna a double-edged sword for Japan's fishermen \| | abstain | 0 | abstained | insufficient_subject_evidence |
| 2070 | candidate | Emerging: Winnipeg Jets Organizational Depth Chart

https://www.rawchili.com/nhl/617697/ | abstain | 6 | abstained | insufficient_subject_evidence |
| 2071 | candidate | Emerging: Who is Clacton by-election candidate Count Binface? | abstain | 21 | junk | insufficient_subject_evidence |
| 2072 | candidate | Emerging: Ireland's Charleen Murphy dumped from Love Island after short but dramatic stint | abstain | 73 | abstained | ambiguous_subject_geo |
| 2074 | candidate | Emerging: Extreme speeding exposed as drivers clocked at up to 114mph on 30mph roads | abstain | 17 | abstained | ambiguous_subject_geo |
| 2075 | candidate | Emerging: Duke Wellington's brings in the community with World Cup | abstain | 24 | abstained | ambiguous_subject_geo |
| 2076 | candidate | Emerging: Bride Feels Robbed Of Joy From Intimate Wedding Ceremony, As Dad Keeps Prioritiz | abstain | 4 | abstained | insufficient_subject_evidence |
| 2077 | candidate | Emerging: Climate change threatens to dent Italy's long-term economic growth and&#xA0; wor | abstain | 253 | abstained | ambiguous_subject_geo |
| 2078 | candidate | Emerging: Detached &#xA3;1m four-bed house in Portishead on the market | abstain | 42 | abstained | ambiguous_subject_geo |
| 2079 | candidate | Emerging: 'Law & Order: SVU' star Mariska Hargitay tapped to host 2026 Emmy Awards &#x2013 | abstain | 2 | abstained | insufficient_subject_evidence |
| 2080 | candidate | Emerging: Greg James leaks behind the scenes details after attending Taylor Swift and Trav | abstain | 33 | abstained | ambiguous_subject_geo |
| 2081 | candidate | Christopher Nolan's The Odyssey | abstain | 37 | junk | ambiguous_subject_geo |
| 2082 | candidate | Emerging: Cheap Charlie's in Rochester closing after 58 years | abstain | 210 | abstained | ambiguous_subject_geo |
| 2084 | active | Child Sexual Assault and Murder Cases | abstain | 110 | abstained | ambiguous_subject_geo |
| 2085 | candidate | Emerging: Klart: Alvaro Arbeloa tar &#xF6;ver Premier League-klubben Fulham | abstain | 21 | abstained | ambiguous_subject_geo |
| 2086 | candidate | Emerging: 'Jesus Christ Superstar' returns to rock roots with West End revival \| WABX 107. | abstain | 0 | abstained | insufficient_subject_evidence |
| 2087 | candidate | Emerging: 私に劣等感抱えすぎな従妹、昔私にマウント取って普通に従妹が間違えてたんだけど
後で謝罪とか何も無く、それで合ってたっていうのを自分からちゃんと言ってて
イラッと | abstain | 0 | junk | insufficient_subject_evidence |
| 2088 | candidate | Emerging: 【ゼンゼロ】衣装ナーフ前後のノルムーで比較🥰【ゼンレスゾーンゼロ】

https://www.playing-games.com/1050662/

【ゼンゼロ | abstain | 0 | abstained | insufficient_subject_evidence |
| 2089 | candidate | Emerging: &#x41D;&#x43E;&#x432;&#x43E;&#x441;&#x438;&#x431;&#x438;&#x440;&#x441;&#x43A;&#x | abstain | 65 | abstained | ambiguous_subject_geo |
| 2090 | candidate | Emerging: EU aviation agency tells operators to avoid Iran, Iraq and Lebanon airspaces unt | abstain | 0 | abstained | insufficient_subject_evidence |
| 2091 | candidate | Emerging: New US attacks on Iran were absolutely necessary, NATO chief says | abstain | 14 | abstained | ambiguous_subject_geo |
| 2092 | candidate | Emerging: The older I get, the more news and information I digest. As I get wiser, the tas | abstain | 0 | junk | insufficient_subject_evidence |
| 2093 | candidate | Emerging: IOC lifts Russia suspension ahead of LA 2028 Olympics | RU | 2 | inferred | headline_geo_consensus |
| 2094 | active | Emerging: Qu&#xE9;bec veut aider l'industrie foresti&#xE8;re &#xE0; se diversifier | abstain | 166 | abstained | ambiguous_subject_geo |
| 2095 | candidate | Emerging: Immigration agent fatally shot a man in Houston during an enforcement operation, | abstain | 38 | abstained | ambiguous_subject_geo |
| 2096 | candidate | Yoon's Arrest Obstruction Conviction | abstain | 16 | junk | insufficient_subject_evidence |
| 2097 | candidate | Emerging: 10 Best Sting Songs of All Time - Singersroom.com | abstain | 61 | abstained | insufficient_subject_evidence |
| 2098 | candidate | Emerging: The spinning wheel of luck - The Tribune | abstain | 184 | abstained | ambiguous_subject_geo |
| 2099 | candidate | Emerging: This Day in Rock History: July 8 | abstain | 23 | abstained | insufficient_subject_evidence |
| 2100 | candidate | Emerging: Naslovne strane za sredu, 8. jul 2026. godine | abstain | 80 | abstained | ambiguous_subject_geo |
| 2101 | candidate | Emerging: Sot certifikohen rezultatet p&#xEB;rfundimtare t&#xEB; zgjedhjeve t&#xEB; 7 qers | abstain | 9 | abstained | ambiguous_subject_geo |
| 2102 | candidate | Emerging: U Skup&#x161;tini nastavljena objedinjena rasprava o 18 ta&#x10D;aka dnevnog red | abstain | 0 | abstained | insufficient_subject_evidence |
| 2103 | candidate | Emerging: Koncerti i Kanye West, Rama: 4 mln euro p&#xEB;r t&#xEB; mos turp&#xEB;ruar Shqi | abstain | 40 | abstained | ambiguous_subject_geo |
| 2104 | candidate | Emerging: O&#x161;tra rasprava o Srbiji u EP: Kos podr&#x17E;ala Klaster 3, Picula tra&#x1 | abstain | 212 | abstained | ambiguous_subject_geo |
| 2105 | candidate | Emerging: Danimarka i p&#xEB;rgjigjet Trumpit: Grenlanda nuk &#xEB;sht&#xEB; n&#xEB; shitj | abstain | 184 | abstained | ambiguous_subject_geo |
| 2106 | candidate | Emerging: استاندار یزد: حضور حماسی مردم در تشییع رهبر شهید، خار چشم بدخواهان نظام است | abstain | 143 | abstained | ambiguous_subject_geo |
| 2145 | candidate | Emerging: ジェリーズポップコーン期間限定イベント販売がなんばマルイで開催

📅 7/15(水)
📍 なんばマルイ

https://eventpotal.com/osak | abstain | 5 | abstained | insufficient_subject_evidence |
| 2146 | candidate | Emerging: Shohei Ohtani hits 300th homer, but Dodgers' errors fuel Rockies' 8th-inning ral | abstain | 5 | abstained | insufficient_subject_evidence |
| 2147 | candidate | Emerging: President Ilham Aliyev receives Deputy Prime Minister of Jordan (PHOTO) | abstain | 88 | abstained | ambiguous_subject_geo |
| 2148 | candidate | Emerging: Questions over AI campaign parodies rise as regulations struggle to control it | abstain | 34 | abstained | ambiguous_subject_geo |
| 2149 | candidate | Live-Action Moana Remake | abstain | 29 | junk | ambiguous_subject_geo |
| 2150 | candidate | Emerging: Platner may be finished, but voters' hunger for change and willingness to take r | abstain | 35 | abstained | insufficient_subject_evidence |
| 2151 | candidate | Emerging: &#x986;&#x99C; &#x98F;&#x995;&#x987; &#x9B8;&#x9AE;&#x9DF;&#x9C7; &#x9B8;&#x9C2; | abstain | 1 | abstained | insufficient_subject_evidence |
| 2152 | candidate | Emerging: Lauren Bennett kimdir? Lauren Bennett kaç yaşında, nereli? Lauren Bennett neden | abstain | 23 | abstained | insufficient_subject_evidence |
| 2153 | active | Mysterious Airstrikes on Iran | IR | 21 | inferred | headline_geo_consensus |
| 2154 | candidate | Emerging: Are You Chasing False Gods? \| News, Sports, Jobs | abstain | 31 | junk | ambiguous_subject_geo |
| 2155 | candidate | Emerging: How to Protect Yourself from the Foodborne Illness Sweeping NY | abstain | 453 | abstained | ambiguous_subject_geo |
| 2156 | active | Upcoming Events 2026-2027 | abstain | 208 | abstained | ambiguous_subject_geo |
| 2157 | active | Erdogan Gifts Pistols at NATO Summit | abstain | 18 | abstained | ambiguous_subject_geo |
| 2158 | candidate | Emerging: Arrestohen dy v&#xEB;llez&#xEB;r n&#xEB; Prishtin&#xEB;, sulmuan edhe polic&#xEB | abstain | 672 | abstained | ambiguous_subject_geo |
| 2159 | candidate | Emerging: &#x41F;&#x43E; &#x438;&#x442;&#x43E;&#x433;&#x430;&#x43C; 5 &#x43C;&#x435;&#x441 | abstain | 18 | abstained | ambiguous_subject_geo |
| 2160 | candidate | Emerging: '&#x92C;&#x939;&#x942; &#x92C;&#x928;&#x93E;&#x915;&#x930; &#x932;&#x93E;&#x92F; | abstain | 125 | abstained | ambiguous_subject_geo |
| 2161 | candidate | Emerging: Avrupa Borsalar&#x131;nda Y&#xFC;zde 1,2'ye Varan D&#xFC;&#x15F;&#xFC;&#x15F; | abstain | 940 | abstained | ambiguous_subject_geo |
| 2162 | candidate | Emerging: Mot me diell dhe vran&#xEB;sira, pasdite mund&#xEB;si p&#xEB;r shi dhe bubullima | abstain | 814 | abstained | ambiguous_subject_geo |
| 2163 | candidate | Quotes and Proverbs on Life Lessons | abstain | 6 | abstained | insufficient_subject_evidence |
| 2164 | candidate | Mixed: German corporate news | abstain | 0 | junk | insufficient_subject_evidence |
| 2165 | candidate | Mixed: Creative hobbies and personal updates | abstain | 0 | junk | insufficient_subject_evidence |
| 2166 | candidate | Mixed: Personal Daily Struggles | abstain | 0 | junk | insufficient_subject_evidence |
| 2167 | candidate | Sheikh Hasina plans December return to Bangladesh | abstain | 2 | abstained | insufficient_subject_evidence |
| 2168 | candidate | SUNshine Girls Features | abstain | 14 | junk | insufficient_subject_evidence |
| 2169 | candidate | Public Records Guides | abstain | 22 | junk | insufficient_subject_evidence |
| 2170 | candidate | Mixed: Polish news | abstain | 0 | junk | insufficient_subject_evidence |
| 2171 | candidate | Mixed: Auto and Tech Product Launches | abstain | 0 | junk | insufficient_subject_evidence |
| 2172 | active | Ryanair Window Incident | abstain | 41 | abstained | ambiguous_subject_geo |
| 2173 | candidate | Mixed: Education and Training Camps | abstain | 0 | junk | insufficient_subject_evidence |
| 2174 | candidate | Portugal appoints Jorge Jesus as head coach | abstain | 6 | abstained | ambiguous_subject_geo |
| 2175 | candidate | UN: 1 million women lose aid after funding cuts | abstain | 2 | abstained | insufficient_subject_evidence |
| 2176 | candidate | New 'Little House' series remake | abstain | 30 | abstained | ambiguous_subject_geo |
| 2177 | active | Burnham Apologizes for Gaza Stance | PS | 19 | inferred | headline_geo_consensus |
| 2178 | candidate | Apollo bids $7.7B for EasyJet | abstain | 0 | abstained | insufficient_subject_evidence |
| 2179 | candidate | Mixed: Local News and Opinions | abstain | 0 | junk | insufficient_subject_evidence |
| 2180 | active | Turkey Sells S-400 to Gulf | abstain | 14 | abstained | ambiguous_subject_geo |
| 2181 | candidate | Price Target Changes by Analysts | abstain | 68 | abstained | ambiguous_subject_geo |
| 2182 | candidate | Mixed: TV series and health news | abstain | 0 | junk | insufficient_subject_evidence |
| 2183 | candidate | Mixed: Indian regional news | abstain | 0 | junk | insufficient_subject_evidence |
| 2184 | candidate | AP-NORC poll: US Jewish adults experience antisemitic assault/harassment | abstain | 4 | abstained | ambiguous_subject_geo |
| 2185 | candidate | Mixed: UK retail and food business openings | abstain | 0 | junk | insufficient_subject_evidence |
| 2186 | candidate | Gordie Howe Bridge opening delayed to late July | abstain | 26 | abstained | ambiguous_subject_geo |
| 2187 | active | Dangote Kenya Refinery Project | abstain | 21 | abstained | ambiguous_subject_geo |
| 2188 | active | Weekend Events and Activities | abstain | 22 | abstained | insufficient_subject_evidence |
| 2189 | candidate | Heathrow losing Europe's busiest airport status | abstain | 21 | abstained | ambiguous_subject_geo |
| 2190 | candidate | China first reusable rocket landing | abstain | 8 | abstained | ambiguous_subject_geo |
| 2191 | candidate | Bear scavenges human remains in Colorado | abstain | 27 | abstained | ambiguous_subject_geo |
| 2192 | candidate | King Charles hosts Prince Harry and family for reunion | abstain | 56 | abstained | ambiguous_subject_geo |
| 2193 | candidate | The Rolling Stones 25th studio album | abstain | 4 | abstained | ambiguous_subject_geo |
| 2194 | candidate | Ann Widdecombe Dies Aged 78 | abstain | 108 | junk | ambiguous_subject_geo |
| 2195 | candidate | Bonnie Tyler Dies at 75 | abstain | 25 | junk | insufficient_subject_evidence |
| 2196 | candidate | Emerging: Lionel Messi once bathed baby Lamine Yamal in mind-blowing photo &#x2013; NBC Lo | abstain | 128 | abstained | ambiguous_subject_geo |
| 2197 | candidate | Emerging: 私は幸せ贅沢者だからペットのお掃除したし　お料理したごはん食べれたし　お風呂入れたし　ベットでゴロゴロしてるし　スマホいじいじして　眠くなったら　誰にも襲われる | abstain | 26 | abstained | ambiguous_subject_geo |
| 2198 | candidate | Emerging: Caldwell Appoints John Blank as Chief Operating Officer and Names Regional Manag | abstain | 32 | abstained | ambiguous_subject_geo |
| 2199 | candidate | Emerging: B.C. whale watchers join forces to help tangled humpback 'Pop Tart' \| Fort St. J | abstain | 20 | abstained | ambiguous_subject_geo |
| 2200 | candidate | Emerging: &#x411;&#x43B;&#x438;&#x441;&#x442;&#x430;&#x432;&#x438; &#x443;&#x43C; &#x2013; | abstain | 66 | abstained | insufficient_subject_evidence |
| 2201 | candidate | Emerging: Scotdesco water security project completed with new storage tanks | abstain | 992 | abstained | ambiguous_subject_geo |
| 2202 | candidate | Emerging: Victor Marx projected to win Colorado GOP gubernatorial primary | abstain | 219 | abstained | ambiguous_subject_geo |
| 2203 | candidate | Emerging: Domestic Shifts in America | abstain | 102 | abstained | ambiguous_subject_geo |
| 2204 | candidate | Emerging: Asda builds giant 'Wonderwall' as England fans rally behind Three Lions ahead of | abstain | 49 | abstained | ambiguous_subject_geo |
| 2205 | active | Wimbledon 2026 Women's Singles | GB | 107 | inferred | headline_geo_consensus |
| 2206 | candidate | Emerging: Pourquoi les trentenaires (et plus) sont-elles accro aux s&#xE9;ries pour ados&# | abstain | 116 | abstained | ambiguous_subject_geo |
| 2207 | candidate | Labor Market Deterioration | abstain | 20 | abstained | insufficient_subject_evidence |
| 2208 | candidate | Emerging: No negotiations as Brigham and Women's nurses work stoppage continues | abstain | 169 | abstained | ambiguous_subject_geo |
| 2209 | candidate | Emerging: Shit is so dystopian in our country rn i am not losing hope but I'd be lying if | abstain | 48 | abstained | ambiguous_subject_geo |
| 2210 | active | Trump Vetoes Housing Bill | US | 23 | inferred | anchor_corroborated_subject_geo |
| 2211 | active | Trump Subpoenas NYT Journalists | abstain | 14 | abstained | ambiguous_subject_geo |
| 2212 | active | Legionnaires' Outbreak NYC Buildings | abstain | 15 | abstained | insufficient_subject_evidence |
| 2213 | candidate | Walz Pardon Deportation Controversy | abstain | 12 | abstained | insufficient_subject_evidence |
| 2214 | candidate | Last Iron Lung User Dies | abstain | 9 | abstained | ambiguous_subject_geo |
| 2215 | active | Stocks To Watch Today | abstain | 10 | abstained | insufficient_subject_evidence |
| 2216 | active | Explosive Diarrhea Outbreak | abstain | 9 | abstained | insufficient_subject_evidence |
| 2217 | active | Rajpal Yadav Sentenced | abstain | 20 | abstained | insufficient_subject_evidence |
| 2218 | active | Jana Nayagan Censor Clearance | abstain | 14 | abstained | ambiguous_subject_geo |
| 2219 | active | 1996 Srinagar Violence Chargesheet | abstain | 12 | abstained | ambiguous_subject_geo |
| 2220 | active | ED Attaches Vikas Garg Assets | abstain | 9 | abstained | insufficient_subject_evidence |
| 2221 | active | S. Janaki Dies at 88 | abstain | 20 | abstained | ambiguous_subject_geo |
| 2222 | active | ED FEMA Probe Film Producer | abstain | 8 | abstained | ambiguous_subject_geo |
| 2223 | active | National Anthem Guidelines | abstain | 8 | abstained | ambiguous_subject_geo |
| 2224 | active | Bonnie Tyler Death | abstain | 10 | abstained | insufficient_subject_evidence |
| 2225 | active | Bonnie Tyler Dies at 75 | abstain | 22 | abstained | ambiguous_subject_geo |
| 2226 | candidate | GP Surgery Rankings 2026 | abstain | 14 | abstained | insufficient_subject_evidence |
| 2227 | active | Hosepipe Bans in Essex | abstain | 13 | abstained | ambiguous_subject_geo |
| 2228 | active | Michael Ward Acquitted | abstain | 14 | abstained | ambiguous_subject_geo |
| 2229 | active | Bayeux Tapestry Returns to UK | abstain | 12 | abstained | ambiguous_subject_geo |
| 2230 | active | Wimbledon 2026 Semifinals | GB | 10 | inferred | anchor_corroborated_subject_geo |
| 2231 | candidate | Rupert Lowe Dunblane Outrage | abstain | 10 | abstained | insufficient_subject_evidence |
| 2232 | candidate | Brexit Politician Murder Investigation | abstain | 9 | abstained | insufficient_subject_evidence |
| 2233 | candidate | Bonnie Tyler Death | abstain | 9 | abstained | insufficient_subject_evidence |
| 2234 | active | Dermot Murnaghan Tributes | abstain | 10 | abstained | ambiguous_subject_geo |
| 2235 | candidate | Cyclone Approaching Moscow | RU | 12 | inferred | anchor_corroborated_subject_geo |
| 2236 | active | Desecration of Soviet War Cemetery in Netherlands | abstain | 10 | abstained | insufficient_subject_evidence |
| 2237 | active | Alpinists Fall in Kabardino-Balkaria | abstain | 10 | abstained | insufficient_subject_evidence |
| 2238 | candidate | Голикова о болезнях-всадниках | abstain | 9 | abstained | ambiguous_subject_geo |
| 2239 | active | Israel Alerts US of Iran Plot to Kill Trump | abstain | 24 | abstained | ambiguous_subject_geo |
| 2240 | active | US Strikes Kill 14 in Iran | IR | 13 | inferred | anchor_corroborated_subject_geo |
| 2241 | active | Trump Ends Ceasefire, Continues Talks | US | 19 | inferred | headline_geo_consensus |
| 2242 | candidate | Trump Claims Iran Wants Deal | abstain | 12 | abstained | ambiguous_subject_geo |
| 2243 | active | US-Iran Gulf Exchanges | IR | 10 | inferred | headline_geo_consensus |
| 2244 | candidate | Italy Expels Russian Attachés | abstain | 13 | abstained | ambiguous_subject_geo |
| 2245 | active | Bonnie Tyler Death | abstain | 20 | abstained | insufficient_subject_evidence |
| 2246 | active | Düsseldorf-Köln Bahnstrecke Sperrung | abstain | 16 | abstained | insufficient_subject_evidence |
| 2247 | candidate | tz-Wiesn-Madl 2026 Candidates | abstain | 14 | abstained | insufficient_subject_evidence |
| 2248 | candidate | Achim Wolff Death | abstain | 12 | abstained | insufficient_subject_evidence |
| 2249 | active | Bundesrat Supports Yes Means Yes | abstain | 12 | abstained | insufficient_subject_evidence |
| 2250 | active | Germany Buys US Tomahawk Missiles | DE | 13 | inferred | headline_geo_consensus |
| 2251 | candidate | Germany Buys Tomahawk Missiles | abstain | 11 | abstained | ambiguous_subject_geo |
| 2252 | candidate | Schongau Amoktat Schüler Helden | abstain | 10 | abstained | insufficient_subject_evidence |
| 2253 | active | Ryanair Window Incident | abstain | 8 | abstained | insufficient_subject_evidence |
| 2254 | active | Spain Deadly Wildfire | abstain | 11 | abstained | insufficient_subject_evidence |
| 2255 | active | Southern Spain Wildfire Deaths | abstain | 9 | abstained | insufficient_subject_evidence |
| 2256 | candidate | Heat Alerts in Spain | abstain | 8 | abstained | insufficient_subject_evidence |
| 2257 | active | Erdogan's Revolver Gift | TR | 20 | inferred | anchor_corroborated_subject_geo |
| 2258 | active | Erdogan Gifts Revolvers to NATO Leaders | TR | 13 | inferred | anchor_corroborated_subject_geo |
| 2259 | active | Trump Greenland Threats Rhetorical | US | 9 | inferred | headline_geo_consensus |
| 2260 | active | Turkey S-400 Sale Sensitivity | abstain | 8 | abstained | ambiguous_subject_geo |
| 2261 | active | Patriot Missile Production in Ukraine | abstain | 16 | abstained | ambiguous_subject_geo |
| 2262 | active | Bribery Scandal at Chamber of Commerce | abstain | 12 | abstained | insufficient_subject_evidence |
| 2263 | active | Best New Books | abstain | 15 | abstained | insufficient_subject_evidence |
| 2264 | active | National French Fry Day Deals | FR | 12 | inferred | headline_geo_consensus |
| 2265 | active | Bonnie Tyler Death | abstain | 12 | abstained | insufficient_subject_evidence |
| 2266 | candidate | Weather Forecast Jakarta | ID | 12 | inferred | anchor_corroborated_subject_geo |
| 2267 | active | Bonnie Tyler Morre | abstain | 14 | abstained | insufficient_subject_evidence |
| 2268 | active | Andrey Santos Transfer | abstain | 10 | abstained | ambiguous_subject_geo |
| 2269 | active | Sheinbaum vs Feinmann Controversy | MX | 16 | inferred | headline_geo_consensus |
| 2270 | active | Mexico Seeks ICE Death Charges | MX | 13 | inferred | anchor_corroborated_subject_geo |
| 2271 | active | Quansah Two-Match Ban | MX | 10 | inferred | headline_geo_consensus |
| 2272 | active | Infanta Sofía's First Speech | abstain | 10 | abstained | insufficient_subject_evidence |
| 2273 | active | New CJNG Leader Identified | abstain | 9 | abstained | insufficient_subject_evidence |
| 2274 | candidate | Heavy Rain Warnings in Chungnam | abstain | 12 | abstained | insufficient_subject_evidence |
| 2275 | candidate | Weather Alerts in Gyeongbuk | abstain | 9 | abstained | insufficient_subject_evidence |
| 2276 | candidate | Heavy Rain Warnings in Chungbuk | abstain | 8 | abstained | insufficient_subject_evidence |
| 2277 | active | Shoe Factory Fire | CN | 10 | inferred | headline_geo_consensus |
| 2278 | active | China CPI PPI June | CN | 13 | inferred | headline_geo_consensus |
| 2279 | active | Southern China Flood Deaths | CN | 13 | inferred | anchor_corroborated_subject_geo |
| 2280 | active | Typhoon Bavi Approaches | abstain | 13 | abstained | ambiguous_subject_geo |
| 2281 | active | Typhoon Prevention and Rescue | CN | 10 | inferred | headline_geo_consensus |
| 2282 | active | China Warns of Claude Code Backdoor | CN | 9 | inferred | anchor_corroborated_subject_geo |
| 2283 | active | Typhoon Bavi Landfall | CN | 15 | inferred | headline_geo_consensus |
| 2284 | candidate | Taifun Bavi Evakuierungen | abstain | 8 | abstained | ambiguous_subject_geo |
| 2285 | active | Philippines Rejects Chinese Claims | abstain | 8 | abstained | ambiguous_subject_geo |
| 2286 | candidate | China Shoe Factory Fire | CN | 8 | inferred | anchor_corroborated_subject_geo |
| 2287 | active | June Employment Data | abstain | 13 | abstained | insufficient_subject_evidence |
| 2288 | active | Amber Alert Alberta | abstain | 12 | abstained | insufficient_subject_evidence |
| 2289 | active | B.C. Charter Boat Sinking | abstain | 11 | abstained | insufficient_subject_evidence |
| 2290 | active | B.C. Nurses Strike Escalates | abstain | 10 | abstained | insufficient_subject_evidence |
| 2291 | candidate | Vancouver Wine Bars | abstain | 9 | abstained | insufficient_subject_evidence |
| 2292 | active | Edmonton Dining Guide | abstain | 9 | abstained | insufficient_subject_evidence |
| 2293 | active | Canoe Rescue in Burrard Inlet | abstain | 8 | abstained | insufficient_subject_evidence |
| 2294 | active | FIFA Racism Probe IShowSpeed | abstain | 12 | abstained | ambiguous_subject_geo |
| 2295 | candidate | AKTOR Motor Oil Dioriga Gas Deal | abstain | 11 | abstained | insufficient_subject_evidence |
| 2296 | active | Ioane Sa'ula Acting Journey | abstain | 24 | abstained | insufficient_subject_evidence |
| 2297 | active | Telstra Outage Prevention | abstain | 24 | abstained | insufficient_subject_evidence |
| 2298 | active | Chris Hemsworth's $2000 Meal | abstain | 24 | abstained | insufficient_subject_evidence |
| 2299 | active | Leuralla Estate Record Sale | abstain | 24 | abstained | insufficient_subject_evidence |
| 2300 | active | Jacky Hudson Bowls Star | abstain | 24 | abstained | insufficient_subject_evidence |
| 2301 | active | iPhone and Baby Bust | abstain | 24 | abstained | insufficient_subject_evidence |
| 2302 | active | Government Blamed for Slump | abstain | 24 | abstained | insufficient_subject_evidence |
| 2303 | active | Sydney Beauty Vantage Points | abstain | 24 | abstained | insufficient_subject_evidence |
| 2304 | active | David Eadie Rescue | abstain | 23 | abstained | insufficient_subject_evidence |
| 2305 | active | Murray's Bus Trip | abstain | 20 | abstained | insufficient_subject_evidence |
| 2306 | active | Gold Coast Retro Motels | abstain | 17 | abstained | insufficient_subject_evidence |
| 2307 | active | Procurement Costs Drain | abstain | 15 | abstained | insufficient_subject_evidence |
| 2308 | active | Derryn Hinch Dies | abstain | 13 | abstained | insufficient_subject_evidence |
| 2309 | candidate | Support for Lower House Prices | abstain | 9 | abstained | insufficient_subject_evidence |
| 2310 | candidate | Telstra Outage Halts V/Line Trains | abstain | 9 | abstained | insufficient_subject_evidence |
| 2311 | active | Bonnie Tyler Death | abstain | 24 | abstained | insufficient_subject_evidence |
| 2312 | active | Bonnie Tyler Death | abstain | 8 | abstained | insufficient_subject_evidence |
| 2313 | candidate | Bonnie Tyler Death | abstain | 8 | abstained | insufficient_subject_evidence |
| 2314 | active | Bonnie Tyler's Husband | abstain | 8 | abstained | insufficient_subject_evidence |
| 2315 | active | Romanian Companies 2025 Financial Results | abstain | 9 | abstained | insufficient_subject_evidence |
| 2316 | active | World Cup Screening Organizer Killed | abstain | 9 | abstained | ambiguous_subject_geo |
| 2317 | active | Egypt Referee Complaint | abstain | 10 | abstained | ambiguous_subject_geo |
| 2318 | active | Journalist Zainab Sodiq Detained | abstain | 12 | abstained | ambiguous_subject_geo |
| 2319 | active | Zamfara Governor Refuses Ransom | abstain | 10 | abstained | ambiguous_subject_geo |
| 2320 | active | Oyo Abduction Threats | abstain | 10 | abstained | ambiguous_subject_geo |
| 2321 | active | CBN Warns on N100 Note | abstain | 9 | abstained | ambiguous_subject_geo |
| 2322 | candidate | EFCC Arraigns Refinery Ex-MDs | abstain | 8 | abstained | ambiguous_subject_geo |
| 2323 | active | Phil Regan Fallece | abstain | 10 | abstained | ambiguous_subject_geo |
| 2324 | active | Japan Lip Sewing Arrest | abstain | 10 | abstained | ambiguous_subject_geo |
| 2325 | active | Major Cannabis Seizures | abstain | 13 | abstained | insufficient_subject_evidence |
| 2326 | active | Belgium Defeats USMNT 4-1 | US | 9 | inferred | headline_geo_consensus |
| 2327 | candidate | Jayden Adams Death | abstain | 24 | abstained | insufficient_subject_evidence |
| 2328 | active | Ekurhuleni Officials Arrested | abstain | 9 | abstained | ambiguous_subject_geo |
| 2329 | active | Jayden Adams Dies at 25 | ZA | 12 | inferred | headline_geo_consensus |
| 2330 | active | Madlanga Commission Developments | abstain | 8 | abstained | insufficient_subject_evidence |
| 2331 | active | Treasury Freezes Municipal Funds | abstain | 10 | abstained | ambiguous_subject_geo |
| 2332 | active | Albania PM Defends Kanye Concert | abstain | 10 | abstained | ambiguous_subject_geo |
| 2333 | active | England-Norway World Cup Quarterfinal | abstain | 10 | abstained | insufficient_subject_evidence |
| 2334 | candidate | Car Models in Malaysia | MY | 10 | inferred | headline_geo_consensus |
| 2335 | candidate | Managers' Transactions and Liquidity Reports | abstain | 8 | abstained | insufficient_subject_evidence |
| 2336 | candidate | All-Czech Wimbledon Final | GB | 8 | inferred | headline_geo_consensus |
| 2337 | active | Denmark Defends Greenland | US | 15 | inferred | headline_geo_consensus |
| 2338 | active | Trump Removes Syria from Terror List | abstain | 17 | abstained | ambiguous_subject_geo |
| 2339 | active | Armenian Opposition Crackdown | abstain | 9 | abstained | insufficient_subject_evidence |
| 2340 | candidate | US-Iran Military Escalation | abstain | 8 | abstained | insufficient_subject_evidence |
| 2341 | active | Katie Price's Husband Lee Andrews | abstain | 11 | abstained | ambiguous_subject_geo |
| 2342 | active | Trump Greenland Push | US | 13 | inferred | headline_geo_consensus |
| 2343 | active | Trump Covets Greenland | US | 10 | inferred | headline_geo_consensus |
| 2344 | active | Ebola Death Toll Reaches 600 | CD | 16 | inferred | headline_geo_consensus |
| 2350 | candidate | France Heatwave and Violence | abstain | 136 | abstained | ambiguous_subject_geo |
| 2352 | active | Ukraine War Escalation | abstain | 67 | abstained | ambiguous_subject_geo |
| 2363 | candidate | Emerging: Who is in the I, Jack Wright cast? Full list of actors starring in BBC murder my | abstain | 8 | junk | insufficient_subject_evidence |
| 2364 | candidate | Emerging: &#x936;&#x93F;&#x915;&#x94D;&#x937;&#x93E;&#x92E;&#x93E; &#x932;&#x917;&#x93E;&# | abstain | 17 | abstained | insufficient_subject_evidence |
| 2365 | candidate | Emerging: 김주형, 33개월 침묵 깨고 PGA 투어 스코틀랜드 오픈 우승(종합) | abstain | 14 | abstained | ambiguous_subject_geo |
| 2366 | active | Emerging: El Arco que deb&#xED;a durar unos d&#xED;as lleva m&#xE1;s de 100 a&#xF1;os en p | abstain | 28 | abstained | ambiguous_subject_geo |
| 2367 | candidate | Emerging: Drug-free Tamilnadu &#xBAE;&#xBBE;&#xBA8;&#xBBE;&#xB9F;&#xBC1;: &#xBAA;&#xBCA;&# | abstain | 13 | abstained | ambiguous_subject_geo |
| 2368 | candidate | Emerging: Man 'with stick left house linked to Widdecombe murder suspect and drove away' \| | abstain | 10 | abstained | ambiguous_subject_geo |
| 2369 | candidate | Emerging: Keystone Pipeline operator agrees to pay $26.9 million over 2022 oil spill | abstain | 18 | abstained | ambiguous_subject_geo |
| 2370 | candidate | Emerging: TFF Group (OTCMKTS:FRFTF) Short Interest Down 73.7% in June | abstain | 26 | abstained | ambiguous_subject_geo |
| 2371 | candidate | Emerging: Rs 1835 cr transferred into bank accounts of 1.25 cr Ladli Behna scheme benefici | abstain | 14 | abstained | ambiguous_subject_geo |
| 2372 | candidate | Emerging: Bull gores runner in the face at Spain's San Fermin bull run festival | abstain | 9 | abstained | insufficient_subject_evidence |
| 2373 | candidate | Emerging: New York Times reporters are subpoenaed after Air Force One reporting, newspaper | abstain | 13 | abstained | ambiguous_subject_geo |
| 2374 | candidate | Emerging: One-off Test: Yastika, bowlers put India on doorstep of historic victory over En | IN | 10 | inferred | headline_geo_consensus |
| 2375 | candidate | Emerging: Mortal remains of 15 Indian nationals who died in Vietnam boat tragedy arrive in | abstain | 13 | abstained | ambiguous_subject_geo |
| 2376 | candidate | Emerging: 24Kurier.pl - Zapisane w &#x201E;Kurierze" (31.12.1964-8.01.1965 r.) | abstain | 19 | abstained | insufficient_subject_evidence |
| 2377 | active | Emerging: &#x410;&#x440;&#x442;&#x438;&#x43B;&#x435;&#x440;&#x438;&#x441;&#x43A;&#x430; &# | abstain | 17 | abstained | insufficient_subject_evidence |
| 2378 | candidate | Emerging: Finding Closure And Connection: A Complete Guide To Seattle Times Obituaries And | abstain | 22 | abstained | insufficient_subject_evidence |
| 2379 | active | Emerging: Shooting near Toronto street festival kills 2 people and wounds 4, police say | abstain | 24 | abstained | insufficient_subject_evidence |
| 2380 | candidate | Emerging: Dermot Murnaghan remembered as 'legendary news journalist and presenter' \| Harwi | abstain | 9 | abstained | ambiguous_subject_geo |
| 2381 | candidate | Emerging: Isra&#xEB;lische verkiezingen definitief op 27 oktober | IL | 21 | inferred | headline_geo_consensus |
| 2382 | active | Emerging: Former Qatar ruler Sheikh Hamad, a moderniser who seized power, has died | QA | 36 | inferred | headline_geo_consensus |
| 2383 | candidate | Reactions to Graham's Death | abstain | 24 | abstained | ambiguous_subject_geo |
| 2384 | candidate | Death of Lindsey Graham | US | 20 | inferred | headline_geo_consensus |
| 2385 | candidate | Senator Lindsey Graham Dies | abstain | 14 | abstained | ambiguous_subject_geo |
| 2386 | candidate | Lindsey Graham Dies at 71 | abstain | 12 | abstained | insufficient_subject_evidence |
| 2387 | candidate | Racially Aggravated Assaults | abstain | 11 | abstained | insufficient_subject_evidence |
| 2388 | candidate | UK Household Waste Costs | abstain | 9 | abstained | ambiguous_subject_geo |
| 2389 | candidate | SCS Choir Reunion | abstain | 8 | abstained | insufficient_subject_evidence |
| 2390 | candidate | Death of Senator Lindsey Graham | abstain | 11 | abstained | ambiguous_subject_geo |
| 2391 | candidate | Russian Sports Achievements | RU | 11 | inferred | anchor_corroborated_subject_geo |
| 2392 | candidate | Russia Regions Without Power | abstain | 10 | abstained | ambiguous_subject_geo |
| 2393 | candidate | Iran Strikes US Bases | abstain | 10 | abstained | ambiguous_subject_geo |
| 2394 | candidate | New 2000 Hryvnia Banknote | abstain | 24 | abstained | ambiguous_subject_geo |
| 2395 | candidate | Lindsey Graham Death Reports | abstain | 20 | abstained | ambiguous_subject_geo |
| 2396 | candidate | Timnas Indonesia Piala AFF 2026 | ID | 8 | inferred | headline_geo_consensus |
| 2397 | candidate | Rafa Márquez Named Mexico Coach | MX | 13 | inferred | anchor_corroborated_subject_geo |
| 2398 | candidate | Allies Reject China Sea Claims | CN | 9 | inferred | anchor_corroborated_subject_geo |
| 2399 | candidate | Grizzly Bear Encounters | abstain | 20 | abstained | insufficient_subject_evidence |
| 2400 | candidate | P-Plater Licence Loss | abstain | 24 | abstained | insufficient_subject_evidence |
| 2401 | candidate | Government Taxes on Housing | abstain | 24 | abstained | insufficient_subject_evidence |
| 2402 | candidate | Lindsey Graham Dies at 71 | abstain | 8 | abstained | ambiguous_subject_geo |
| 2403 | candidate | Palestinian Detainee Torture Allegations | abstain | 8 | abstained | ambiguous_subject_geo |
| 2404 | candidate | New Scooter Launches | abstain | 8 | abstained | insufficient_subject_evidence |
| 2405 | candidate | Atiku Warns on Obi Safety | NG | 8 | inferred | headline_geo_consensus |
| 2406 | candidate | Bangkok Pub Fire | TH | 14 | inferred | anchor_corroborated_subject_geo |
| 2407 | candidate | Bangkok Bar Fire | abstain | 8 | abstained | insufficient_subject_evidence |
| 2408 | candidate | Cuba Power Grid Restored | CU | 8 | inferred | anchor_corroborated_subject_geo |
| 2409 | candidate | Bahrain Missile Alert Sirens | IR | 10 | inferred | headline_geo_consensus |
| 2410 | active | Major Russian Strikes on Ukraine | abstain | 35 | abstained | ambiguous_subject_geo |
| 2411 | active | US Strikes Iran Retaliation | abstain | 33 | abstained | ambiguous_subject_geo |
| 2414 | active | Suiza Elimina a Colombia | abstain | 33 | abstained | ambiguous_subject_geo |
| 2416 | active | Μουντιάλ 2026 Προκρίσεις | abstain | 24 | abstained | insufficient_subject_evidence |
| 2418 | active | Fas Hollanda'yı Eledi | abstain | 56 | abstained | ambiguous_subject_geo |
| 2421 | active | Καύσωνας και Καιρός | abstain | 23 | abstained | ambiguous_subject_geo |
| 2422 | active | Violent Crimes in Uruguay | abstain | 34 | abstained | ambiguous_subject_geo |
| 2423 | active | Weather Alerts in Brazil | abstain | 26 | abstained | ambiguous_subject_geo |
| 2425 | active | Iran vs Egypt World Cup Draw | abstain | 27 | abstained | ambiguous_subject_geo |
| 2426 | active | Canicule en Belgique | abstain | 34 | abstained | ambiguous_subject_geo |
| 2428 | active | Croacia vs Ghana Mundial 2026 | GB | 18 | inferred | headline_geo_consensus |
| 2429 | active | Senegal Political Turmoil | abstain | 48 | abstained | ambiguous_subject_geo |
| 2430 | active | DR Congo Ebola Outbreak | CD | 30 | inferred | anchor_corroborated_subject_geo |
| 2431 | active | Gaza Conflict Casualties | PS | 20 | inferred |  |
| 2432 | active | Burkina Faso News | abstain | 37 | abstained | ambiguous_subject_geo |
| 2434 | active | Ryanair Window Incident | abstain | 23 | abstained | insufficient_subject_evidence |
| 2435 | active | Bonnie Tyler Death | abstain | 36 | abstained | insufficient_subject_evidence |
