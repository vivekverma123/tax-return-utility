from datetime import datetime, timedelta
import json
import os

from unittest.mock import patch
import pandas as pd
import pytest
from src.exchangerateutility import ExchangeRateUtility


@pytest.fixture
def test_data():
    test_file = os.path.join(os.path.dirname(__file__), "test_exchange_rate_data.json")
    with open(test_file, "r", encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def mock_exchange_data(test_data): # pylint: disable=W0621
    data = test_data["mock_exchange_rates"]
    return pd.DataFrame({
        'DATE': data["dates"],
        'PDF_FILE': data["pdf_files"],
        'TT_BUY': data["tt_buy_rates"]
    })


@patch('pandas.read_csv')
def test_exchange_rate_utility_initialization(mock_read_csv, mock_exchange_data, test_data): # pylint: disable=W0621
    mock_read_csv.return_value = mock_exchange_data

    util = ExchangeRateUtility()

    rates = test_data["mock_exchange_rates"]
    for i, date_str in enumerate(rates["dates"]):
        date_key = date_str.split(" ")[0]
        assert date_key in util.date_to_rate
        assert util.date_to_rate[date_key] == rates["tt_buy_rates"][i]


@patch('pandas.read_csv')
def test_get_exchange_rate_exact_date(mock_read_csv, mock_exchange_data, test_data): # pylint: disable=W0621
    mock_read_csv.return_value = mock_exchange_data

    util = ExchangeRateUtility()
    rate, date = util.get_exchange_rate('2023-01-01')

    expected_rate = test_data["mock_exchange_rates"]["tt_buy_rates"][0]
    assert rate == expected_rate
    assert date == '2023-01-01'


@patch('pandas.read_csv')
def test_get_exchange_rate_fallback_to_previous_day(mock_read_csv, test_data): # pylint: disable=W0621
    mock_read_csv.return_value = pd.DataFrame({
        'DATE': test_data["fallback_tests"][0]["available_dates"],
        'PDF_FILE': ['file1.pdf', 'file2.pdf', 'file3.pdf'],
        'TT_BUY': [82.5, 82.7, 82.3]
    })

    util = ExchangeRateUtility()
    fallback_case = test_data["fallback_tests"][0]
    rate, date = util.get_exchange_rate(fallback_case["query_date"])

    assert rate == fallback_case["expected_fallback_rate"]
    assert date == fallback_case["expected_fallback_date"]


@patch('pandas.read_csv')
def test_get_exchange_rate_weekend_fallback(mock_read_csv, test_data): # pylint: disable=W0621
    mock_read_csv.return_value = pd.DataFrame({
        'DATE': test_data["fallback_tests"][1]["available_dates"],
        'PDF_FILE': ['file1.pdf', 'file2.pdf', 'file3.pdf'],
        'TT_BUY': [82.5, 82.7, 82.3]
    })

    util = ExchangeRateUtility()
    fallback_case = test_data["fallback_tests"][1]
    rate, date = util.get_exchange_rate(fallback_case["query_date"])

    assert rate == fallback_case["expected_fallback_rate"]
    assert date == fallback_case["expected_fallback_date"]


@patch('pandas.read_csv')
def test_get_exchange_rate_last_month(mock_read_csv, test_data): # pylint: disable=W0621
    data = test_data["multi_month_test"]
    mock_read_csv.return_value = pd.DataFrame({
        'DATE': data["dates"],
        'PDF_FILE': data["pdf_files"],
        'TT_BUY': data["tt_buy_rates"]
    })

    util = ExchangeRateUtility()
    rate, date = util.get_exchange_rate_last_month(data["query_date"])

    assert rate == data["expected_rate"]
    assert date == data["expected_date"]


def test_get_last_date_of_previous_month(test_data): # pylint: disable=W0621
    util = ExchangeRateUtility.__new__(ExchangeRateUtility)

    for case in test_data["date_calculation_tests"]:
        result = util._get_last_date_of_previous_month(case["input_date"]) # pylint: disable=W0212
                                                                           # it's a legitimate testcase
        assert result == case["expected_last_month"]


@patch('pandas.read_csv')
def test_exchange_rate_with_zero_values(mock_read_csv, test_data): # pylint: disable=W0621
    zero_case = test_data["zero_rate_test"]
    mock_read_csv.return_value = pd.DataFrame({
        'DATE': zero_case["dates"],
        'PDF_FILE': zero_case["pdf_files"],
        'TT_BUY': zero_case["tt_buy_rates"]
    })

    util = ExchangeRateUtility()
    rate, date = util.get_exchange_rate(zero_case["test_date"])

    assert rate == zero_case["expected_rate"]
    assert date == zero_case["expected_date"]


@patch('pandas.read_csv')
def test_exchange_rate_data_not_available_error(mock_read_csv): # pylint: disable=W0621
    mock_read_csv.return_value = pd.DataFrame({
        'DATE': ['2023-01-01 00:00:00'],
        'PDF_FILE': ['file1.pdf'],
        'TT_BUY': [82.5]
    })

    util = ExchangeRateUtility()

    # Request a date far before available data should raise assertion
    with pytest.raises(AssertionError, match="Data not available for the requested date"):
        util.get_exchange_rate('2019-01-01')


@patch('pandas.read_csv')
def test_traverse_helper_method(mock_read_csv, mock_exchange_data, test_data): # pylint: disable=W0621
    mock_read_csv.return_value = mock_exchange_data

    util = ExchangeRateUtility()

    # Test the internal _traverse method
    check_func = lambda temp: temp >= util.lower_limit  # pylint: disable=C3001
    update_func = lambda temp: temp - timedelta(days=1)  # pylint: disable=C3001
                                                         # it's a legitimate testcase
    start_temp = datetime.strptime('2023-01-03', '%Y-%m-%d')

    rate, temp_date = util._traverse(check_func, update_func, start_temp) # pylint: disable=W0212
                                                                          # it's a legitimate testcase

    expected_rate = test_data["mock_exchange_rates"]["tt_buy_rates"][1]
    assert rate == expected_rate
    assert temp_date == '2023-01-02'
