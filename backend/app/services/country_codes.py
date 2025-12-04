"""
FIPS 10-4 to ISO 3166-1 alpha-2 country code conversion.
GDELT uses FIPS codes, but maps/APIs expect ISO codes.

Critical conversions:
- UK → GB (United Kingdom)
- GM → DE (Germany)
- RS → RU (Russia)
- CH → CN (China) ⚠️ CH is Switzerland in ISO!
- SZ → CH (Switzerland)
"""

FIPS_TO_ISO = {
    # Major differences (most common)
    'UK': 'GB',  # United Kingdom
    'GM': 'DE',  # Germany
    'RS': 'RU',  # Russia
    'CH': 'CN',  # China (CRITICAL - CH is Switzerland in ISO!)
    'SZ': 'CH',  # Switzerland
    'JA': 'JP',  # Japan
    'EI': 'IE',  # Ireland
    'SP': 'ES',  # Spain
    'SF': 'ZA',  # South Africa
    'NI': 'NG',  # Nigeria (FIPS NI = Nigeria, ISO NI = Nicaragua)
    'UP': 'UA',  # Ukraine
    'KS': 'KR',  # South Korea
    'KN': 'KP',  # North Korea
    'AS': 'AU',  # Australia
    'PO': 'PL',  # Poland
    'TU': 'TR',  # Turkey
    'IS': 'IL',  # Israel
    'IZ': 'IQ',  # Iraq
    'SW': 'SE',  # Sweden
    'DA': 'DK',  # Denmark
    'AU': 'AT',  # Austria (FIPS AU = Austria, ISO AU = Australia!)
    'BU': 'BG',  # Bulgaria
    'LO': 'SK',  # Slovakia
    'EZ': 'CZ',  # Czech Republic
    'EN': 'EE',  # Estonia
    'LG': 'LV',  # Latvia
    'LH': 'LT',  # Lithuania
    'BO': 'BY',  # Belarus
    'SN': 'SG',  # Singapore
    'VM': 'VN',  # Vietnam
    'CB': 'KH',  # Cambodia
    'BM': 'MM',  # Myanmar/Burma
    'CE': 'LK',  # Sri Lanka
    'BG': 'BD',  # Bangladesh
    'CI': 'CL',  # Chile
    'BL': 'BO',  # Bolivia
    'NU': 'NI',  # Nicaragua
    'HO': 'HN',  # Honduras
    'ES': 'SV',  # El Salvador
    'DR': 'DO',  # Dominican Republic
    'HA': 'HT',  # Haiti
    'MO': 'MA',  # Morocco
    'AG': 'DZ',  # Algeria
    'TS': 'TN',  # Tunisia
    'SU': 'SD',  # Sudan
    'CG': 'CD',  # DRC (Congo Kinshasa)
    'CF': 'CG',  # Congo Brazzaville
    'ZI': 'ZW',  # Zimbabwe
    'WA': 'NA',  # Namibia
    'BC': 'BW',  # Botswana
    'MI': 'MW',  # Malawi
    'IV': 'CI',  # Ivory Coast
    'NG': 'NE',  # Niger
    'UV': 'BF',  # Burkina Faso
    'TO': 'TG',  # Togo
    'BN': 'BJ',  # Benin
    'CT': 'CF',  # Central African Republic
    'CD': 'TD',  # Chad
    'WZ': 'SZ',  # Eswatini/Swaziland
    'LE': 'LS',  # Lesotho
    'BY': 'BI',  # Burundi
    'SE': 'SC',  # Seychelles
    'MP': 'MU',  # Mauritius
    'PU': 'GW',  # Guinea-Bissau
    'GV': 'GN',  # Guinea
    'LI': 'LR',  # Liberia
    
    # Same in both FIPS and ISO (for completeness)
    'US': 'US',  # United States
    'CA': 'CA',  # Canada
    'MX': 'MX',  # Mexico
    'BR': 'BR',  # Brazil
    'AR': 'AR',  # Argentina
    'CO': 'CO',  # Colombia
    'VE': 'VE',  # Venezuela
    'PE': 'PE',  # Peru
    'EC': 'EC',  # Ecuador
    'PA': 'PA',  # Panama
    'GT': 'GT',  # Guatemala
    'CU': 'CU',  # Cuba
    'JM': 'JM',  # Jamaica
    'FR': 'FR',  # France
    'IT': 'IT',  # Italy
    'NL': 'NL',  # Netherlands
    'BE': 'BE',  # Belgium
    'NO': 'NO',  # Norway
    'FI': 'FI',  # Finland
    'GR': 'GR',  # Greece
    'RO': 'RO',  # Romania
    'HU': 'HU',  # Hungary
    'MD': 'MD',  # Moldova
    'NZ': 'NZ',  # New Zealand
    'MY': 'MY',  # Malaysia
    'ID': 'ID',  # Indonesia
    'TH': 'TH',  # Thailand
    'PK': 'PK',  # Pakistan
    'IN': 'IN',  # India
    'TW': 'TW',  # Taiwan
    'SY': 'SY',  # Syria
    'IR': 'IR',  # Iran
    'AF': 'AF',  # Afghanistan
    'EG': 'EG',  # Egypt
    'SA': 'SA',  # Saudi Arabia
    'AE': 'AE',  # UAE
    'NP': 'NP',  # Nepal
    'LY': 'LY',  # Libya
    'ET': 'ET',  # Ethiopia
    'KE': 'KE',  # Kenya
    'TZ': 'TZ',  # Tanzania
    'UG': 'UG',  # Uganda
    'AO': 'AO',  # Angola
    'ZA': 'ZA',  # South Africa (also SF in FIPS)
    'MZ': 'MZ',  # Mozambique
    'ZM': 'ZM',  # Zambia
    'SL': 'SL',  # Sierra Leone
    'GH': 'GH',  # Ghana
    'ML': 'ML',  # Mali
    'CM': 'CM',  # Cameroon
    'GA': 'GA',  # Gabon
    'SO': 'SO',  # Somalia
    'DJ': 'DJ',  # Djibouti
    'ER': 'ER',  # Eritrea
    'RW': 'RW',  # Rwanda
    'MR': 'MR',  # Mauritania
}


def fips_to_iso(fips_code: str) -> str:
    """
    Convert FIPS 10-4 code to ISO 3166-1 alpha-2.
    
    Args:
        fips_code: FIPS 10-4 country code (e.g., 'UK', 'GM', 'CH')
        
    Returns:
        ISO 3166-1 alpha-2 code (e.g., 'GB', 'DE', 'CN')
        Returns input if no mapping found (assumed same in both standards)
    """
    if not fips_code:
        return None
    
    code = fips_code.upper().strip()[:2]
    return FIPS_TO_ISO.get(code, code)
