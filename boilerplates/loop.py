import asyncio
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Optional

from pydantic import BaseModel


class LoopLifecycleConfig(BaseModel):
    wait_between_iteration: timedelta
    wait_between_iteration_when_error: timedelta


class BaseLoop(ABC):
    def __init__(self, logger, loop_config: LoopLifecycleConfig):
        self._loop_config = loop_config
        self.logger = logger
        self._is_last_iter_succeeded = False
        self._is_current_iter_succeeded = False
        self._loop_task: Optional[asyncio.Task] = None

    async def start_loop(self):
        self._loop_task = asyncio.create_task(self._main_loop())

    async def stop_loop(self):
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                self.logger.debug(f"{self._loop_task!r} отменен")
            finally:
                self._loop_task = None

    async def health_check(self) -> bool:
        return self._is_last_iter_succeeded and bool(self._loop_task)

    async def callback_iteration_failed(self, exception: Exception) -> None:
        self._is_last_iter_succeeded = False

    async def _main_loop(self):
        self.logger.debug("Бесконечный цикл запущен")
        while True:
            try:
                self._is_current_iter_succeeded = True
                delay = self._loop_config.wait_between_iteration.total_seconds()
                await self._do_iteration()
                self.logger.debug(f"Итерация завершилась, до след. запуска {delay} сек.")

            except asyncio.CancelledError:
                break

            except Exception as exc:  # pylint: disable=broad-except
                self._is_current_iter_succeeded = False
                delay = self._loop_config.wait_between_iteration_when_error.total_seconds()
                self.logger.error(
                    f"Ошибка в цикле, перед повторным запуском добавим задержку {delay} сек. " f"{exc}",
                    exc_info=True,
                )
                await self.callback_iteration_failed(exc)

            self._is_last_iter_succeeded = self._is_current_iter_succeeded
            await asyncio.sleep(delay)

    @abstractmethod
    async def _do_iteration(self):
        """Implement"""
