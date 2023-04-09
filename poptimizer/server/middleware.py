"""Middleware для перехвата ошибок и исправления низкой точности времени uvloop для логирования."""
import time

from aiohttp import web
from aiohttp.typedefs import Handler
from pydantic import ValidationError

from poptimizer.core.exceptions import ClientError
from poptimizer.server import logger


@web.middleware
async def set_start_time_and_headers(
    request: web.Request,
    handler: Handler,
) -> web.StreamResponse:
    """Устанавливает время поступления запроса для логирования и заголовок сервера.

    Время начала обработки нужно для логирования, так как при использовании uvloop оно вычисляется с точностью до 1мс.
    Дополнительно устанавливается заголовок сервера.
    """
    request[logger.START_TIME] = time.monotonic()

    response = await handler(request)

    response.headers["Server"] = "POptimizer"

    return response


@web.middleware
async def error(
    request: web.Request,
    handler: Handler,
) -> web.StreamResponse:
    """Преобразует ошибки в web.HTTPBadRequest для пользовательских ошибок."""
    try:
        return await handler(request)
    except (ValidationError, ClientError) as err:
        reason = str(err)
        raise web.HTTPBadRequest(text=reason.splitlines()[0], reason=reason)
