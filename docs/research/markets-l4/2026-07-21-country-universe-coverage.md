# L4 markets — all-countries instrument universe coverage (2026-07-21)

Built by `markets/build_country_universe.py`. Every symbol below returned
>=1 real close from Yahoo's public chart API; non-resolving tickers were
dropped (no fabrication). `basis='descriptive'` on every row — true by
identity, no #226 gate.

## Coverage

- Countries placed with >=1 instrument: **171** of 179 in the candidate table
- With own/shared currency: **170**
- With a country index/ETF: **43**
- With >=1 national champion: **11**
- With an export-commodity tag: **25**
- Currency-only (no index/champion): **127**
- Distinct verified symbols: **204** (from 212 candidates; 8 dropped)

## Countries WITH a country index/ETF

AE United Arab Emirates, AR Argentina, AT Austria, AU Australia, BE Belgium, BR Brazil, CA Canada, CH Switzerland, CL Chile, CN China, CO Colombia, DE Germany, DK Denmark, ES Spain, FI Finland, FR France, GB United Kingdom, GR Greece, HK Hong Kong, ID Indonesia, IE Ireland, IL Israel, IN India, IT Italy, JP Japan, KR South Korea, MX Mexico, MY Malaysia, NL Netherlands, NO Norway, NZ New Zealand, PE Peru, PH Philippines, PL Poland, QA Qatar, SA Saudi Arabia, SE Sweden, SG Singapore, TH Thailand, TR Turkey, TW Taiwan, VN Vietnam, ZA South Africa

## Currency-only countries (own/shared FX verifies, no equity vehicle)

AF Afghanistan, AL Albania, AM Armenia, AO Angola, AZ Azerbaijan, BA Bosnia and Herzegovina, BB Barbados, BD Bangladesh, BF Burkina Faso, BH Bahrain, BI Burundi, BJ Benin, BN Brunei, BO Bolivia, BS Bahamas, BW Botswana, BY Belarus, BZ Belize, CD DR Congo, CF Central African Republic, CG Republic of the Congo, CI Ivory Coast, CM Cameroon, CR Costa Rica, CU Cuba, CV Cape Verde, CY Cyprus, CZ Czechia, DJ Djibouti, DO Dominican Republic, DZ Algeria, EE Estonia, EG Egypt, ER Eritrea, ET Ethiopia, FJ Fiji, GA Gabon, GE Georgia, GH Ghana, GM Gambia, GN Guinea, GQ Equatorial Guinea, GT Guatemala, GW Guinea-Bissau, GY Guyana, HN Honduras, HR Croatia, HT Haiti, HU Hungary, IQ Iraq, IR Iran, IS Iceland, JM Jamaica, JO Jordan, KE Kenya, KH Cambodia, KM Comoros, KW Kuwait, KZ Kazakhstan, LA Laos, LB Lebanon, LK Sri Lanka, LR Liberia, LS Lesotho, LT Lithuania, LU Luxembourg, LV Latvia, LY Libya, MA Morocco, MD Moldova, ME Montenegro, MG Madagascar, MK North Macedonia, ML Mali, MM Myanmar, MN Mongolia, MO Macau, MR Mauritania, MT Malta, MU Mauritius, MV Maldives, MW Malawi, MZ Mozambique, NA Namibia, NE Niger, NG Nigeria, NI Nicaragua, NP Nepal, OM Oman, PG Papua New Guinea, PK Pakistan, PT Portugal, PY Paraguay, RO Romania, RS Serbia, RU Russia, RW Rwanda, SB Solomon Islands, SC Seychelles, SD Sudan, SI Slovenia, SK Slovakia, SL Sierra Leone, SN Senegal, SO Somalia, SR Suriname, ST Sao Tome and Principe, SY Syria, SZ Eswatini, TD Chad, TG Togo, TJ Tajikistan, TM Turkmenistan, TN Tunisia, TO Tonga, TT Trinidad and Tobago, TZ Tanzania, UA Ukraine, UG Uganda, UY Uruguay, UZ Uzbekistan, VE Venezuela, VU Vanuatu, WS Samoa, XK Kosovo, YE Yemen, ZM Zambia

## Honest gaps — countries left with NO instrument

These had no currency FX pair, ETF, or champion that resolved on Yahoo
(exotic/pegged/sanctioned currencies, no single-country ETF). Shown, not hidden.


BG Bulgaria, BT Bhutan, KG Kyrgyzstan, PA Panama, SS South Sudan, SV El Salvador, ZW Zimbabwe

## Dropped symbols (candidate did not resolve on Yahoo)

`BGN=X`, `BTN=X`, `EGPT`, `KGS=X`, `NGE`, `PAK`, `PGAL`, `SSP=X`
