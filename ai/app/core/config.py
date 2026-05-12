from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import ConfigurationError


def _env_str(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _env_int(name: str, default: int) -> int:
    value = _env_str(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer.") from error


def _env_float(name: str, default: float) -> float:
    value = _env_str(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a number.") from error


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the AI service.

    Keep environment access here so pipeline modules can depend on a typed
    settings object instead of calling os.getenv throughout the codebase.
    """

    repo_root: Path
    ai_host: str = "0.0.0.0"
    ai_port: int = 8000

    stt_provider: str = "whisper"
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2
    llm_temperature: float = 0.0

    temp_dir: Path | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        repo_root = Path(__file__).resolve().parents[3]
        temp_dir = _env_str("AI_TEMP_DIR")

        settings = cls(
            repo_root=repo_root,
            ai_host=_env_str("AI_HOST", "0.0.0.0") or "0.0.0.0",
            ai_port=_env_int("AI_PORT", 8000),
            stt_provider=(_env_str("STT_PROVIDER", "whisper") or "whisper").lower(),
            whisper_model=_env_str("WHISPER_MODEL", "base") or "base",
            whisper_device=_env_str("WHISPER_DEVICE", "cpu") or "cpu",
            whisper_compute_type=_env_str("WHISPER_COMPUTE_TYPE", "int8") or "int8",
            llm_provider=(_env_str("LLM_PROVIDER", "openai") or "openai").lower(),
            openai_api_key=_env_str("OPENAI_API_KEY"),
            openai_model=_env_str("OPENAI_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini",
            openai_base_url=_env_str("OPENAI_BASE_URL", "https://api.openai.com/v1")
            or "https://api.openai.com/v1",
            llm_timeout_seconds=_env_int("LLM_TIMEOUT_SECONDS", 60),
            llm_max_retries=_env_int("LLM_MAX_RETRIES", 2),
            llm_temperature=_env_float("LLM_TEMPERATURE", 0.0),
            temp_dir=Path(temp_dir).expanduser().resolve() if temp_dir else None,
        )
        settings.validate()
        return settings

    @property
    def shared_schema_dir(self) -> Path:
        return self.repo_root / "shared" / "schemas"

    def shared_schema_path(self, filename: str) -> Path:
        return self.shared_schema_dir / filename

    def validate(self) -> None:
        if self.stt_provider not in {"whisper", "whisperx", "faster_whisper"}:
            raise ConfigurationError(
                "STT_PROVIDER must be one of: whisper, whisperx, faster_whisper."
            )

        if self.llm_provider != "openai":
            raise ConfigurationError("LLM_PROVIDER currently supports only openai.")

        if self.ai_port <= 0 or self.ai_port > 65535:
            raise ConfigurationError("AI_PORT must be between 1 and 65535.")

        if self.llm_timeout_seconds <= 0:
            raise ConfigurationError("LLM_TIMEOUT_SECONDS must be greater than 0.")

        if self.llm_max_retries < 0:
            raise ConfigurationError("LLM_MAX_RETRIES must be greater than or equal to 0.")


settings = Settings.from_env()
