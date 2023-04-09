"""Сервер, показывающий SPA Frontend."""
import logging

from aiohttp import web

from poptimizer.core.actor import Ctx, SystemMsg
from poptimizer.data.edit import dividends
from poptimizer.portfolio.edit import accounts, port_srv, selected
from poptimizer.server import logger, middleware, views


class Server:
    """Актор, показывающий SPA Frontend и отвечающий на Backend запросы."""

    def __init__(  # noqa: PLR0913
        self,
        host: str,
        port: int,
        selected_srv: selected.Service,
        accounts_srv: accounts.Service,
        portfolio_srv: port_srv.Service,
        dividends_srv: dividends.Service,
    ) -> None:
        self._logger = logging.getLogger("Server")
        self._host = host
        self._port = port

        self._selected_srv = selected_srv
        self._accounts_srv = accounts_srv
        self._portfolio_srv = portfolio_srv
        self._dividends_srv = dividends_srv

        self._server: web.AppRunner | None = None

    async def __call__(self, ctx: Ctx, msg: SystemMsg) -> None:  # noqa: ARG002
        """Создает и останавливает сервер."""
        match msg:
            case SystemMsg.STARTING:
                app = await self._mount_handlers_and_middleware()

                if self._server is not None:
                    self._logger.warning("already started")

                    return

                self._server = web.AppRunner(
                    app,
                    handle_signals=False,
                    access_log_class=logger.AccessLogger,
                    access_log=self._logger,
                )
                await self._server.setup()
                site = web.TCPSite(
                    self._server,
                    self._host,
                    self._port,
                )

                await site.start()

                self._logger.info(
                    "started on http://%s:%s - press CTRL+C to quit",
                    self._host,
                    self._port,
                )

            case SystemMsg.STOPPING:
                if self._server is None:
                    self._logger.warning("stopping before started")

                    return

                await self._server.cleanup()

    async def _mount_handlers_and_middleware(self) -> web.Application:
        app = web.Application(middlewares=[middleware.set_start_time_and_headers, middleware.error])

        views.Selected.register(app, self._selected_srv)
        views.Accounts.register(app, self._accounts_srv)
        views.Portfolio.register(app, self._portfolio_srv)
        views.Dividends.register(app, self._dividends_srv)
        views.Frontend.register(app)

        return app
