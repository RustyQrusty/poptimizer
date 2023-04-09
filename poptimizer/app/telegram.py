"""Актор для отправки сообщений в Телеграм."""
import html
import logging
import types
from typing import Final

import aiohttp

from poptimizer.core import actor

_MAX_TELEGRAM_MSG_SIZE: Final = 4096
_level_num: Final = types.MappingProxyType(
    {
        "CRITICAL": logging.CRITICAL,
        "FATAL": logging.FATAL,
        "ERROR": logging.ERROR,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
    },
)


class Telegram:

    """Актор для отправки сообщений логера в Телеграм."""

    def __init__(self, client: aiohttp.ClientSession, level: int | str, token: str, chat_id: str) -> None:
        self._logger = logging.getLogger("Telegram")
        self._client = client

        match level:
            case int():
                self._level = level
            case str():
                self._level = _level_num.get(level, logging.INFO)

        self._api_url = f"https://api.telegram.org/bot{token}/SendMessage"
        self._chat_id = chat_id
        self._fmt = "<strong>{name}</strong>\n{message}"

    async def __call__(self, ctx: actor.Ctx, msg: logging.LogRecord) -> None:
        """Посылает сообщения в телеграм с уровнем логирования начиная с заданного.

        Игнорирует сообщения от логера Telegram, чтобы избежать рекурсии на ошибках с отправкой.

        https://core.telegram.org/bots/api#sendmessage.
        """
        if msg.name == "Telegram":
            return

        message = html.escape(msg.msg) % msg.args

        json = {
            "chat_id": self._chat_id,
            "parse_mode": "HTML",
            "text": self._fmt.format(name=msg.name, message=message)[:_MAX_TELEGRAM_MSG_SIZE],
        }

        if msg.levelno >= self._level:
            async with self._client.post(self._api_url, json=json) as resp:
                if not resp.ok:
                    err_desc = await resp.json()
                    self._logger.warning("can't send %s", err_desc)
