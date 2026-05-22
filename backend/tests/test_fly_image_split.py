from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "Dockerfile"
FLY_TOML = ROOT / "fly.toml"
API_DEPLOY = ROOT / "scripts" / "deploy-fly-api.sh"
WORKER_DEPLOY = ROOT / "scripts" / "deploy-fly-nlp-worker.sh"


def test_dockerfile_defines_light_api_and_heavy_nlp_targets():
    source = DOCKERFILE.read_text(encoding="utf-8")
    api_section = source[source.index("FROM base AS api-runtime"):source.index("FROM base AS nlp-runtime")]
    nlp_section = source[source.index("FROM base AS nlp-runtime"):]

    assert "FROM python:3.11-slim AS base" in source
    assert "FROM base AS api-runtime" in source
    assert "FROM base AS nlp-runtime" in source
    assert "pip install --no-cache-dir torch" not in api_section
    assert "transformers" not in api_section
    assert 'CMD ["python", "-m", "enrichment.nlp_worker"]' in nlp_section
    assert "TRANSFORMERS_OFFLINE=1" in nlp_section


def test_fly_config_keeps_inline_nlp_off_for_light_api_image():
    source = FLY_TOML.read_text(encoding="utf-8")

    assert 'NLP_INLINE_ENABLED = "false"' in source
    assert 'app = "bash start.sh"' in source
    assert 'nlp_worker = "python -m enrichment.nlp_worker"' in source
    assert "api-runtime" in source
    assert "nlp-runtime" in source


def test_deploy_scripts_target_one_process_group_at_a_time():
    api = API_DEPLOY.read_text(encoding="utf-8")
    worker = WORKER_DEPLOY.read_text(encoding="utf-8")

    assert "--build-target api-runtime" in api
    assert "--process-groups app" in api
    assert "--build-target nlp-runtime" in worker
    assert "--process-groups nlp_worker" in worker
