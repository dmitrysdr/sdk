from typing import Optional, overload

from aio_pika import Message
from aio_pika.abc import AbstractChannel

from boilerplates.rabbitmq.connection import ConnectionHolder


@overload
async def publish_message(
    *,
    connection_holder: ConnectionHolder,
    message: Message,
    exchange_name: str,
    rk: str,
    create_exchange_with_memory_leak: bool,
) -> None:
    ...


@overload
async def publish_message(
    *,
    channel: AbstractChannel,
    message: Message,
    exchange_name: str,
    rk: str,
    create_exchange_with_memory_leak: bool,
) -> None:
    ...


async def publish_message(
    *,
    connection_holder: Optional[ConnectionHolder] = None,
    channel: Optional[AbstractChannel] = None,
    message: Message,
    exchange_name: str,
    rk: str,
    create_exchange_with_memory_leak: bool = False,
) -> None:
    """Опубликовать сообщение в указанный Exchange

    Args:
        message (Message):
            тело сообщения
        exchange_name (str):
            имя Exchange
        rk (str):
            routing key
        connection_holder (ConnectionHolder | None, optional):
            класс, хранящий пулы соединений
        channel (AbstractChannel | None, optional):
            канал
        create_exchange_with_memory_leak (bool):
            создает exchange, если его не было. Ведёт к утечке памяти, поэтому значение по умолчанию инвертировано

    Raises:
        ValueError: _description_
    """
    if not connection_holder and not channel:
        raise ValueError("Необходимо передать connection_holder или channel")

    if channel:
        exchange = await channel.get_exchange(exchange_name, ensure=create_exchange_with_memory_leak)
        await exchange.publish(message=message, routing_key=rk)
        return

    if connection_holder:
        async with connection_holder.channel_pool.acquire() as channel:
            exchange = await channel.get_exchange(exchange_name, ensure=create_exchange_with_memory_leak)
            await exchange.publish(message=message, routing_key=rk)
