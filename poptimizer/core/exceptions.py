"""Базовая ошибка приложения."""
import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

import aiohttp
from pydantic import BaseModel, Field

_FuncParams = ParamSpec("_FuncParams")
_FuncReturn = TypeVar("_FuncReturn")


class _ErrorWrapper:

    """Асинхронный декоратор для обертывания внешних ошибок."""

    def __init__(
        self,
        errs: tuple[type[Exception], ...],
        to_err: type[Exception],
        msg: str,
    ) -> None:
        self._errs = errs
        self._to_err = to_err
        self._msg = msg

    def __call__(
        self,
        func: Callable[_FuncParams, Awaitable[_FuncReturn]],
    ) -> Callable[_FuncParams, Awaitable[_FuncReturn]]:
        """Декоратор обертывающий ошибку в другую с сообщением."""

        @wraps(func)
        async def _wrap(
            *args: _FuncParams.args,
            **kwargs: _FuncParams.kwargs,
        ) -> _FuncReturn:
            try:
                return await func(*args, **kwargs)
            except self._errs as err:
                raise self._to_err(self._msg) from err

        return _wrap


class _ErrorSuppressor:

    """Асинхронный декоратор для подавления и логирования ошибки."""

    def __init__(
        self,
        errs: tuple[type[Exception], ...],
        logger: logging.Logger,
    ) -> None:
        self._errs = errs
        self._logger = logger

    def __call__(
        self,
        func: Callable[_FuncParams, Awaitable[_FuncReturn]],
    ) -> Callable[_FuncParams, Awaitable[_FuncReturn | None]]:
        """Декоратор логирует и игнорирует ошибку."""

        @wraps(func)
        async def _wrap(
            *args: _FuncParams.args,
            **kwargs: _FuncParams.kwargs,
        ) -> _FuncReturn | None:
            try:
                return await func(*args, **kwargs)
            except self._errs as err:
                self._logger.warning("can't complete update -> %s", err)

                return None

        return _wrap


class _Policy(BaseModel):

    """Политика осуществления повторов."""

    attempts: int = Field(ge=2)
    start_timeout_sec: float = Field(gt=0)
    factor: float = Field(ge=1)
    exceptions: type[Exception] | tuple[type[Exception], ...]


class _ExponentialRetryer:

    """Асинхронный декоратор для экспоненциального повторного вызова асинхронных функций."""

    def __init__(
        self,
        policy: _Policy,
        logger: logging.Logger,
    ) -> None:
        self._attempts = policy.attempts
        self._start_timeout_sec = policy.start_timeout_sec
        self._factor = policy.factor
        self._exceptions = policy.exceptions
        self._logger = logger

    def __call__(
        self,
        func: Callable[_FuncParams, Awaitable[_FuncReturn]],
    ) -> Callable[_FuncParams, Awaitable[_FuncReturn]]:
        """Асинхронный декоратор, осуществляющий повторный вызов в случае исключений."""

        @wraps(func)
        async def _wrap(
            *args: _FuncParams.args,
            **kwargs: _FuncParams.kwargs,
        ) -> _FuncReturn:
            timeout = self._start_timeout_sec
            count = 1

            while True:
                try:
                    return await func(*args, **kwargs)
                except self._exceptions as err:
                    self._logger.debug("attempt %d -> %s", count, err)

                    last_exc = err

                if count == self._attempts:
                    raise last_exc

                await asyncio.sleep(timeout)

                timeout *= self._factor
                count += 1

        return _wrap


class POError(Exception):

    """Базовая ошибка приложения."""

    def __str__(self) -> str:
        """Выводи исходную причину ошибки при ее наличии для удобства логирования.

        https://peps.python.org/pep-3134/
        """
        errs = [repr(self)]
        cause_err: BaseException | None = self

        while cause_err := cause_err and (cause_err.__cause__ or cause_err.__context__):
            errs.append(repr(cause_err))

        return " -> ".join(errs)


class DataUpdateError(POError):

    """Ошибка модуля обновления данных."""

    @classmethod
    def wrap_errors(cls, msg: str) -> _ErrorWrapper:
        """Асинхронный декоратор для обертывания внешних ошибок."""
        return _ErrorWrapper((aiohttp.ClientError, asyncio.TimeoutError), cls, msg)

    @classmethod
    def suppress_errors(cls, logger: logging.Logger) -> _ErrorSuppressor:
        """Асинхронный декоратор для подавления и логирования ошибки."""
        return _ErrorSuppressor((cls, aiohttp.ClientError, asyncio.TimeoutError), logger)

    @classmethod
    def retry_on_error(cls, logger: logging.Logger) -> _ExponentialRetryer:
        """Асинхронный декоратор для экспоненциального повторного вызова асинхронных функций."""
        policy = _Policy(
            attempts=3,
            start_timeout_sec=60,
            factor=2,
            exceptions=(cls, aiohttp.ClientError, asyncio.TimeoutError),
        )

        return _ExponentialRetryer(policy, logger)


class ClientError(POError):

    """Ошибки обусловленные некорректными данными, переданными web-клиентом."""
