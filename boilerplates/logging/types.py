from enum import auto, unique

from structlog.types import FilteringBoundLogger

from boilerplates.enums import LowerStringEnum


@unique
class LogFormat(LowerStringEnum):
    JSON = auto()
    PLAIN = auto()


LogLevel = str | int
LoggerType = FilteringBoundLogger


__all__ = (
    "LogFormat",
    "LogLevel",
    "LoggerType",
)
