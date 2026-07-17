// Round-2 item 2 (fix round 2026-07-17) — polygon-less microstates.
//
// The map basemap is Natural Earth 110m: countries below ~a few hundred km²
// simply have NO feature — Malta, Singapore, Barbados and every Caribbean /
// Pacific / Indian-Ocean microstate Atlas serves signals for. Consequences
// before this fix: the tiny-island click/hover assist had nothing to target,
// and flyCountry silently no-op'd (searching "Malta" left the camera parked
// over wherever it was — the Yemen repro).
//
// This table gives each such ISO code a representative centroid [lon, lat].
// The island assist treats each as a ZERO-SIZE bbox at its projected centroid
// (hover + click within the same ISLAND_NEAR_PX tolerance) and flyCountry
// falls back to the centroid when no polygon matches.
//
// AUDIT (2026-07-17, countries.geojson =110m, 177 features): the ISO codes in
// COUNTRY_NAMES with no usable polygon fall into two classes —
//   (a) genuine ISO microstates/territories with real signals (heat/search):
//       MT SG BB BH MV SC HK MO CV ST KM GD LC VC AG DM PW FM MH NR TV TO
//       WS CK GI FO RE PM CW AW BQ SX TC BM VI GU MP — ALL below.
//       (TT Trinidad DOES have a 110m polygon — excluded by the audit test.)
//   (b) legacy GDELT/FIPS residue with no ISO meaning (VQ EI GZ AC WB KN KS
//       CJ RQ WE YM RI RB HO PC NF AN UM SW) — handled by the ISO-first
//       boundary (lib/countryCodeBoundary), NOT here.
// TW and XK are in the geojson but under ISO_A2 'CN-TW'/'-99'; the map reads
// ISO_A2_EH for those, so they have real polygons and are NOT listed here.
export const MICRO_CENTROIDS: Record<string, [number, number]> = {
    // Mediterranean / Europe
    MT: [14.40, 35.89],   // Malta
    GI: [-5.35, 36.14],   // Gibraltar
    FO: [-6.91, 61.89],   // Faroe Islands
    // Gulf / Indian Ocean
    BH: [50.55, 26.03],   // Bahrain
    MV: [73.40, 3.20],    // Maldives
    SC: [55.45, -4.68],   // Seychelles
    KM: [43.35, -11.65],  // Comoros
    RE: [55.54, -21.13],  // Réunion
    // East / Southeast Asia
    SG: [103.82, 1.35],   // Singapore
    HK: [114.17, 22.30],  // Hong Kong
    MO: [113.55, 22.19],  // Macau
    // Atlantic / Africa
    CV: [-23.63, 15.09],  // Cape Verde
    ST: [6.61, 0.22],     // São Tomé
    BM: [-64.75, 32.31],  // Bermuda
    // Caribbean
    BB: [-59.56, 13.19],  // Barbados
    GD: [-61.68, 12.11],  // Grenada
    LC: [-60.97, 13.90],  // Saint Lucia
    VC: [-61.19, 13.26],  // St. Vincent
    AG: [-61.80, 17.07],  // Antigua
    DM: [-61.35, 15.42],  // Dominica
    CW: [-68.97, 12.20],  // Curaçao
    AW: [-69.97, 12.52],  // Aruba
    BQ: [-68.26, 12.18],  // Bonaire
    SX: [-63.06, 18.04],  // Sint Maarten
    TC: [-71.80, 21.75],  // Turks & Caicos
    VI: [-64.90, 18.34],  // Virgin Islands
    PM: [-56.33, 46.89],  // St. Pierre
    // Pacific
    PW: [134.58, 7.50],   // Palau
    FM: [158.25, 6.92],   // Micronesia
    MH: [171.18, 7.13],   // Marshall Islands
    NR: [166.93, -0.52],  // Nauru
    TV: [179.20, -8.52],  // Tuvalu
    TO: [-175.20, -21.18],// Tonga
    WS: [-172.10, -13.76],// Samoa
    CK: [-159.78, -21.23],// Cook Islands
    GU: [144.77, 13.45],  // Guam
    MP: [145.75, 15.18],  // N. Mariana Is.
}
