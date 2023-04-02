"""HTTP клиент."""
import types
from typing import Final

import aiohttp

_HEADERS: Final = types.MappingProxyType(
    {
        "User-Agent": "POptimizer",
        "Connection": "keep-alive",
    },
)


def client(con_per_host: int) -> aiohttp.ClientSession:
    """Асинхронный HTTP клиент с разумными настройками."""
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit_per_host=con_per_host),
        headers=_HEADERS,
    )
