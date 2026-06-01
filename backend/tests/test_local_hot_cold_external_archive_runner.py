"""Shape tests for the local hot/cold runner external archive defaults."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "run-local-hot-cold-catchup.sh"


def test_hot_cold_runner_defaults_archive_to_external_disk():
    source = RUNNER.read_text(encoding="utf-8")

    assert 'DEFAULT_ARCHIVE_ROOT="/Volumes/Ext/Atlas/Archive"' in source
    assert 'ARCHIVE_ROOT="${ATLAS_ARCHIVE_ROOT:-$DEFAULT_ARCHIVE_ROOT}"' in source
    assert 'OUTPUT_DIR="${ATLAS_PROCESSED_HISTORY_DIR:-/Volumes/Ext/Atlas/Processed}"' in source


def test_hot_cold_runner_refuses_missing_external_archive_mount():
    source = RUNNER.read_text(encoding="utf-8")

    assert 'if [[ "$ARCHIVE_ROOT" == /Volumes/* ]]; then' in source
    assert 'VOLUME_NAME="${ARCHIVE_ROOT#/Volumes/}"' in source
    assert 'VOLUME_ROOT="/Volumes/$VOLUME_NAME"' in source
    assert "external archive volume is not mounted" in source
