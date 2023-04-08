"""Сборка отдельных компонент."""
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.adapters.portfolio import PortfolioData
from poptimizer.app import config, lgr, telegram
from poptimizer.core import actor, repository
from poptimizer.data import updater
from poptimizer.data.update import cpi, divs, indexes, quotes, securities, trading_date, usd
from poptimizer.data.update.raw import check_raw, nasdaq, reestry, status


def create_root_actor(http: aiohttp.ClientSession, cfg: config.Logger) -> actor.Root:
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


def create_updater(http: aiohttp.ClientSession, mongo: AsyncIOMotorClient) -> updater.Updater:
    """Создает сервис обновления данных."""
    repo = repository.Repo(mongo)

    portfolio_data = PortfolioData(repo)

    return updater.Updater(
        trading_date.Service(repo, http),
        cpi.Service(repo, http),
        indexes.Service(repo, http),
        securities.Service(repo, http),
        quotes.Service(repo, http),
        usd.Service(repo, http),
        divs.Service(repo),
        status.Service(repo, http, portfolio_data),
        reestry.Service(repo, http),
        nasdaq.Service(repo, http),
        check_raw.Service(repo),
        [],
    )
