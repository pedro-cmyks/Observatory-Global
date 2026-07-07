"""Facet typer + canonical-stem tests for constellation assembly (2026-07-06)."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "assemble_constellation",
    Path(__file__).resolve().parent.parent / "scripts" / "assemble_constellation.py",
)
ac = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ac)


def test_facet_of_disaster_angles():
    assert ac.facet_of("Venezuela Earthquake Death Toll") == "death-toll"
    assert ac.facet_of("Venezuela Earthquakes Kill 32") == "death-toll"
    assert ac.facet_of("Venezuela Earthquake Casualties") == "death-toll"
    # nationality-scoped victims win over the generic death-toll match
    assert ac.facet_of("Italian Victims in Venezuela Earthquake") == "foreign-victims"
    assert ac.facet_of("Spanish Deaths in Venezuela Earthquakes") == "foreign-victims"
    assert ac.facet_of("Portuguese Repatriation from Venezuela") == "foreign-victims"
    assert ac.facet_of("Venezuela Earthquake Rescues") == "rescues"
    assert ac.facet_of("Venezuela Earthquake Aftermath") == "aftermath"
    assert ac.facet_of("Earthquake Aid Venezuela") == "international-aid"
    assert ac.facet_of("ONU Estima Afectados Terremotos Venezuela") == "international-aid"
    # generic event word alone → core (not death-toll): keeps facets discriminating
    assert ac.facet_of("Double Séisme Venezuela") == "core"
    assert ac.facet_of("Venezuela Earthquake") == "core"


def test_canonical_stem_strips_facet_pollution():
    labels = [
        "Venezuela Earthquake Death Toll", "Venezuela Earthquake Rescues",
        "Venezuela Earthquake Aftermath", "Italian Victims in Venezuela Earthquake",
    ]
    stem = ac.canonical_stem(labels, "Italian Victims in Venezuela Earthquake")
    assert stem == "Venezuela Earthquake"


def test_generic_event_words_excluded_from_facet():
    # a pure hazard word must not, by itself, type as an impact facet
    for w in ("earthquake", "terremoto", "flood", "storm"):
        assert ac.facet_of(w) == "core"
