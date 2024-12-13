# Boilerplates

Переиспользуемые компоненты.
Опциональные модули:
* mongodb - работа с `MongoDB`, зависимости: `motor, pydantic`
* rabbitmq - работа с `RabbitMQ`, зависимости: `aio-pika`
* sentry - интеграция с `Sentry`, зависимости: `sentry-sdk`
* celery - поддержка `Celery` воркеров, зависимости: `celery, aio-pika`
* logging - настройка логирования при помощи 'structlog', зависимости: `structlog`
* logging-sentry - настройка логирования с интеграцией с sentry, зависимости: `structlog-sentry, structlog, sentry-sdk`

## Пример использования celery в проекте
```python
from logging import basicConfig, getLogger
from typing import Any

from boilerplates.celery import AsyncTask, CelerySettings, GenericWorkerContext, RetryPolicy, TaskConfig, run_worker
from boilerplates.rabbitmq import AMQPConnectionSettings

basicConfig(level="DEBUG", format="%(asctime)s %(levelname)s %(name)s %(message)s")


class MyException(Exception):
    ...


class MyWorkerSettings(CelerySettings):
    test_message: str


class MyWorkerContext(GenericWorkerContext[MyWorkerSettings]):
    def __init__(self, logger: Any, config: MyWorkerSettings) -> None:
        super().__init__(logger, config)

    async def on_startup(self, *args, **kwargs) -> None:
        self._logger.debug("Async startup done")

    async def on_shutdown(self, *args, **kwargs) -> None:
        self._logger.debug("Async shutdown done")


class TestTask(AsyncTask[MyWorkerContext]):
    name = "test_task"

    async def execute(self, *args, **kwargs) -> Any:
        self.logger.info(self.context.config.test_message)


run_worker(
    context=MyWorkerContext(
        logger=getLogger("test_worker"),
        config=MyWorkerSettings(
            debug=True,
            test_message="Hello world!",
            app_name="test_worker",
            rabbitmq=AMQPConnectionSettings(
                host="localhost",
                port=5672,
                username="user",
                password="password", # noqa
                vhost="/celery_test",
                connection_pool_size=1,
                channel_pool_size=3,
            ),
            default_task_expiration=120,
            tasks={
                "test_task": TaskConfig(
                    schedule=5.0, # Every 5 seconds
                    retry=RetryPolicy(
                        retry_backoff_max=60,
                        retry_backoff=5,
                        max_retries=10,
                    ),
                    time_limit=120,
                ),
            },
        ),
    ),
    tasks=[TestTask],
    autoretry_for_exc_types=[MyException],
)
```

## Пример настройки логирования в проекте

### Базовая настройка:
```python
from logging import DEBUG, WARNING, getLogger as std_getLogger
from pathlib import Path

from boilerplates.logging import FileLoggingConfig, LogFormat, LoggingConfig, get_logger, setup_logging

setup_logging(
    config=LoggingConfig(
        use_colors=True,
        log_format=LogFormat.PLAIN,
        dt_format="%Y-%m-%d %H:%M:%S",
        log_level=DEBUG,
        log_levels={"my_logger": DEBUG, "spammy_logger": WARNING},
        is_sentry_enabled=False,
        file_logging=FileLoggingConfig(
            clean_dir_on_setup=True,
            logs_folder=Path(__file__).parent / "logs",
            logger_names=["my_logger", "spammy_logger"],
        ),
    ),
)

std_getLogger("my_logger").debug("this is test message")
get_logger("my_logger", server_id=1).debug("this is test message")
```

### Добавление контекста к логгерам:
```python
from boilerplates.logging import get_logger

service_logger = get_logger("root")
service_logger.debug("Service started")

match_logger = service_logger.bind(match_id="123")
match_logger.debug("Match started")
```
**Вывод:**
```
⋊> ~ ◦ python test.py
2024-02-19 10:03:55 [debug    ] Service started                [root] 
2024-02-19 10:03:55 [debug    ] Match started                  [root] match_id=123
```

### Добавление кастомных процессоров:
```python
import random

from boilerplates.logging import ChainBuilder, LogFormat, get_logger, setup_logging

def random_value_generator(logger, name, event):
    event["random_value"] = random.randint(0, 1000)
    return event

chain = (
    ChainBuilder
    .create_default_preset(is_sentry_enabled=False)
    .add(random_value_generator, "random_value_generator", append_after=None) # Добавление в конец
    .build()
)

setup_logging(
    config=...,
    processors_chain=chain,
)

get_logger("my_logger").debug("this is test message")
```

### Настройка логирования для uvicorn
```python
from uvicorn import run
from boilerplates.logging import LogFormat, StructlogFormatter, generate_uvicorn_log_config

run(
    ...,
    log_config=generate_uvicorn_log_config(
        log_level="DEBUG",
        is_sentry_enabled=True,
        log_format=LogFormat.JSON,
        formatter=StructlogFormatter,
    ),
    ...
)
```

## Как поддерживать и обновлять пакет?

При выпуске новой версии (вариант с автоматизацией):

  - меняем в pyproject.toml поле version
  - коммитим
  - создаем тег версии с правильным неймингом в gitlab
  - пушим тег в gitlab
  - далее gitlab автоматом соберет и закинет в PyPi пакет
