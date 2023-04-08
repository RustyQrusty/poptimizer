"""Сборка отдельных компонент."""
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.adapters import market_data, portfolio
from poptimizer.app import config, lgr, telegram
from poptimizer.core import actor, repository
from poptimizer.data.actor import MarketData
from poptimizer.data.update import cpi, divs, indexes, quotes, securities, trading_date, usd
from poptimizer.data.update.raw import check_raw, nasdaq, reestry, status
from poptimizer.portfolio.actor import Portfolio


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


def create_data_updater(http: aiohttp.ClientSession, mongo: AsyncIOMotorClient, refs: list[actor.Ref]) -> MarketData:
    """Создает актора обновления рыночных данных."""
    repo = repository.Repo(mongo)
    portfolio_data = portfolio.Adapter(repo)

    return MarketData(
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
        refs,
    )


def create_portfolio_updater(mongo: AsyncIOMotorClient) -> Portfolio:
    """Создает актора обновления стоимости портфеля."""
    repo = repository.Repo(mongo)
    data_adapter = market_data.Adapter(repo)

    return Portfolio(repo, data_adapter)
