from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "019_atlas_topic_intelligence.sql"
)


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_topic_intelligence_migration_exists():
    assert MIGRATION.exists()


def test_migration_creates_normalized_topic_tables():
    sql = _sql()
    assert "CREATE TABLE IF NOT EXISTS atlas_topics" in sql
    assert "CREATE TABLE IF NOT EXISTS signal_topic_assignments" in sql
    assert "CREATE TABLE IF NOT EXISTS topic_learning_examples" in sql
    assert "FOREIGN KEY (signal_id) REFERENCES signals_v2(id)" in sql
    assert "FOREIGN KEY (topic_id) REFERENCES atlas_topics(id)" in sql


def test_signal_assignments_preserve_method_and_confidence():
    sql = _sql()
    assert "method         TEXT NOT NULL" in sql
    assert "model_version  TEXT NOT NULL DEFAULT 'atlas-topic-v1'" in sql
    assert "signal_topic_assignments_confidence_range" in sql
    assert "CHECK (confidence >= 0.0 AND confidence <= 1.0)" in sql
    assert "PRIMARY KEY (signal_id, topic_id, method, model_version)" in sql


def test_learning_examples_support_feedback_loop():
    sql = _sql()
    assert "topic_learning_examples_decision_valid" in sql
    for decision in [
        "auto_accept",
        "auto_reject",
        "analyst_confirm",
        "analyst_reject",
        "analyst_correct",
        "threshold_review",
        "benchmark_label",
    ]:
        assert f"'{decision}'" in sql
    assert "corrected_topic_id" in sql
    assert "idx_topic_learning_examples_source_lang" in sql
    assert "idx_topic_learning_examples_model" in sql


def test_migration_seeds_enough_v1_topics():
    sql = _sql()
    # Count value tuples by slug literals in the seed block.
    seeded_slugs = [
        line.strip()
        for line in sql.splitlines()
        if line.strip().startswith("('") and "'," in line
    ]
    assert len(seeded_slugs) >= 25
    assert "fuel-subsidy-unrest" in sql
    assert "mining-royalty-risk" in sql
    assert "humanitarian-access-conflict" in sql
    assert "election-legitimacy-dispute" in sql
