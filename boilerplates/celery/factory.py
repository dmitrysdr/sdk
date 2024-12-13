from typing import Sequence

from celery import signals

from .context import AsyncTask, GenericWorkerContext, _TaskRegistry
from .types import SettingsT


def run_worker(
    context: GenericWorkerContext[SettingsT],
    tasks: list[type[AsyncTask]],
    concurrency: int = 1,
    disable_log_config: bool = True,
    autoretry_for_exc_types: Sequence[type[Exception]] | None = None,
) -> None:
    if disable_log_config:
        signals.setup_logging.connect(_disable_default_logger)

    signals.worker_init.connect(context._on_startup)
    signals.worker_shutdown.connect(context._on_shutdown)

    registry = _TaskRegistry(context)
    for task_cls in tasks:
        if (task_config := context.config.tasks.get(task_cls.name)) is None:
            raise ValueError(f"Task {task_cls.name} is not configured (settings section is missing)")

        registry.register_task_class(task_cls, task_config, autoretry_for_exc_types)

    context.celery.worker_main(["--quiet", "worker", "-P", "solo", f"--concurrency={concurrency}", "-E", "--beat"])


def _disable_default_logger(*args, **kwargs) -> None:
    """Disable default celery log config."""
    # https://docs.celeryq.dev/en/stable/userguide/signals.html#setup-logging
