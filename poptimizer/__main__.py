"""Основная точка входа для запуска приложения."""
import asyncio

import uvloop

from poptimizer.app import backup, clients, config, modules


async def main() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    cfg = config.Cfg()

    async with (  # noqa:  WPS316
        clients.http(cfg.http_client.con_per_host) as http,
        clients.mongo(cfg.mongo.uri) as mongo,
        modules.root_actor(http, cfg.logger) as app,
    ):
        app.spawn(backup.Backup(mongo))


if __name__ == "__main__":
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        runner.run(main())
