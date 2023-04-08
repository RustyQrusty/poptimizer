"""Реализация репозитория для доменных объектов."""
from typing import Any, Final, TypeVar

from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.core import domain

_MONGO_ID: Final = "_id"

Entity = TypeVar("Entity", bound=domain.BaseEntity)
Doc = dict[str, Any]


class Repo:
    """Репозиторий для хранения доменных объектов.

    При сохранении валидирует данные.
    """

    def __init__(self, mongo: AsyncIOMotorClient) -> None:
        self._mongo = mongo

    async def get(self, entity_type: type[Entity], id_: str | None = None) -> Entity:
        """Загружает доменную сущность."""
        collection = self._mongo[entity_type.group.module][entity_type.group.group]
        id_ = id_ or entity_type.group.group

        doc = await collection.find_one({_MONGO_ID: id_})

        return entity_type.parse_obj(doc or {_MONGO_ID: id_})

    async def get_doc(self, group: domain.Group, id_: str | None = None) -> Doc:
        """Загружает доменную сущность в виде словаря."""
        collection = self._mongo[group.module][group.group]
        id_ = id_ or group.group

        return (await collection.find_one({_MONGO_ID: id_})) or {_MONGO_ID: id_}

    async def list(self, entity_type: type[Entity]) -> list[str]:
        """Список id всех объектов данного типа."""
        collection = self._mongo[entity_type.group.module][entity_type.group.group]

        cursor = collection.find({}, projection={_MONGO_ID: True})

        return [doc[_MONGO_ID] async for doc in cursor]

    async def save(self, entity: Entity) -> None:
        """Валидирует и сохраняет доменный объект."""
        doc = _validate(entity)

        collection = self._mongo[entity.group.module][entity.group.group]

        await collection.replace_one(
            filter={_MONGO_ID: entity.id_},
            replacement=doc,
            upsert=True,
        )


def _validate(table: Entity) -> dict[str, Any]:
    doc = table.dict()
    table.parse_obj(doc | {_MONGO_ID: table.id_})

    return doc
