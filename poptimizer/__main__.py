"""Основная точка входа для запуска приложения."""
import asyncio

import uvloop

from poptimizer.core import actor, clients, config, lgr, telegram


async def main() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT."""
    cfg = config.Cfg()

    async with (  # noqa:  WPS316
        clients.http(cfg.http_client.con_per_host) as http,
        clients.mongo(cfg.mongo.uri) as mongo,
    ):
        app = actor.App(
            telegram.Telegram(
                http,
                cfg.logger.telegram_token,
                cfg.logger.telegram_chat_id,
            ),
        )
        lgr.config(app, cfg.logger.level)

        await app.join()


if __name__ == "__main__":
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        runner.run(main())
