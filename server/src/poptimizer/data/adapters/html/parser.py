"""Парсер html-таблиц."""
import ssl
from datetime import datetime
from typing import Callable, List, Union

import aiohttp
import bs4
import certifi
import pandas as pd

from poptimizer.data.adapters.html import description
from poptimizer.shared import connections

Descriptions = List[description.ColDesc]
ParseFuncType = Callable[[str], Union[None, float, datetime]]


async def get_html(
    url: str,
    session: aiohttp.ClientSession = connections.HTTP_SESSION,
) -> str:
    """Загружает html-код страницы."""
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    async with session.get(url, ssl_context=ssl_context) as respond:
        try:
            respond.raise_for_status()
        except aiohttp.ClientResponseError:
            raise description.ParserError(f"Данные {url} не загружены")
        return await respond.text()


def _get_table_from_html(html: str, table_num: int) -> str:
    """Выбирает таблицу по номеру из html-страницы."""
    soup = bs4.BeautifulSoup(html, "lxml")
    try:
        table = soup.find_all("table")[table_num]
    except IndexError:
        raise description.ParserError(f"На странице нет таблицы {table_num}")
    return f"<html>{table}</html>"


def _get_raw_df(table: str, cols_desc: Descriptions) -> pd.DataFrame:
    """Формирует изначальный DataFrame из html-таблицы."""
    converters = {desc.num: desc.parser_func for desc in cols_desc if desc.parser_func is not None}
    raw_name = cols_desc[0].raw_name
    num_of_headers = len(raw_name)
    header_nums = list(range(num_of_headers))

    return pd.read_html(
        table,
        header=header_nums,
        converters=converters,
        thousands=" ",
        displayed_only=False,
    )[0]


def _validate_header(columns: pd.Index, cols_desc: Descriptions) -> None:
    """Проверяет, что заголовки соответствуют описанию."""
    for desc in cols_desc:
        header = columns[desc.num]
        if not isinstance(header, tuple):
            header = [header]
        raw_name = desc.raw_name
        if all(part in name for part, name in zip(raw_name, header)):
            continue
        raise description.ParserError(f"Неверный заголовок: {desc.raw_name} не входит в {header}")


def _get_selected_col(df: pd.DataFrame, cols_desc: Descriptions) -> pd.DataFrame:
    """Выбирает столбцы в соответствии с описанием и форматирует их."""
    selected_col = [desc.num for desc in cols_desc]
    df = df.iloc[:, selected_col]
    df.columns = [desc.name for desc in cols_desc]
    index_name = cols_desc[0].name
    return df.set_index(index_name)


def get_df_from_html(html: str, table_num: int, cols_desc: Descriptions) -> pd.DataFrame:
    """Получает таблицу из html-страницы и форматирует ее в соответствии с описанием."""
    table = _get_table_from_html(html, table_num)
    df = _get_raw_df(table, cols_desc)
    _validate_header(df.columns, cols_desc)
    return _get_selected_col(df, cols_desc)


async def get_df_from_url(url: str, table_num: int, cols_desc: Descriptions) -> pd.DataFrame:
    """Загружает таблицу по URL и форматирует ее в соответствии с описанием."""
    html = await get_html(url)
    return get_df_from_html(html, table_num, cols_desc)
