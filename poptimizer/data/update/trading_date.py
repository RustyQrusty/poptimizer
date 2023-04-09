"""Информация о торговых днях."""
from datetime import datetime
from typing import ClassVar

import aiohttp
import aiomoex
from pydantic import BaseModel, Field, validator

from poptimizer.core import domain, repository
from poptimizer.core.exceptions import DataUpdateError


class _TradingDate(domain.Row):
    date: datetime = Field(alias="till")


class _Payload(BaseModel):
    df: list[_TradingDate]

    def last_date(self) -> datetime:
        """Возвращает последнюю дату торгов."""
        return self.df[0].date

    @validator("df")
    def _must_be_one_row(cls, df: list[_TradingDate]) -> list[_TradingDate]:
        """Строка с данными о торговых днях - должна быть одна."""
        if (count := len(df)) != 1:
            raise ValueError(f"wrong rows count {count}")

        return df


class Table(domain.BaseEntity):

    """Таблица с информацией о последней торговой дате."""

    group: ClassVar[domain.Group] = domain.Group.TRADING_DATE
    id_: str = Field(default=domain.Group.TRADING_DATE.group, alias="_id", exclude=True)
    timestamp: datetime = datetime.fromtimestamp(0)


class Service:

    """Сервис обновления таблицы с данными о торговых днях."""

    def __init__(self, repo: repository.Repo, session: aiohttp.ClientSession) -> None:
        self._repo = repo
        self._session = session

    async def get_date_from_local_store(self) -> datetime:
        """Выдает последнюю торговую дату, сохраненную локально."""
        table = await self._repo.get(Table)

        return table.timestamp

    @DataUpdateError.wrap_errors("can't download trading dates")
    async def get_date_from_iss(self) -> datetime:
        """Получает информацию о последней торговой дате c MOEX ISS."""
        json = await aiomoex.get_board_dates(
            self._session,
            board="TQBR",
            market="shares",
            engine="stock",
        )

        return _Payload.parse_obj({"df": json}).last_date()

    async def save(self, timestamp: datetime) -> None:
        """Сохраняет информацию о торговой дате."""
        table = Table(timestamp=timestamp)

        await self._repo.save(table)
