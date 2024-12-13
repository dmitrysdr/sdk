from pydantic import BaseModel

from boilerplates._utils import optional_dependency

with optional_dependency("sentry"):
    import sentry_sdk
    from sentry_sdk.integrations import Integration


class SentrySettings(BaseModel):
    dsn: str
    is_enabled: bool
    environment: str
    traces_sample_rate: float = 0.0
    max_value_length: int = 1024


def setup_sentry(settings: SentrySettings, app_version: str, integrations: list[Integration] | None = None) -> None:
    if not integrations:
        integrations = []

    sentry_sdk.init(
        dsn=settings.dsn,
        environment=settings.environment,
        release=app_version,
        traces_sample_rate=settings.traces_sample_rate,
        integrations=integrations,
        default_integrations=False,
        max_value_length=settings.max_value_length,
    )


__all__ = ("setup_sentry", "SentrySettings")
