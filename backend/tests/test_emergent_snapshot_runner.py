"""Shape tests for the launchd-safe emergent snapshot runner."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "run-emergent-snapshot.sh"
INSTALLER = ROOT / "scripts" / "install-emergent-snapshot-launchd.sh"
PLIST = ROOT / "infra" / "launchd" / "com.atlas.emergent-snapshot.plist"


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
