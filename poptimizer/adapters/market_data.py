"""Адаптер для просмотра данных другими модулями."""
import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from enum import StrEnum, unique

import pandas as pd

from poptimizer.core import domain, repository


@unique
class Columns(StrEnum):

    """Существующие столбцы данных."""

    TICKER = "TICKER"
    LOT = "LOT"
    BOARD = "BOARD"
    TYPE = "TYPE"
    INSTRUMENT = "INSTRUMENT"

    DATE = "DATE"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    HIGH = "HIGH"
    LOW = "LOW"
    TURNOVER = "TURNOVER"


class Adapter:

    """Позволяет внешним модулям просматривать рыночную информацию в удобном виде."""

    def __init__(self, repo: repository.Repo) -> None:
        self._repo = repo

    async def securities(self) -> pd.DataFrame:
        """Информация о существующих ценных бумагах."""
        doc = await self._repo.get_doc(domain.Group.SECURITIES)

        return (
            pd.DataFrame(doc["df"])
            .drop(columns="isin")
            .rename(
                columns={
                    "ticker": Columns.TICKER,
                    "lot": Columns.LOT,
                    "board": Columns.BOARD,
                    "type": Columns.TYPE,
                    "instrument": Columns.INSTRUMENT,
                },
            )
            .set_index(Columns.TICKER)
        )

    async def turnover(self, last_date: datetime, tickers: tuple[str, ...]) -> pd.DataFrame:
        """Информация об оборотах для заданных тикеров с заполненными пропусками."""
        turnover = pd.concat(
            [df[Columns.TURNOVER] for df in await self._quotes(tickers)],
            axis=1,
            sort=True,
        )
        turnover.columns = tickers

        return turnover.fillna(0).loc[:last_date]

    async def price(
        self,
        last_date: datetime,
        tickers: tuple[str, ...],
        price_type: Columns = Columns.CLOSE,
    ) -> pd.DataFrame:
        """Информация о ценах для заданных тикеров с заполненными пропусками."""
        price = pd.concat(
            [df[price_type] for df in await self._quotes(tickers)],
            axis=1,
            sort=True,
        )
        price.columns = tickers

        return price.fillna(method="ffill").loc[:last_date]

    async def dividends(self, ticker: str) -> AsyncIterator[tuple[datetime, float]]:
        """Дивиденды для заданного тикера."""
        doc = await self._repo.get_doc(domain.Group.DIVIDENDS, ticker)

        for row in doc["df"]:
            yield row["date"], row["dividend"]

    async def _quotes(self, tickers: tuple[str, ...]) -> list[pd.DataFrame]:
        aws = [self._repo.get_doc(domain.Group.QUOTES, ticker) for ticker in tickers]
        docs = await asyncio.gather(*aws)

        return [
            pd.DataFrame(doc["df"])
            .rename(
                columns={
                    "date": Columns.DATE,
                    "open": Columns.OPEN,
                    "close": Columns.CLOSE,
                    "high": Columns.HIGH,
                    "low": Columns.LOW,
                    "turnover": Columns.TURNOVER,
                },
            )
            .set_index(Columns.DATE)
            for doc in docs
        ]
