"""
FIPS 10-4 (GEC) -> ISO 3166-1 alpha-2 country code conversion.

GDELT geocodes with FIPS 10-4 codes; every Atlas surface (maps, briefs, APIs,
country filters) speaks ISO 3166-1 alpha-2. This module is the only bridge.

WHY THIS IS DANGEROUS TO GET WRONG
----------------------------------
The two standards reuse the same two letters for DIFFERENT countries, so a
missing or wrong entry does not fail loudly -- it silently files one country's
news under another. Measured examples of exactly that, all fixed 2026-07-28:

    FIPS LE = Lebanon    was mapped to ISO LS -> rendered as Lesotho
    FIPS PO = Portugal   was mapped to ISO PL -> merged into Poland
    FIPS PA = Paraguay   was mapped to ISO PA -> rendered as Panama
    FIPS ZA = Zambia     was mapped to ISO ZA -> merged into South Africa
    FIPS GA = Gambia     was mapped to ISO GA -> rendered as Gabon

CONTRACT
--------
fips_to_iso() input MUST be a FIPS 10-4 code, never an ISO code. Feeding an ISO
code in returns a confidently wrong country -- ISO 'GB' maps to 'GA', so the
United Kingdom would become Gabon. A caller holding a possibly-ISO value must
test membership in ISO_COUNTRY_NAMES first, as daily_publication.py does.

INVARIANT (what makes the passthrough in fips_to_iso safe)
----------------------------------------------------------
Unmapped codes pass through unchanged. That is only correct because EVERY FIPS
code whose meaning differs from the identically-spelled ISO code is present in
FIPS_TO_ISO below. When adding a country, check BOTH directions: what does this
FIPS code mean, and what does that same string mean in ISO?

Source: FIPS 10-4 / NGA "Geopolitical Entities and Codes" (GEC), cross-checked
against the Wikipedia FIPS 10-4 country-code list.
"""

