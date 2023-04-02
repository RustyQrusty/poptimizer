"""Различные клиенты для доступа к внешней инфраструктуре."""
import types
from contextlib import asynccontextmanager
from typing import AsyncIterator, Final

import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient

_HEADERS: Final = types.MappingProxyType(
    {
        "User-Agent": "POptimizer",
        "Connection": "keep-alive",
    },
)


def http(con_per_host: int) -> aiohttp.ClientSession:
    """Асинхронный HTTP клиент с разумными настройками."""
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit_per_host=con_per_host),
        headers=_HEADERS,
    )


@asynccontextmanager
async def mongo(uri: str) -> AsyncIterator[AsyncIOMotorClient]:
    """Контекстный менеджер создающий клиента MongoDB и завершающий его работу."""
    motor = AsyncIOMotorClient(uri, tz_aware=False)
    try:
        yield motor
    finally:
        motor.close()
