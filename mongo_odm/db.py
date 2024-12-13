from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Self

from beanie import Document, View, init_beanie
from boilerplates.logging import get_logger
from boilerplates.mongodb import MongoDBWrapper
from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorDatabase
from structlog.types import FilteringBoundLogger

from .config import MongoConfig


class Mongo(MongoDBWrapper):
    def __init__(
        self,
        config: MongoConfig,
        document_models: list[type[Document] | type[View] | str] | None = None,
        logger: FilteringBoundLogger | None = None,
    ) -> None:
        logger = logger or get_logger("mongo")
        super().__init__(logger, config)  # type: ignore[arg-type]
        self._beanie_options: dict[str, Any] = {
            "document_models": document_models or [],
            "recreate_views": True,
            "allow_index_dropping": config.allow_index_dropping,
        }

    async def startup(self) -> None:
        await init_beanie(database=self.get_db(), **self._beanie_options)
        await self.startup_event_handler()

    async def shutdown(self) -> None:
        await self.shutdown_event_handler()

    @asynccontextmanager
    async def use(self) -> AsyncGenerator[Self, None]:
        try:
            await self.startup()
            yield self
        finally:
            await self.shutdown()

    def get_db(self) -> "AsyncIOMotorDatabase[Any]":
        return self.client.get_database(
            self._config.db_name,
            codec_options=CodecOptions(
                uuid_representation=UuidRepresentation.STANDARD,
                tz_aware=True,
            ),
        )
