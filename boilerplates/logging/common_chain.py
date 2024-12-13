import sys
import traceback

import structlog
from structlog.types import EventDict, Processor, WrappedLogger


class _NOTSET:
    ...


NOT_SET = _NOTSET()


def add_exc_info(logger: WrappedLogger, name: str, event: EventDict) -> EventDict:
    """
    Adds information about the exception if the log call occured in an exception block and exc_info was not provided
    """
    if sys.version_info < (3, 11):
        # sys.exception method was added in python 3.11
        return event

    if sys.exception() and event.get("exc_info", NOT_SET) is NOT_SET and name not in ("info", "debug", "trace"):
        event["exc_info"] = True

    return event


def exception_formatter(exc_info: structlog.types.ExcInfo) -> str:
    formatter = traceback.TracebackException(*exc_info, limit=None, compact=True)
    if sys.version_info >= (3, 11):
        # remove python 3.11 traceback features
        lines = (line.rstrip("\n").rstrip("^").rstrip(" ").rstrip("\n") for line in formatter.format(chain=True))
        return "\n".join(lines)

    return "\n".join(formatter.format(chain=True))


def create_common_chain(dt_format: str | None = None) -> list[tuple[Processor, str]]:
    return [
        (structlog.processors.TimeStamper(fmt=dt_format or "iso"), "add_timestamp"),
        (structlog.stdlib.add_log_level, "add_log_level"),
        (structlog.stdlib.add_logger_name, "add_logger_name"),
        (add_exc_info, "add_exc_info"),
        (structlog.stdlib.PositionalArgumentsFormatter(), "format_positional_args"),
        (structlog.processors.StackInfoRenderer(), "add_stack_info"),
        (structlog.processors.ExceptionRenderer(exception_formatter), "fix_exception_format"),
    ]
