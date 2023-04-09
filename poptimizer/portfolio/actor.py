"""Актор обновления стоимости и оборачиваемости портфеля."""
import logging
from datetime import datetime
from typing import Final

import pandas as pd

from poptimizer.adapters import market_data
from poptimizer.core import consts, repository
from poptimizer.core.actor import Ctx
from poptimizer.portfolio import entity

CURRENT_ID: Final = "Current"


class Portfolio:
    """Актор обновления стоимости и оборачиваемости портфеля."""

    def __init__(self, repo: repository.Repo, data_adapter: market_data.Adapter) -> None:
        self._logger = logging.getLogger("Portfolio")
        self._repo = repo
        self._data_adapter = data_adapter

    async def __call__(self, ctx: Ctx, msg: datetime) -> None:  # noqa: ARG002
        """Обновляет стоимость и оборачиваемости портфеля."""
        await self._update(msg)

        self._logger.info("update is completed")

    async def _update(self, update_day: datetime) -> None:
        port = await self._repo.get(entity.Portfolio, CURRENT_ID)

        if not port.positions:
            return

        port = await self._update_lots(port)
        port = await self._update_market_data(port, update_day)

        await self._save_portfolio(port, update_day)

    async def _save_portfolio(self, port: entity.Portfolio, update_day: datetime) -> None:
        if port.timestamp < update_day:
            port.timestamp = update_day

            port_old = port.copy()
            port_old.id_ = port.timestamp.date().isoformat()
            await self._repo.save(port_old)

        await self._repo.save(port)

    async def _update_lots(self, port: entity.Portfolio) -> entity.Portfolio:
        lots = (await self._data_adapter.securities())[market_data.Columns.LOT]

        for pos in port.positions:
            pos.lot = int(lots[pos.ticker])

        return port

    async def _update_market_data(self, port: entity.Portfolio, update_day: datetime) -> entity.Portfolio:
        tickers = tuple(pos.ticker for pos in port.positions)
        quotes = (await self._data_adapter.price(update_day, tickers)).iloc[-1]
        turnovers = await self._prepare_turnover(update_day, tickers)

        for pos in port.positions:
            ticker = pos.ticker
            pos.price = float(quotes[ticker])
            pos.turnover = float(turnovers[ticker])

        return port

    async def _prepare_turnover(self, update_day: datetime, tickers: tuple[str, ...]) -> pd.Series:
        turnover = await self._data_adapter.turnover(update_day, tickers)
        turnover_last = turnover.iloc[consts.LIQUIDITY_DAYS_UPPER :]
        backward_expanding_median = turnover_last.sort_index(ascending=False).expanding().median()

        return backward_expanding_median.iloc[consts.LIQUIDITY_DAYS_LOWER :].min()
