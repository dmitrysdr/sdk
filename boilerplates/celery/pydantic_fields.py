from collections.abc import Callable, Generator

from celery.schedules import crontab
from pydantic import __version__ as pydantic_version

LEGACY_MODE = pydantic_version.startswith("1.")


class CronTab(str, crontab):
    @classmethod
    def __get_validators__(cls) -> Generator[Callable[[str], crontab], None, None]:
        if LEGACY_MODE:
            yield cls.validate_v1
        else:
            yield cls.validate

    @classmethod
    def validate(cls, value: str, *args, **kwargs) -> crontab:
        minute, hour, day_of_month, month_of_year, day_of_week = value.split()
        return crontab(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
            day_of_week=day_of_week,
        )

    @classmethod
    def validate_v1(cls, value: str) -> crontab:
        return cls.validate(value)
