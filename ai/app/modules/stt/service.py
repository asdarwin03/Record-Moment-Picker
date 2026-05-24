from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable

from app.core.config import settings
from app.core.exceptions import STTProcessingError
from app.schemas.stt import validate_stt_output
from app.modules.stt.providers import faster_whisper, openai_stt, whisper, whisperx


ProviderTranscribe = Callable[[str | Path], list[dict]]


@dataclass(frozen=True)
class ChunkingOptions:
    enabled: bool = True
    chunk_seconds: float = 600.0
    overlap_seconds: float = 8.0
    min_duration_seconds: float = 660.0
    command_timeout_seconds: int = 120


class _ChunkingError(Exception):
    pass


_PROVIDER_MAP: dict[str, ProviderTranscribe] = {
    "whisper": whisper.transcribe,
    "whisperx": whisperx.transcribe,
    "faster_whisper": faster_whisper.transcribe,
    "faster-whisper": faster_whisper.transcribe,
    "openai_stt": openai_stt.transcribe,
    "openai-stt": openai_stt.transcribe,
}


def transcribe_audio(audio_path: str | Path) -> list[dict]:
    """
    Input:
    audio file path

    Output:
    [
      {
        "start_time": 41,
        "end_time": 56,
        "text": "안냥하세요, RecordMomentPicker 발표를 시작하겠습니다."
      }
    ]
    """
    provider_name = settings.stt_provider
    transcribe = _get_provider(provider_name)

    try:
        stt_output = _transcribe_with_optional_chunking(audio_path, transcribe)
        validated_output = validate_stt_output(stt_output)
        return [item.model_dump() for item in validated_output]
    except STTProcessingError:
        raise
    except Exception as error:
        raise STTProcessingError(f"STT processing failed with provider '{provider_name}': {error}") from error


def _get_provider(provider_name: str) -> ProviderTranscribe:
    normalized_name = provider_name.strip().lower()

    if normalized_name not in _PROVIDER_MAP:
        available = ", ".join(sorted(_PROVIDER_MAP))
        raise STTProcessingError(
            f"Unsupported STT provider: {provider_name}. Available providers: {available}"
        )

    return _PROVIDER_MAP[normalized_name]


def _transcribe_with_optional_chunking(
    audio_path: str | Path,
    transcribe: ProviderTranscribe,
) -> list[dict]:
    path = _validate_audio_path(audio_path)
    options = _chunking_options_from_env()

    if not options.enabled:
        return transcribe(path)

    duration_seconds = _get_audio_duration_seconds(path, options.command_timeout_seconds)
    if duration_seconds is None or duration_seconds < options.min_duration_seconds:
        return transcribe(path)

    try:
        return _transcribe_audio_chunks(path, duration_seconds, transcribe, options)
    except _ChunkingError:
        return transcribe(path)


def _transcribe_audio_chunks(
    audio_path: Path,
    duration_seconds: float,
    transcribe: ProviderTranscribe,
    options: ChunkingOptions,
) -> list[dict]:
    chunk_items: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="record_moment_stt_chunks_") as temp_dir:
        temp_path = Path(temp_dir)

        for index, (start_time, chunk_duration) in enumerate(
            _iter_chunk_ranges(duration_seconds, options.chunk_seconds, options.overlap_seconds)
        ):
            chunk_path = temp_path / f"chunk_{index:04d}.wav"
            _write_audio_chunk(
                audio_path,
                chunk_path,
                start_time,
                chunk_duration,
                options.command_timeout_seconds,
            )

            chunk_result = transcribe(chunk_path)
            chunk_items.extend(_offset_chunk_result(chunk_result, start_time))

    return _deduplicate_chunk_items(chunk_items)


def _iter_chunk_ranges(
    duration_seconds: float,
    chunk_seconds: float,
    overlap_seconds: float,
) -> list[tuple[float, float]]:
    overlap_seconds = max(0.0, min(overlap_seconds, chunk_seconds / 2))
    stride_seconds = max(1.0, chunk_seconds - overlap_seconds)
    ranges: list[tuple[float, float]] = []
    start_time = 0.0

    while start_time < duration_seconds:
        chunk_duration = min(chunk_seconds, duration_seconds - start_time)
        ranges.append((start_time, chunk_duration))

        if start_time + chunk_duration >= duration_seconds:
            break
        start_time += stride_seconds

    return ranges


