"""Метка данных."""
from typing import Tuple

import torch

from poptimizer.config import DEVICE, FORECAST_DIV
from poptimizer.dl.features import data_params
from poptimizer.dl.features.feature import Feature, FeatureType


class Label(Feature):
    """Метка - полная доходность за определенный период."""

    def __init__(self, ticker: str, params: data_params.DataParams):
        super().__init__(ticker, params)
        div = torch.tensor(params.div(ticker).values, dtype=torch.float, device=DEVICE)
        self.cum_div = torch.cumsum(div, dim=0)
        self.price = torch.tensor(params.price(ticker).values, dtype=torch.float, device=DEVICE)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        price = self.price
        div = self.cum_div

        start = item + self.history_days - 1
        last_history_price = price[start]
        last_history_div = div[start]

        end = start + data_params.FORECAST_DAYS
        last_forecast_price = price[end]
        last_forecast_div = div[end]

        div = last_forecast_div - last_history_div
        price_growth = last_forecast_price - last_history_price
        label = (price_growth * (1 - FORECAST_DIV) + div) / last_history_price
        return label.reshape(-1)

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.LABEL, data_params.FORECAST_DAYS
