from typing import Any, Generic

from boilerplates.types import T


class ProtectedProperty(Generic[T]):
    """Дескриптор, гарантирующий, что используемое значение не является `None`"""

    def __set_name__(self, _owner: Any, name: str) -> None:
        # pylint: disable=attribute-defined-outside-init
        self.public_name = name
        self.private_name = "_" + name

    def __set__(self, instance: Any, value: T) -> None:
        setattr(instance, self.private_name, value)

    def __get__(self, instance: Any, _owner: Any) -> T:
        value = getattr(instance, self.private_name, None)
        if value is None:
            raise RuntimeError(f"{self.public_name} не инициализирован")

        return value
