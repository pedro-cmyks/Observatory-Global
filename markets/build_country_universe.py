#!/usr/bin/env python3
"""L4 markets — build the ALL-COUNTRIES descriptive instrument universe (VERIFIED).

Pedro: "todos los países, me interesa el mundo." This script holds a candidate
country -> instruments table (currency / index-ETF / champion / export-commodity,
per the design doc §5), VERIFIES every ticker against Yahoo's public chart API,
and emits the verified universe as:

  A. backend/migrations/089_markets_country_universe_all.sql  (mirrors 088's format)
  B. markets/country_universe_verified.json                   (the verified dict)
  C. a coverage report printed to stdout + written under docs/research/markets-l4/

HARD RULE — NO FABRICATION: a symbol is kept ONLY if Yahoo returns >=1 real close.
Anything that 404s / returns empty is dropped and reported as an honest gap. This
mirrors the whole project's evidence-gated principle: a ticker that does not
resolve is never seeded.

Separate-consumer rule (design §6): hits Yahoo's public chart API ONLY; writes
files, never Atlas's DB (the migration is EMITTED for the main thread to review +
apply). Stdlib-only, idempotent (verification results cache to a sidecar json so
re-runs resume / go fast).

Usage:
  python3 markets/build_country_universe.py [--sleep 0.7] [--no-network]
                                            [--refresh] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MIGRATION_OUT = REPO / "backend" / "migrations" / "089_markets_country_universe_all.sql"
JSON_OUT = REPO / "markets" / "country_universe_verified.json"
REPORT_OUT = REPO / "docs" / "research" / "markets-l4" / "2026-07-21-country-universe-coverage.md"
CACHE = REPO / "markets" / ".yahoo_verify_cache.json"

# ── country -> ISO-3166 name (alpha-2) — only countries we place instruments for ──
COUNTRY_NAME: dict[str, str] = {
    # Americas
    "US": "United States", "CA": "Canada", "MX": "Mexico", "BR": "Brazil",
    "AR": "Argentina", "CL": "Chile", "CO": "Colombia", "PE": "Peru",
    "VE": "Venezuela", "UY": "Uruguay", "PY": "Paraguay", "BO": "Bolivia",
    "EC": "Ecuador", "GT": "Guatemala", "HN": "Honduras", "NI": "Nicaragua",
    "CR": "Costa Rica", "PA": "Panama", "SV": "El Salvador", "DO": "Dominican Republic",
    "CU": "Cuba", "JM": "Jamaica", "TT": "Trinidad and Tobago", "HT": "Haiti",
    "GY": "Guyana", "SR": "Suriname", "BS": "Bahamas", "BB": "Barbados", "BZ": "Belize",
    # Europe
    "GB": "United Kingdom", "IE": "Ireland", "FR": "France", "DE": "Germany",
    "IT": "Italy", "ES": "Spain", "PT": "Portugal", "NL": "Netherlands",
    "BE": "Belgium", "LU": "Luxembourg", "CH": "Switzerland", "AT": "Austria",
    "SE": "Sweden", "NO": "Norway", "DK": "Denmark", "FI": "Finland",
    "IS": "Iceland", "PL": "Poland", "CZ": "Czechia", "HU": "Hungary",
    "RO": "Romania", "BG": "Bulgaria", "GR": "Greece", "HR": "Croatia",
    "SI": "Slovenia", "SK": "Slovakia", "EE": "Estonia", "LV": "Latvia",
    "LT": "Lithuania", "CY": "Cyprus", "MT": "Malta", "RS": "Serbia",
    "UA": "Ukraine", "BY": "Belarus", "MD": "Moldova", "AL": "Albania",
    "MK": "North Macedonia", "BA": "Bosnia and Herzegovina", "ME": "Montenegro",
    "XK": "Kosovo", "GE": "Georgia", "AM": "Armenia", "AZ": "Azerbaijan",
    "RU": "Russia",
    # Middle East
    "TR": "Turkey", "SA": "Saudi Arabia", "AE": "United Arab Emirates",
    "QA": "Qatar", "KW": "Kuwait", "BH": "Bahrain", "OM": "Oman",
    "IL": "Israel", "JO": "Jordan", "LB": "Lebanon", "IQ": "Iraq",
    "IR": "Iran", "SY": "Syria", "YE": "Yemen",
    # Asia
    "CN": "China", "JP": "Japan", "KR": "South Korea", "IN": "India",
    "ID": "Indonesia", "MY": "Malaysia", "TH": "Thailand", "PH": "Philippines",
    "VN": "Vietnam", "SG": "Singapore", "HK": "Hong Kong", "TW": "Taiwan",
    "PK": "Pakistan", "BD": "Bangladesh", "LK": "Sri Lanka", "NP": "Nepal",
    "MM": "Myanmar", "KH": "Cambodia", "LA": "Laos", "MN": "Mongolia",
    "KZ": "Kazakhstan", "UZ": "Uzbekistan", "TM": "Turkmenistan", "KG": "Kyrgyzstan",
    "TJ": "Tajikistan", "AF": "Afghanistan", "BN": "Brunei", "MO": "Macau",
    "MV": "Maldives", "BT": "Bhutan",
    # Africa
    "EG": "Egypt", "NG": "Nigeria", "ZA": "South Africa", "KE": "Kenya",
    "GH": "Ghana", "MA": "Morocco", "DZ": "Algeria", "TN": "Tunisia",
    "LY": "Libya", "ET": "Ethiopia", "TZ": "Tanzania", "UG": "Uganda",
    "RW": "Rwanda", "ZM": "Zambia", "ZW": "Zimbabwe", "AO": "Angola",
    "MZ": "Mozambique", "BW": "Botswana", "NA": "Namibia", "MU": "Mauritius",
    "SN": "Senegal", "CI": "Ivory Coast", "ML": "Mali", "BF": "Burkina Faso",
    "NE": "Niger", "BJ": "Benin", "TG": "Togo", "GW": "Guinea-Bissau",
    "CM": "Cameroon", "GA": "Gabon", "CG": "Republic of the Congo", "TD": "Chad",
    "CF": "Central African Republic", "GQ": "Equatorial Guinea", "CD": "DR Congo",
    "SD": "Sudan", "SS": "South Sudan", "SO": "Somalia", "MG": "Madagascar",
    "MW": "Malawi", "SL": "Sierra Leone", "LR": "Liberia", "GM": "Gambia",
    "GN": "Guinea", "MR": "Mauritania", "SC": "Seychelles", "CV": "Cape Verde",
    "SZ": "Eswatini", "LS": "Lesotho", "BI": "Burundi", "ER": "Eritrea",
    "DJ": "Djibouti", "KM": "Comoros", "ST": "Sao Tome and Principe",
    # Oceania
    "AU": "Australia", "NZ": "New Zealand", "FJ": "Fiji", "PG": "Papua New Guinea",
    "SB": "Solomon Islands", "VU": "Vanuatu", "WS": "Samoa", "TO": "Tonga",
}

# ── currency: country -> ISO-4217 code. None = dollarized / no own currency ──
# "EUR" = eurozone member (represented once as EUR=X). US has no self FX pair.
EUROZONE = {
    "AT", "BE", "CY", "EE", "FI", "FR", "DE", "GR", "IE", "IT", "LV", "LT",
    "LU", "MT", "NL", "PT", "SK", "SI", "ES", "HR", "ME", "XK",  # ME/XK use EUR unilaterally
}
NO_OWN_CURRENCY = {  # dollarized / multi-currency — no own FX pair to show (design §5)
    "US": "issuer of USD (shown via ^GSPC/^DJI, no self FX pair)",
    "EC": "fully dollarized (USD)",
    "SV": "fully dollarized (USD)",
    "PA": "USD circulates; balboa pegged 1:1",
    "ZW": "multi-currency (USD-dominant)",
}
COUNTRY_CCY: dict[str, str] = {
    "CA": "CAD", "MX": "MXN", "BR": "BRL", "AR": "ARS", "CL": "CLP", "CO": "COP",
    "PE": "PEN", "VE": "VES", "UY": "UYU", "PY": "PYG", "BO": "BOB", "GT": "GTQ",
    "HN": "HNL", "NI": "NIO", "CR": "CRC", "DO": "DOP", "CU": "CUP", "JM": "JMD",
    "TT": "TTD", "HT": "HTG", "GY": "GYD", "SR": "SRD", "BS": "BSD", "BB": "BBD",
    "BZ": "BZD",
    "GB": "GBP", "CH": "CHF", "SE": "SEK", "NO": "NOK", "DK": "DKK", "IS": "ISK",
    "PL": "PLN", "CZ": "CZK", "HU": "HUF", "RO": "RON", "BG": "BGN", "RS": "RSD",
    "UA": "UAH", "BY": "BYN", "MD": "MDL", "AL": "ALL", "MK": "MKD", "BA": "BAM",
    "GE": "GEL", "AM": "AMD", "AZ": "AZN", "RU": "RUB",
    "TR": "TRY", "SA": "SAR", "AE": "AED", "QA": "QAR", "KW": "KWD", "BH": "BHD",
    "OM": "OMR", "IL": "ILS", "JO": "JOD", "LB": "LBP", "IQ": "IQD", "IR": "IRR",
    "SY": "SYP", "YE": "YER",
    "CN": "CNY", "JP": "JPY", "KR": "KRW", "IN": "INR", "ID": "IDR", "MY": "MYR",
    "TH": "THB", "PH": "PHP", "VN": "VND", "SG": "SGD", "HK": "HKD", "TW": "TWD",
    "PK": "PKR", "BD": "BDT", "LK": "LKR", "NP": "NPR", "MM": "MMK", "KH": "KHR",
    "LA": "LAK", "MN": "MNT", "KZ": "KZT", "UZ": "UZS", "TM": "TMT", "KG": "KGS",
    "TJ": "TJS", "AF": "AFN", "BN": "BND", "MO": "MOP", "MV": "MVR", "BT": "BTN",
    "EG": "EGP", "NG": "NGN", "ZA": "ZAR", "KE": "KES", "GH": "GHS", "MA": "MAD",
    "DZ": "DZD", "TN": "TND", "LY": "LYD", "ET": "ETB", "TZ": "TZS", "UG": "UGX",
    "RW": "RWF", "ZM": "ZMW", "AO": "AOA", "MZ": "MZN", "BW": "BWP", "NA": "NAD",
    "MU": "MUR", "SN": "XOF", "CI": "XOF", "ML": "XOF", "BF": "XOF", "NE": "XOF",
    "BJ": "XOF", "TG": "XOF", "GW": "XOF", "CM": "XAF", "GA": "XAF", "CG": "XAF",
    "TD": "XAF", "CF": "XAF", "GQ": "XAF", "CD": "CDF", "SD": "SDG", "SS": "SSP",
    "SO": "SOS", "MG": "MGA", "MW": "MWK", "SL": "SLE", "LR": "LRD", "GM": "GMD",
    "GN": "GNF", "MR": "MRU", "SC": "SCR", "CV": "CVE", "SZ": "SZL", "LS": "LSL",
    "BI": "BIF", "ER": "ERN", "DJ": "DJF", "KM": "KMF", "ST": "STN",
    "AU": "AUD", "NZ": "NZD", "FJ": "FJD", "PG": "PGK", "SB": "SBD", "VU": "VUV",
    "WS": "WST", "TO": "TOP",
}

CCY_NAME: dict[str, str] = {
    "USD": "US dollar", "EUR": "Euro", "JPY": "Japanese yen", "GBP": "Pound sterling",
    "CNY": "Chinese yuan", "CHF": "Swiss franc", "CAD": "Canadian dollar",
    "AUD": "Australian dollar", "NZD": "New Zealand dollar", "SEK": "Swedish krona",
    "NOK": "Norwegian krone", "DKK": "Danish krone", "ISK": "Icelandic krona",
    "INR": "Indian rupee", "RUB": "Russian ruble", "BRL": "Brazilian real",
    "MXN": "Mexican peso", "ZAR": "South African rand", "KRW": "South Korean won",
    "SGD": "Singapore dollar", "HKD": "Hong Kong dollar", "TWD": "New Taiwan dollar",
    "TRY": "Turkish lira", "ARS": "Argentine peso", "CLP": "Chilean peso",
    "COP": "Colombian peso", "PEN": "Peruvian sol", "VES": "Venezuelan bolivar",
    "UYU": "Uruguayan peso", "PYG": "Paraguayan guarani", "BOB": "Bolivian boliviano",
    "GTQ": "Guatemalan quetzal", "HNL": "Honduran lempira", "NIO": "Nicaraguan cordoba",
    "CRC": "Costa Rican colon", "DOP": "Dominican peso", "CUP": "Cuban peso",
    "JMD": "Jamaican dollar", "TTD": "Trinidad and Tobago dollar", "HTG": "Haitian gourde",
    "GYD": "Guyanese dollar", "SRD": "Surinamese dollar", "BSD": "Bahamian dollar",
    "BBD": "Barbadian dollar", "BZD": "Belize dollar", "PLN": "Polish zloty",
    "CZK": "Czech koruna", "HUF": "Hungarian forint", "RON": "Romanian leu",
    "BGN": "Bulgarian lev", "RSD": "Serbian dinar", "UAH": "Ukrainian hryvnia",
    "BYN": "Belarusian ruble", "MDL": "Moldovan leu", "ALL": "Albanian lek",
    "MKD": "Macedonian denar", "BAM": "Bosnia convertible mark", "GEL": "Georgian lari",
    "AMD": "Armenian dram", "AZN": "Azerbaijani manat", "SAR": "Saudi riyal",
    "AED": "UAE dirham", "QAR": "Qatari riyal", "KWD": "Kuwaiti dinar",
    "BHD": "Bahraini dinar", "OMR": "Omani rial", "ILS": "Israeli shekel",
    "JOD": "Jordanian dinar", "LBP": "Lebanese pound", "IQD": "Iraqi dinar",
    "IRR": "Iranian rial", "SYP": "Syrian pound", "YER": "Yemeni rial",
    "IDR": "Indonesian rupiah", "MYR": "Malaysian ringgit", "THB": "Thai baht",
    "PHP": "Philippine peso", "VND": "Vietnamese dong", "PKR": "Pakistani rupee",
    "BDT": "Bangladeshi taka", "LKR": "Sri Lankan rupee", "NPR": "Nepalese rupee",
    "MMK": "Myanmar kyat", "KHR": "Cambodian riel", "LAK": "Lao kip",
    "MNT": "Mongolian tugrik", "KZT": "Kazakhstani tenge", "UZS": "Uzbekistani som",
    "TMT": "Turkmenistani manat", "KGS": "Kyrgyzstani som", "TJS": "Tajikistani somoni",
    "AFN": "Afghan afghani", "BND": "Brunei dollar", "MOP": "Macanese pataca",
    "MVR": "Maldivian rufiyaa", "BTN": "Bhutanese ngultrum", "EGP": "Egyptian pound",
    "NGN": "Nigerian naira", "KES": "Kenyan shilling", "GHS": "Ghanaian cedi",
    "MAD": "Moroccan dirham", "DZD": "Algerian dinar", "TND": "Tunisian dinar",
    "LYD": "Libyan dinar", "ETB": "Ethiopian birr", "TZS": "Tanzanian shilling",
    "UGX": "Ugandan shilling", "RWF": "Rwandan franc", "ZMW": "Zambian kwacha",
    "AOA": "Angolan kwanza", "MZN": "Mozambican metical", "BWP": "Botswana pula",
    "NAD": "Namibian dollar", "MUR": "Mauritian rupee", "XOF": "West African CFA franc",
    "XAF": "Central African CFA franc", "CDF": "Congolese franc", "SDG": "Sudanese pound",
    "SSP": "South Sudanese pound", "SOS": "Somali shilling", "MGA": "Malagasy ariary",
    "MWK": "Malawian kwacha", "SLE": "Sierra Leonean leone", "LRD": "Liberian dollar",
    "GMD": "Gambian dalasi", "GNF": "Guinean franc", "MRU": "Mauritanian ouguiya",
    "SCR": "Seychellois rupee", "CVE": "Cape Verdean escudo", "SZL": "Swazi lilangeni",
    "LSL": "Lesotho loti", "BIF": "Burundian franc", "ERN": "Eritrean nakfa",
    "DJF": "Djiboutian franc", "KMF": "Comorian franc", "STN": "Sao Tome dobra",
    "FJD": "Fijian dollar", "PGK": "Papua New Guinean kina", "SBD": "Solomon Islands dollar",
    "VUV": "Vanuatu vatu", "WST": "Samoan tala", "TOP": "Tongan pa'anga",
}
# Yahoo quotes these 4 as CUR/USD (foreign-base); everything else is USD/CUR.
FOREIGN_BASE = {"EUR", "GBP", "AUD", "NZD"}

# ── single-country ETF (country -> (yahoo symbol, label)) ──
COUNTRY_ETF: dict[str, tuple[str, str]] = {
    "BR": ("EWZ", "iShares MSCI Brazil ETF"),
    "MX": ("EWW", "iShares MSCI Mexico ETF"),
    "CA": ("EWC", "iShares MSCI Canada ETF"),
    "DE": ("EWG", "iShares MSCI Germany ETF"),
    "JP": ("EWJ", "iShares MSCI Japan ETF"),
    "GB": ("EWU", "iShares MSCI United Kingdom ETF"),
    "AU": ("EWA", "iShares MSCI Australia ETF"),
    "KR": ("EWY", "iShares MSCI South Korea ETF"),
    "TW": ("EWT", "iShares MSCI Taiwan ETF"),
    "IN": ("INDA", "iShares MSCI India ETF"),
    "CN": ("MCHI", "iShares MSCI China ETF"),
    "HK": ("EWH", "iShares MSCI Hong Kong ETF"),
    "SG": ("EWS", "iShares MSCI Singapore ETF"),
    "MY": ("EWM", "iShares MSCI Malaysia ETF"),
    "ID": ("EIDO", "iShares MSCI Indonesia ETF"),
    "PH": ("EPHE", "iShares MSCI Philippines ETF"),
    "TH": ("THD", "iShares MSCI Thailand ETF"),
    "TR": ("TUR", "iShares MSCI Turkey ETF"),
    "ZA": ("EZA", "iShares MSCI South Africa ETF"),
    "CO": ("GXG", "Global X MSCI Colombia ETF"),
    "CL": ("ECH", "iShares MSCI Chile ETF"),
    "PE": ("EPU", "iShares MSCI Peru ETF"),
    "AR": ("ARGT", "Global X MSCI Argentina ETF"),
    "ES": ("EWP", "iShares MSCI Spain ETF"),
    "IT": ("EWI", "iShares MSCI Italy ETF"),
    "FR": ("EWQ", "iShares MSCI France ETF"),
    "CH": ("EWL", "iShares MSCI Switzerland ETF"),
    "SE": ("EWD", "iShares MSCI Sweden ETF"),
    "NL": ("EWN", "iShares MSCI Netherlands ETF"),
    "BE": ("EWK", "iShares MSCI Belgium ETF"),
    "AT": ("EWO", "iShares MSCI Austria ETF"),
    "IL": ("EIS", "iShares MSCI Israel ETF"),
    "SA": ("KSA", "iShares MSCI Saudi Arabia ETF"),
    "QA": ("QAT", "iShares MSCI Qatar ETF"),
    "AE": ("UAE", "iShares MSCI UAE ETF"),
    "EG": ("EGPT", "VanEck Egypt Index ETF"),
    "NG": ("NGE", "Global X MSCI Nigeria ETF"),
    "PL": ("EPOL", "iShares MSCI Poland ETF"),
    "GR": ("GREK", "Global X MSCI Greece ETF"),
    "IE": ("EIRL", "iShares MSCI Ireland ETF"),
    "NO": ("ENOR", "iShares MSCI Norway ETF"),
    "DK": ("EDEN", "iShares MSCI Denmark ETF"),
    "FI": ("EFNL", "iShares MSCI Finland ETF"),
    "VN": ("VNM", "VanEck Vietnam ETF"),
    "PK": ("PAK", "Global X MSCI Pakistan ETF"),
    "NZ": ("ENZL", "iShares MSCI New Zealand ETF"),
    "PT": ("PGAL", "Global X MSCI Portugal ETF"),
}

# ── national champions (majors only, LIGHT; country -> [(symbol, label)]) ──
COUNTRY_CHAMPIONS: dict[str, list[tuple[str, str]]] = {
    "TW": [("TSM", "Taiwan Semiconductor (ADR)")],
    "SA": [("2222.SR", "Saudi Aramco (Tadawul)")],
    "NL": [("ASML", "ASML Holding")],
    "CH": [("NVS", "Novartis (ADR)"), ("NSRGY", "Nestle (ADR)")],
    "DE": [("SAP", "SAP SE (ADR)")],
    "JP": [("TM", "Toyota Motor (ADR)"), ("SONY", "Sony Group (ADR)")],
    "IN": [("INFY", "Infosys (ADR)"), ("HDB", "HDFC Bank (ADR)")],
    "CN": [("BABA", "Alibaba (ADR)")],
    "AR": [("YPF", "YPF (ADR)"), ("MELI", "MercadoLibre")],
    "CL": [("SQM", "Sociedad Quimica y Minera (ADR)")],
    "MX": [("AMX", "America Movil (ADR)")],
}

# ── obvious dominant single-commodity exporters (stored, NOT a country-card tile) ──
COUNTRY_EXPORT: dict[str, list[str]] = {
    "SA": ["CL=F"], "AE": ["CL=F"], "KW": ["CL=F"], "IQ": ["CL=F"], "QA": ["NG=F", "CL=F"],
    "NG": ["CL=F"], "AO": ["CL=F"], "DZ": ["CL=F", "NG=F"], "LY": ["CL=F"], "KZ": ["CL=F"],
    "NO": ["CL=F"], "VE": ["CL=F"], "EC": ["CL=F"], "RU": ["CL=F", "ZW=F"],
    "CL": ["HG=F"], "PE": ["HG=F"], "CD": ["HG=F"], "CO": ["CL=F", "KC=F"],
    "GH": ["CC=F", "GC=F"], "CI": ["CC=F"], "AR": ["ZS=F"], "UA": ["ZW=F", "ZC=F"],
    "ZM": ["HG=F"], "BR": ["ZS=F"], "AU": ["GC=F"],
}
COMMODITY: dict[str, tuple[str, str]] = {  # symbol -> (label, asset_class)
    "CL=F": ("WTI crude, front-month", "energy"),
    "NG=F": ("Henry Hub natural gas, front-month", "energy"),
    "GC=F": ("Gold, front-month", "metal"),
    "HG=F": ("Copper, front-month", "metal"),
    "KC=F": ("Coffee, front-month", "ag"),
    "CC=F": ("Cocoa, front-month", "ag"),
    "ZW=F": ("Wheat, front-month", "ag"),
    "ZS=F": ("Soybeans, front-month", "ag"),
    "ZC=F": ("Corn, front-month", "ag"),
}


def currency_symbol_label(ccy: str) -> tuple[str, str]:
    """Yahoo FX symbol + honest directional label for a currency code."""
    sym = f"{ccy}=X"
    name = CCY_NAME.get(ccy, ccy)
    if ccy in FOREIGN_BASE:
        return sym, f"{name} ({ccy}/USD)"
    return sym, f"{name} (USD/{ccy})"


def build_candidates() -> list[dict]:
    """Every candidate (country, symbol, role, label, asset_class, note) row."""
    rows: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    def add(cc, sym, role, label, cls, note):
        key = (cc, sym, role)
        if key in seen:
            return
        seen.add(key)
        rows.append({"country_code": cc, "symbol": sym, "role": role,
                     "label": label, "asset_class": cls, "note": note})

    for cc in sorted(COUNTRY_NAME):
        cname = COUNTRY_NAME[cc]
        # 1. currency
        if cc in EUROZONE:
            add(cc, "EUR=X", "currency", "Euro (EUR/USD)", "fx",
                f"{cname} shares the euro")
        elif cc in NO_OWN_CURRENCY:
            pass  # honest gap — recorded in the report, no row
        elif cc in COUNTRY_CCY:
            ccy = COUNTRY_CCY[cc]
            sym, label = currency_symbol_label(ccy)
            add(cc, sym, "currency", label, "fx", f"{cname}'s currency")
        # 2. index / country ETF
        if cc in COUNTRY_ETF:
            sym, label = COUNTRY_ETF[cc]
            add(cc, sym, "index", label, "equity-etf", f"{cname} country ETF")
        # 3. champions
        for sym, label in COUNTRY_CHAMPIONS.get(cc, []):
            add(cc, sym, "champion", label, "equity-single", f"{cname} champion")
        # 4. export commodity
        for sym in COUNTRY_EXPORT.get(cc, []):
            label, cls = COMMODITY[sym]
            add(cc, sym, "export-commodity", label, cls,
                f"{cname} top export (customs) — NOT a Brief country-card tile")
    return rows


# ── verification ──
def fetch_yahoo_daily(symbol: str, sleep: float) -> dict[str, float]:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.request.quote(symbol)}?range=1mo&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read())
            res = (d.get("chart", {}).get("result") or [None])[0]
            if not res:
                return {}
            ts = res.get("timestamp") or []
            quote = (res.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
            closes: dict[str, float] = {}
            for t, c in zip(ts, quote):
                if c is not None:
                    closes[date.fromtimestamp(t).isoformat()] = float(c)
            return closes
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                print(f"  ! {symbol}: give up ({e})", file=sys.stderr)
                return {}
            time.sleep(3 * (attempt + 1))
    return {}


def load_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text())
        except Exception:  # noqa: BLE001
            return {}
    return {}


def save_cache(cache: dict) -> None:
    CACHE.write_text(json.dumps(cache, indent=0, sort_keys=True))


def verify_symbols(symbols: list[str], sleep: float, no_network: bool,
                   refresh: bool, limit: int | None) -> dict[str, dict]:
    """symbol -> {'ok': bool, 'n_closes': int, 'last_close': float|None, 'last_date': str|None}."""
    cache = load_cache()
    out: dict[str, dict] = {}
    todo = symbols if limit is None else symbols[:limit]
    for i, sym in enumerate(todo, 1):
        if not refresh and sym in cache:
            out[sym] = cache[sym]
            continue
        if no_network:
            out[sym] = cache.get(sym, {"ok": False, "n_closes": 0,
                                       "last_close": None, "last_date": None})
            continue
        closes = fetch_yahoo_daily(sym, sleep)
        if closes:
            last_d = max(closes)
            rec = {"ok": True, "n_closes": len(closes),
                   "last_close": closes[last_d], "last_date": last_d}
        else:
            rec = {"ok": False, "n_closes": 0, "last_close": None, "last_date": None}
        out[sym] = rec
        cache[sym] = rec
        save_cache(cache)
        flag = "OK " if rec["ok"] else "DROP"
        print(f"  [{i:3d}/{len(todo)}] {flag} {sym:10s} "
              f"{rec['n_closes']:3d} closes"
              + (f"  last {rec['last_close']} @ {rec['last_date']}" if rec["ok"] else ""),
              file=sys.stderr)
        time.sleep(sleep)
    return out


# ── emitters ──
def sql_escape(s: str) -> str:
    return s.replace("'", "''")


def emit_migration(series: list[tuple[str, str, str]],
                   universe: list[dict]) -> str:
    lines: list[str] = []
    lines.append(
        "-- 089_markets_country_universe_all.sql — L4 markets: the ALL-COUNTRIES\n"
        "-- descriptive instrument universe (design §5). DATA-ONLY: extends the seed in\n"
        "-- 088 to every country whose instruments VERIFY against Yahoo's public chart\n"
        "-- API (markets/build_country_universe.py). basis='descriptive' on every row —\n"
        "-- true by identity (COP *is* Colombia's currency); no discovery, no #226 gate.\n"
        "--\n"
        "-- NO FABRICATION: every symbol below returned >=1 real Yahoo close at build\n"
        "-- time; tickers that did not resolve were dropped (honest coverage gaps are in\n"
        "-- docs/research/markets-l4/2026-07-21-country-universe-coverage.md).\n"
        "--\n"
        "-- RLS / REVOKE were already set in 088; this migration only INSERTs data.\n"
        "-- role='export-commodity' rows are a customs fact — stored, but the Brief\n"
        "-- COUNTRY card must NOT render them as a tile (design §5/§7).\n")
    lines.append("-- ── descriptive metadata (instrument identities) ──")
    lines.append("INSERT INTO market_series (symbol, label, asset_class) VALUES")
    body = [f"    ('{sql_escape(sym)}', '{sql_escape(lab)}', '{sql_escape(cls)}')"
            for sym, lab, cls in series]
    lines.append(",\n".join(body))
    lines.append("ON CONFLICT (symbol) DO NOTHING;\n")

    lines.append("-- ── per-country descriptive universe (currency / index / champion / export) ──")
    lines.append("INSERT INTO country_instrument_universe (country_code, symbol, role, note) VALUES")
    urows = [f"    ('{r['country_code']}', '{sql_escape(r['symbol'])}', "
             f"'{r['role']}', '{sql_escape(r['note'])}')"
             for r in universe]
    lines.append(",\n".join(urows))
    lines.append("ON CONFLICT (country_code, symbol, role) DO NOTHING;")
    return "\n".join(lines) + "\n"


def emit_report(candidates: list[dict], verified: list[dict],
                verify: dict[str, dict]) -> tuple[str, dict]:
    placed = {r["country_code"] for r in verified}
    all_countries = set(COUNTRY_NAME)
    by_role: dict[str, set[str]] = {}
    for r in verified:
        by_role.setdefault(r["role"], set()).add(r["country_code"])
    with_currency = by_role.get("currency", set())
    with_index = by_role.get("index", set())
    with_champ = by_role.get("champion", set())
    with_export = by_role.get("export-commodity", set())
    currency_only = {cc for cc in placed
                     if cc in with_currency and cc not in with_index and cc not in with_champ}
    no_instrument = sorted(all_countries - placed - {"US"})  # US carried by 088 indices
    distinct_symbols = sorted({r["symbol"] for r in verified})
    dropped = sorted(s for s, v in verify.items() if not v.get("ok"))

    stats = {
        "countries_total": len(all_countries),
        "countries_with_instrument": len(placed),
        "with_currency": len(with_currency),
        "with_index": len(with_index),
        "with_champion": len(with_champ),
        "with_export_commodity": len(with_export),
        "currency_only": len(currency_only),
        "distinct_symbols": len(distinct_symbols),
        "candidate_symbols": len({r["symbol"] for r in candidates}),
        "dropped_symbols": len(dropped),
        "no_instrument_countries": no_instrument,
    }

    def names(cs):
        return ", ".join(f"{c} {COUNTRY_NAME[c]}" for c in sorted(cs))

    md = []
    md.append("# L4 markets — all-countries instrument universe coverage (2026-07-21)\n")
    md.append("Built by `markets/build_country_universe.py`. Every symbol below returned\n"
              ">=1 real close from Yahoo's public chart API; non-resolving tickers were\n"
              "dropped (no fabrication). `basis='descriptive'` on every row — true by\n"
              "identity, no #226 gate.\n")
    md.append("## Coverage\n")
    md.append(f"- Countries placed with >=1 instrument: **{stats['countries_with_instrument']}** "
              f"of {stats['countries_total']} in the candidate table\n"
              f"- With own/shared currency: **{stats['with_currency']}**\n"
              f"- With a country index/ETF: **{stats['with_index']}**\n"
              f"- With >=1 national champion: **{stats['with_champion']}**\n"
              f"- With an export-commodity tag: **{stats['with_export_commodity']}**\n"
              f"- Currency-only (no index/champion): **{stats['currency_only']}**\n"
              f"- Distinct verified symbols: **{stats['distinct_symbols']}** "
              f"(from {stats['candidate_symbols']} candidates; "
              f"{stats['dropped_symbols']} dropped)\n")
    md.append("## Countries WITH a country index/ETF\n")
    md.append(names(with_index) + "\n")
    md.append("## Currency-only countries (own/shared FX verifies, no equity vehicle)\n")
    md.append(names(currency_only) + "\n")
    md.append("## Honest gaps — countries left with NO instrument\n")
    md.append("These had no currency FX pair, ETF, or champion that resolved on Yahoo\n"
              "(exotic/pegged/sanctioned currencies, no single-country ETF). Shown, not hidden.\n\n")
    md.append((names(no_instrument) if no_instrument else "(none)") + "\n")
    md.append("## Dropped symbols (candidate did not resolve on Yahoo)\n")
    md.append(("`" + "`, `".join(dropped) + "`") if dropped else "(none)")
    return "\n".join(md) + "\n", stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleep", type=float, default=0.7,
                    help="seconds between Yahoo fetches (be polite)")
    ap.add_argument("--no-network", action="store_true",
                    help="use only cached verification results (offline)")
    ap.add_argument("--refresh", action="store_true",
                    help="ignore cache, re-verify every symbol")
    ap.add_argument("--limit", type=int, default=None,
                    help="verify only the first N distinct symbols (debug)")
    args = ap.parse_args()

    candidates = build_candidates()
    distinct = sorted({r["symbol"] for r in candidates})
    print(f"candidates: {len(candidates)} country-rows over "
          f"{len(COUNTRY_NAME)} countries; {len(distinct)} distinct symbols to verify",
          file=sys.stderr)

    verify = verify_symbols(distinct, args.sleep, args.no_network, args.refresh, args.limit)

    verified = [r for r in candidates if verify.get(r["symbol"], {}).get("ok")]
    verified.sort(key=lambda r: (r["country_code"],
                                 {"currency": 0, "index": 1, "champion": 2,
                                  "export-commodity": 3}[r["role"]], r["symbol"]))

    # market_series rows: distinct verified symbols with label + asset_class
    series_map: dict[str, tuple[str, str]] = {}
    for r in verified:
        series_map.setdefault(r["symbol"], (r["label"], r["asset_class"]))
    series = [(sym, lab, cls) for sym, (lab, cls) in sorted(series_map.items())]

    # emit migration
    MIGRATION_OUT.write_text(emit_migration(series, verified))
    print(f"wrote {MIGRATION_OUT.relative_to(REPO)}", file=sys.stderr)

    # emit verified JSON (dict of country -> instrument rows)
    by_country: dict[str, list[dict]] = {}
    for r in verified:
        by_country.setdefault(r["country_code"], []).append(
            {k: r[k] for k in ("symbol", "label", "role", "asset_class", "note")})
    JSON_OUT.write_text(json.dumps({
        "built_at": date.today().isoformat(),
        "source": "Yahoo public chart API (v8/finance/chart)",
        "basis": "descriptive",
        "countries": by_country,
    }, indent=2))
    print(f"wrote {JSON_OUT.relative_to(REPO)}", file=sys.stderr)

    # report
    report, stats = emit_report(candidates, verified, verify)
    REPORT_OUT.write_text(report)
    print(f"wrote {REPORT_OUT.relative_to(REPO)}", file=sys.stderr)

    print("\n=== COVERAGE SUMMARY ===")
    print(f"countries placed        : {stats['countries_with_instrument']} / {stats['countries_total']}")
    print(f"  with currency         : {stats['with_currency']}")
    print(f"  with index/ETF        : {stats['with_index']}")
    print(f"  with champion         : {stats['with_champion']}")
    print(f"  with export-commodity : {stats['with_export_commodity']}")
    print(f"  currency-only         : {stats['currency_only']}")
    print(f"distinct symbols        : {stats['distinct_symbols']} "
          f"({stats['dropped_symbols']} dropped of {stats['candidate_symbols']} candidates)")
    print(f"no-instrument countries : {len(stats['no_instrument_countries'])}"
          + (f"  ({', '.join(stats['no_instrument_countries'])})"
             if stats['no_instrument_countries'] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
