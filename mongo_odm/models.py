from typing import Any

from beanie import Document


class DBModel(Document):
    def to_bson(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)
