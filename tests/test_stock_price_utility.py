from datetime import datetime
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from stockpriceutility import StockPriceUtility # pylint: disable=E0401, C0413
from exchangerateutility import ExchangeRateUtility # pylint: disable=E0401, C0413

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

def test_stock_price_utility_all_days(test_case_data): # pylint: disable=W0621
    trading_days = test_case_data
    exchg_rt_utl = ExchangeRateUtility()
    stockpriceutil = StockPriceUtility("MSFT", "2023-01-01", "2023-12-31", exchg_rt_utl)
    trading_days_retrieved = list(stockpriceutil.date_to_peak_price.keys())
    trading_days_retrieved.sort()
    trading_days_retrieved = retrieve_queried_collection(trading_days_retrieved, '2023-01-01')
    assert trading_days_retrieved == trading_days

def test_stock_price_utility_inclusivity(test_case_data): # # pylint: disable=W0621
    exchg_rt_utl = ExchangeRateUtility()
    stockpriceutil = StockPriceUtility("MSFT", test_case_data[0], test_case_data[-1], exchg_rt_utl)
    assert test_case_data[-1] in stockpriceutil.date_to_peak_price.keys()
    assert test_case_data[0] in stockpriceutil.date_to_peak_price.keys()
