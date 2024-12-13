from pydantic import BaseModel

try:
    from pydantic.v1 import validator
except ImportError:
    from pydantic import validator  # type: ignore


class AMQPConnectionSettings(BaseModel):
    vhost: str
    host: str
    port: int
    username: str
    password: str
    connection_pool_size: int
    channel_pool_size: int
    connect_timeout: int | float | None = None

    @property
    def dsn(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}{self.vhost}"

    @validator("vhost")
    def validate_vhost(cls, value: str) -> str:  # noqa: N805
        if not value.startswith("/"):
            return f"/{value}"

        return value
