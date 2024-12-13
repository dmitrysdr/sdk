from boilerplates._utils import optional_dependency

with optional_dependency("mongodb"):
    from .config import MongoConfig
    from .wrapper import MongoDBWrapper

__all__ = ("MongoConfig", "MongoDBWrapper")
