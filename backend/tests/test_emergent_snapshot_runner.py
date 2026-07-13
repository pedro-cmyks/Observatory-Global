"""Shape tests for the launchd-safe emergent snapshot runner."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "run-emergent-snapshot.sh"
INSTALLER = ROOT / "scripts" / "install-emergent-snapshot-launchd.sh"
PLIST = ROOT / "infra" / "launchd" / "com.atlas.emergent-snapshot.plist"
SCOPED_RUNNER = ROOT / "scripts" / "run-scoped-snapshot.sh"
SCOPED_WRITER = ROOT / "backend" / "scripts" / "run_scoped_snapshot.py"


def test_runner_uses_local_worker_env_by_default():
    source = RUNNER.read_text(encoding="utf-8")

    assert 'LOCAL_ENV="${ATLAS_LOCAL_ENV:-$ROOT_DIR/.env}"' in source
    assert "load_env_file \"$LOCAL_ENV\"" in source
    assert "ATLAS_ALLOW_DESKTOP_ENV" in source
    assert "DESKTOP_ENV=" not in source


def test_installer_writes_private_local_env_and_never_installs_desktop_env_path():
    source = INSTALLER.read_text(encoding="utf-8")

    assert 'TARGET_ENV="$WORKER_HOME/.env"' in source
    assert "chmod 600 \"$TARGET_ENV\"" in source
    assert "ATLAS_DESKTOP_ENV" not in source


def test_launchd_plist_points_at_worker_runner():
    source = PLIST.read_text(encoding="utf-8")

    assert "<string>com.atlas.emergent-snapshot</string>" in source
    assert "<string>/Users/pedro/AtlasLocalWorker/run-emergent-snapshot.sh</string>" in source
    assert "<string>/Users/pedro/AtlasLocalWorker</string>" in source


def test_scoped_snapshot_is_staged_and_committed_only_after_complete_country_pass():
    source = SCOPED_WRITER.read_text(encoding="utf-8")

    assert "prepared_rows.extend(_prepare_snapshot_rows(" in source
    assert "await _insert_prepared_snapshot(" in source
    assert "if failed:" in source
    assert "incomplete country pass" in source
    assert "_write_snapshot(" not in source


def test_scoped_shell_stops_before_projection_when_snapshot_write_fails():
    source = SCOPED_RUNNER.read_text(encoding="utf-8")
    write_at = source.index("# Step 1:")
    project_at = source.index("scripts.project_dynamic_topics")
    block = source[write_at:project_at]

    assert "if !" in block
    assert "exit 1" in block
    assert "R1 write failed" in block


def test_production_scoped_snapshot_has_no_signal_or_cluster_top_ceiling():
    shell = SCOPED_RUNNER.read_text(encoding="utf-8")
    writer = SCOPED_WRITER.read_text(encoding="utf-8")

    assert 'TOP_PER_COUNTRY="${ATLAS_SCOPED_TOP_PER_COUNTRY:-0}"' in shell
    assert 'PER_COUNTRY_CAP="${ATLAS_SCOPED_CAP:-0}"' in shell
    assert 'default=0' in writer
    assert "clusters = gated if top_n <= 0 else gated[:top_n]" in writer
