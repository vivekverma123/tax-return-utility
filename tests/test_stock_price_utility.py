import json
import os
import pytest
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from datetime import datetime
from stockpriceutility import StockPriceUtility
from exchangerateutility import ExchangeRateUtility

@pytest.fixture
def test_case_data():
    data = None
    test_file = os.path.join(os.path.dirname(__file__), "test_stock_price_utility_data.json")
    with open(test_file, "r") as f:
        data = json.load(f)
    yield data

def retrieve_queried_collection(dates, start_date):
    idx = 0
    start_date_timestamp = datetime.strptime(start_date, "%Y-%m-%d")
    while(datetime.strptime(dates[idx], "%Y-%m-%d") < start_date_timestamp):
        idx += 1
    return dates[idx:]

def test_stock_price_utility_all_days(test_case_data):
    trading_days = test_case_data
    exchg_rt_utl = ExchangeRateUtility()
    stockpriceutil = StockPriceUtility("MSFT", "2023-01-01", "2023-12-31", exchg_rt_utl)
    trading_days_retrieved = list(stockpriceutil.date_to_peak_price.keys())
    trading_days_retrieved.sort()
    trading_days_retrieved = retrieve_queried_collection(trading_days_retrieved, '2023-01-01')
    assert trading_days_retrieved == trading_days

