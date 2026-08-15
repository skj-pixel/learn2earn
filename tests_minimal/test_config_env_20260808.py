"""Regression checks for LLM environment variable discovery."""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def test_env_import_meta_contains_common_variables(monkeypatch):
    from app.routers import config

    monkeypatch.setattr(config, "is_local_demo_mode", lambda: True)
    result = config.env_import_meta(user={"id": "local:test"})

    assert "LEARN2EARN_LLM_API_KEY" in result["env_vars"]
    assert "OPENAI_API_KEY" in result["env_vars"]
    assert "ANTHROPIC_API_KEY" in result["env_vars"]
    assert "DOUBAO_CLOUD_API" in result["env_vars"]
