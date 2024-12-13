from typing import Any

from celery.utils.log import get_task_logger as celery_get_task_logger

from boilerplates.features import STRUCTLOG_SUPPORTED


def get_task_logger(name: str, debug: bool) -> Any:
    logger = celery_get_task_logger(name)
    logger.setLevel("DEBUG" if debug else "INFO")

    if STRUCTLOG_SUPPORTED:
        import structlog

        logger = structlog.wrap_logger(logger)

    return logger
