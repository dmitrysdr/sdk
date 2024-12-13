from pathlib import Path

from pydantic import BaseModel, Field

from .types import LogFormat, LogLevel


class FileLoggingConfig(BaseModel):
    clean_dir_on_setup: bool = Field(
        ...,
        description="If True, the logs folder will be cleared before setting up logging",
    )
    logs_folder: Path = Field(..., description="The folder where logs will be stored")
    logger_names: list[str] = Field(..., description="Logger names that will be logged to files")


class LoggingConfig(BaseModel):
    use_colors: bool = Field(..., description="If True, colored logs will be used")
    log_format: LogFormat = Field(..., description="The format of the logs")
    log_level: LogLevel = Field(..., description="The log level for the root logger")
    is_sentry_enabled: bool = Field(..., description="If True, Sentry integration will be enabled")
    dt_format: str = Field(default="iso", description="Date format")
    clear_existing_handlers: bool = Field(default=True, description="If True, existing log handlers will be cleared")
    log_levels: dict[str, LogLevel] = Field(default_factory=dict, description="Log levels for specific loggers")
    file_logging: FileLoggingConfig | None = Field(default=None, description="File logging configuration")
