"""Актор для отправки сообщений в Телеграм."""
import html
import logging
from typing import Final

import aiohttp

from poptimizer.core import actor

_MAX_TELEGRAM_MSG_SIZE: Final = 4096


class Telegram:
    """Актор для отправки сообщений логера в Телеграм."""
    def __init__(self, session: aiohttp.ClientSession, token: str, chat_id: str, level: int = logging.WARNING) -> None:
        self._logger = logging.getLogger("Telegram")
        self._session = session
        self._api_url = f"https://api.telegram.org/bot{token}/SendMessage"
        self._chat_id = chat_id
        self._fmt = "<strong>{name}</strong>\n{message}"
        self._level = level

    async def __call__(self, ctx: actor.Ctx, record: logging.LogRecord) -> None:
        """Посылает сообщения в телеграм с уровнем логирования начиная с заданного.

        Игнорирует сообщения от логера Telegram, чтобы избежать рекурсии на ошибках с отправкой.

        https://core.telegram.org/bots/api#sendmessage.
        """
        if record.name == "Telegram":
            return

        msg = html.escape(record.msg) % record.args

        json = {
            "chat_id": self._chat_id,
            "parse_mode": "HTML",
            "text": self._fmt.format(name=record.name, message=msg)[:_MAX_TELEGRAM_MSG_SIZE],
        }

        if record.levelno >= self._level:
            async with self._session.post(self._api_url, json=json) as resp:
                if not resp.ok:
                    err_desc = await resp.json()
                    self._logger.warning(f"can't send {err_desc}")