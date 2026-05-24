from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def test_migration_037_expands_armed_conflict_with_verified_multilingual_terms():
    migration = MIGRATIONS_DIR / "037_armed_conflict_multilingual_lex.sql"

    assert migration.exists()

    sql = migration.read_text(encoding="utf-8")
    assert "armed-conflict-escalation" in sql
    assert "Path A" in sql
    assert "Rejected" in sql
    assert "lex_pct" in sql

    for term in [
        "airstrike",
        "drone strike",
        "drone attack",
        "missile attack",
        "offensive campaign",
        "bombardeo",
        "enfrentamientos",
        "attaque armée",
        "frappe aérienne",
        "bombardement",
        "bewaffneter angriff",
        "hava saldırısı",
    ]:
        assert f"'{term}'" in sql

    assert "'clashes'" not in sql
    assert "'offensive'" not in sql
    assert "'shelling'" not in sql
    assert "'shots fired'" not in sql
    assert "'opening fire'" not in sql
    assert "'firing at'" not in sql
    assert "'ataque armado'" not in sql
    assert "'battlefield'" not in sql
    assert "WHERE slug='armed-conflict-escalation'" in sql


def test_migration_038_expands_remaining_low_lex_topics_with_precise_terms():
    migration = MIGRATIONS_DIR / "038_remaining_low_lex_multilingual_terms.sql"

    assert migration.exists()

    sql = migration.read_text(encoding="utf-8")
    assert "Path A" in sql
    assert "fuel-subsidy-unrest" in sql
    assert "food-price-stress" in sql
    assert "housing-cost-pressure" in sql
    assert "mining-royalty-risk" in sql

    for term in [
        "fuel subsidy",
        "gasoline price",
        "diesel price",
        "subsidio combustible",
        "precio gasolina",
        "food inflation",
        "food prices",
        "canasta basica",
        "precios alimentos",
        "housing crisis",
        "rent increase",
        "affordable housing",
        "crisis vivienda",
        "mining royalty",
        "copper royalty",
        "mining concession",
        "royalty minera",
    ]:
        assert f"'{term}'" in sql

    for term in [
        "fuel",
        "food",
        "rent",
        "mining",
        "royalty",
    ]:
        assert f"'{term}'" not in sql
