from asyncio import get_running_loop
from typing import Any

from aio_pika import connect_robust
from aio_pika.abc import AbstractChannel, AbstractRobustConnection
from aio_pika.pool import Pool

from boilerplates.descriptors import ProtectedProperty
from boilerplates.rabbitmq.settings import AMQPConnectionSettings


class ConnectionHolder:
    """
    Класс-обёртка для подключения к amqp-серверу, позволяющий получать
    каналы из пула каналов и соединения из пула соединений для работы с
    очередями.

    Пример использования:
        ```python
        holder = ConnectionHolder(
            settings=settings,
            logger=get_logger("tests.rabbitmq"),
        )
        async with self.holder.channel_pool.acquire() as channel:
            exchange = await channel.get_exchange(exchange_name)
        ```
    """

    connection_pool = ProtectedProperty[Pool[AbstractRobustConnection]]()
    channel_pool = ProtectedProperty[Pool[AbstractChannel]]()

    def __init__(self, settings: AMQPConnectionSettings, logger: Any) -> None:
        self.logger = logger
        self._settings = settings

    async def __aenter__(self) -> "ConnectionHolder":
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.stop()

    async def start(self) -> None:
        loop = get_running_loop()
        self.logger.debug("Инициализация пулов соединений")
        self.connection_pool = Pool(
            self._get_connection,
            max_size=self._settings.connection_pool_size,
            loop=loop,
        )
        self.channel_pool = Pool(
            self._get_channel,
            max_size=self._settings.channel_pool_size,
            loop=loop,
        )
        self.logger.debug("Пулы соединений инициализированы")

    async def stop(self) -> None:
        self.logger.debug("Закрытие пулов соединений")
        await self.channel_pool.close()
        await self.connection_pool.close()
        self.logger.debug("Пулы соединений закрыты")

    async def health_check(self) -> bool:
        async with self.channel_pool.acquire() as channel:
            return not channel.is_closed

    async def _get_connection(self) -> AbstractRobustConnection:
        return await connect_robust(self._settings.dsn, timeout=self._settings.connect_timeout)

    async def _get_channel(self) -> AbstractChannel:
        async with self.connection_pool.acquire() as connection:
            return await connection.channel()

    async def get_channel_from_pool(self) -> AbstractChannel:
        """Получить канал из пула каналов"""
        return await self.channel_pool._get()  # pylint: disable=protected-access

    async def return_to_pool(self, channel: AbstractChannel) -> None:
        """Вернуть канал в пул каналов"""
        self.channel_pool.put(channel)
