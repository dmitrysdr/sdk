from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from boilerplates.mongodb.config import MongoConfig


class MongoDBWrapper:
    def __init__(
        self,
        logger,
        config: MongoConfig,
    ) -> None:
        self._logger = logger
        self._config = config
        self.client = AsyncIOMotorClient(
            self._config.as_dsn,
            minPoolSize=self._config.min_connections_count,
            maxPoolSize=self._config.max_connections_count,
            timeoutMS=self._config.timeout_ms,
            uuidRepresentation="standard",
        )

    async def on_startup(self) -> None:
        ...

    async def on_shutdown(self) -> None:
        ...

    async def startup_event_handler(self) -> None:
        self._logger.debug("Событие: startup")
        try:
            await self.health_check()
            await self.on_startup()
        except Exception as err:
            self._logger.error(err, exc_info=True)
            raise err

    async def shutdown_event_handler(self) -> None:
        self._logger.debug("Событие: shutdown")
        await self.on_shutdown()
        self.client.close()

    async def health_check(self) -> bool:
        await self.client.server_info()
        return True

    def get_db(self) -> AsyncIOMotorDatabase:
        return self.client.get_database(self._config.db_name)
