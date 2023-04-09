"""Основная точка входа для запуска приложения."""
import asyncio

import uvloop

from poptimizer.app import backup, clients, config, modules


async def main() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    cfg = config.Cfg()

    async with (  # :  WPS316
        clients.http(cfg.http_client.con_per_host) as http,
        clients.mongo(cfg.mongo.uri) as mongo,
        modules.create_root_actor(http, cfg.logger) as app,
    ):
        backup_ref = app.spawn(backup.Backup(mongo))
        port_ref = app.spawn(modules.create_portfolio_updater(mongo))
        app.spawn(modules.create_data_updater(http, mongo, [port_ref]))
        app.spawn(modules.create_server(cfg.server, mongo, lambda: app.send(backup.BACKUP_COLLECTION, backup_ref)))


if __name__ == "__main__":
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        runner.run(main())
