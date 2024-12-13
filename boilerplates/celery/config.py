from pydantic import BaseModel, Field

from boilerplates.rabbitmq import AMQPConnectionSettings

from .pydantic_fields import CronTab


class RetryPolicy(BaseModel):
    retry_backoff_max: int = Field(..., description="Maximum retry backoff in seconds")
    retry_backoff: int = Field(..., description="Retry backoff in seconds")
    max_retries: int = Field(..., description="Maximum number of retries")


class TaskConfig(BaseModel):
    schedule: float | CronTab | None = Field(
        None,
        description="Task schedule, in seconds or crontab format, None for no schedule",
    )
    retry: RetryPolicy | None = Field(None, description="Task retry policy")
    time_limit: int = Field(..., description="Task time limit in seconds")


class CelerySettings(BaseModel):
    debug: bool = Field(..., description="Celery debug mode")
    app_name: str = Field(..., description="Celery app name")
    rabbitmq: AMQPConnectionSettings = Field(..., description="RabbitMQ broker settings")
    default_task_expiration: int = Field(..., description="Default task expiration in seconds")
    tasks: dict[str, TaskConfig] = Field(..., description="Celery tasks configuration")
