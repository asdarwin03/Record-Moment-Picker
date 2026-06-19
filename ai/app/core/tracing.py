from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator


LOGGER_NAME = "record_moment.ai"

_request_id: ContextVar[str | None] = ContextVar("ai_request_id", default=None)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    logging.getLogger(LOGGER_NAME).setLevel(logging.INFO)


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


@contextmanager
def request_context(request_id: str) -> Iterator[None]:
    token = _request_id.set(request_id)
    try:
        yield
    finally:
        _request_id.reset(token)


@contextmanager
def track_stage(stage: str, **fields: Any) -> Iterator[None]:
    start_time = time.perf_counter()
    log_event("stage_started", stage=stage, **fields)

    try:
        yield
    except Exception as error:
        log_event(
            "stage_failed",
            stage=stage,
            elapsed_seconds=_elapsed_seconds(start_time),
            error_type=error.__class__.__name__,
            error=str(error),
        )
        raise

    log_event(
        "stage_completed",
        stage=stage,
        elapsed_seconds=_elapsed_seconds(start_time),
    )


def log_event(event: str, **fields: Any) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.info(_format_log_line(event, fields))


def _format_log_line(event: str, fields: dict[str, Any]) -> str:
    request_id = _request_id.get() or "-"
    parts = [f"[AI][{request_id}]", f"event={event}"]

    for key, value in fields.items():
        if value is None:
            continue
        parts.append(f"{key}={_format_value(value)}")

    return " ".join(parts)


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"

    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    if not text:
        return '""'
    if any(character.isspace() for character in text):
        return repr(text)
    return text


def _elapsed_seconds(start_time: float) -> float:
    return time.perf_counter() - start_time
