from boilerplates._utils import optional_dependency

with optional_dependency("rabbitmq"):
    from .connection import ConnectionHolder
    from .exceptions import MessageDecodeError
    from .helpers import publish_message
    from .listener import QueueListener
    from .settings import AMQPConnectionSettings

__all__ = ("ConnectionHolder", "MessageDecodeError", "publish_message", "QueueListener", "AMQPConnectionSettings")
