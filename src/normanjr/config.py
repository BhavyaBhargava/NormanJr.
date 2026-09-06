"""Hierarchical configuration management for NormanJr."""

from __future__ import annotations

import os
import tomllib
import dotenv
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelSettings(BaseModel):
    requested_model: str = "google/gemini-2.5-flash"
    allow_free_router: bool = True
    require_vision: bool = False
    require_structured_output: bool = True
    request_timeout_seconds: float = 60.0
    max_retries: int = 2
    max_calls: int = 40
    max_input_tokens: int = 64000
    max_output_tokens: int = 4096
    max_cost_usd: float = 2.0


class BrowserSettings(BaseModel):
    browser_name: str = "chromium"
    headless: bool = True
    isolated: bool = True
    viewport_width: int = 1280
    viewport_height: int = 800
    action_timeout_ms: int = 10000
    navigation_timeout_ms: int = 30000
    settle_timeout_ms: int = 1500
    output_max_bytes: int = 52428800
    storage_state_path: str | None = None
    save_storage_state_path: str | None = None
    profile: str = "desktop"
    has_touch: bool = False
    is_mobile: bool = False
    device_scale_factor: float = 1.0
    user_agent: str | None = None
    stealth: bool = False

    def apply_profile(self, profile: str) -> None:
        """Apply mobile or desktop viewport and user agent presets."""
        self.profile = profile.lower()
        if self.profile in ("mobile", "mobile-safari", "iphone"):
            self.viewport_width = 390
            self.viewport_height = 844
            self.has_touch = True
            self.is_mobile = True
            self.device_scale_factor = 3.0
            self.user_agent = (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
                "WebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
            )
        elif self.profile == "desktop":
            self.viewport_width = 1280
            self.viewport_height = 800
            self.has_touch = False
            self.is_mobile = False
            self.device_scale_factor = 1.0
            self.user_agent = None


class ExplorationSettings(BaseModel):
    max_journeys: int = 3
    max_steps_per_journey: int = 20
    max_unique_states: int = 60
    max_pages: int = 25
    max_duration_seconds: int = 1800
    max_repeated_state_visits: int = 3
    same_origin_only: bool = True
    allowed_origins: list[str] = Field(default_factory=list)
    denied_url_patterns: list[str] = Field(default_factory=list)


class SafetySettings(BaseModel):
    allow_final_submit: bool = False
    allow_download: bool = False
    allow_upload: bool = False
    allow_external_navigation: bool = False
    allow_authentication: bool = False
    allow_destructive_actions: bool = False
    stop_on_captcha: bool = True
    redact_form_values: bool = True
    allow_private_target: bool = False


class ReportSettings(BaseModel):
    output_directory: str = "runs"
    include_full_snapshots: bool = False
    include_console_errors: bool = True
    include_network_urls: bool = True
    screenshot_quality: int = 85
    retain_days: int = 30


class ScoringSettings(BaseModel):
    rubric_path: str = "config/rubrics/ux-rubric-v1.yaml"
    rubric_version: str = "1.0.0"
    score_probable_findings: bool = False


class AppConfig(BaseSettings):
    """Main application configuration containing all subsystem settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        env_nested_delimiter="__",
        extra="ignore",
    )

    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_model: str | None = Field(default=None, alias="OPENROUTER_MODEL")
    openrouter_http_referer: str | None = Field(
        default="https://github.com/normanjr/normanjr", alias="OPENROUTER_HTTP_REFERER"
    )
    openrouter_title: str | None = Field(
        default="NormanJr UX Auditor", alias="OPENROUTER_TITLE"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model: ModelSettings = Field(default_factory=ModelSettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    exploration: ExplorationSettings = Field(default_factory=ExplorationSettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)
    report: ReportSettings = Field(default_factory=ReportSettings)
    scoring: ScoringSettings = Field(default_factory=ScoringSettings)

    @model_validator(mode="after")
    def validate_incompatible_options(self) -> AppConfig:
        if self.openrouter_model and not self.model.requested_model:
            self.model.requested_model = self.openrouter_model
        if self.browser.storage_state_path and not self.safety.allow_authentication:
            raise ValueError(
                "storage_state_path is specified, but safety.allow_authentication is False."
            )
        if self.safety.allow_final_submit and not self.exploration.allowed_origins:
            raise ValueError(
                "safety.allow_final_submit is True, but no exploration.allowed_origins are configured."
            )
        if self.exploration.max_journeys <= 0:
            raise ValueError("exploration.max_journeys must be greater than 0.")
        if self.exploration.max_steps_per_journey <= 0:
            raise ValueError("exploration.max_steps_per_journey must be greater than 0.")
        return self

    def redacted_dict(self) -> dict[str, Any]:
        """Return a safe dictionary representation with secrets redacted."""
        data = self.model_dump(by_alias=True)
        if data.get("OPENROUTER_API_KEY"):
            data["OPENROUTER_API_KEY"] = "REDACTED"
        return data


def load_config(
    toml_path: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
    load_env: bool = True,
    env_path: str | Path | None = None,
) -> AppConfig:
    """Load configuration from TOML file, environment variables (.env), and explicit overrides."""
    if load_env:
        target_env = Path(env_path) if env_path else Path(".env")
        if target_env.exists():
            dotenv.load_dotenv(dotenv_path=target_env, override=False)
        else:
            dotenv.load_dotenv(override=False)

    toml_data: dict[str, Any] = {}

    default_toml = Path("config/default.toml")
    if toml_path:
        target_path = Path(toml_path)
        if target_path.exists():
            with open(target_path, "rb") as f:
                toml_data = tomllib.load(f)
        else:
            raise FileNotFoundError(f"Configuration file not found: {toml_path}")
    elif default_toml.exists():
        with open(default_toml, "rb") as f:
            toml_data = tomllib.load(f)

    # Allow environment variables (from .env or shell) to override default TOML
    env_model = (
        os.environ.get("OPENROUTER_MODEL")
        or os.environ.get("NORMANJR_MODEL")
        or os.environ.get("MODEL")
    )
    if env_model:
        toml_data.setdefault("model", {})["requested_model"] = env_model

    env_api_key = os.environ.get("OPENROUTER_API_KEY")
    if env_api_key:
        toml_data["openrouter_api_key"] = env_api_key

    # Explicit programmatic / CLI overrides take highest precedence
    if overrides:
        for key, value in overrides.items():
            if value is not None:
                parts = key.split(".")
                curr = toml_data
                for part in parts[:-1]:
                    curr = curr.setdefault(part, {})
                curr[parts[-1]] = value

    return AppConfig(**toml_data)

