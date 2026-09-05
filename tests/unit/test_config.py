"""Unit tests for configuration loading and validation."""

import pytest
from normanjr.config import AppConfig, load_config


def test_load_default_config():
    config = load_config()
    assert config.model.requested_model == "google/gemini-2.5-flash"
    assert config.safety.allow_final_submit is False
    assert config.exploration.max_journeys == 3
    assert config.exploration.max_steps_per_journey == 20


def test_config_overrides():
    config = load_config(overrides={"model.requested_model": "test-model", "exploration.max_journeys": 5})
    assert config.model.requested_model == "test-model"
    assert config.exploration.max_journeys == 5


def test_config_incompatible_storage_state():
    with pytest.raises(ValueError, match="storage_state_path is specified"):
        AppConfig(
            browser={"storage_state_path": "path/to/state.json"},
            safety={"allow_authentication": False},
        )


def test_config_incompatible_final_submit():
    with pytest.raises(ValueError, match="allow_final_submit is True"):
        AppConfig(
            safety={"allow_final_submit": True},
            exploration={"allowed_origins": []},
        )


def test_redacted_dict():
    config = AppConfig(OPENROUTER_API_KEY="sk-secret12345678901234567890")
    redacted = config.redacted_dict()
    assert redacted["OPENROUTER_API_KEY"] == "REDACTED"


def test_config_env_model_override(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    config = load_config(load_env=False)
    assert config.model.requested_model == "anthropic/claude-3.5-sonnet"


def test_config_cli_overrides_env_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    config = load_config(overrides={"model.requested_model": "custom-override-model"}, load_env=False)
    assert config.model.requested_model == "custom-override-model"

