"""Vagón 6 (panel ciego 2026-08-18 §5) — the excerpt must never be the
cookie banner.

Camila's receipt from eltiempo.com read "En este portal utilizamos datos de
navegación / cookies…" — the portal's consent boilerplate served as if it were
the article. Measured in pinned_articles (2026-08-18): 726 rows with excerpts,
2 consent-class (eltiempo.com, ansa.it), 6 subscription-wall-class (Australian
Community Media syndication). The witnesses below are VERBATIM from the stored
rows — frozen, not invented.

The filter contract (conservative by design — a false positive loses real
content, so every pattern is unequivocal banner/portal speak, and only the
LEADING run of paragraphs is ever touched):

- a leading paragraph matching the boilerplate class is dropped and the next
  real paragraph takes its place;
- tiny stubs ("aquí", "Noticia", "Error 505") are dropped only INSIDE an
  already-matched boilerplate run — a short real lead is never touched;
- the scan stops permanently at the first real paragraph — mid-article text
  (including quotes ABOUT cookies) is byte-identical;
- if nothing real remains, extraction reports the existing honest wall state
  (paywall / no_extractable_text) — the banner is never served as an article.
"""
from __future__ import annotations

import json
import sys
import types

import pytest

from app.services import article_fetch as af


# ── frozen witnesses (verbatim from pinned_articles, 2026-08-18) ─────────────

ELTIEMPO_CONSENT = (
    "En este portal utilizamos datos de navegación / cookies propias y de "
    "terceros para gestionar el portal, elaborar información estadística, "
    "optimizar la funcionalidad del sitio y mostrar publicidad relacionada "
    "con sus preferencias a través del análisis de la navegación. Si "
    "continúa navegando, usted estará aceptando esta utilización. Puede "
    "conocer cómo deshabilitarlas u obtener más información"
)

ELTIEMPO_REAL_LEAD = (
    "Investigan muerte de mujer de 28 años que fue atropellada por una moto "
    "que iba en aparente exceso de velocidad en Barranquilla: dejó tres hijos"
)

ELTIEMPO_TEXT = "\n".join([
    ELTIEMPO_CONSENT,
    "aquí",
    "Ya tienes una cuenta vinculada a EL TIEMPO, por favor inicia sesión con "
    "ella y no te pierdas de todos los beneficios que tenemos para tí. "
    "Iniciar sesión",
    "¡Hola! Parece que has alcanzado tu límite diario de 3 búsquedas en "
    "nuestro chat bot como usuario registrado.",
    "¿Quieres seguir disfrutando de este y otros beneficios exclusivos?",
    "Adquiere el plan de suscripción que se adapte a tus preferencias y "
    "accede a ¡contenido ilimitado! No te",
    "pierdas la oportunidad de disfrutar todas las funcionalidades que "
    "ofrecemos. 🌟",
    "¡Hola! Haz excedido el máximo de peticiones mensuales.",
    "Para más información continua navegando en eltiempo.com",
    "Error 505",
    "Estamos resolviendo el problema, inténtalo nuevamente más tarde.",
    "Procesando tu pregunta... ¡Un momento, por favor!",
    "¿Sabías que registrándote en nuestro portal podrás acceder al chatbot "
    "de El Tiempo y obtener información",
    "precisa en tus búsquedas?",
    "Con el envío de tus consultas, aceptas los Términos y Condiciones del "
    "Chat disponibles en la parte superior. Recuerda que las respuestas "
    "generadas pueden presentar inexactitudes o bloqueos, de acuerdo con las "
    "políticas de filtros de contenido o el estado del modelo. Este Chat "
    "tiene finalidades únicamente informativas.",
    "De acuerdo con las políticas de la IA que usa EL TIEMPO, no es posible "
    "responder a las preguntas relacionadas con los siguientes temas: odio, "
    "sexual, violencia y autolesiones",
    "Noticia",
    ELTIEMPO_REAL_LEAD,
    "La víctima fue identificada como Nini Johana Torres García, quien vivía "
    "en el barrio Las Malvinas, mismo lugar donde ocurrieron los hechos.",
])

ANSA_TEXT = "\n".join([
    "Se hai scelto di non accettare i cookie di profilazione e tracciamento, "
    "puoi aderire all’abbonamento \"Consentless\" a un costo molto "
    "accessibile, oppure scegliere un altro abbonamento per accedere ad "
    "ANSA.it.",
    "Ti invitiamo a leggere le Condizioni Generali di Servizio, la Cookie "
    "Policy e l'Informativa Privacy.",
    "Puoi leggere tutti i titoli di ANSA.it",
    " e 10  contenuti ogni 30 giorni",
    "a €16,99/anno",
    "Se hai cambiato idea e non ti vuoi abbonare, puoi sempre esprimere il "
    "tuo consenso ai cookie di profilazione e tracciamento per leggere tutti "
    "i titoli di ANSA.it e 10 contenuti ogni 30 giorni (servizio base):",
    "Se accetti tutti i cookie di profilazione pubblicitaria e di "
    "tracciamento, noi e 750 terze parti selezionate utilizzeremo cookie e "
    "tecnologie simili per raccogliere ed elaborare i tuoi dati personali e "
    "fornirti annunci e contenuti personalizzati, valutare l’interazione "
    "con annunci e contenuti, effettuare ricerche di mercato, migliorare i "
    "prodotti e i servizi.Per maggiori informazioni accedi alla Cookie "
    "Policy e all'Informativa Privacy.",
    "Per maggiori informazioni sui servizi di ANSA.it, puoi consultare le "
    "nostre risposte alle domande più frequenti, oppure contattarci inviando "
    "una mail a register@ansa.it o telefonando al numero verde 800 938 881. "
    "Il servizio di assistenza clienti è attivo dal lunedì al venerdì dalle "
    "ore 09.00 alle ore 18:30, il sabato dalle ore 09:00 alle ore 14:00.",
    "In evidenza",
    "In evidenza",
])

