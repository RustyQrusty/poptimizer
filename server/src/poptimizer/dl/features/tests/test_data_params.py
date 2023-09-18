import pandas as pd
import pytest

from poptimizer.data.app import bootstrap
from poptimizer.dl.features import data_params

TICKERS = ("CBOM", "DSKY", "IRKT")
DATE = pd.Timestamp("2020-03-17")

PARAMS = {
    "batch_size": 100,
    "history_days": 16,
    "features": {"Label": {"on": True}, "Prices": {"on": True}, "Turnover": {"on": False}},
}


@pytest.fixture(scope="function", autouse=True)
def set_split(monkeypatch):
    monkeypatch.setattr(data_params, "FORECAST_DAYS", 240)
    monkeypatch.setattr(bootstrap, "START_DATE", pd.Timestamp("2010-09-01"))
    yield


def test_div_price_train_size():
    div, price, train_size = data_params.div_price_train_size(TICKERS, DATE)
    assert isinstance(div, pd.DataFrame)
    assert isinstance(price, pd.DataFrame)
    assert isinstance(train_size, int)

    assert tuple(div.columns) == TICKERS
    assert tuple(price.columns) == TICKERS

    assert div.index[0] == pd.Timestamp("2010-09-01")
    assert price.index[0] == pd.Timestamp("2010-09-01")

    assert div.index[-1] == pd.Timestamp("2020-03-17")
    assert price.index[-1] == pd.Timestamp("2020-03-17")

    assert price.loc["2010-09-01", "IRKT"] == pytest.approx(8.962)
    assert div.loc["2014-07-17", "DSKY"] == pytest.approx(0)
    assert price.loc["2020-03-17", "CBOM"] == pytest.approx(5.072)

    assert train_size == 2158


@pytest.fixture(scope="function", name="train_params")
def make_train_params():
    yield data_params.TrainParams(TICKERS, DATE, PARAMS)


class TestTrainParams:
    def test_shuffle(self, train_params):
        assert train_params.shuffle is True

    def test_history_days(self, train_params):
        assert train_params.history_days == 16

    def test_batch_size(self, train_params):
        assert train_params.batch_size == 100

    def test_price(self, train_params):
        df = train_params.price("CBOM")
        assert isinstance(df, pd.Series)
        assert df.index[0] == pd.Timestamp("2015-07-01")
        assert df.index[-1] == pd.Timestamp("2019-04-02")
        assert df[pd.Timestamp("2019-03-19")] == pytest.approx(5.952)

    def test_div(self, train_params):
        df = train_params.div("DSKY")
        assert isinstance(df, pd.Series)
        assert df.index[0] == pd.Timestamp("2017-02-10")
        assert df.index[-1] == pd.Timestamp("2019-04-02")
        assert df[pd.Timestamp("2017-07-14")] == pytest.approx(3.48 * 0.87)

    def test_len(self, train_params):
        assert train_params.len("CBOM") == 927 + 7 - 239
        assert train_params.len("DSKY") == 517 + 7 - 239
        assert train_params.len("IRKT") == 2135 + 7 - 239

    def test_get_all_feat(self, train_params):
        assert list(train_params.get_all_feat()) == ["Label", "Prices"]

    def test_get_feat_params(self, train_params):
        assert train_params.get_feat_params("Label") == {"on": True}


@pytest.fixture(scope="function", name="test_params")
def make_test_params():
    yield data_params.TestParams(TICKERS, DATE, PARAMS)


class TestTestParams:
    def test_shuffle(self, test_params):
        assert test_params.shuffle is False

    def test_price(self, test_params):
        df = test_params.price("IRKT")
        assert isinstance(df, pd.Series)
        assert df.index[0] == pd.Timestamp("2019-03-12")
        assert df.index[-1] == pd.Timestamp("2020-03-17")
        assert df[pd.Timestamp("2020-03-16")] == pytest.approx(28.9)

    def test_div(self, test_params):
        df = test_params.div("CBOM")
        assert isinstance(df, pd.Series)
        assert df.index[0] == pd.Timestamp("2019-03-12")
        assert df.index[-1] == pd.Timestamp("2020-03-17")
        assert df[pd.Timestamp("2019-06-06")] == pytest.approx(0.11 * 0.87)

    def test_len(self, test_params):
        assert test_params.len("CBOM") == 1
        assert test_params.len("DSKY") == 1
        assert test_params.len("IRKT") == 1

    def test_get_all_feat(self, test_params):
        assert list(test_params.get_all_feat()) == ["Label", "Prices"]


@pytest.fixture(scope="function", name="forecast_params")
def make_forecast_params():
    yield data_params.ForecastParams(TICKERS, DATE, PARAMS)


class TestForecastParams:
    def test_shuffle(self, forecast_params):
        assert forecast_params.shuffle is False

    def test_price(self, forecast_params):
        df = forecast_params.price("IRKT")
        assert isinstance(df, pd.Series)
        assert df.index[0] == pd.Timestamp("2020-02-21")
        assert df.index[-1] == pd.Timestamp("2020-03-17")
        assert df[pd.Timestamp("2020-03-16")] == pytest.approx(28.9)

    def test_div(self, forecast_params):
        df = forecast_params.div("CBOM")
        assert isinstance(df, pd.Series)
        assert df.index[0] == pd.Timestamp("2020-02-21")
        assert df.index[-1] == pd.Timestamp("2020-03-17")
        assert df[pd.Timestamp("2020-03-04")] == pytest.approx(0)

    def test_len(self, forecast_params):
        assert forecast_params.len("CBOM") == 1
        assert forecast_params.len("DSKY") == 1
        assert forecast_params.len("IRKT") == 1

    def test_get_all_feat(self, forecast_params):
        assert list(forecast_params.get_all_feat()) == ["Prices"]
