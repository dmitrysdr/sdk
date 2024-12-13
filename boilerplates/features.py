from contextlib import suppress

STRUCTLOG_SUPPORTED = False
PYDANTIC_V2_SUPPORTED = False

with suppress(ImportError):
    import structlog  # noqa: F401

    STRUCTLOG_SUPPORTED = True

with suppress(ImportError):
    import pydantic.v1  # noqa: F401

    PYDANTIC_V2_SUPPORTED = True

__all__ = (
    "STRUCTLOG_SUPPORTED",
    "PYDANTIC_V2_SUPPORTED",
)
