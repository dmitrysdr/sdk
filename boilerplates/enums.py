from enum import Enum
from typing import Any


class LowerStringEnum(str, Enum):
    """
    Автоматически генерирует значение для enum как имя ключа в нижнем регистре

    Примеры использования:

    ```python
    @unique
    class LogFormat(LowerStringEnum):
        JSON = auto()
        PLAIN = auto()

    val = LogFormat.JSON.value  # "json"
    ```
    """

    @staticmethod
    def _generate_next_value_(name: str, *_: Any) -> str:
        return name.lower()
