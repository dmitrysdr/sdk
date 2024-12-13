import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import timedelta
from typing import Any, Generic, TypeVar

Context = TypeVar("Context")


class RepeatedTask:
    """
    Может использоваться как асинхронный итератор
    или как асинхронный контекстный менеджер (для выполнения в фоне).
    Задача выполнится не чаще, чем раз в interval.
    Время выполнения задачи засчитывается как часть interval.
    """

    def __init__(
        self,
        interval: timedelta,
        coro: Callable[[], Awaitable[None]],
        logger: Any,
    ) -> None:
        self._interval = interval.total_seconds()
        self._coro = coro
        self._task: asyncio.Task | None = None
        self._logger = logger

    async def __anext__(self) -> None:
        await asyncio.gather(asyncio.sleep(self._interval), self._coro())

    def __aiter__(self) -> "RepeatedTask":
        return self

    async def _run(self) -> None:
        async for _ in self:
            self._logger.debug("Iteration completed")

    async def __aenter__(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._task:
            self._task.cancel()
            self._task = None

    @property
    def task(self) -> asyncio.Task | None:
        return self._task


class BaseTask(Generic[Context]):
    """
    Альтернатива классу boilerplates.celery.AsyncTask.
    name и execute работают аналогично.
    Запуск с контролем времени выполнения, перехватом исключений - run().
    Бизнес-логика - в execute().
    """

    name: str

    def __init__(self, context: Context, logger: Any) -> None:
        self.context = context
        self.logger = logger

    async def execute(self, *args, **kwargs) -> None:
        raise NotImplementedError()

    def get_max_duration(self) -> float | None:
        raise NotImplementedError()

    async def run(self, **kwargs) -> None:
        try:
            await asyncio.wait_for(self.execute(**kwargs), self.get_max_duration())
        except Exception as exc:
            self.logger.exception("Failed to execute task", exc_info=exc)

    def at_schedule(self, interval: timedelta) -> RepeatedTask:
        return RepeatedTask(interval=interval, coro=self.run, logger=self.logger)


class Scheduler:
    """
    Запускает задачи по расписанию.
    Также даёт возможность дёрнуть задачу по её имени через call().
    Вызов use() предназначен для лайфспана приложения.
    Перед вызовом use все задачи должны быть добавлены через register().
    Если кроме фоновых задач в приложении ничего нет,
    можно воспользоваться методом wait() в качестве основного.
    """

    def __init__(self, logger: Any) -> None:
        self.tasks: dict[str, BaseTask] = {}
        self.logger = logger
        self.wait_list: list[asyncio.Task] = []

    def register(self, task: BaseTask) -> None:
        self.tasks[task.name] = task

    def _get_task(self, task_name: str) -> BaseTask | None:
        if task := self.tasks.get(task_name):
            return task

        msg = f"Unknown task: {task_name}"
        self.logger.error(msg)
        return None

    async def call(self, task_name: str, **kwargs) -> None:
        if task := self._get_task(task_name):
            await task.run(**kwargs)

    @asynccontextmanager
    async def use(self, schedule: dict[str, timedelta]) -> AsyncGenerator["Scheduler", None]:
        async with AsyncExitStack() as stack:
            for task_name, interval in schedule.items():
                if task := self._get_task(task_name):
                    repeated_task = task.at_schedule(interval)
                    await stack.enter_async_context(repeated_task)
                    if aio_task := repeated_task.task:
                        self.wait_list.append(aio_task)

            yield self

    async def wait(self) -> None:
        await asyncio.wait(self.wait_list)
