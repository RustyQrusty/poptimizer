"""Настройка мэппинга данных и необходимых коллекций."""
import asyncio
import logging
import pathlib
from typing import Final

import aiohttp
import pandas as pd
import psutil
from motor import motor_asyncio

from poptimizer.shared import adapters, connections

# Путь к dump с данными по дивидендам
MONGO_DUMP: Final = pathlib.Path(__file__).parents[3] / "dump/source"

# Ссылки на данные по дивидендам в интернете
DIV_DATA_URL: Final = (
    (
        "dividends.bson",
        "https://github.com/WLM1ke/poptimizer/blob/master/dump/source/dividends.bson?raw=true",
    ),
    (
        "dividends.metadata.json",
        "https://github.com/WLM1ke/poptimizer/blob/master/dump/source/dividends.metadata.json?raw=true",
    ),
)

# База и коллекция с источником данных по дивидендам
SOURCE_DB: Final = "source"
COLLECTION: Final = "dividends"

# ID и ключ документа с информацией о количестве документов с дивидендами
ID: Final = "count"
KEY: Final = "dividends"

# Настройки мэппинга
DATA_DESCRIPTION: Final = (
    adapters.Desc(
        field_name="_df",
        doc_name="data",
        factory_name="df",
        encoder=lambda df: df.to_dict("split"),
        decoder=lambda doc_df: pd.DataFrame(**doc_df),
    ),
    adapters.Desc(
        field_name="_timestamp",
        doc_name="timestamp",
        factory_name="timestamp",
    ),
)


async def _download_dump(http_session: aiohttp.ClientSession) -> None:
    """Загружает резервную версию дивидендов с GitHub."""
    if not MONGO_DUMP.exists():
        logging.info("Файлы с данными о дивидендах отсутствуют - начинается загрузка")
        path = MONGO_DUMP / SOURCE_DB
        path.mkdir(parents=True)
        for name, url in DIV_DATA_URL:
            async with http_session.get(url) as respond:
                with open(path / name, "wb") as fin:
                    fin.write(await respond.read())
        logging.info("Файлы с данными о дивидендах загружены")


async def _restore_dump(
    client: motor_asyncio.AsyncIOMotorClient,
) -> None:
    """Осуществляет восстановление данных по дивидендам."""
    if SOURCE_DB not in await client.list_database_names():
        logging.info("Начато восстановление данных с дивидендами")
        attach = "docker exec -it poptimizer-database sh -c"
        restore = f'"mongorestore --uri mongodb://localhost:27017 --db {MONGO_DUMP.stem} {MONGO_DUMP}"'
        mongo_restore = [f'{attach} {restore}']
        process = psutil.Popen(mongo_restore, shell=True)
        status = process.wait()
        logging.info(f"Восстановление данных с дивидендами завершен со статусом {status}")


async def _dump_dividends_db(client: motor_asyncio.AsyncIOMotorClient) -> None:
    """Осуществляет резервное копирование базы данных с дивидендами."""
    collection = client[SOURCE_DB][COLLECTION]
    n_docs = await collection.count_documents({})
    div_count = await collection.find_one({"_id": ID})
    if div_count is None or n_docs != div_count[KEY]:
        logging.info(f"Backup данных с дивидендами {n_docs} документов")
        attach = "docker exec -it poptimizer-database sh -c"
        dump = f'"mongodump --uri mongodb://localhost:27017 --out {MONGO_DUMP} --db {SOURCE_DB}"'
        mongo_dump = [f"{attach} {dump}"]
        process = psutil.Popen(mongo_dump, shell=True)
        status = process.wait()
        await collection.replace_one({"_id": ID}, {KEY: n_docs}, upsert=True)
        logging.info(f"Backup данных с дивидендами завершен со статусом {status}")


async def prepare_div_collection(
    mongo: motor_asyncio.AsyncIOMotorClient = connections.MONGO_CLIENT,
    http: aiohttp.ClientSession = connections.HTTP_SESSION,
) -> None:
    """Запускает сервер.

    При необходимости создает коллекцию с исходными данными по дивидендам или сохраняет ее резервную
    копию.
    """
    await _download_dump(http)
    await _restore_dump(mongo)
    await _dump_dividends_db(mongo)


loop = asyncio.get_event_loop()
loop.run_until_complete(prepare_div_collection())