FIPS_TO_ISO = {
    # ------------------------------------------------------------------
    # DIVERGENT: the FIPS code differs from the ISO code for that country.
    # A [WARNING] note means the FIPS key is ALSO a valid ISO code for a
    # DIFFERENT country. Those are the entries that silently corrupt data if
    # they go missing, because they pass through looking perfectly plausible.
    # ------------------------------------------------------------------
    'AA': 'AW',       # Aruba
    'AC': 'AG',       # Antigua and Barbuda
    'AG': 'DZ',       # Algeria  [WARNING ISO AG = Antigua and Barbuda]
    'AJ': 'AZ',       # Azerbaijan
    'AN': 'AD',       # Andorra
    'AQ': 'AS',       # American Samoa  [WARNING ISO AQ = Antarctica]
    'AS': 'AU',       # Australia  [WARNING ISO AS = American Samoa]
    'AT': 'AU',       # Ashmore and Cartier Islands  [WARNING ISO AT = Austria]
    'AU': 'AT',       # Austria  [WARNING ISO AU = Ashmore and Cartier Islands]
    'AV': 'AI',       # Anguilla
    'AY': 'AQ',       # Antarctica
    'BA': 'BH',       # Bahrain  [WARNING ISO BA = Bosnia and Herzegovina]
    'BC': 'BW',       # Botswana
    'BD': 'BM',       # Bermuda  [WARNING ISO BD = Bangladesh]
    'BF': 'BS',       # Bahamas, The  [WARNING ISO BF = Burkina Faso]
    'BG': 'BD',       # Bangladesh  [WARNING ISO BG = Bulgaria]
    'BH': 'BZ',       # Belize  [WARNING ISO BH = Bahrain]
    'BK': 'BA',       # Bosnia and Herzegovina
    'BL': 'BO',       # Bolivia  [WARNING ISO BL = Saint Barthelemy]
    'BM': 'MM',       # Myanmar  [WARNING ISO BM = Bermuda]
    'BN': 'BJ',       # Benin  [WARNING ISO BN = Brunei]
    'BO': 'BY',       # Belarus  [WARNING ISO BO = Bolivia]
    'BP': 'SB',       # Solomon Islands
    'BQ': 'UM',       # Navassa Island
    'BS': 'RE',       # Bassas da India  [WARNING ISO BS = Bahamas, The]
    'BU': 'BG',       # Bulgaria
    'BX': 'BN',       # Brunei
    'BY': 'BI',       # Burundi  [WARNING ISO BY = Belarus]
    'CB': 'KH',       # Cambodia
    'CD': 'TD',       # Chad  [WARNING ISO CD = Congo, Democratic Republic of the]
    'CE': 'LK',       # Sri Lanka
    'CF': 'CG',       # Congo, Republic of the  [WARNING ISO CF = Central African Republic]
    'CG': 'CD',       # Congo, Democratic Republic of the  [WARNING ISO CG = Congo, Republic of the]
    'CH': 'CN',       # China  [WARNING ISO CH = Switzerland]
    'CI': 'CL',       # Chile  [WARNING ISO CI = Cote d'Ivoire]
    'CJ': 'KY',       # Cayman Islands
    'CK': 'CC',       # Cocos (Keeling) Islands  [WARNING ISO CK = Cook Islands]
    'CN': 'KM',       # Comoros  [WARNING ISO CN = China]
    'CQ': 'MP',       # Northern Mariana Islands
    'CR': 'AU',       # Coral Sea Islands  [WARNING ISO CR = Costa Rica]
    'CS': 'CR',       # Costa Rica
    'CT': 'CF',       # Central African Republic
    'CW': 'CK',       # Cook Islands  [WARNING ISO CW = Curacao]
    'DA': 'DK',       # Denmark
    'DO': 'DM',       # Dominica  [WARNING ISO DO = Dominican Republic]
    'DQ': 'UM',       # Jarvis Island
    'DR': 'DO',       # Dominican Republic
    'EI': 'IE',       # Ireland
    'EK': 'GQ',       # Equatorial Guinea
    'EN': 'EE',       # Estonia
    'ES': 'SV',       # El Salvador  [WARNING ISO ES = Spain]
    'EU': 'RE',       # Europa Island
    'EZ': 'CZ',       # Czech Republic
    'FG': 'GF',       # French Guiana
    'FP': 'PF',       # French Polynesia
    'FQ': 'UM',       # Baker Island
    'FS': 'TF',       # French Southern and Antarctic Lands
    'GA': 'GM',       # Gambia, The  [WARNING ISO GA = Gabon]
    'GB': 'GA',       # Gabon  [WARNING ISO GB = United Kingdom]
    'GG': 'GE',       # Georgia  [WARNING ISO GG = Guernsey]
    'GJ': 'GD',       # Grenada
    'GK': 'GG',       # Guernsey
    'GM': 'DE',       # Germany  [WARNING ISO GM = Gambia, The]
    'GO': 'RE',       # Glorioso Islands
    'GQ': 'GU',       # Guam  [WARNING ISO GQ = Equatorial Guinea]
    'GV': 'GN',       # Guinea
    'GZ': 'PS',       # Gaza Strip
    'HA': 'HT',       # Haiti
    'HO': 'HN',       # Honduras
    'HQ': 'UM',       # Howland Island
    'IC': 'IS',       # Iceland
    'IP': 'PF',       # Clipperton Island
    'IS': 'IL',       # Israel  [WARNING ISO IS = Iceland]
    'IV': 'CI',       # Cote d'Ivoire
    'IZ': 'IQ',       # Iraq
    'JA': 'JP',       # Japan
    'JN': 'SJ',       # Jan Mayen
    'JQ': 'UM',       # Johnston Atoll
    'JU': 'RE',       # Juan de Nova Island
    'KN': 'KP',       # Korea, North  [WARNING ISO KN = Saint Kitts and Nevis]
    'KQ': 'UM',       # Kingman Reef
    'KR': 'KI',       # Kiribati  [WARNING ISO KR = Korea, South]
    'KS': 'KR',       # Korea, South
    'KT': 'CX',       # Christmas Island
    'KU': 'KW',       # Kuwait
    'KV': 'XK',       # Kosovo (ISO user-assigned XK)
    'LE': 'LB',       # Lebanon
    'LG': 'LV',       # Latvia
    'LH': 'LT',       # Lithuania
    'LI': 'LR',       # Liberia  [WARNING ISO LI = Liechtenstein]
    'LO': 'SK',       # Slovakia
    'LQ': 'UM',       # Palmyra Atoll
    'LS': 'LI',       # Liechtenstein  [WARNING ISO LS = Lesotho]
    'LT': 'LS',       # Lesotho  [WARNING ISO LT = Lithuania]
    'MA': 'MG',       # Madagascar  [WARNING ISO MA = Morocco]
    'MB': 'MQ',       # Martinique
    'MC': 'MO',       # Macau  [WARNING ISO MC = Monaco]
    'MF': 'YT',       # Mayotte  [WARNING ISO MF = Saint Martin]
    'MG': 'MN',       # Mongolia  [WARNING ISO MG = Madagascar]
    'MH': 'MS',       # Montserrat  [WARNING ISO MH = Marshall Islands]
    'MI': 'MW',       # Malawi
    'MJ': 'ME',       # Montenegro
    'MN': 'MC',       # Monaco  [WARNING ISO MN = Mongolia]
    'MO': 'MA',       # Morocco  [WARNING ISO MO = Macau]
    'MP': 'MU',       # Mauritius  [WARNING ISO MP = Northern Mariana Islands]
    'MQ': 'UM',       # Midway Islands  [WARNING ISO MQ = Martinique]
    'MU': 'OM',       # Oman  [WARNING ISO MU = Mauritius]
    'NE': 'NU',       # Niue  [WARNING ISO NE = Niger]
    'NG': 'NE',       # Niger  [WARNING ISO NG = Nigeria]
    'NH': 'VU',       # Vanuatu
    'NI': 'NG',       # Nigeria  [WARNING ISO NI = Nicaragua]
    'NN': 'SX',       # Sint Maarten
    'NS': 'SR',       # Suriname
    'NU': 'NI',       # Nicaragua  [WARNING ISO NU = Niue]
    'OD': 'SS',       # South Sudan
    'PA': 'PY',       # Paraguay  [WARNING ISO PA = Panama]
    'PC': 'PN',       # Pitcairn Islands
    'PM': 'PA',       # Panama  [WARNING ISO PM = Saint Pierre and Miquelon]
    'PO': 'PT',       # Portugal
    'PP': 'PG',       # Papua New Guinea
    'PS': 'PW',       # Palau  [WARNING ISO PS = Gaza Strip]
    'PU': 'GW',       # Guinea-Bissau
    'RB': 'RS',       # Serbia (pre-2008 GEC code, still emitted by GDELT)
    'RI': 'RS',       # Serbia
    'RM': 'MH',       # Marshall Islands
    'RN': 'MF',       # Saint Martin
    'RP': 'PH',       # Philippines
    'RQ': 'PR',       # Puerto Rico
    'RS': 'RU',       # Russia  [WARNING ISO RS = Serbia]
    'SB': 'PM',       # Saint Pierre and Miquelon  [WARNING ISO SB = Solomon Islands]
    'SC': 'KN',       # Saint Kitts and Nevis  [WARNING ISO SC = Seychelles]
    'SE': 'SC',       # Seychelles  [WARNING ISO SE = Sweden]
    'SF': 'ZA',       # South Africa
    'SG': 'SN',       # Senegal  [WARNING ISO SG = Singapore]
    'SN': 'SG',       # Singapore  [WARNING ISO SN = Senegal]
    'SP': 'ES',       # Spain
    'ST': 'LC',       # Saint Lucia  [WARNING ISO ST = Sao Tome and Principe]
    'SU': 'SD',       # Sudan
    'SV': 'SJ',       # Svalbard  [WARNING ISO SV = El Salvador]
    'SW': 'SE',       # Sweden
    'SX': 'GS',       # South Georgia and the Islands  [WARNING ISO SX = Sint Maarten]
    'SZ': 'CH',       # Switzerland  [WARNING ISO SZ = Swaziland]
    'TB': 'BL',       # Saint Barthelemy
    'TD': 'TT',       # Trinidad and Tobago  [WARNING ISO TD = Chad]
    'TI': 'TJ',       # Tajikistan
    'TK': 'TC',       # Turks and Caicos Islands  [WARNING ISO TK = Tokelau]
    'TL': 'TK',       # Tokelau  [WARNING ISO TL = Timor-Leste]
    'TN': 'TO',       # Tonga  [WARNING ISO TN = Tunisia]
    'TO': 'TG',       # Togo  [WARNING ISO TO = Tonga]
    'TP': 'ST',       # Sao Tome and Principe
    'TS': 'TN',       # Tunisia
    'TT': 'TL',       # Timor-Leste  [WARNING ISO TT = Trinidad and Tobago]
    'TU': 'TR',       # Turkey
    'TX': 'TM',       # Turkmenistan
    'UC': 'CW',       # Curacao
    'UK': 'GB',       # United Kingdom
    'UP': 'UA',       # Ukraine
    'UV': 'BF',       # Burkina Faso
    'VI': 'VG',       # Virgin Islands, British  [WARNING ISO VI = Virgin Islands, U.S.]
    'VM': 'VN',       # Vietnam
    'VQ': 'VI',       # Virgin Islands, U.S.
    'VT': 'VA',       # Vatican City
    'WA': 'NA',       # Namibia
    'WE': 'PS',       # West Bank
    'WI': 'EH',       # Western Sahara
    'WQ': 'UM',       # Wake Island
    'WZ': 'SZ',       # Swaziland
    'YM': 'YE',       # Yemen
    'ZA': 'ZM',       # Zambia  [WARNING ISO ZA = South Africa]
    'ZI': 'ZW',       # Zimbabwe

    # ------------------------------------------------------------------
    # IDENTICAL in FIPS and ISO. Documentation only -- the passthrough in
    # fips_to_iso() would handle these anyway.
    # ------------------------------------------------------------------
    'AE': 'AE',       # United Arab Emirates
    'AF': 'AF',       # Afghanistan
    'AO': 'AO',       # Angola
    'AR': 'AR',       # Argentina
    'BE': 'BE',       # Belgium
    'BR': 'BR',       # Brazil
    'CA': 'CA',       # Canada
    'CM': 'CM',       # Cameroon
    'CO': 'CO',       # Colombia
    'CU': 'CU',       # Cuba
    'DJ': 'DJ',       # Djibouti
    'EC': 'EC',       # Ecuador
    'EG': 'EG',       # Egypt
    'ER': 'ER',       # Eritrea
    'ET': 'ET',       # Ethiopia
    'FI': 'FI',       # Finland
    'FR': 'FR',       # France
    'GH': 'GH',       # Ghana
    'GR': 'GR',       # Greece
    'GT': 'GT',       # Guatemala
    'HU': 'HU',       # Hungary
    'ID': 'ID',       # Indonesia
    'IN': 'IN',       # India
    'IR': 'IR',       # Iran
    'IT': 'IT',       # Italy
    'JM': 'JM',       # Jamaica
    'KE': 'KE',       # Kenya
    'LY': 'LY',       # Libya
    'MD': 'MD',       # Moldova
    'ML': 'ML',       # Mali
    'MR': 'MR',       # Mauritania
    'MX': 'MX',       # Mexico
    'MY': 'MY',       # Malaysia
    'MZ': 'MZ',       # Mozambique
    'NL': 'NL',       # Netherlands
    'NO': 'NO',       # Norway
    'NP': 'NP',       # Nepal
    'NZ': 'NZ',       # New Zealand
    'PE': 'PE',       # Peru
    'PK': 'PK',       # Pakistan
    'RO': 'RO',       # Romania
    'RW': 'RW',       # Rwanda
    'SA': 'SA',       # Saudi Arabia
    'SL': 'SL',       # Sierra Leone
    'SO': 'SO',       # Somalia
    'SY': 'SY',       # Syria
    'TH': 'TH',       # Thailand
    'TW': 'TW',       # Taiwan
    'TZ': 'TZ',       # Tanzania
    'UG': 'UG',       # Uganda
    'US': 'US',       # United States
    'VE': 'VE',       # Venezuela
}


