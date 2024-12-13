from typing import Any, Type

from structlog.stdlib import ProcessorFormatter

from .setup import ChainBuilder, LogFormat
from .types import LogLevel


def generate_uvicorn_log_config(
    log_level: LogLevel,
    formatter: Type[ProcessorFormatter],
    log_format: LogFormat,
    is_sentry_enabled: bool,
) -> dict[str, Any]:
    formatter_cfg = {
        "()": formatter,
        "log_format": log_format,
        "foreign_chain": ChainBuilder.create_default_preset(is_sentry_enabled).build(),
    }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": formatter_cfg,
            "access": formatter_cfg,
            "error": formatter_cfg,
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {
                "level": log_level,
                "handlers": ["stdout"],
                "propagate": False,
            },
        },
    }