def _write_audio_chunk(
    source_path: Path,
    chunk_path: Path,
    start_time: float,
    chunk_duration: float,
    timeout_seconds: int,
) -> None:
    command = [
        _env_str("FFMPEG_BINARY", "ffmpeg"),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{start_time:.3f}",
        "-t",
        f"{chunk_duration:.3f}",
        "-i",
        str(source_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(chunk_path),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise _ChunkingError(f"failed to create audio chunk: {error}") from error

    if completed.returncode != 0 or not chunk_path.exists():
        message = completed.stderr.strip() or "ffmpeg failed without stderr"
        raise _ChunkingError(f"failed to create audio chunk: {message}")


def _offset_chunk_result(chunk_result: list[dict], offset_seconds: float) -> list[dict]:
    offset_items: list[dict] = []

    for item in chunk_result:
        text = str(item.get("text", "")).strip()
        if not text:
            continue

        start_time = max(0.0, float(item.get("start_time", 0.0)) + offset_seconds)
        end_time = max(start_time, float(item.get("end_time", 0.0)) + offset_seconds)
        offset_items.append(
            {
                "start_time": start_time,
                "end_time": end_time,
                "text": text,
            }
        )

    return offset_items


def _deduplicate_chunk_items(items: list[dict]) -> list[dict]:
    deduplicated: list[dict] = []

    for item in sorted(items, key=lambda value: (value["start_time"], value["end_time"])):
        duplicate_index = _find_duplicate_index(deduplicated, item)
        if duplicate_index is None:
            deduplicated.append(item)
            continue

        existing = deduplicated[duplicate_index]
        if len(_normalize_for_duplicate_check(item["text"])) > len(
            _normalize_for_duplicate_check(existing["text"])
        ):
            deduplicated[duplicate_index] = {
                "start_time": existing["start_time"],
                "end_time": existing["end_time"],
                "text": item["text"],
            }

    return deduplicated


def _find_duplicate_index(items: list[dict], candidate: dict) -> int | None:
    for index in range(max(0, len(items) - 8), len(items)):
        if _is_duplicate_segment(items[index], candidate):
            return index
    return None


def _is_duplicate_segment(left: dict, right: dict) -> bool:
    left_text = _normalize_for_duplicate_check(left["text"])
    right_text = _normalize_for_duplicate_check(right["text"])
    if not left_text or not right_text:
        return False

    if not _timestamps_are_close(left, right):
        return False

    shorter_length = min(len(left_text), len(right_text))
    if shorter_length >= 12 and (left_text in right_text or right_text in left_text):
        return True

    return SequenceMatcher(None, left_text, right_text).ratio() >= 0.88


def _timestamps_are_close(left: dict, right: dict) -> bool:
    overlap = min(left["end_time"], right["end_time"]) - max(
        left["start_time"], right["start_time"]
    )
    shorter_duration = max(
        0.1,
        min(
            left["end_time"] - left["start_time"],
            right["end_time"] - right["start_time"],
        ),
    )

    if overlap >= shorter_duration * 0.5:
        return True

    return abs(left["start_time"] - right["start_time"]) <= 2.0


def _normalize_for_duplicate_check(text: str) -> str:
    return "".join(character.lower() for character in text if character.isalnum())


def _get_audio_duration_seconds(path: Path, timeout_seconds: int) -> float | None:
    command = [
        _env_str("FFPROBE_BINARY", "ffprobe"),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if completed.returncode != 0:
        return None

    try:
        return float(completed.stdout.strip())
    except ValueError:
        return None


def _chunking_options_from_env() -> ChunkingOptions:
    chunk_seconds = _env_float("STT_CHUNK_SECONDS", ChunkingOptions.chunk_seconds)
    overlap_seconds = _env_float("STT_CHUNK_OVERLAP_SECONDS", ChunkingOptions.overlap_seconds)
    min_duration_seconds = _env_float(
        "STT_CHUNK_MIN_DURATION_SECONDS",
        max(chunk_seconds + overlap_seconds, ChunkingOptions.min_duration_seconds),
    )

    return ChunkingOptions(
        enabled=_env_bool("STT_CHUNKING_ENABLED", True),
        chunk_seconds=max(30.0, chunk_seconds),
        overlap_seconds=max(0.0, overlap_seconds),
        min_duration_seconds=max(30.0, min_duration_seconds),
        command_timeout_seconds=max(
            10,
            _env_int("STT_CHUNK_COMMAND_TIMEOUT_SECONDS", ChunkingOptions.command_timeout_seconds),
        ),
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _validate_audio_path(audio_path: str | Path) -> Path:
    path = Path(audio_path)
    if not path.exists():
        raise STTProcessingError(f"Audio file not found: {path}")
    if not path.is_file():
        raise STTProcessingError(f"Audio path is not a file: {path}")
    return path
