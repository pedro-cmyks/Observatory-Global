"""L4 markets — the instrument universe (config).

Two descriptive-by-definition sets, per the master design route
(docs/research/markets-l4/2026-07-21-markets-relational-axis-design.md §5):

  WORLD_BASKET        — a fixed set of global bellwethers (world Brief strip).
  COUNTRY_INSTRUMENTS — each country's OWN instruments by identity (FX / index /
                        national champion / top-export commodity). basis = descriptive:
                        COP *is* Colombia's currency — no discovery, no #226 gate.

These drive ONLY the descriptive price accumulator. They are NOT a claim that any
news moves any price — that relation is the DISCOVERED object, gated on the #226
re-run (see the design doc §8). INSTRUMENT_MAP (in m0_event_study.py) stays the
category→instrument PRIOR, never imported here as a relation.

Seed is deliberately small + correct (US/CO/BR/MX + the world basket); extend by
adding rows. Symbols are Yahoo Finance chart-API tickers (free, daily closes).
ADRs are used where a local bourse index/firm is not on the free feed.
"""
from __future__ import annotations

# symbol, label, asset_class
WORLD_BASKET: list[tuple[str, str, str]] = [
    ("CL=F", "WTI crude, front-month", "energy"),
    ("GC=F", "Gold, front-month", "metal"),
    ("HG=F", "Copper, front-month", "metal"),
    ("^GSPC", "S&P 500", "equity-index"),
    ("DX-Y.NYB", "US Dollar Index (DXY)", "fx-index"),
    ("^VIX", "CBOE Volatility Index", "risk"),
]

# country_code -> [(symbol, label, role, asset_class)]
# role ∈ {currency, index, champion, export-commodity}. export-commodity is stored
# as data (a customs fact) but is NOT rendered on the Brief country card (design §5/§7:
# a globally-moving price beside country news is the strongest post-hoc causal trap).
COUNTRY_INSTRUMENTS: dict[str, list[tuple[str, str, str, str]]] = {
    "US": [
        ("^GSPC", "S&P 500", "index", "equity-index"),
        ("^DJI", "Dow Jones Industrial Average", "index", "equity-index"),
    ],
    "CO": [
        ("COP=X", "Colombian peso (USD/COP)", "currency", "fx"),
        ("GXG", "Global X MSCI Colombia ETF", "index", "equity-etf"),
        ("EC", "Ecopetrol (ADR)", "champion", "equity-single"),
        ("CIB", "Bancolombia (ADR)", "champion", "equity-single"),
        ("KC=F", "Coffee, front-month", "export-commodity", "ag"),
    ],
    "BR": [
        ("BRL=X", "Brazilian real (USD/BRL)", "currency", "fx"),
        ("EWZ", "iShares MSCI Brazil ETF", "index", "equity-etf"),
        ("PBR", "Petrobras (ADR)", "champion", "equity-single"),
        ("VALE", "Vale (ADR)", "champion", "equity-single"),
    ],
    "MX": [
        ("MXN=X", "Mexican peso (USD/MXN)", "currency", "fx"),
        ("EWW", "iShares MSCI Mexico ETF", "index", "equity-etf"),
    ],
}


def all_symbols() -> list[str]:
    """Deduped list of every symbol to fetch (world basket ∪ country universe)."""
    seen: dict[str, None] = {}
    for sym, _, _ in WORLD_BASKET:
        seen[sym] = None
    for rows in COUNTRY_INSTRUMENTS.values():
        for sym, _, _, _ in rows:
            seen[sym] = None
    return list(seen)


def symbol_labels() -> dict[str, tuple[str, str]]:
    """symbol -> (label, asset_class) for the price node metadata."""
    out: dict[str, tuple[str, str]] = {}
    for sym, label, cls in WORLD_BASKET:
        out.setdefault(sym, (label, cls))
    for rows in COUNTRY_INSTRUMENTS.values():
        for sym, label, _role, cls in rows:
            out.setdefault(sym, (label, cls))
    return out
