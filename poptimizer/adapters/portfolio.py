"""Адаптер для просмотра данных о портфеле другими модулями."""
from poptimizer.core import domain, repository
from poptimizer.portfolio import updater


class Adapter:
    """Адаптер для просмотра информации о портфеле из других модулей."""

    def __init__(self, repo: repository.Repo) -> None:
        self._repo = repo

    async def tickers(self) -> tuple[str, ...]:
        """Упорядоченный перечень тикеров в портфеле."""
        port = await self._repo.get_doc(domain.Group.PORTFOLIO, updater.CURRENT_ID)

        return tuple(pos["ticker"] for pos in port.get("positions", []))
