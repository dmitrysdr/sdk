from typing import Optional

from pydantic import BaseModel, SecretStr


class MongoConfig(BaseModel):
    host: str
    db_name: str
    user: str
    password: SecretStr
    timeout_ms: int
    min_connections_count: int
    max_connections_count: int
    custom_auth_source: Optional[str] = None

    @property
    def as_dsn(self) -> str:
        dsn = "mongodb://"
        if self.user and self.password:
            dsn += f"{self.user}:{self.password.get_secret_value()}@"

        dsn += self.host
        if self.custom_auth_source:
            if not dsn.endswith("/"):
                dsn += "/"

            dsn += f"?authSource={self.custom_auth_source}"

        return dsn
