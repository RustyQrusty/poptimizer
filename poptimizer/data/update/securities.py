"""Обновляет информацию о торгуемых бумагах."""
import asyncio
import itertools
import logging
from datetime import datetime
from typing import ClassVar, Final

import aiohttp
import aiomoex
from pydantic import Field, validator

from poptimizer.core import domain, repository
from poptimizer.core.exceptions import DataUpdateError

_PREFERRED_TYPE: Final = "2"
_PREFERRED_SUFFIX: Final = "P"

_FOREIGN_BOARD: Final = "FQBR"
_FOREIGN_SUFFIX: Final = "-RM"

_MARKETS_BOARDS: Final = (
    ("shares", "TQBR"),
    ("shares", "TQTF"),
    ("foreignshares", "FQBR"),
)

_COLUMNS: Final = (
    "SECID",
    "LOTSIZE",
    "ISIN",
    "BOARDID",
    "SECTYPE",
    "INSTRID",
)


class Security(domain.Row):

    """Информация об отдельной бумаге.

    Бумага может быть выбрана для включения в портфель и отслеживания дивидендов.
    """

    ticker: str = Field(alias="SECID")
    lot: int = Field(alias="LOTSIZE")
    isin: str = Field(alias="ISIN")
    board: str = Field(alias="BOARDID")
    type: str = Field(alias="SECTYPE")
    instrument: str = Field(alias="INSTRID")

    @property
    def is_preferred(self) -> bool:
        """Является ли акция привилегированной."""
        return self.type == _PREFERRED_TYPE

    @property
    def is_foreign(self) -> bool:
        """Является ли акция иностранной."""
        return self.board == _FOREIGN_BOARD

    @property
    def ticker_base(self) -> str:
        """Базовый тикер без суффикса привилегированной или иностранной акции."""
        if self.is_preferred:
            return self.ticker.removesuffix(_PREFERRED_SUFFIX)

        if self.is_foreign:
            return self.ticker.removesuffix(_FOREIGN_SUFFIX)

        return self.ticker


class Table(domain.BaseEntity):

    """Таблица с торгуемыми бумагами."""

    group: ClassVar[domain.Group] = domain.Group.SECURITIES
    df: list[Security] = Field(default_factory=list[Security])

    def update(self, update_day: datetime, rows: list[Security]) -> None:
        """Обновляет таблицу."""
        self.timestamp = update_day

        rows.sort(key=lambda sec: sec.ticker)

        self.df = rows

    @validator("df")
    def _must_be_sorted_by_ticker(cls, df: list[Security]) -> list[Security]:
        ticker_pairs = itertools.pairwise(row.ticker for row in df)

        if not all(ticker < next_ for ticker, next_ in ticker_pairs):
            raise ValueError("tickers are not sorted")

        return df


class Service:

    """Сервис обновления перечня торгуемых бумаг."""

    def __init__(self, repo: repository.Repo, session: aiohttp.ClientSession) -> None:
        self._logger = logging.getLogger("Securities")
        self._repo = repo
        self._session = session

    async def update(self, update_day: datetime) -> list[Security]:
        """Обновляет перечень торгуемых бумаг, и переносит список выбранных ранее."""
        sec = await self._update(update_day)

        self._logger.info("update is completed")

        return sec

    async def _update(self, update_day: datetime) -> list[Security]:
        table = await self._repo.get(Table)

        rows = await self._download()

        table.update(update_day, rows)

        await self._repo.save(table)

        return table.df

    @DataUpdateError.wrap_errors("can't update securities")
    async def _download(self) -> list[Security]:
        aws = [
            aiomoex.get_board_securities(
                self._session,
                market=market,
                board=board,
                columns=_COLUMNS,
            )
            for market, board in _MARKETS_BOARDS
        ]
        json_list = await asyncio.gather(*aws)
        json = list(itertools.chain(*json_list))

        return domain.Rows[Security].parse_obj(json).__root__
