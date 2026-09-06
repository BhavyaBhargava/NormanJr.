"""Unit tests for configuration loading and validation."""

import pytest
from normanjr.config import AppConfig, load_config


def test_load_default_config(monkeypatch):
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    config = load_config(load_env=False)
    assert config.model.requested_model == "google/gemini-2.5-flash"
    assert config.safety.allow_final_submit is False
    assert config.exploration.max_journeys == 3
    assert config.exploration.max_steps_per_journey == 20


def test_browser_profiles():
    config = load_config(load_env=False)
    config.browser.apply_profile("mobile")
    assert config.browser.viewport_width == 390
    assert config.browser.viewport_height == 844
    assert config.browser.has_touch is True
    assert config.browser.is_mobile is True

    config.browser.apply_profile("desktop")
    assert config.browser.viewport_width == 1280
    assert config.browser.viewport_height == 800
    assert config.browser.has_touch is False


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

