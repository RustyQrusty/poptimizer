"""Сборка отдельных компонент."""
import aiohttp

from poptimizer.app import config, lgr, telegram
from poptimizer.core import actor


def root_actor(http: aiohttp.ClientSession, cfg: config.Logger) -> actor.Root:
    """Настраивает корневого актора, отвечающего за логирование, в том числе в Телеграм."""
    root = actor.Root(
        telegram.Telegram(
            http,
            cfg.telegram_level,
            cfg.telegram_token,
            cfg.telegram_chat_id,
        ),
    )
    lgr.config(root, cfg.level)

    return root
