import asyncio
from abc import ABC, abstractmethod
from functools import wraps
from logging import getLogger
from typing import Any, ClassVar, Generic, Sequence, TypeVar

from celery import Celery

from boilerplates.features import PYDANTIC_V2_SUPPORTED

from .config import TaskConfig
from .logger import get_task_logger
from .types import SettingsT


class GenericWorkerContext(ABC, Generic[SettingsT]):
    def __init__(self, logger: Any, config: SettingsT) -> None:
        self.config = config
        self.celery = Celery(
            config.app_name,
            broker=config.rabbitmq.dsn,
            broker_connection_retry_on_startup=True,
        )
        self.debug = config.debug
        self._logger = logger
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()

            except RuntimeError:
                self._loop = asyncio.new_event_loop()

        return self._loop

    @abstractmethod
    async def on_startup(self, *args, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    async def on_shutdown(self, *args, **kwargs) -> None:
        raise NotImplementedError

    def _on_startup(self, *args: Any, **kwargs: Any) -> None:
        self.loop.run_until_complete(self.on_startup(*args, **kwargs))
        self._logger.info("Startup complete")

    def _on_shutdown(self, *args: Any, **kwargs: Any) -> None:
        self.loop.run_until_complete(self.on_shutdown(*args, **kwargs))
        self._logger.info("Shutdown complete")


WorkerContextT = TypeVar("WorkerContextT", bound=GenericWorkerContext)


class AsyncTask(ABC, Generic[WorkerContextT]):
    name: ClassVar[str]

    def __init__(self, context: WorkerContextT) -> None:
        self.context = context
        self.logger = get_task_logger(self.name, debug=context.debug)

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        ...


class _TaskRegistry:
    def __init__(self, context: GenericWorkerContext[SettingsT]) -> None:
        self.context = context
        self.celery = context.celery
        self.config = context.config
        self.logger = getLogger("task_registry")

    def _get_retry_settings(self, config: TaskConfig, autoretry_for_exc_types: Sequence[type[Exception]]) -> dict:
        # https://docs.celeryq.dev/en/stable/userguide/tasks.html
        # ?highlight=retry_backoff#automatic-retry-for-known-exceptions
        if not config.retry:
            return {}

        result = config.retry.model_dump() if PYDANTIC_V2_SUPPORTED else config.retry.dict()

        result["retry_jitter"] = False
        result["autoretry_for"] = list(autoretry_for_exc_types)

        return result

    def _update_schedule(self, name: str, config: TaskConfig) -> None:
        # https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html#entries  noqa
        if config.schedule:
            self.celery.conf.beat_schedule[name] = {
                "task": name,
                "schedule": config.schedule,
                "options": {"expires": self.config.default_task_expiration},
            }

    def register_task_class(
        self,
        task_class: type[AsyncTask],
        config: TaskConfig,
        autoretry_for_exc_types: Sequence[type[Exception]] | None = None,
    ) -> None:
        """Костыль для запуска корутин, заменяющий @celery.task."""
        if not autoretry_for_exc_types:
            # По умолчанию повторяем задачу при любом исключении
            autoretry_for_exc_types = (Exception,)

        self._update_schedule(task_class.name, config)
        task = task_class(self.context)

        @wraps(task.execute)
        def task_wrapper(*args, **kwargs) -> Any:
            coro = task.execute(*args, context=self, **kwargs)

            if config.time_limit and not self.config.debug:
                coro = asyncio.wait_for(coro, config.time_limit)

            return self.context.loop.run_until_complete(coro)

        task_factory = self.celery.task(
            name=task_class.name,
            **self._get_retry_settings(config, autoretry_for_exc_types),
        )

        task_factory(task_wrapper)

        if self.context.debug:
            self.logger.debug(f"Registered task {task.name} with schedule {config.schedule}")
