"""Настройки логирования."""
import logging
import sys
import types
from copy import copy
from typing import Final, Literal, TextIO

from poptimizer.app import actor

COLOR_MSG: Final = "color_msg"
_LOGGER_NAME_SIZE: Final = 11
_MAX_TELEGRAM_MSG_SIZE: Final = 4096


class _TelegramHandler(logging.StreamHandler[TextIO]):
    def __init__(self, app: actor.App) -> None:
        super().__init__(sys.stdout)
        self._app = app

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self._app.send(record, self._app.ref)


class _ColorFormatter(logging.Formatter):
    """Цветное логирование."""

    levels: Final = types.MappingProxyType(
        {
            logging.DEBUG: "\033[90mDBG\033[0m",
            logging.INFO: "\033[34mINF\033[0m",
            logging.WARNING: "\033[31mWRN\033[0m",
            logging.ERROR: "\033[1;31mERR\033[0m",
            logging.CRITICAL: "\033[1;91mCRT\033[0m",
        },
    )

    def __init__(
        self,
        fmt: str = "{asctime} {levelname} {name} {message}",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        style: Literal["%", "{", "$"] = "{",
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def formatMessage(self, record: logging.LogRecord) -> str:  # noqa: N802
        """Подменяет отображение уровня логирования цветным аналогом."""
        record = copy(record)
        record.levelname = self.levels[record.levelno]

        if "aiohttp" in record.name:
            record.name = "Server"

        record.name = f"{record.name}:".ljust(_LOGGER_NAME_SIZE)

        if color_msg := getattr(record, COLOR_MSG, None):
            record.msg = color_msg
            record.message = record.getMessage()

        return super().formatMessage(record)


def config(app: actor.App, level: int | str = logging.INFO) -> None:
    """Настраивает логирование в stdout."""
    stream_handler = _TelegramHandler(app)
    stream_handler.setFormatter(_ColorFormatter())

    logging.basicConfig(
        level=level,
        handlers=[stream_handler],
    )
