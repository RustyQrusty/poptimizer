"""Запуск основных операций с помощью CLI."""
import logging

import typer

from poptimizer import config
from poptimizer.data.views import div_status
from poptimizer.evolve import Evolution
from poptimizer.portfolio import load_from_yaml, optimizer_hmean, optimizer_resample


LOGGER = logging.getLogger()


def evolve() -> None:
    """Run evolution."""
    ev = Evolution()
    ev.evolve()


def dividends(ticker: str) -> None:
    """Get dividends status."""
    div_status.dividends_validation(ticker)


def optimize(date: str = typer.Argument(..., help="YYYY-MM-DD"), for_sell: int = 1) -> None:
    """Optimize portfolio."""
    port = load_from_yaml(date)

    if config.OPTIMIZER == "resample":
        opt = optimizer_resample.Optimizer(port, for_sell=for_sell)
    else:
        opt = optimizer_hmean.Optimizer(port)

    LOGGER.info(opt.portfolio)
    LOGGER.info(opt.metrics)
    LOGGER.info(opt)

    div_status.new_dividends(tuple(port.index[:-2]))

def add_tickers(date: str = typer.Argument(..., help="YYYY-MM-DD")) -> None:
    """Check tickers-candidates for adding in portfolio."""
    port = load_from_yaml(date)
    port.add_tickers()
    
def remove_tickers(date: str = typer.Argument(..., help="YYYY-MM-DD")) -> None:
    """Check tickers-candidates for removing."""
    port = load_from_yaml(date)
    port.remove_tickers()
    
def all_tickers(date: str = typer.Argument(..., help="YYYY-MM-DD")) -> None:
    """All tickers on MOEX."""
    port = load_from_yaml(date)
    port.all_tickers()
    
def portfolio(date: str = typer.Argument(..., help="YYYY-MM-DD")) -> None:
    """Info about portfolio."""
    port = load_from_yaml(date)
    print(port)

if __name__ == "__main__":
    app = typer.Typer(help="Run poptimizer subcommands.", add_completion=False)

    app.command()(evolve)
    app.command()(dividends)
    app.command()(optimize)
    app.command()(add_tickers)
    app.command()(remove_tickers)
    app.command()(all_tickers)
    app.command()(portfolio)

    app(prog_name="poptimizer")
