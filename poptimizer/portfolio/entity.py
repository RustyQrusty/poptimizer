"""Доменные объекты, связанные с портфелем."""
import bisect
import itertools
from typing import Any, ClassVar

from pydantic import BaseModel, Field, root_validator, validator

from poptimizer.core import domain
from poptimizer.core.exceptions import ClientError


class Position(BaseModel):

    """Позиция в портфеле."""

    ticker: str
    shares: dict[str, int]
    lot: int = Field(default=1, ge=1)
    price: float = Field(default=0, ge=0)
    turnover: float = Field(default=0, ge=0)

    @root_validator
    def _shares_positive_multiple_of_lots(cls, attr_dict: dict[str, Any]) -> dict[str, Any]:
        ticker = attr_dict["ticker"]
        lot = attr_dict["lot"]

        for acc, shares in attr_dict["shares"].items():
            if shares < 0:
                raise ValueError(f"{acc} {ticker} has negative shares")
            if shares % lot:
                raise ValueError(f"{acc} {ticker} is not multiple of lots {lot}")

        return attr_dict


class Portfolio(domain.BaseEntity):

    """Портфель."""

    group: ClassVar[domain.Group] = domain.Group.PORTFOLIO
    cash: dict[str, int] = Field(default_factory=dict)
    positions: list[Position] = Field(default_factory=list)

    def creat_account(self, name: str) -> None:
        """Добавляет счет в портфель."""
        if name in self.cash:
            raise ClientError(f"can't add existing account {name}")

        self.cash[name] = 0

        for pos in self.positions:
            pos.shares[name] = 0

    def remove_account(self, name: str) -> None:
        """Удаляет пустой счет из портфеля."""
        if self.cash.pop(name):
            raise ClientError(f"can't remove non empty account {name}")

        for pos in self.positions:
            if pos.shares.pop(name):
                raise ClientError(f"can't remove non empty account {name}")

    def remove_ticker(self, ticker: str) -> None:
        """Удаляет существующий пустой тикер из портфеля."""
        count = bisect.bisect_left(self.positions, ticker, key=lambda position: position.ticker)
        if count == len(self.positions):
            raise ClientError(f"no {ticker} in portfolio")
        if self.positions[count].ticker != ticker:
            raise ClientError(f"no {ticker} in portfolio")

        for shares in self.positions.pop(count).shares.values():
            if shares:
                raise ClientError(f"can't remove non empty ticker {ticker}")

    def add_ticker(self, ticker: str) -> None:
        """Добавляет отсутствующий тикер в портфель."""
        count = bisect.bisect_left(self.positions, ticker, key=lambda position: position.ticker)
        if count != len(self.positions) and self.positions[count].ticker == ticker:
            raise ClientError(f"can't add existing {ticker} in portfolio")

        shares = {acc: 0 for acc in self.cash}

        self.positions.insert(
            count,
            Position(
                ticker=ticker,
                shares=shares,
            ),
        )

    @validator("cash")
    def _cash_must_be_positive(cls, cash: dict[str, int]) -> dict[str, int]:
        for acc, acc_cash in cash.items():
            if acc_cash < 0:
                raise ValueError(f"{acc} has negative cash")

        return cash

    @validator("positions")
    def _positions_must_sorted_by_ticker(cls, positions: list[Position]) -> list[Position]:
        ticker_pairs = itertools.pairwise(row.ticker for row in positions)

        if not all(ticker < next_ for ticker, next_ in ticker_pairs):
            raise ValueError("tickers are not sorted")

        return positions

    @root_validator
    def _same_accounts(cls, attr_dict: dict[str, Any]) -> dict[str, Any]:
        account = attr_dict["cash"].keys()

        for pos in attr_dict["positions"]:
            if (pos_acc := pos.shares.keys()) != account:
                raise ValueError(f"wrong {pos_acc} for {pos.ticker}")

        return attr_dict
