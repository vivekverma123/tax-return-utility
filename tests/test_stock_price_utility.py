from datetime import datetime
import json
import os


from unittest.mock import Mock, patch
import pandas as pd
import pytest
from src.stockpriceutility import StockPriceUtility
from src.exchangerateutility import ExchangeRateUtility

@pytest.fixture
def test_case_data():
    data = None
    test_file = os.path.join(os.path.dirname(__file__), "test_stock_price_utility_data.json")
    with open(test_file, "r", encoding='utf-8') as f:
        data = json.load(f)
    yield data

def retrieve_queried_collection(dates, start_date):
    idx = 0
    start_date_timestamp = datetime.strptime(start_date, "%Y-%m-%d")
    while datetime.strptime(dates[idx], "%Y-%m-%d") < start_date_timestamp:
        idx += 1
    return dates[idx:]

def test_all_days(test_case_data): # pylint: disable=W0621
    trading_days = test_case_data
    exchg_rt_utl = ExchangeRateUtility()
    stockpriceutil = StockPriceUtility("MSFT", "2023-01-01", "2023-12-31", exchg_rt_utl)
    trading_days_retrieved = list(stockpriceutil.date_to_peak_price.keys())
    trading_days_retrieved.sort()
    trading_days_retrieved = retrieve_queried_collection(trading_days_retrieved, '2023-01-01')
    assert trading_days_retrieved == trading_days

def test_inclusivity(test_case_data): # pylint: disable=W0621
    exchg_rt_utl = ExchangeRateUtility()
    stockpriceutil = StockPriceUtility("MSFT", test_case_data[0], test_case_data[-1], exchg_rt_utl)
    assert test_case_data[-1] in stockpriceutil.date_to_peak_price
    assert test_case_data[0] in stockpriceutil.date_to_peak_price


@patch('yfinance.Ticker')
def test_stock_price_utility_initialization(mock_ticker):
    # Mock exchange rate utility
    mock_exchange_util = Mock()
    mock_exchange_util.get_exchange_rate.return_value = (82.5, "2023-01-01")

    # Mock yfinance data
    mock_history_data = pd.DataFrame({
        'Date': [datetime(2023, 1, 1), datetime(2023, 1, 2)],
        'High': [155.0, 157.0],
        'Open': [150.0, 154.0],
        'Close': [154.0, 156.0]
    })
    mock_history_data.set_index('Date', inplace=True)

    mock_ticker_instance = Mock()
    mock_ticker_instance.history.return_value = mock_history_data
    mock_ticker.return_value = mock_ticker_instance

    util = StockPriceUtility("AAPL", "2023-01-01", "2023-01-02", mock_exchange_util)

    assert util.stock == "AAPL"
    assert util.start_date == "2023-01-01"
    assert util.end_date == "2023-01-02"
    assert "2023-01-01" in util.date_to_peak_price
    assert "2023-01-02" in util.date_to_peak_price


@patch('yfinance.Ticker')
def test_get_peak_price_exact_date(mock_ticker):
    mock_exchange_util = Mock()
    mock_exchange_util.get_exchange_rate.return_value = (82.5, "2023-01-01")

    mock_history_data = pd.DataFrame({
        'Date': [datetime(2023, 1, 1)],
        'High': [155.0],
        'Open': [150.0],
        'Close': [154.0]
    })
    mock_history_data.set_index('Date', inplace=True)

    mock_ticker_instance = Mock()
    mock_ticker_instance.history.return_value = mock_history_data
    mock_ticker.return_value = mock_ticker_instance

    util = StockPriceUtility("AAPL", "2023-01-01", "2023-01-01", mock_exchange_util)

    price_inr, metadata = util.get_peak_price("2023-01-01")

    assert price_inr == 155.0 * 82.5
    assert metadata[0] == 155.0  # USD price
    assert metadata[1] == "2023-01-01"  # date used


@patch('yfinance.Ticker')
def test_get_peak_price_fallback_to_previous_day(mock_ticker):
    mock_exchange_util = Mock()
    mock_exchange_util.get_exchange_rate.return_value = (82.5, "2023-01-01")

    # Only data for Jan 1, but querying Jan 3
    mock_history_data = pd.DataFrame({
        'Date': [datetime(2023, 1, 1)],
        'High': [155.0],
        'Open': [150.0],
        'Close': [154.0]
    })
    mock_history_data.set_index('Date', inplace=True)

    mock_ticker_instance = Mock()
    mock_ticker_instance.history.return_value = mock_history_data
    mock_ticker.return_value = mock_ticker_instance

    util = StockPriceUtility("AAPL", "2023-01-01", "2023-01-03", mock_exchange_util)

    # Should fallback to Jan 1 data when querying Jan 3
    price_inr, metadata = util.get_peak_price("2023-01-03")

    assert price_inr == 155.0 * 82.5
    assert metadata[1] == "2023-01-01"  # Should show fallback date


@patch('yfinance.Ticker')
def test_get_closing_price(mock_ticker):
    mock_exchange_util = Mock()
    mock_exchange_util.get_exchange_rate.return_value = (82.5, "2023-01-02")

    mock_history_data = pd.DataFrame({
        'Date': [datetime(2023, 1, 1), datetime(2023, 1, 2)],
        'High': [155.0, 157.0],
        'Open': [150.0, 154.0],
        'Close': [154.0, 156.0]
    })
    mock_history_data.set_index('Date', inplace=True)

    mock_ticker_instance = Mock()
    mock_ticker_instance.history.return_value = mock_history_data
    mock_ticker.return_value = mock_ticker_instance

    util = StockPriceUtility("AAPL", "2023-01-01", "2023-01-02", mock_exchange_util)

    price_inr, metadata = util.get_closing()

    assert price_inr == 156.0 * 82.5  # Last closing price * exchange rate
    assert metadata[0] == 156.0  # USD closing price


@patch('yfinance.Ticker')
def test_date_out_of_range_error(mock_ticker):
    mock_exchange_util = Mock()
    mock_exchange_util.get_exchange_rate.return_value = (82.5, "2023-01-01")

    mock_history_data = pd.DataFrame({
        'Date': [datetime(2023, 1, 1)],
        'High': [155.0],
        'Open': [150.0],
        'Close': [154.0]
    })
    mock_history_data.set_index('Date', inplace=True)

    mock_ticker_instance = Mock()
    mock_ticker_instance.history.return_value = mock_history_data
    mock_ticker.return_value = mock_ticker_instance

    util = StockPriceUtility("AAPL", "2023-01-01", "2023-01-01", mock_exchange_util)

    # Query date outside range should raise assertion
    with pytest.raises(AssertionError, match="requested date is out of range"):
        util.get_peak_price("2024-01-01")


@patch('yfinance.Ticker')
def test_no_stock_data_available_error(mock_ticker):
    mock_exchange_util = Mock()

    # Mock empty history response
    mock_ticker_instance = Mock()
    mock_ticker_instance.history.return_value = pd.DataFrame()
    mock_ticker.return_value = mock_ticker_instance

    with pytest.raises(AssertionError, match="data not available"):
        StockPriceUtility("INVALID", "2023-01-01", "2023-01-02", mock_exchange_util)
