"""Тесты для загрузки локальных данных по дивидендам."""
import pandas as pd
import pytest

from poptimizer.data.adapters.gateways import dividends
from poptimizer.shared import col


@pytest.mark.asyncio
async def test_div_gateway(mocker):
    """Форматирование загруженного DataFrame."""
    fake_collection = mocker.Mock()
    fake_cursor = mocker.AsyncMock()
    fake_collection.find.return_value = fake_cursor
    fake_cursor.to_list.return_value = [
        {"date": 2, "dividends": 1, "currency": col.RUR},
        {"date": 2, "dividends": 2, "currency": col.USD},
        {"date": 1, "dividends": 4, "currency": col.RUR},
    ]

    gw = dividends.DividendsGateway(fake_collection)
    df = await gw.__call__("AKRN")

    assert df.columns.tolist() == ["AKRN", col.CURRENCY]
    assert df.index.tolist() == [1, 2, 2]
    assert df.values.tolist() == [
        [4, col.RUR],
        [1, col.RUR],
        [2, col.USD],
    ]


@pytest.mark.asyncio
async def test_div_gateway_wrong_currency(mocker):
    """Ошибка при неверном наименовании валюты."""
    fake_collection = mocker.Mock()
    fake_cursor = mocker.AsyncMock()
    fake_collection.find.return_value = fake_cursor
    fake_cursor.to_list.return_value = [
        {"date": 2, "dividends": 1, "currency": "rur"},
    ]

    with pytest.raises(expected_exception=dividends.WrongCurrencyError):
        gw = dividends.DividendsGateway(fake_collection)
        await gw.__call__("AKRN")


@pytest.mark.asyncio
async def test_div_gateway_empty_data(mocker):
    """Регрессионный тест на пустые данные в базе."""
    fake_collection = mocker.Mock()
    fake_cursor = mocker.AsyncMock()
    fake_collection.find.return_value = fake_cursor
    fake_cursor.to_list.return_value = []

    gw = dividends.DividendsGateway(fake_collection)
    df = await gw.__call__("ISKJ")

    pd.testing.assert_frame_equal(df, pd.DataFrame(columns=["ISKJ", col.CURRENCY]))
