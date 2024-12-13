import asyncio
from typing import Any, Awaitable, Callable, Generic, cast

from aio_pika.abc import AbstractIncomingMessage, AbstractQueue, ConsumerTag
from aio_pika.robust_queue import RobustQueue, RobustQueueIterator

from boilerplates.rabbitmq.exceptions import AvoidRequeueError, MessageDecodeError, UseRequeueError
from boilerplates.types import T


class PatchedIterator(RobustQueueIterator):
    async def on_message(self, message: AbstractIncomingMessage) -> None:
        # Этот метод используется в качестве коллбэка в aiormq
        # https://github.com/mosquito/aiormq/blob/a1285d42dd564103a3a5b9dd8c201023c887b613/aiormq/channel.py#L285

        # При этом оригинальная реализация итератора:
        # https://github.com/mosquito/aio-pika/blob/eb5990e9919d0257088d268cd29bc49a1c7d4e87/aio_pika/queue.py#L482

        # Такое сочетание может создать гонку при заполнении очереди в памяти
        # Поэтому делаем on_message синхронным
        self._queue.put_nowait(message)


class QueueListener(Generic[T]):
    """
    Класс для обработки сообщений из очереди.

    Пример использования:
        ```python
        listener = QueueListener(
            queue=queue,
            logger=self._logger,
            handle_message_callback=partial(self._handle_message),
            message_decoder=self._decode_message,
        )
        await listener.start()
        ```
    """

    def __init__(
        self,
        queue: AbstractQueue,
        logger: Any,
        message_decoder: Callable[[AbstractIncomingMessage], Awaitable[T]],
        handle_message_callback: Callable[[T], Awaitable[None]],
        requeue_on_error: bool = False,
        requeue_on_invalid_message: bool = False,
        consume_async: bool = True,
    ) -> None:
        """Инициализация класса.

        Args:
            queue (AbstractQueue):
                очередь, из которой будут получаться сообщения
            logger (Any):
                логгер для записи логов
            message_decoder (Callable[[AbstractIncomingMessage], Awaitable[T]]):
                функция для декодирования сообщения. Если структура сообщения неверная, то
                должен выбрасывать исключение MessageDecodeError.
            handle_message_callback (Callable[[T], Awaitable[None]]):
                функция для обработки сообщения после декодирования
            requeue_on_error (bool, optional):
                отправлять ли сообщение обратно в очередь при ошибке обработки
            requeue_on_invalid_message (bool, optional):
                отправлять ли сообщение обратно в очередь при ошибке декодирования
            consume_async (bool, optional):
                читать ли сообщения из очереди асинхронно или по очереди
        """
        self._queue = queue
        self._handle_message_callback = handle_message_callback
        self._message_decoder = message_decoder
        self._logger = logger
        self._is_running = False
        self._requeue_on_error = requeue_on_error
        self._requeue_on_invalid_message = requeue_on_invalid_message
        self._consume_async = consume_async
        self.consumer_tag: ConsumerTag | None = None
        self.polling_task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> "QueueListener":
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.stop()

    async def start(self) -> None:
        if self._consume_async:
            self.consumer_tag = await self._queue.consume(callback=self._callback)
        else:
            self.polling_task = asyncio.create_task(self._polling_loop())

        self._is_running = True

    async def stop(self) -> None:
        if self._is_running:
            self._logger.debug("Остановка обработки очереди сообщений")

            if self.consumer_tag:
                await self._queue.cancel(self.consumer_tag)

            if self.polling_task:
                self.polling_task.cancel()
                await self.polling_task

            self._is_running = False
            self._logger.debug("Обработка очереди сообщений остановлена")

    async def health_check(self) -> bool:
        return self._is_running

    async def _polling_loop(self) -> None:
        try:
            async with PatchedIterator(cast(RobustQueue, self._queue)) as msg_iter:
                async for message in msg_iter:
                    async with message.process(ignore_processed=True):
                        await self._callback(message)

        except asyncio.CancelledError:
            self._logger.debug("Обработка сообщений остановлена")

    async def _callback(self, message: AbstractIncomingMessage) -> None:
        try:
            decoded = await self._message_decoder(message)

        except MessageDecodeError as exc:
            self._logger.exception(f"Не удалось обработать входящее сообщение: {exc.message}")
            await message.reject(requeue=self._requeue_on_invalid_message)
            return

        try:
            await self._handle_message_callback(decoded)

        except (asyncio.CancelledError, UseRequeueError):
            await message.reject(requeue=True)

        except AvoidRequeueError:
            await message.reject(requeue=False)

        except Exception as exc:
            self._logger.exception(f"Ошибка при обработке входящего сообщения: {type(exc).__name__}]")
            await message.reject(requeue=self._requeue_on_error)

        else:
            await message.ack()
