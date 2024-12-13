from contextlib import contextmanager
from typing import Generator


@contextmanager
def optional_dependency(name: str) -> Generator[None, None, None]:
    try:
        yield
    except ImportError as exc:
        raise RuntimeError(
            f"Boilerplates requires installing `{name}` extra to work. Hint: `pip install boilerplates[{name}]`",
        ) from exc