# FIPS codes for territories with NO ISO 3166-1 equivalent (disputed or
# uninhabited). They are deliberately NOT in the map above, so they currently
# pass through unchanged -- which for PF and PG lands on a real but WRONG
# country. Making fips_to_iso() return None for these changes the function's
# return contract, so it is left as a separate, caller-audited change.
FIPS_NO_ISO = frozenset({
    'AX',  # Akrotiri (UK sovereign base area)
    'DX',  # Dhekelia (UK sovereign base area)
    'PF',  # Paracel Islands   [WARNING ISO PF = French Polynesia]
    'PG',  # Spratly Islands   [WARNING ISO PG = Papua New Guinea]
    'PJ',  # Etorofu/Habomai/Kunashiri/Shikotan (disputed Kuril Islands)
    'TE',  # Tromelin Island
})


def fips_to_iso(fips_code: str) -> str:
    """
    Convert a FIPS 10-4 code to ISO 3166-1 alpha-2.

    Args:
        fips_code: FIPS 10-4 country code (e.g. 'UK', 'GM', 'CH').
                   MUST be FIPS, not ISO -- see the module CONTRACT note.

    Returns:
        ISO 3166-1 alpha-2 code (e.g. 'GB', 'DE', 'CN').

        An unrecognised code is returned unchanged, on the assumption that it
        means the same thing in both standards. That assumption holds only
        while the module INVARIANT holds: every divergent FIPS code is in
        FIPS_TO_ISO. Do not rely on the passthrough for a new country -- add
        it to the map.
    """
    if not fips_code:
        return None

    code = fips_code.upper().strip()[:2]
    return FIPS_TO_ISO.get(code, code)
