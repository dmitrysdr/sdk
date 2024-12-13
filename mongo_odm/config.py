from boilerplates.mongodb import MongoConfig as Base


class MongoConfig(Base):
    allow_index_dropping: bool = False
