"""Асинхронные акторы.

Отдельные модули приложения запускаются в виде акторов, которые могут посылать сообщения другим компонентам.
"""
from __future__ import annotations

import asyncio
import logging
import weakref
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Final, Protocol, Self, runtime_checkable

import pydantic

if TYPE_CHECKING:
    from types import TracebackType

_Logger: Final = logging.getLogger("POptimizer")


class Ref:
    """Ref ссылка на актора."""

    def __init__(self, actor: Actor) -> None:
        self._name = actor.__class__.__name__

    def __str__(self) -> str:
        """Строковое представление ID."""
        return f"{self._name}"


@runtime_checkable
class Ctx(Protocol):
    """Контекст обработки сообщения актором."""

    async def done(self) -> bool:
        """Блокируется, пока контекст работает и возвращает True, когда останавливается.

        Позволяет долгоиграющим задачам отслеживать момент, когда необходимо завершиться.
        """

    def spawn(self, actor: Actor) -> Ref:
        """Запустить дочернего актора."""

    def send(self, msg: Any, to: Ref) -> None:
        """Отправить сообщение по ссылке."""


class SystemMsg(StrEnum):
    """Системные сообщения.

    Актор может реагировать на них, чтобы инициализировать или высвободить ресурсы.
    """

    STARTING = auto()
    STOPPING = auto()


class Actor(Protocol):
    """Актор - умеет асинхронно обрабатывать сообщения."""

    async def __call__(self, ctx: Ctx, msg: Any) -> None:
        """Обрабатывает сообщение."""


class _Context:
    """Управляет жизненным циклом актора."""

    def __init__(
        self,
        dispatcher: _Dispatcher,
        actor: Actor,
    ) -> None:
        self._ref = Ref(actor)
        self._dispatcher = dispatcher
        inbox = dispatcher.register(self._ref)
        self._done = asyncio.Event()
        self._actor = asyncio.create_task(self._runner(actor, inbox))
        self._children: set[_Context] = set()

    @property
    def ref(self) -> Ref:
        return self._ref

    async def done(self) -> bool:
        """Блокируется, пока контекст работает и возвращает True, когда останавливается.

        Позволяет долгоиграющим задачам отслеживать момент, когда необходимо завершиться.
        """
        return await self._done.wait()

    def spawn(self, actor: Actor) -> Ref:
        """Запускает дочернего актора и возвращает ссылку на него."""
        ctx = _Context(self._dispatcher, actor)
        self._children.add(ctx)

        return ctx.ref

    async def shutdown(self) -> None:
        """Дожидается обработки всех сообщений и останавливает актора."""
        async with asyncio.TaskGroup() as tg:
            for child in self._children:
                tg.create_task(child.shutdown())

        self._done.set()
        self.send(SystemMsg.STOPPING, self.ref)
        await self._actor

    def send(self, msg: Any, to: Ref) -> None:
        """Передает сообщение по указанной ссылке."""
        self._dispatcher.send(msg, to)

    async def _runner(self, actor: Actor, inbox: asyncio.Queue[Any]) -> None:
        validator = pydantic.validate_arguments(config={"arbitrary_types_allowed": True})
        validated_actor = validator(actor.__call__)
        inbox.put_nowait(SystemMsg.STARTING)

        stopping = False

        while not stopping or inbox.qsize():
            msg = await inbox.get()

            if isinstance(msg, SystemMsg):
                _Logger.info("%s %s", self._ref, msg)
                stopping = msg == SystemMsg.STOPPING
            try:
                await validated_actor(self, msg)
            except ValueError as err:
                if not isinstance(msg, SystemMsg):
                    _Logger.warning("%s can't process %s -> %s", self._ref, msg, err)
            except Exception as err:  # noqa: BLE001
                _Logger.warning("%s can't process %s -> %s", self._ref, msg, err)

            inbox.task_done()

        _Logger.info("%s stopped", self._ref)


class _Dispatcher:
    def __init__(self) -> None:
        self._inboxes: weakref.WeakValueDictionary[Ref, asyncio.Queue[Any]] = weakref.WeakValueDictionary()

    def register(self, ref: Ref) -> asyncio.Queue[Any]:
        return self._inboxes.setdefault(ref, asyncio.Queue())

    def send(self, msg: Any, to: Ref) -> None:
        """Послать сообщение по заданной ссылке."""
        if inbox := self._inboxes.get(to):
            inbox.put_nowait(msg)
        else:
            _Logger.warning("can't deliver %s to %s", msg, to)


class Root(_Context):
    """Приложение для запуска акторов."""

    def __init__(self, root: Actor) -> None:
        super().__init__(_Dispatcher(), root)

    async def __aenter__(self) -> Self:
        """Контекстный менеджер ждет CancelledError и завершает работу акторов."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Контекстный менеджер ждет CancelledError и завершает работу акторов."""
        try:
            await asyncio.shield(self._actor)
        except asyncio.CancelledError:
            _Logger.info("shutdown signal received...")
            await self.shutdown()
