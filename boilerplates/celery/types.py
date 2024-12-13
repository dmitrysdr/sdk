from typing import TypeVar

from .config import CelerySettings

SettingsT = TypeVar("SettingsT", bound=CelerySettings)
