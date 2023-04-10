"""Основная точка входа для запуска приложения."""
import asyncio

import uvloop

from poptimizer.app import clients, config, modules
from poptimizer.core import backup


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
        backup_srv = backup.Backup(mongo)
        await backup_srv.restore()

        port_ref = app.spawn(modules.create_portfolio_updater(mongo))
        app.spawn(modules.create_data_updater(http, mongo, [port_ref]))
        app.spawn(modules.create_server(cfg.server, mongo, backup_srv))


if __name__ == "__main__":
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        runner.run(main())