ACM_TEXT = "\n".join([
    "Subscribe now for unlimited access.",
    "or signup to continue reading",
    "Tom Eadie, from Chinderah on the NSW far north coast, is rationing his "
    "care through Support at Home program because of its \"excessive\", "
    "uncapped prices which in some cases are more than double the actual "
    "cost of the service.",
    "Instead, he is using his GP's referrals to access care through Medicare "
    "rebates he is eligible for.",
])


# ── strip_leading_boilerplate ────────────────────────────────────────────────

def test_eltiempo_witness_excerpt_is_the_article_not_the_banner():
    cleaned = af.strip_leading_boilerplate(ELTIEMPO_TEXT)
    assert cleaned.startswith(ELTIEMPO_REAL_LEAD)
    ex = af._excerpt(cleaned)
    assert ex.startswith("Investigan muerte de mujer")
    assert "datos de navegación" not in ex
    assert "cookies" not in ex.lower()


def test_ansa_witness_all_boilerplate_leaves_nothing():
    # The whole ANSA extraction is consent + subscription furniture; serving
    # any paragraph of it as the article would be the same embarrassment.
    assert af.strip_leading_boilerplate(ANSA_TEXT) == ""


def test_acm_subscription_wall_paragraphs_are_dropped():
    cleaned = af.strip_leading_boilerplate(ACM_TEXT)
    assert cleaned.startswith("Tom Eadie, from Chinderah")
    assert "Subscribe now" not in cleaned
    assert "signup to continue" not in cleaned


def test_clean_article_passes_byte_identical():
    text = "\n".join([
        "El presidente anunció este viernes un paquete de reformas.",
        "La oposición respondió que acudirá a la corte constitucional.",
    ])
    assert af.strip_leading_boilerplate(text) == text


def test_article_about_cookies_is_not_stripped():
    # The false-positive the mandate warns about: news ABOUT cookies. The
    # patterns are first/second-person banner speak, which a news lead is not.
    text = "\n".join([
        "La UE multó a Google con 500 millones de euros por violar las "
        "normas sobre el uso de cookies en sus portales europeos.",
        "La sanción es la mayor impuesta hasta ahora por este motivo.",
    ])
    assert af.strip_leading_boilerplate(text) == text


def test_short_real_lead_is_never_treated_as_stub():
    # Stubs are only skippable INSIDE an already-matched boilerplate run.
    text = "\n".join([
        "Murió Maradona.",
        "El mundo del fútbol despide a su ídolo más grande.",
    ])
    assert af.strip_leading_boilerplate(text) == text


def test_scan_stops_at_first_real_paragraph_forever():
    # A banner phrase QUOTED mid-article must never be touched: the scan ends
    # at the first real paragraph.
    text = "\n".join([
        "El regulador presentó cargos contra la plataforma.",
        "“Utilizamos cookies para mejorar la experiencia”, se "
        "defendió la empresa en un comunicado.",
        "La audiencia quedó fijada para marzo.",
    ])
    assert af.strip_leading_boilerplate(text) == text


def test_empty_and_none_are_safe():
    assert af.strip_leading_boilerplate("") == ""


# ── integration: _extract applies the filter ─────────────────────────────────

def _fake_trafilatura(monkeypatch, text: str):
    fake = types.ModuleType("trafilatura")
    fake.extract = lambda *_a, **_k: json.dumps(
        {"title": "T", "text": text, "language": "es"})
    monkeypatch.setitem(sys.modules, "trafilatura", fake)


def test_extract_serves_cleaned_text(monkeypatch):
    _fake_trafilatura(monkeypatch, ELTIEMPO_TEXT)
    doc = af._extract(b"<html>x</html>", "text/html", "https://eltiempo.com/a")
    assert doc is not None
    assert doc["text"].startswith(ELTIEMPO_REAL_LEAD)


def test_extract_of_pure_boilerplate_is_the_honest_wall_state(monkeypatch):
    _fake_trafilatura(monkeypatch, ANSA_TEXT)
    doc = af._extract(b"<html>x</html>", "text/html", "https://ansa.it/a")
    assert doc is None
    # and the status machine turns that into the existing honest state:
    assert af.classify_fetch(200, doc) == ("paywall", "no_extractable_text")
