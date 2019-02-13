"""Основные настраиваемые параметры"""
import logging
import pathlib

import pandas as pd


class POptimizerError(Exception):
    """Базовое исключение."""


# Конфигурация логгера
logging.basicConfig(level=logging.INFO)

# Количество колонок в распечатках без переноса на несколько страниц
pd.set_option("display.max_columns", 20)
pd.set_option("display.width", None)

# Путь к директории с данными
DATA_PATH = pathlib.Path(__file__).parents[1] / "data"

# Путь к директории с отчетам
REPORTS_PATH = pathlib.Path(__file__).parents[1] / "reports"

# Множитель, для переходя к после налоговым значениям
AFTER_TAX = 1 - 0.13

# Параметр для доверительных интервалов
T_SCORE = 2.0

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 0.01

# Период в торговых днях, за который медианный оборот торгов
TURNOVER_PERIOD = 21

# Минимальный оборот - преимущества акции снижаются при приближении медианного оборота к данному уровню
TURNOVER_CUT_OFF = 1.1 * MAX_TRADE

# Параметры ML-модели
LABEL_RANGE = [28, 84]
STD_RANGE = [115, 274]
MOM12M_RANGE = [250, 524]
DIVYIELD_RANGE = [240, 444]
MOM1M_RANGE = [13, 21]

ML_PARAMS = (
    (
        (True, {"days": 70}),
        (True, {"days": 138}),
        (True, {}),
        (True, {"days": 283}),
        (True, {"days": 268}),
        (True, {"days": 16}),
    ),
    {
        "bagging_temperature": 0.8358908717393394,
        "depth": 3,
        "l2_leaf_reg": 1.0970465153271944,
        "learning_rate": 0.09516559094366801,
        "one_hot_max_size": 100,
        "random_strength": 0.7279054369802683,
        "ignored_features": [],
    },
)
