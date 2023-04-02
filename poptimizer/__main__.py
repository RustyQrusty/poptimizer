"""Основная точка входа для запуска приложения."""
import asyncio
import logging

import uvloop

from poptimizer.core import actor


async def main() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT."""
    logging.basicConfig(level=logging.INFO)
    app = actor.App()
    await app.join()


if __name__ == "__main__":
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        runner.run(main())
