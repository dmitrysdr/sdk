from datetime import timedelta

from pydantic import BaseModel


class StorageConfig(BaseModel):
    cache_max_size: int
    cache_ttl: timedelta
