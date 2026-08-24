"""La regla monótona congelada del mini-prereg 2026-08-24 — cambiarla exige
cambiar estos tests a la vista."""

from scripts.court_bodies_monotone import monotone_applies


class TestMonotone:
    def test_hardening_transitions_apply(self):
        assert monotone_applies("partial", "failed") is True
        assert monotone_applies("partial", "too_broad") is True
        assert monotone_applies("failed", "too_broad") is True
        assert monotone_applies(None, "failed") is True
        assert monotone_applies(None, "too_broad") is True

    def test_softening_never_applies(self):
        assert monotone_applies("failed", "entailed") is False
        assert monotone_applies("failed", "partial") is False
        assert monotone_applies("partial", "entailed") is False
        assert monotone_applies("too_broad", "failed") is False
        assert monotone_applies(None, "entailed") is False
        assert monotone_applies(None, "partial") is False

    def test_confirm_is_noop(self):
        assert monotone_applies("failed", "failed") is False
        assert monotone_applies("partial", "partial") is False

    def test_entailed_current_never_touched(self):
        # entailed no entra a la población; si entrara, nada aplica
        assert monotone_applies("entailed", "failed") is False
        assert monotone_applies("entailed", "too_broad") is False

    def test_garbage_inputs(self):
        assert monotone_applies("weird", "failed") is True  # tratado como NULL
        assert monotone_applies("partial", None) is False
        assert monotone_applies("partial", "banana") is False
