from dataclasses import dataclass


@dataclass(repr=True, kw_only=True)
class MessageDecodeError(Exception):
    message: str = "Ошибка декодирования AMQP сообщения"


class AvoidRequeueError(Exception):
    pass


class UseRequeueError(Exception):
    pass
