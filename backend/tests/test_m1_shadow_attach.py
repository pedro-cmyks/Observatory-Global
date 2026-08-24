"""Tests de la lógica pura de la lane sombra M1 (m1_shadow_attach).

Los vetos son reglas CONGELADAS v0 — estos tests las fijan; cambiarlas
exige cambiar el test a la vista (no hay retoque silencioso por caso).
Cero DB, cero LLM.
"""

from collections import Counter

from scripts.m1_shadow_attach import (
    TAU_DF, binomial_ci, is_bucket_vague, label_persons, label_token_df,
    person_conflict)


def _df(labels: list[str]) -> Counter:
    return label_token_df(labels)


class TestBucketVague:
    def test_generic_label_is_vague(self):
        # "Crime and Tragedy": ambos tokens ubicuos en el pool → vago
        pool = ["Crime and Tragedy"] + [f"Crime Report {i} Tragedy" for i in range(TAU_DF)]
        df = _df(pool)
        assert is_bucket_vague("Crime and Tragedy", df) is True

    def test_specific_label_survives(self):
        # "Mushroom Murder Appeal": mushroom es raro en el pool → específico
        pool = ["Mushroom Murder Appeal"] + [f"Murder Case {i}" for i in range(TAU_DF)]
        df = _df(pool)
        assert is_bucket_vague("Mushroom Murder Appeal", df) is False

    def test_empty_or_tokenless_label_is_vague(self):
        df = _df(["Whatever Story"])
        assert is_bucket_vague("", df) is True
        assert is_bucket_vague(None, df) is True
        # solo genéricos del vocabulario congelado P-NUEVO (p.ej. 'news')
        assert is_bucket_vague("Breaking Coverage", df) is True

    def test_df_counts_once_per_label(self):
        # un token repetido DENTRO de un label cuenta una vez
        df = _df(["Tolima Tolima Tolima"])
        assert df["tolima"] == 1


class TestLabelPersons:
    def test_member_person_named_in_label(self):
        lp = label_persons("Journalist Shipacheva Sentenced",
                           {"maria shipacheva", "lev shlosberg"})
        assert lp == {"maria shipacheva"}

    def test_no_person_in_label(self):
        assert label_persons("Strait of Hormuz Tanker Incidents",
                            {"donald trump"}) == set()

    def test_two_token_name_needs_both(self):
        # "donald duck" no matchea un label que solo trae "donald"
        assert label_persons("Donald Announces Plan", {"donald duck"}) == set()


class TestPersonConflict:
    def test_label_person_disjoint_veto(self):
        assert person_conflict({"lev shlosberg"}, {"maria shipacheva"}, 0.85) is True

    def test_shared_person_no_veto(self):
        assert person_conflict({"donald trump", "a b"}, {"donald trump"}, 0.85) is False

    def test_no_label_person_no_veto(self):
        # v0.2: sin persona EN EL LABEL no hay veto (la v0.1 amplia vetaba
        # por personas de miembros y mató hogares correctos — 41/150)
        assert person_conflict({"x y"}, set(), 0.85) is False
        assert person_conflict(set(), {"x y"}, 0.85) is False

    def test_high_cos_exempt(self):
        assert person_conflict({"a"}, {"b"}, 0.95) is False


class TestBinomialCI:
    def test_zero_n(self):
        assert binomial_ci(0, 0) == (0.0, 0.0)

    def test_bounds_and_order(self):
        lo, hi = binomial_ci(12, 50)
        assert 0.0 <= lo < 12 / 50 < hi <= 1.0
