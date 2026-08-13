"""The ingest base — one string, so no coverage claim can drift from its base.

X1 (2026-08-13). The veracity scorecard's single REFUTATION and two of its four
divergences all share one defect: Atlas served the shape of ITS OWN INGEST as
the shape of the WORLD. It told testers Colombia had "0% own voices" while El
Tiempo, Caracol and El Colombiano covered the quake massively, and that the US
press had not picked up Hormuz while CNN ran live coverage.

The cure is structural, not editorial: every surface that makes a coverage or
voice SHAPE claim reads its base from here, and every payload that serves one
carries it as a field. If the copy and the data can only say one thing, they
cannot disagree.
"""
from app.services import ingest_basis


def test_short_base_is_a_clause_that_can_be_dropped_into_a_sentence():
    # It has to READ as prose ("In what Atlas ingests, Timor-Leste ran ..."),
    # not as a parenthetical disclaimer bolted to the end.
    assert ingest_basis.IN_INGEST == "In what Atlas ingests"
    assert not ingest_basis.IN_INGEST.endswith(".")


def test_the_named_population_says_feeds_AND_the_firehose():
    # Naming only the curated feeds would understate the base by ~4 orders of
    # magnitude; naming only GDELT would hide the hand-built domestic lane.
    named = ingest_basis.POPULATION.lower()
    assert "feeds" in named
    assert "gdelt" in named


def test_the_note_refuses_the_world_claim_in_words():
    # The exact inference the panel made ("nobody covered it") must be denied
    # explicitly, not merely left unstated.
    note = ingest_basis.NOTE.lower()
    assert "not that nobody did" in note
    assert "atlas" in note


def test_absence_line_names_the_country_and_refuses_silence():
    line = ingest_basis.absence_caveat("Colombia")
    assert "Colombia" in line
    # The refutation, in the copy itself: a zero is a gap in the feed set.
    assert "not proof" in line.lower()
    assert "silent" in line.lower()


def test_share_line_refuses_the_world_denominator():
    line = ingest_basis.share_caveat()
    assert "not of everything published" in line.lower()


def test_basis_field_is_a_serialisable_dict_for_payload_meta():
    field = ingest_basis.basis_field()
    assert field["population"] == ingest_basis.POPULATION
    assert field["note"] == ingest_basis.NOTE
    # A machine-readable handle so a consumer can branch without string-matching.
    assert field["measured_over"] == "atlas_ingest"
