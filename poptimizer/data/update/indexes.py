"""Загрузка биржевых индексов."""
import asyncio
import logging
from datetime import datetime
from typing import ClassVar, Final

import aiohttp
import aiomoex
from pydantic import Field, validator

from poptimizer.core import domain, repository
from poptimizer.core.exceptions import DataUpdateError
from poptimizer.data.update import validate

_INDEXES: Final = ("MCFTRR", "MEOGTRR", "IMOEX", "RVI")


class Index(domain.Row):

    """Котировки индекса."""

    date: datetime = Field(alias="TRADEDATE")
    close: float = Field(alias="CLOSE", gt=0)


class Table(domain.BaseEntity):

    """Таблица с котировками индекса."""

    group: ClassVar[domain.Group] = domain.Group.INDEXES
    df: list[Index] = Field(default_factory=list[Index])

    def update(self, update_day: datetime, rows: list[Index]) -> None:
        """Обновляет таблицу."""
        self.timestamp = update_day

        if not self.df:
            self.df = rows

            return

        last = self.df[-1]

        if last != (first := rows[0]):
            raise DataUpdateError(f"{self.id_} data missmatch {last} vs {first}")

        self.df.extend(rows[1:])

    def last_row_date(self) -> datetime | None:
        """Дата последней строки при наличии."""
        if not self.df:
            return None

        return self.df[-1].date

    _must_be_sorted_by_date = validator("df", allow_reuse=True)(validate.sorted_by_date)


class Service:

    """Сервис обновления котировок биржевых индексов."""

    def __init__(self, repo: repository.Repo, session: aiohttp.ClientSession) -> None:
        self._logger = logging.getLogger("Index")
        self._repo = repo
        self._session = session

    async def update(self, update_day: datetime) -> None:
        """Обновляет котировки биржевых индексов."""
        coro = [self._update_one(update_day, index) for index in _INDEXES]
        await asyncio.gather(*coro)

        self._logger.info("update is completed")

    async def _update_one(self, update_day: datetime, index: str) -> None:
        table = await self._repo.get(Table, index)

        start_date = table.last_row_date()
        rows = await self._download(index, start_date, update_day)

        table.update(update_day, rows)

        await self._repo.save(table)

    @DataUpdateError.wrap_errors("can't download indexes")
    async def _download(
        self,
        index: str,
        start_date: datetime | None,
        update_day: datetime,
    ) -> list[Index]:
        json = await aiomoex.get_market_history(
            session=self._session,
            start=start_date and str(start_date.date()),
            end=str(update_day.date()),
            security=index,
            columns=(
                "TRADEDATE",
                "CLOSE",
            ),
            market="index",
        )

        return domain.Rows[Index].parse_obj(json).__root__
