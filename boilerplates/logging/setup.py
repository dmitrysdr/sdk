import logging
import sys
from typing import Any

import structlog
from structlog.types import FilteringBoundLogger, Processor

from .common_chain import create_common_chain
from .config import FileLoggingConfig, LoggingConfig
from .types import LogFormat


class StructlogFormatter(structlog.stdlib.ProcessorFormatter):
    def __init__(
        self,
        log_format: LogFormat,
        foreign_chain: list[Processor],
        use_colors: bool = False,
    ) -> None:
        renderer: Any

        match log_format:
            case LogFormat.JSON:
                renderer = structlog.processors.JSONRenderer(ensure_ascii=False)
            case LogFormat.PLAIN:
                renderer = structlog.dev.ConsoleRenderer(colors=use_colors)
            case _:
                raise ValueError(f"Unsupported log_format value: {log_format}")

        super().__init__(
            foreign_pre_chain=foreign_chain,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
        )


class ChainBuilder:
    def __init__(self) -> None:
        self._processors: list[tuple[Processor, str]] = []
        self._processor_names = set[str]()

    @property
    def processors(self) -> tuple[tuple[Processor, str], ...]:
        return tuple(self._processors)

    @classmethod
    def create_default_preset(
        cls,
        is_sentry_enabled: bool,
        dt_format: str | None = None,
        exclude_processor_names: list[str] | None = None,
    ) -> "ChainBuilder":
        return (
            cls()
            .add_common_chain(
                dt_format=dt_format,
                exclude_processor_names=exclude_processor_names,
            )
            .add_sentry(is_sentry_enabled)
        )

    def add(
        self,
        processor: Processor,
        name: str,
        /,
        append_after: str | None,
    ) -> "ChainBuilder":
        """Add processor to the chain

        Args:
            processor (Processor): processor to add
            name (str): processor name

            append_after (str | None):
                Name of the processor after which the new processor should be added. If None, the processor will be
                added to the end of the chain.

        Raises:
            ValueError: if processor with the same name already exists
        """
        if name in self._processor_names:
            raise ValueError(f"Processor with name {name} already exists")

        if append_after:
            append_to_position = self._get_index(append_after) + 1
            self._processors.insert(append_to_position, (processor, name))
        else:
            self._processors.append((processor, name))

        self._processor_names.add(name)
        return self

    def remove(
        self,
        name: str,
    ) -> "ChainBuilder":
        """Remove processor from the chain

        Args:
            name (str): processor name

        Raises:
            ValueError: if processor with provided name not found
        """
        if name not in self._processor_names:
            raise ValueError(f"Processor with name {name} not found")

        index = self._get_index(name)
        self._processors.pop(index)
        self._processor_names.discard(name)
        return self

    def add_common_chain(
        self,
        dt_format: str | None = None,
        exclude_processor_names: list[str] | None = None,
    ) -> "ChainBuilder":
        """Add common chain to the chain

        Args:
            exclude_processor_names (list[str] | None, optional): exclude processors with provided names from chain.

        Raises:
            ValueError: if common chain contains processors with names already in chain
        """
        chain = create_common_chain(dt_format=dt_format)
        if {name for _, name in chain}.intersection(self._processor_names):
            raise ValueError("Common chain contains processors with names already in chain")

        if exclude_processor_names:
            chain = [processor for processor in chain if processor[1] not in exclude_processor_names]

        for proc, name in chain:
            self.add(proc, name, append_after=None)

        return self

    def add_sentry(self, is_sentry_enabled: bool) -> "ChainBuilder":
        """Add sentry integration to the chain. Requires "logging-sentry" extra to be installed.

        Args:
            is_sentry_enabled (bool): whether sentry integration should be added

        Raises:
            ValueError: if processor with name already exists
        """
        if not is_sentry_enabled:
            return self

        from .sentry_integration import SentryProcessor

        processor = SentryProcessor(
            level=logging.DEBUG,
            event_level=logging.WARNING,
            breadcrumb_level=logging.DEBUG,
            active=True,
        )

        if processor.name in self._processor_names:
            raise ValueError(f"Processor with name {processor.name} already exists")

        self.add(processor, processor.name, append_after=None)
        return self

    def clear(self) -> "ChainBuilder":
        """Clear chain"""
        self._processors.clear()
        self._processor_names.clear()
        return self

    def build(self) -> list[Processor]:
        """Get resulting list of processors"""
        return [processor for processor, _ in self._processors]

    def _get_index(self, name: str) -> int:
        for index, (_, processor_name) in enumerate(self._processors):
            if processor_name == name:
                return index

        raise ValueError(f"Processor with name {name} not found")


def setup_logging(
    *,
    config: LoggingConfig,
    processors_chain: list[Processor] | None = None,
) -> None:
    """Setup logging

    Args:
        config (LoggingConfig):
            Logging configuration

        processors_chain (list[Processor] | None, optional):
            Custom processors chain. If None, default chain preset will be used. Defaults to None.
    """
    if not processors_chain:
        processors_chain = ChainBuilder.create_default_preset(
            is_sentry_enabled=config.is_sentry_enabled,
            dt_format=config.dt_format,
        ).build()

    structlog.configure(
        processors=processors_chain + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = StructlogFormatter(
        log_format=config.log_format,
        foreign_chain=processors_chain,
        use_colors=config.use_colors,
    )

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()

    if config.clear_existing_handlers:
        root_logger.handlers = []

    root_logger.addHandler(handler)
    root_logger.setLevel(config.log_level)

    for logger_name, logger_level in (config.log_levels or {}).items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(logger_level)

    if config.file_logging:
        _add_logging_to_files(config.file_logging, config.log_format, processors_chain)


def _add_logging_to_files(
    config: FileLoggingConfig,
    log_format: LogFormat,
    processors_chain: list[Processor],
) -> None:
    if config.clean_dir_on_setup:
        for file in config.logs_folder.glob("*.log"):
            if file.is_file():
                file.unlink()

    formatter = StructlogFormatter(
        log_format=log_format,
        foreign_chain=processors_chain,
        use_colors=False,  # file logs should not have colors
    )

    for logger_name in config.logger_names:
        logger = logging.getLogger(logger_name)
        file_handler = logging.FileHandler(config.logs_folder / f"{logger_name}.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_logger(*args: Any, **kwargs: Any) -> FilteringBoundLogger:
    return structlog.get_logger(*args, **kwargs)


__all__ = (
    "LogFormat",
    "ChainBuilder",
    "setup_logging",
    "get_logger",
)
