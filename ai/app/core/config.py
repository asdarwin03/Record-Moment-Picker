from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import ConfigurationError


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_dotenv() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv
    except ImportError as error:
        raise ConfigurationError(
            "python-dotenv is required to load .env. "
            "Run `.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt`."
        ) from error

    load_dotenv(env_path, override=True)


_load_dotenv()


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


def _env_bool(name: str, default: bool) -> bool:
    value = _env_str(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ConfigurationError(f"{name} must be a boolean.")


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the AI service.

    Keep environment access here so pipeline modules can depend on a typed
    settings object instead of calling os.getenv throughout the codebase.
    """

    repo_root: Path
    ai_host: str = "0.0.0.0"
    ai_port: int = 8000
    ai_pipeline_mode: str = "demo"

    stt_provider: str = "whisper"
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_cpu_threads: int = 2
    max_audio_upload_bytes: int = 25 * 1024 * 1024

    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2
    llm_temperature: float = 0.0
    llm_strict_json_schema: bool = True
    llm_refine_max_output_tokens: int = 4096
    llm_segment_chunk_seconds: int = 300
    llm_segment_max_output_tokens: int = 32768
    llm_merge_max_output_tokens: int = 8192
    llm_reasoning_max_output_tokens: int = 8192

    temp_dir: Path | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        temp_dir = _env_str("AI_TEMP_DIR")

        settings = cls(
            repo_root=REPO_ROOT,
            ai_host=_env_str("AI_HOST", "0.0.0.0") or "0.0.0.0",
            ai_port=_env_int("AI_PORT", 8000),
            ai_pipeline_mode=(_env_str("AI_PIPELINE_MODE", "demo") or "demo").lower(),
            stt_provider=(_env_str("STT_PROVIDER", "whisper") or "whisper").lower(),
            whisper_model=_env_str("WHISPER_MODEL", "base") or "base",
            whisper_device=_env_str("WHISPER_DEVICE", "cpu") or "cpu",
            whisper_compute_type=_env_str("WHISPER_COMPUTE_TYPE", "int8") or "int8",
            whisper_cpu_threads=_env_int("WHISPER_CPU_THREADS", 2),
            max_audio_upload_bytes=_env_int("AI_MAX_AUDIO_UPLOAD_BYTES", 25 * 1024 * 1024),
            llm_provider=(_env_str("LLM_PROVIDER", "openai") or "openai").lower(),
            openai_api_key=_env_str("OPENAI_API_KEY"),
            openai_model=_env_str("OPENAI_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini",
            openai_base_url=_env_str("OPENAI_BASE_URL", "https://api.openai.com/v1")
            or "https://api.openai.com/v1",
            llm_timeout_seconds=_env_int("LLM_TIMEOUT_SECONDS", 60),
            llm_max_retries=_env_int("LLM_MAX_RETRIES", 2),
            llm_temperature=_env_float("LLM_TEMPERATURE", 0.0),
            llm_strict_json_schema=_env_bool("LLM_STRICT_JSON_SCHEMA", True),
            llm_refine_max_output_tokens=_env_int("LLM_REFINE_MAX_OUTPUT_TOKENS", 4096),
            llm_segment_chunk_seconds=_env_int("LLM_SEGMENT_CHUNK_SECONDS", 300),
            llm_segment_max_output_tokens=_env_int("LLM_SEGMENT_MAX_OUTPUT_TOKENS", 32768),
            llm_merge_max_output_tokens=_env_int("LLM_MERGE_MAX_OUTPUT_TOKENS", 8192),
            llm_reasoning_max_output_tokens=_env_int("LLM_REASONING_MAX_OUTPUT_TOKENS", 8192),
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

        if self.ai_pipeline_mode not in {"demo", "full"}:
            raise ConfigurationError("AI_PIPELINE_MODE must be either demo or full.")

        if self.llm_timeout_seconds <= 0:
            raise ConfigurationError("LLM_TIMEOUT_SECONDS must be greater than 0.")

        if self.llm_max_retries < 0:
            raise ConfigurationError("LLM_MAX_RETRIES must be greater than or equal to 0.")

        if self.llm_refine_max_output_tokens <= 0:
            raise ConfigurationError("LLM_REFINE_MAX_OUTPUT_TOKENS must be greater than 0.")

        if self.llm_segment_chunk_seconds <= 0:
            raise ConfigurationError("LLM_SEGMENT_CHUNK_SECONDS must be greater than 0.")

        if self.llm_segment_max_output_tokens <= 0:
            raise ConfigurationError("LLM_SEGMENT_MAX_OUTPUT_TOKENS must be greater than 0.")

        if self.llm_merge_max_output_tokens <= 0:
            raise ConfigurationError("LLM_MERGE_MAX_OUTPUT_TOKENS must be greater than 0.")

        if self.llm_reasoning_max_output_tokens <= 0:
            raise ConfigurationError("LLM_REASONING_MAX_OUTPUT_TOKENS must be greater than 0.")

        if self.whisper_cpu_threads <= 0:
            raise ConfigurationError("WHISPER_CPU_THREADS must be greater than 0.")

        if self.max_audio_upload_bytes <= 0:
            raise ConfigurationError("AI_MAX_AUDIO_UPLOAD_BYTES must be greater than 0.")

def _apply_process_limits(runtime_settings: Settings) -> None:
    thread_count = str(runtime_settings.whisper_cpu_threads)
    os.environ.setdefault("OMP_NUM_THREADS", thread_count)
    os.environ.setdefault("MKL_NUM_THREADS", thread_count)
    os.environ.setdefault("OPENBLAS_NUM_THREADS", thread_count)
    os.environ.setdefault("NUMEXPR_NUM_THREADS", thread_count)


settings = Settings.from_env()
_apply_process_limits(settings)
