from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_fixed_launcher_uses_history_repo_and_runtime_config():
    source = (ROOT / "scripts/start_fixed_release.ps1").read_text(encoding="utf-8")
    assert "LEARN2EARN_HISTORY_REPO" in source
    assert "LEARN2EARN_LLM_CONFIG_PATH" in source
    assert "LEARN2EARN_LOCAL_DEMO_EMAIL" in source
    assert "kunjunsong@gmail.com" in source


def test_runtime_config_and_local_identity_are_environment_overridable():
    config = (ROOT / "backend/app/services/llm_config.py").read_text(encoding="utf-8")
    auth = (ROOT / "backend/app/auth.py").read_text(encoding="utf-8")
    assert 'os.environ.get("LEARN2EARN_LLM_CONFIG_PATH")' in config
    assert 'os.environ.get("LEARN2EARN_LOCAL_DEMO_EMAIL"' in auth
