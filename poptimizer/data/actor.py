"""Актор обновления данных."""
import asyncio
import logging
import zoneinfo
from datetime import datetime, timedelta
from typing import Final

from poptimizer.core.actor import Ctx, Ref, SystemMsg
from poptimizer.core.exceptions import DataUpdateError
from poptimizer.data.update import (
    cpi,
    divs,
    indexes,
    quotes,
    securities,
    trading_date,
    usd,
)
from poptimizer.data.update.raw import check_raw, nasdaq, reestry, status

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
_END_HOUR: Final = 0
_END_MINUTE: Final = 45

_CHECK_INTERVAL: Final = timedelta(minutes=1)
_BACK_OFF_FACTOR: Final = 2


class MarketData:
    """Актор обновления рыночных данных."""

    def __init__(  # noqa: PLR0913
        self,
        date_srv: trading_date.Service,
        cpi_srv: cpi.Service,
        indexes_srv: indexes.Service,
        securities_srv: securities.Service,
        quotes_srv: quotes.Service,
        usd_srv: usd.Service,
        dividends_srv: divs.Service,
        status_srv: status.Service,
        reestry_srv: reestry.Service,
        nasdaq_srv: nasdaq.Service,
        check_raw_srv: check_raw.Service,
        subscribers: list[Ref],
    ) -> None:
        self._logger = logging.getLogger("MarketData")
        self._check_interval = _CHECK_INTERVAL
        self._checked_day = datetime.fromtimestamp(0)

        self._date_srv = date_srv

        self._cpi_srv = cpi_srv
        self._indexes_srv = indexes_srv

        self._securities_srv = securities_srv
        self._quotes_srv = quotes_srv
        self._usd_srv = usd_srv
        self._dividends_srv = dividends_srv

        self._status_srv = status_srv
        self._reestry_srv = reestry_srv
        self._nasdaq_srv = nasdaq_srv
        self._check_raw_srv = check_raw_srv

        self._subscribers = subscribers

    async def __call__(self, ctx: Ctx, msg: SystemMsg) -> None:
        """Создает и останавливает периодическую задачу обновления данных.

        Рассылает сообщения об окончании обновления всем подписчикам.
        """
        match msg:
            case SystemMsg.STARTING:
                await self._run(ctx)

    async def _run(self, ctx: Ctx) -> None:
        self._checked_day = await self._date_srv.get_date_from_local_store()
        self._logger.info("last update on %s", self._checked_day.date())

        stopped_task = asyncio.create_task(ctx.done())

        while not stopped_task.done():
            try:
                await self._try_to_update(ctx)
            except DataUpdateError as err:
                self._check_interval *= _BACK_OFF_FACTOR
                self._logger.warning("can't complete update %s - waiting %s", err, self._check_interval)
            else:
                self._check_interval = _CHECK_INTERVAL

            await asyncio.wait((stopped_task,), timeout=self._check_interval.total_seconds())

        self._logger.info("last update on %s", self._checked_day.date())

    async def _try_to_update(self, ctx: Ctx) -> None:
        last_day = _last_day()

        if self._checked_day >= last_day:
            return

        self._logger.info("checking new trading data on %s", last_day.date())

        new_update_day = await self._date_srv.get_date_from_iss()

        if new_update_day <= self._checked_day:
            self._checked_day = last_day
            self._logger.info("update not required")

            return

        self._logger.info("update is beginning")
        await self._update(new_update_day)
        await self._date_srv.save(new_update_day)

        for ref in self._subscribers:
            ctx.send(new_update_day, ref)

        self._checked_day = last_day
        self._logger.info("update is completed")

    async def _update(self, update_day: datetime) -> None:
        await asyncio.gather(
            self._cpi_srv.update(update_day),
            self._indexes_srv.update(update_day),
            self._update_sec(update_day),
        )

    async def _update_sec(self, update_day: datetime) -> None:
        sec_list, usd_list = await asyncio.gather(
            self._securities_srv.update(update_day),
            self._usd_srv.update(update_day),
        )

        await asyncio.gather(
            self._quotes_srv.update(update_day, sec_list),
            self._dividends_srv.update(update_day, sec_list, usd_list),
            self._update_raw_div(update_day, sec_list),
        )

    async def _update_raw_div(self, update_day: datetime, sec: list[securities.Security]) -> None:
        status_rows = await self._status_srv.update(update_day, sec)

        if status_rows is not None:
            await asyncio.gather(
                self._reestry_srv.update(update_day, status_rows),
                self._nasdaq_srv.update(update_day, status_rows),
                self._check_raw_srv.check(status_rows),
            )


def _last_day() -> datetime:
    now = datetime.now(_MOEX_TZ)
    end_of_trading = now.replace(
        hour=_END_HOUR,
        minute=_END_MINUTE,
        second=0,
        microsecond=0,
        tzinfo=_MOEX_TZ,
    )

    delta = 2
    if end_of_trading < now:
        delta = 1

    return datetime(
        year=now.year,
        month=now.month,
        day=now.day,
    ) - timedelta(days=delta)
