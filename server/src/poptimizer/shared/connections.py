"""Общие соединения http и MongoDB."""
import asyncio
import atexit
import pathlib
from typing import Final, Optional

import aiohttp
import psutil
from motor import motor_asyncio

# Настройки сервера MongoDB
_MONGO_URI: Final = "mongodb://localhost:27017"

# Размер пула http-соединений - при большем размере многие сайты ругаются
_POOL_SIZE: Final = 20

def _clean_up(session: aiohttp.ClientSession) -> None:
    """Закрывает клиентскую сессию aiohttp."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(session.close())


def http_session_factory(pool_size: int) -> aiohttp.ClientSession:
    """Клиентская сессия aiohttp."""
    connector = aiohttp.TCPConnector(limit=pool_size)
    session = aiohttp.ClientSession(connector=connector)
    atexit.register(_clean_up, session)
    return session


MONGO_CLIENT: Final = motor_asyncio.AsyncIOMotorClient(_MONGO_URI, tz_aware=False)
HTTP_SESSION: Final = http_session_factory(_POOL_SIZE)
