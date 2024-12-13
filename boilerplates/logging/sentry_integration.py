from typing import Any

from boilerplates._utils import optional_dependency

with optional_dependency("logging-sentry"):
    from structlog.types import EventDict
    from structlog_sentry import SentryProcessor as SimpleSentryProcessor


class SentryProcessor(SimpleSentryProcessor):
    """Extensions to SentryProcessor, appends additional information provided by the logger to breadcrumbs"""

    name = "add_sentry_integration"

    def __init__(  # pylint: disable=too-many-arguments
        self,
        breadcrumb_level: int,
        level: int,
        event_level: int,
        active: bool = False,
        tag_keys: list[str] | str | None = None,
    ) -> None:
        self.breadcrumb_level = breadcrumb_level
        super().__init__(
            level=level,
            active=active,
            tag_keys=tag_keys,
            event_level=event_level,
        )

    def _get_breadcrumb_and_hint(self, event_dict: EventDict) -> tuple[dict[Any, Any], dict[Any, Any]]:
        data = event_dict.copy()
        event = data.pop("event")
        logger = data.pop("logger", None)
        level = data.pop("level", None)
        data.pop("timestamp", None)

        breadcrumb = {
            "ty": "log",
            "level": level.lower() if level else None,
            "category": logger,
            "message": event,
            "data": data,
        }

        return breadcrumb, {"log_record": event_dict}
