"""Casualty-term guard for the translation path.

WHY THIS EXISTS. 2026-08-13 veracity scorecard, claim 2, confirmed as a real
Atlas error: a Romanian headline about the Colombia earthquake reached the
reader in English as "224 dead and over 600 dead". Every Romanian original
said "224 de morţi şi peste 600 de **răniţi**" — răniţi is INJURED. Three
blind testers caught it independently. In a product whose whole promise is
receipts, a casualty figure that changes category in translation is the worst
failure available to us: the reader holds a number the source never said,
under a link that appears to back it.

WHAT IT DOES. After a translation comes back we extract (number, casualty
category) pairs from BOTH the original and the translation and compare them:

  category_flip            the same number carries incompatible categories on
                           the two sides (injured -> dead) — the witness
  uncorroborated_category  the number is in the original but nothing anywhere
                           near it there says it is a casualty count
  number_absent            the translation attaches a casualty category to a
                           number the original never printed

Any of those and the translation is NOT served: the caller returns the
original text with `translation_unverified`. A refusal is honest; a flipped
death toll is not.

DESIGN RULE: PRECISION FIRST. A guard that cries wolf gets switched off, so
every ambiguous shape resolves to silence, not to an accusation:

  * Categories are compared as SETS with umbrella words ("casualties",
    "victime", "жертв") expanding to {dead, injured} — so "dead" -> "killed"
    and "жертв" -> "death toll" can never fire.
  * A number takes the category of the NEAREST term within ANCHOR_GAP chars,
    preferring one not cut off by a clause break (the CJK case: "…死亡、600人
    受伤" puts 死亡 one character before 600 and 受伤 two after).
  * Both sides are scanned with the SAME union of all languages, so a term we
    mis-fire on (a person named Luka, German "Tote" vs English "tote") fires
    symmetrically and cancels instead of accusing.
  * The weak rules stand down whenever we might simply be blind: a casualty
    word anywhere within CONTEXT_GAP suppresses `uncorroborated_category`, and
    a scale word ("mii", "тыс", "thousand") suppresses `number_absent`,
    because "12,5 mii" -> "12,500" is one fact written two ways.
  * Original with no digits, or with no casualty vocabulary we recognise
    (Thai, Greek, …) = skipped. Refusing every translation in a language we
    cannot read would be a louder lie than the one we are fixing.

The lexicon is deliberately BOUNDED — explicit inflected forms, no stem
wildcards. Wildcards were tried and rejected: Turkish `ölü*` folded onto
`olur` ("it happens"), one of the commonest words in the language. Same
reason there is no global diacritic folding: it collides French "tués" with
English "Tues" and it is not needed, because the one language whose feeds
demonstrably drop diacritics (Romanian, the witness) carries its bare-ASCII
forms explicitly.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

CASUALTY_CATEGORIES: tuple[str, ...] = ("dead", "injured", "missing")

#: Terms filed under this key are umbrella words that legitimately cover both
#: the dead and the injured; they expand to {"dead", "injured"} and therefore
#: can never trip the flip rule on their own.
UMBRELLA = "casualties"

#: Characters that may separate a number from the casualty word it belongs to.
ANCHOR_GAP = 24
#: Wider window used only to STAY SILENT: a casualty word this close means the
#: original plausibly does anchor the number and we merely cannot see how.
CONTEXT_GAP = 80


# --------------------------------------------------------------------------
# The lexicon
# --------------------------------------------------------------------------
# Languages Atlas actually serves (RSS wave set + GDELT translated lane).
# Every entry is a whole word form, lower-cased. Romanian additionally carries
# its diacritic-stripped forms because Romanian feeds ship all three spellings
# of the same word (răniți / răniţi / raniti) — the witness itself arrived in
# the legacy-cedilla spelling.

LEXICON: dict[str, dict[str, tuple[str, ...]]] = {
    "en": {
        # NOTE "die"/"dies" are deliberately absent: they are the German
        # article and demonstrative, and German is a high-volume source
        # language here. "600 die in quake" therefore anchors nothing — a
        # missed catch, never a false accusation.
        "dead": (
            "dead", "death", "deaths", "death toll", "died", "killed", "kill",
            "kills", "fatalities", "fatality", "fatal", "perished", "slain",
            "lives lost", "dead bodies",
        ),
        "injured": (
            "injured", "injury", "injuries", "wounded", "wounds", "hurt",
            "maimed", "hospitalised", "hospitalized",
        ),
        "missing": ("missing", "unaccounted for", "disappeared", "lost at sea"),
        UMBRELLA: ("casualties", "casualty", "victims", "victim"),
    },
    "ro": {
        "dead": (
            "morți", "morţi", "morti", "mort", "moarte", "morților",
            "decedați", "decedaţi", "decedati", "decese", "deces",
            "uciși", "ucişi", "ucisi", "ucis", "murit", "au murit", "morţii",
        ),
        "injured": (
            "răniți", "răniţi", "raniti", "rănit", "rănită", "rănite",
            "ranit", "ranite", "răniților", "vătămați", "vatamati",
        ),
        "missing": (
            "dispăruți", "dispăruţi", "disparuti", "dispărut", "disparut",
            "dispărute", "dați dispăruți",
        ),
        UMBRELLA: ("victime", "victimă", "victima"),
    },
    "es": {
        "dead": (
            "muertos", "muertas", "muerto", "muerta", "muertes", "muerte",
            "fallecidos", "fallecidas", "fallecido", "fallecida",
            "murieron", "asesinados", "asesinado", "decesos", "difuntos",
        ),
        "injured": (
            "heridos", "heridas", "herido", "herida", "lesionados",
            "lesionado", "hospitalizados",
        ),
        "missing": ("desaparecidos", "desaparecidas", "desaparecido", "desaparecida"),
        UMBRELLA: ("víctimas", "victimas", "víctima", "victima"),
    },
    "pt": {
        "dead": (
            "mortos", "mortas", "morto", "morta", "mortes", "morte",
            "falecidos", "falecido", "morreram", "óbitos", "obitos",
        ),
        "injured": ("feridos", "feridas", "ferido", "ferida", "lesionados"),
        "missing": ("desaparecidos", "desaparecido", "desaparecidas"),
        UMBRELLA: ("vítimas", "vitimas", "vítima", "vitima"),
    },
    "fr": {
        "dead": (
            "morts", "mort", "morte", "mortes", "décès", "deces",
            "décédés", "décédé", "tués", "tué", "tuées", "tuée",
        ),
        "injured": ("blessés", "blessé", "blessées", "blessée", "hospitalisés"),
        "missing": ("disparus", "disparu", "disparues", "portés disparus"),
        UMBRELLA: ("victimes", "victime"),
    },
    "de": {
        # Bare "tot" is excluded (too short, collides across languages);
        # German headlines count with "Tote"/"Todesopfer" anyway.
        "dead": (
            "tote", "toten", "toter", "todesopfer", "todesfälle", "todesfaelle",
            "getötet", "getoetet", "gestorben", "starben", "umgekommen",
            "ums leben gekommen",
        ),
        "injured": (
            "verletzte", "verletzten", "verletzt", "verletzter",
            "verwundete", "verwundet", "schwerverletzte", "leichtverletzte",
        ),
        "missing": ("vermisste", "vermissten", "vermisst", "vermisster"),
        UMBRELLA: ("opfer",),
    },
    "it": {
        "dead": ("morti", "morto", "morta", "morte", "decessi", "deceduti", "uccisi", "ucciso"),
        "injured": ("feriti", "ferito", "ferite", "ferita", "contusi"),
        "missing": ("dispersi", "disperso", "scomparsi"),
        UMBRELLA: ("vittime", "vittima"),
    },
    "ru": {
        "dead": (
            "погиб", "погибли", "погибло", "погибших", "погибшие", "погибшими",
            "убиты", "убит", "убитых", "умерли", "умер", "смертей", "смерть",
            "смертельным исходом",
        ),
        "injured": (
            "ранены", "ранен", "ранено", "раненых", "раненые", "ранения",
            "травмированы", "травмы", "госпитализированы",
        ),
        "missing": ("пропали", "пропавших", "пропал", "без вести"),
        UMBRELLA: ("жертв", "жертвы", "жертва", "пострадавших", "пострадали"),
    },
    "uk": {
        "dead": (
            "загинули", "загинуло", "загинув", "загиблих", "загиблі",
            "вбито", "вбитих", "померли", "помер", "смертей",
        ),
        "injured": (
            "поранено", "поранені", "поранених", "поранений", "травмовано",
            "госпіталізовано",
        ),
        "missing": ("зниклих", "зникли", "безвісти", "без вісти"),
        UMBRELLA: ("жертв", "жертви", "постраждалих", "постраждали"),
    },
    "tr": {
        # Explicit forms, no stem wildcards: `ölü*` would swallow "olur".
        "dead": (
            "ölü", "ölüler", "ölüsü", "ölüm", "ölümü", "ölümler", "öldü",
            "öldürüldü", "can kaybı", "hayatını kaybetti", "hayatını kaybeden",
            "yaşamını yitirdi",
        ),
        "injured": (
            "yaralı", "yaralılar", "yaralıların", "yaralandı", "yaralanan",
            "yaralanma", "yaralananların", "ağır yaralı",
        ),
        "missing": ("kayıp", "kayıplar", "kaybolan", "kayboldu"),
        UMBRELLA: ("kurban", "kurbanı"),
    },
    "id": {
        "dead": ("tewas", "meninggal", "meninggal dunia", "korban jiwa", "tewasnya", "wafat"),
        "injured": ("luka", "luka-luka", "terluka", "cedera", "luka berat", "luka ringan"),
        "missing": ("hilang", "orang hilang", "menghilang"),
        UMBRELLA: ("korban",),
    },
    "ar": {
        # Written WITHOUT the alef hamza forms: the normaliser folds
        # أ/إ/آ -> ا and strips harakat before matching.
        # مصرع ("the death of") heads a very common Egyptian/Levantine
        # accident headline — "مصرع 4 سيدات وإصابة 13" — and its absence was
        # half of the one prod false positive this guard was measured against.
        "dead": (
            "قتلى", "قتيل", "قتل", "مقتل", "مصرع", "وفاة", "وفيات",
            "متوفين", "هلاك", "ضحية وفاة",
        ),
        "injured": ("جرحى", "جريح", "مصاب", "مصابين", "اصابة", "اصابات", "اصيب", "جرح"),
        "missing": ("مفقود", "مفقودين", "مفقودا", "فقدان"),
        UMBRELLA: ("ضحايا", "ضحية"),
    },
    "ko": {
        "dead": ("사망", "사망자", "숨졌", "숨진", "숨져", "희생자", "사망했"),
        "injured": ("부상", "부상자", "다쳤", "다친", "중상", "경상"),
        "missing": ("실종", "실종자", "행방불명"),
        UMBRELLA: ("사상자", "인명피해"),
    },
    "zh": {
        "dead": ("死亡", "死者", "遇难", "遇难者", "罹难", "身亡", "死"),
        "injured": ("受伤", "伤者", "负伤", "受伤者", "重伤", "轻伤"),
        "missing": ("失踪", "下落不明", "失联"),
        UMBRELLA: ("伤亡", "死伤"),
    },
    "ja": {
        "dead": ("死亡", "死者", "犠牲", "犠牲者", "亡くなった", "死去"),
        "injured": ("負傷", "負傷者", "けが人", "けが", "重傷", "軽傷"),
        "missing": ("行方不明", "安否不明"),
        UMBRELLA: ("死傷", "被害者"),
    },
}

#: Scale words. Their presence means the two sides may legitimately write the
#: same magnitude with different digits ("12,5 mii" / "12,500"), so the
#: `number_absent` rule stands down.
SCALE_WORDS: tuple[str, ...] = (
    "thousand", "thousands", "million", "millions", "billion", "billions",
    "mii", "mie", "milioane", "miliarde",
    "mil", "miles", "millón", "millon", "millones",
    "milhões", "milhoes", "milhão", "milhao",
    "mille", "milliers", "millions", "mila", "milioni",
    "tausend", "millionen", "milliarden",
    "тыс", "тысяч", "тысячи", "млн", "миллион", "миллионов",
    "тис", "тисяч", "мільйон", "мільйонів",
    "bin", "milyon", "ribu", "juta",
    "الف", "الاف", "مليون", "ملايين",
    "万", "千", "亿", "億", "百万",
)

#: Scripts where words are not space-delimited: match as plain substrings.
_SUBSTRING_LANGS = frozenset({"zh", "ja", "ko"})
#: Arabic-script languages: allow the clitic prefixes (و، ف، ب، ك، ل، ال).
_ARABIC_LANGS = frozenset({"ar", "fa", "ur"})

#: A clause break between a number and a term demotes that term: it is used
#: only when no un-broken candidate exists. This is what lets the guard read
#: "…224人死亡、600人受伤" the way a reader does.
_CLAUSE_BREAKS = frozenset(",;:.!?，、。；：！？…—–|/\n\r\t")

#: Coordinating conjunctions break a clause exactly like a comma does, and
#: they are what a real prod false positive turned on: "4 women killed **and**
#: 13 others injured" put `killed` five characters before 13 while the true
#: anchor `injured` sat eight after, so nearest-wins read 13 as dead and would
#: have refused a perfectly faithful Arabic translation (signal 17573672,
#: measured over 409 cached prod pairs). With `and` demoting, 13 reads injured.
_CONJUNCTIONS = frozenset({
    "and", "y", "e", "ed", "et", "und", "sowie", "iar", "și", "şi", "si",
    "и", "та", "і", "й", "ve", "dan", "serta", "و", "atau", "or",
})
#: CJK conjunctions are written without spaces, so they are matched as chars.
_CJK_CONJUNCTIONS = frozenset("和及與与と")
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------

# Romanian ships both the correct comma-below letters and the legacy cedilla
# ones; they are the same letters. (The bare-ASCII spellings are covered by
# explicit lexicon entries instead, so no global diacritic folding is needed.)
_CHAR_MAP = {
    "ţ": "ț",  # ţ -> ț
    "Ţ": "Ț",
    "ş": "ș",  # ş -> ș
    "Ş": "Ș",
    "’": "'",
    " ": " ",
    " ": " ",
    " ": " ",
}

# Arabic harakat, tatweel and superscript alef carry no lexical weight here.
_ARABIC_STRIP = re.compile(r"[ً-ْـٰ]")
_ARABIC_ALEF = re.compile(r"[أإآٱ]")

_DIGIT_MAP = {}
for _base in (0x0660, 0x06F0, 0x0966, 0x09E6):  # Arabic-Indic, Persian, Devanagari, Bengali
    for _d in range(10):
        _DIGIT_MAP[chr(_base + _d)] = str(_d)


def normalize(text: str) -> str:
    """Fold the spellings that are the same word, and nothing else."""
    if not text:
        return ""
    out = unicodedata.normalize("NFKC", text).casefold()
    out = "".join(_CHAR_MAP.get(ch, _DIGIT_MAP.get(ch, ch)) for ch in out)
    out = _ARABIC_STRIP.sub("", out)
    out = _ARABIC_ALEF.sub("ا", out)
    return re.sub(r"[ \t]+", " ", out)


# --------------------------------------------------------------------------
# Compiled matchers
# --------------------------------------------------------------------------

_LETTER = r"[^\W\d_]"
_ARABIC_LETTER = r"[ء-ي]"


def _term_pattern(lang: str, term: str) -> str:
    body = re.escape(normalize(term))
    if lang in _SUBSTRING_LANGS:
        return body
    if lang in _ARABIC_LANGS:
        # The definite article joins the word (القتلى) so it lives INSIDE the
        # match; the one-letter clitics (و ف ب ك ل) are left OUTSIDE it via the
        # lookbehind, so that "وإصابة" still matches AND the conjunction و
        # remains visible to the clause-break scan. Pronominal suffixes
        # (مصرعه، قتلاهم) are allowed on the right.
        return (
            rf"(?:(?<!{_ARABIC_LETTER})|(?<=[وفبكل]))(?:ال)?{body}"
            rf"(?:ه|ها|هم|هن|نا)?(?!{_ARABIC_LETTER})"
        )
    return rf"(?<!{_LETTER}){body}(?!{_LETTER})"


def _build_matchers() -> tuple[tuple[re.Pattern[str], frozenset[str], str], ...]:
    out: list[tuple[re.Pattern[str], frozenset[str], str]] = []
    for lang, groups in LEXICON.items():
        for category, terms in groups.items():
            cats = (
                frozenset({"dead", "injured"})
                if category == UMBRELLA
                else frozenset({category})
            )
            for term in terms:
                out.append((re.compile(_term_pattern(lang, term), re.UNICODE), cats, term))
    return tuple(out)


_MATCHERS = _build_matchers()

_SCALE_RE = re.compile(
    "|".join(
        sorted(
            (
                (w if any(ch in w for ch in "万千亿億") else rf"(?<!{_LETTER}){re.escape(w)}(?!{_LETTER})")
                for w in {normalize(s) for s in SCALE_WORDS}
            ),
            key=len,
            reverse=True,
        )
    ),
    re.UNICODE,
)

# 224 · 1,200 · 1.200 · 1 200 · 12,5 — grouped thousands then an optional
# decimal tail. Both sides are canonicalised the same way before comparison.
_NUMBER_RE = re.compile(r"\d+(?:[.,' ]\d{3})*(?:[.,]\d{1,2})?")
_THOUSANDS_SEP = re.compile(r"[.,' ](?=\d{3}(?!\d))")

# Dates and clock times are not casualty counts, and they are the commonest
# spurious anchor in the live corpus ("…погиб 13/08/2026 – Новости" anchored
# 13, 8 and 2026 to `dead`). They are also the numbers most likely to be
# RE-FORMATTED in translation, which is exactly what would make the
# number_absent rule misfire — so they are blanked before analysis. Blanking
# preserves length so every span stays aligned. Bare years are NOT touched:
# "Mehr als 2000 Todesfälle" is a real toll.
_DATELIKE_RE = re.compile(r"\d{1,4}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}:\d{2}(?::\d{2})?")


def _blank_datelike(text: str) -> str:
    return _DATELIKE_RE.sub(lambda m: " " * len(m.group(0)), text)


def _canonical_number(raw: str) -> str:
    s = _THOUSANDS_SEP.sub("", raw).replace(",", ".")
    if s.endswith("."):
        s = s[:-1]
    if "." in s:
        s = s.rstrip("0").rstrip(".") or "0"
    return s.lstrip("0") or "0"


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class _Analysis:
    numbers: dict[str, tuple[tuple[int, int], ...]]      # canonical -> spans
    anchored: dict[str, frozenset[str]]                  # canonical -> categories
    near_context: frozenset[str]                         # canonical numbers with a term within CONTEXT_GAP
    terms: tuple[str, ...]
    has_scale_word: bool


def _term_hits(text: str) -> list[tuple[int, int, frozenset[str], str]]:
    hits: list[tuple[int, int, frozenset[str], str]] = []
    for pattern, cats, term in _MATCHERS:
        for m in pattern.finditer(text):
            hits.append((m.start(), m.end(), cats, term))
    return hits


def _gap(num_span: tuple[int, int], term_span: tuple[int, int], text: str) -> tuple[int, bool, bool]:
    """(characters between, term-comes-after, a clause break separates them)."""
    ns, ne = num_span
    ts, te = term_span
    if ts >= ne:
        between = text[ne:ts]
        after = True
    elif te <= ns:
        between = text[te:ns]
        after = False
    else:  # overlapping (a number glued inside a term) — treat as adjacent
        return 0, ts >= ns, False
    return len(between), after, _breaks_clause(between)


def _breaks_clause(between: str) -> bool:
    """Is there a clause boundary between a number and a casualty word?"""
    if any(ch in _CLAUSE_BREAKS for ch in between):
        return True
    if any(ch in _CJK_CONJUNCTIONS for ch in between):
        return True
    return any(w in _CONJUNCTIONS for w in _WORD_RE.findall(between))


def _analyze(text: str) -> _Analysis:
    norm = _blank_datelike(normalize(text))
    numbers: dict[str, list[tuple[int, int]]] = {}
    for m in _NUMBER_RE.finditer(norm):
        numbers.setdefault(_canonical_number(m.group(0)), []).append((m.start(), m.end()))

    hits = _term_hits(norm)
    anchored: dict[str, set[str]] = {}
    context: set[str] = set()

    for key, spans in numbers.items():
        for span in spans:
            candidates = []
            for ts, te, cats, _term in hits:
                gap, after, separated = _gap(span, (ts, te), norm)
                if gap <= CONTEXT_GAP:
                    context.add(key)
                if gap <= ANCHOR_GAP:
                    candidates.append((gap, after, separated, cats))
            if not candidates:
                continue
            # A clause break demotes a candidate: only fall back to broken ones
            # when nothing un-broken is in range.
            pool = [c for c in candidates if not c[2]] or candidates
            best = min(c[0] for c in pool)
            winners = [c for c in pool if c[0] == best]
            # Most languages write the count then the word ("600 injured",
            # "600 de răniți", "600人受伤"); on a tie the word after wins.
            after_winners = [c for c in winners if c[1]]
            if after_winners:
                winners = after_winners
            cats: set[str] = set()
            for c in winners:
                cats |= set(c[3])
            anchored.setdefault(key, set()).update(cats)

    return _Analysis(
        numbers={k: tuple(v) for k, v in numbers.items()},
        anchored={k: frozenset(v) for k, v in anchored.items()},
        near_context=frozenset(context),
        terms=tuple(sorted({t for _s, _e, _c, t in hits})),
        has_scale_word=bool(_SCALE_RE.search(norm)),
    )


def extract_casualty_numbers(text: str) -> dict[str, set[str]]:
    """{canonical number -> categories} for every casualty figure in `text`."""
    return {k: set(v) for k, v in _analyze(text).anchored.items()}


def casualty_terms_in(text: str) -> tuple[str, ...]:
    """The casualty vocabulary found in `text`, across every lexicon language."""
    return _analyze(text).terms


# --------------------------------------------------------------------------
# The verdict
# --------------------------------------------------------------------------

#: Most severe first — the reason reported for the verdict as a whole.
_REASON_ORDER = ("category_flip", "uncorroborated_category", "number_absent")


@dataclass(frozen=True)
class Finding:
    number: str
    reason: str
    original_categories: tuple[str, ...] = ()
    translated_categories: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "number": self.number,
            "reason": self.reason,
            "original_categories": list(self.original_categories),
            "translated_categories": list(self.translated_categories),
        }


@dataclass(frozen=True)
class GuardVerdict:
    fired: bool
    reason: Optional[str] = None
    skipped: Optional[str] = None
    findings: tuple[Finding, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return {
            "fired": self.fired,
            "reason": self.reason,
            "skipped": self.skipped,
            "findings": [f.as_dict() for f in self.findings],
        }

    @property
    def message(self) -> str:
        if not self.fired:
            return ""
        f = self.findings[0]
        if f.reason == "category_flip":
            return (
                f"casualty figure {f.number} changed category in translation: "
                f"{'/'.join(f.original_categories)} -> {'/'.join(f.translated_categories)}"
            )
        if f.reason == "uncorroborated_category":
            return (
                f"translation calls {f.number} "
                f"{'/'.join(f.translated_categories)}; the original does not"
            )
        return f"translation reports {f.number} casualties absent from the original"


def check_translation(original: str, translated: str) -> GuardVerdict:
    """Compare casualty figures on both sides. Fired = do NOT serve.

    Silence is the default: anything we cannot read, cannot anchor, or could
    plausibly be writing two ways returns `fired=False` with a `skipped`
    reason where one applies.
    """
    if not original or not translated:
        return GuardVerdict(False, skipped="empty_text")

    orig = _analyze(original)
    if not orig.numbers:
        return GuardVerdict(False, skipped="no_numbers_in_original")
    if not orig.terms:
        return GuardVerdict(False, skipped="no_casualty_terms_in_original")

    trans = _analyze(translated)
    if not trans.anchored:
        return GuardVerdict(False, skipped="no_casualty_numbers_in_translation")

    findings: list[Finding] = []
    for key, tcats in sorted(trans.anchored.items()):
        ocats = orig.anchored.get(key)
        if ocats:
            if ocats & tcats:
                continue
            findings.append(
                Finding(
                    number=key,
                    reason="category_flip",
                    original_categories=tuple(sorted(ocats)),
                    translated_categories=tuple(sorted(tcats)),
                )
            )
            continue
        if key in orig.numbers:
            # The number is there but unanchored. If ANY casualty word sits in
            # the wider context we assume our reading, not the translator, is
            # what failed.
            if key in orig.near_context:
                continue
            findings.append(
                Finding(
                    number=key,
                    reason="uncorroborated_category",
                    translated_categories=tuple(sorted(tcats)),
                )
            )
            continue
        # Number absent from the original entirely. Suppressed when either
        # side uses a scale word: "12,5 mii" and "12,500" are one figure.
        if orig.has_scale_word or trans.has_scale_word:
            continue
        findings.append(
            Finding(
                number=key,
                reason="number_absent",
                translated_categories=tuple(sorted(tcats)),
            )
        )

    if not findings:
        return GuardVerdict(False)

    findings.sort(key=lambda f: (_REASON_ORDER.index(f.reason), f.number))
    return GuardVerdict(True, reason=findings[0].reason, findings=tuple(findings))


# --------------------------------------------------------------------------
# Ledger — every fire is a datapoint about the translator, keep them all
# --------------------------------------------------------------------------

_DEFAULT_LEDGER = ("docs", "research", "translation-guard", "guard-fires.jsonl")


def ledger_path() -> Optional[Path]:
    """Where fires are appended, or None when there is nowhere sensible.

    `ATLAS_TRANSLATION_GUARD_LOG` wins. Otherwise the repo's research folder,
    but only if it already exists — on Fly it does not, and a guard must not
    invent directories on a production box. There the warning log is the
    record.
    """
    env = os.environ.get("ATLAS_TRANSLATION_GUARD_LOG")
    if env:
        return Path(env)
    root = Path(__file__).resolve().parents[3]
    if (root / "docs" / "research").is_dir():
        return root.joinpath(*_DEFAULT_LEDGER)
    return None


def record_fire(verdict: GuardVerdict, context: Optional[dict] = None) -> None:
    """One JSONL line per refusal + one warning. Never raises, ever."""
    try:
        entry = {
            "at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            **(context or {}),
            **verdict.as_dict(),
        }
        logger.warning("TRANSLATION_GUARD_FIRED %s", json.dumps(entry, ensure_ascii=False))
        path = ledger_path()
        if not path:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:  # pragma: no cover - a ledger must never break serving
        logger.debug("translation guard ledger write failed", exc_info=True)


def guard_payload(verdict: GuardVerdict) -> dict:
    """The shape served to the client when a translation is refused."""
    return {
        "reason": verdict.reason,
        "message": verdict.message,
        "findings": [f.as_dict() for f in verdict.findings],
    }


def coverage() -> dict[str, dict[str, int]]:
    """Term counts per language and category (used by the coverage report)."""
    return {
        lang: {cat: len(terms) for cat, terms in groups.items()}
        for lang, groups in LEXICON.items()
    }


__all__ = [
    "ANCHOR_GAP",
    "CASUALTY_CATEGORIES",
    "CONTEXT_GAP",
    "Finding",
    "GuardVerdict",
    "LEXICON",
    "UMBRELLA",
    "casualty_terms_in",
    "check_translation",
    "coverage",
    "extract_casualty_numbers",
    "guard_payload",
    "ledger_path",
    "normalize",
    "record_fire",
]
