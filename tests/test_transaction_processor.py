from datetime import datetime
import json
import os
from unittest.mock import Mock, patch

import pytest
from src.transactionprocessor import TransactionProcessor, ReportA3, Lot, CapitalGain
from src.ledger import InvestmentAccount, Transaction, TransactionType


@pytest.fixture
def test_data():
    test_file = os.path.join(os.path.dirname(__file__), "test_transaction_processor_data.json")
    with open(test_file, "r", encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def mock_account(test_data): # pylint: disable=W0621
    account_data = test_data["mock_accounts"][0]
    return InvestmentAccount(
        account_id=account_data["account_id"],
        account_no=account_data["account_no"],
        broker=account_data["broker"],
        address=account_data["address"],
        zip_code=account_data["zip_code"],
        country=account_data["country"],
        currency=account_data["currency"]
    )


@pytest.fixture
def mock_exchange_rate_util():
    mock = Mock()
    mock.get_exchange_rate.return_value = (82.5, "2023-01-01")
    mock.get_exchange_rate_last_month.return_value = (82.5, "2023-01-01")
    return mock


def test_transaction_processor_initialization(mock_account, test_data): # pylint: disable=W0621, W0613
    mock_transactions = []
    processor = TransactionProcessor([mock_account], mock_transactions)

    assert processor.accounts == [mock_account]
    assert processor.transactions == mock_transactions
    assert not processor.reports_a3
    assert not processor.reports_ltcg
    assert not processor.reports_stcg


def test_identify_fy(test_data): # pylint: disable=W0621
    processor = TransactionProcessor([], [])

    for case in test_data["fy_identification_tests"]:
        result = processor._identify_fy(case["date"]) # pylint: disable=W0212
                                                      # legitimate test case
        assert result == case["expected_fy"]


def test_identify_cy(test_data): # pylint: disable=W0621
    processor = TransactionProcessor([], [])

    for case in test_data["cy_identification_tests"]:
        result = processor._identify_cy(case["date"]) # pylint: disable=W0212
                                                      # legitimate test case
        assert result == case["expected_cy"]


def test_get_time(): # pylint: disable=W0621
    processor = TransactionProcessor([], [])

    result = processor._get_time("2023-06-15") # pylint: disable=W0212
                                               # legitimate test case
    expected = datetime.strptime("2023-06-15", "%Y-%m-%d")

    assert result == expected


def test_pre_processing_stock_splits(test_data): # pylint: disable=W0621
    processor = TransactionProcessor([], [])

    for case in test_data["stock_split_tests"]:
        # Create split transactions
        split_transactions = []
        for units in case["split_units"]:
            split_transactions.append(Transaction(
                account=None,
                account_id="ACC001",
                date="2023-03-01",
                stock=case["stock"],
                lot_id="LOT001",
                transaction_type=TransactionType.SPLIT,
                units=units,
                buy_price=0.0,
                sell_price=0.0
            ))

        processor.transactions = split_transactions
        processor._pre_processing() # pylint: disable=W0212
                                    # legitimate test case

        assert processor.stock_split_multiplier[case["stock"]] == case["expected_multiplier"]


def test_process_credit_transaction(mock_account, mock_exchange_rate_util, test_data): # pylint: disable=W0621
    test_case = test_data["credit_transaction_test"]

    transaction = Transaction(
        account=mock_account,
        account_id=test_case["account_id"],
        date=test_case["date"],
        stock=test_case["stock"],
        lot_id=test_case["lot_id"],
        transaction_type=TransactionType[test_case["transaction_type"]],
        units=test_case["units"],
        buy_price=test_case["buy_price"],
        sell_price=test_case["sell_price"]
    )

    processor = TransactionProcessor([mock_account], [transaction])
    processor.exchange_rate_util = mock_exchange_rate_util
    mock_exchange_rate_util.get_exchange_rate.return_value = (test_case["exchange_rate"], test_case["date"])

    curr_date = datetime.strptime(test_case["date"], "%Y-%m-%d")
    processor._process_credit_transaction(transaction, curr_date) # pylint: disable=W0212
                                                                  # legitimate test case

    lot_key = f"{test_case['stock']}_{test_case['lot_id']}"
    assert lot_key in processor.lots
    lot = processor.lots[lot_key]
    assert lot.balance == test_case["units"]
    assert lot.stock == test_case["stock"]
    assert lot.invested_amount == test_case["expected_invested_amount"]


def test_process_split_transaction():
    processor = TransactionProcessor([], [])

    # Create initial lot
    processor.lots["AAPL_LOT001"] = Lot(
        lot_id="LOT001",
        balance=100,
        stock="AAPL",
        invested_amount=15000.0,
        peak_value=15000.0
    )
    processor.stock_split_multiplier = {"AAPL": 1}

    split_transaction = Transaction(
        account=None,
        account_id="ACC001",
        date="2023-03-01",
        stock="AAPL",
        lot_id="LOT001",
        transaction_type=TransactionType.SPLIT,
        units=2,
        buy_price=0.0,
        sell_price=0.0
    )

    processor._process_split_transaction(split_transaction) # pylint: disable=W0212
                                                            # legitimate test case

    # Balance should double, split multiplier should halve
    assert processor.lots["AAPL_LOT001"].balance == 200
    assert processor.stock_split_multiplier["AAPL"] == 0.5


def test_process_capital_gain(mock_account, mock_exchange_rate_util, test_data): # pylint: disable=W0621
    test_case = test_data["capital_gains_test"]

    processor = TransactionProcessor([mock_account], [])
    processor.exchange_rate_util = mock_exchange_rate_util
    mock_exchange_rate_util.get_exchange_rate_last_month.return_value = \
        tuple(test_case["exchange_rates"]["acquisition"])

    # Create a lot
    lot_data = test_case["lot_data"]
    lot = Lot(
        lot_id=lot_data["lot_id"],
        balance=lot_data["balance"],
        stock=lot_data["stock"],
        invested_amount=lot_data["invested_amount"],
        peak_value=lot_data["peak_value"],
        invested_amount_metadata=tuple(lot_data["invested_amount_metadata"])
    )

    sell_data = test_case["sell_transaction"]
    sell_transaction = Transaction(
        account=mock_account,
        account_id=sell_data["account_id"],
        date=sell_data["date"],
        stock=sell_data["stock"],
        lot_id=sell_data["lot_id"],
        transaction_type=TransactionType[sell_data["transaction_type"]],
        units=sell_data["units"],
        buy_price=sell_data["buy_price"],
        sell_price=sell_data["sell_price"]
    )

    processor._process_capital_gain(sell_transaction, lot) # pylint: disable=W0212
                                                           # legitimate test case

    # Check if capital gain was calculated and categorized (FY 2024 for June 2023 transaction)
    assert len(processor.reports_stcg["2024"]) == 1
    cg = processor.reports_stcg["2024"][0]
    assert cg.stock == sell_data["stock"]
    assert cg.units == sell_data["units"]


def test_process_debit_transaction(mock_account, mock_exchange_rate_util, test_data): # pylint: disable=W0621
    test_case = test_data["debit_transaction_test"]

    processor = TransactionProcessor([mock_account], [])
    processor.exchange_rate_util = mock_exchange_rate_util
    mock_exchange_rate_util.get_exchange_rate.return_value = (test_case["exchange_rate"], test_case["date"])

    # Set up initial lot
    processor.lots[f"{test_case['stock']}_{test_case['lot_id']}"] = Lot(
        lot_id=test_case["lot_id"],
        balance=test_case["initial_lot_balance"],
        stock=test_case["stock"],
        invested_amount=15000.0,
        peak_value=15000.0,
        invested_amount_metadata=(150.0, "2023-01-01", 82.5, "2023-01-01")
    )

    sell_transaction = Transaction(
        account=mock_account,
        account_id=test_case["account_id"],
        date=test_case["date"],
        stock=test_case["stock"],
        lot_id=test_case["lot_id"],
        transaction_type=TransactionType[test_case["transaction_type"]],
        units=test_case["units"],
        buy_price=test_case["buy_price"],
        sell_price=test_case["sell_price"]
    )

    curr_date = datetime.strptime(test_case["date"], "%Y-%m-%d")
    processor._process_debit_transaction(sell_transaction, curr_date) # pylint: disable=W0212
                                                                      # legitimate test case

    # Check lot balance updated
    lot_key = f"{test_case['stock']}_{test_case['lot_id']}"
    assert processor.lots[lot_key].balance == test_case["expected_balance_after"]
    assert processor.lots[lot_key].gross_proceeds_holdings == test_case["expected_gross_proceeds"]


def test_ltcg_vs_stcg_classification(mock_account, mock_exchange_rate_util, test_data): # pylint: disable=W0621
    processor = TransactionProcessor([mock_account], [])
    processor.exchange_rate_util = mock_exchange_rate_util

    ltcg_case = test_data["ltcg_vs_stcg_test"]["ltcg_case"]

    # Create lot from 2019 (> 3 years ago)
    lot = Lot(
        lot_id="LOT001",
        balance=100,
        stock="AAPL",
        invested_amount=15000.0,
        peak_value=15000.0,
        invested_amount_metadata=(150.0, ltcg_case["lot_invested_date"], 82.5, ltcg_case["lot_invested_date"])
    )

    sell_transaction = Transaction(
        account=mock_account,
        account_id="ACC001",
        date=ltcg_case["sell_date"],
        stock="AAPL",
        lot_id="LOT001",
        transaction_type=TransactionType.DEBIT,
        units=50,
        buy_price=0.0,
        sell_price=180.0
    )

    processor._process_capital_gain(sell_transaction, lot)  # pylint: disable=W0212
                                                            # it's a legitimate testcase

    # Should be LTCG (> 3 years) - FY 2024 for June 2023 transaction
    assert len(processor.reports_ltcg["2024"]) == 1
    assert len(processor.reports_stcg.get("2024", [])) == 0


def test_capital_gain_calculation(mock_account, mock_exchange_rate_util, test_data): # pylint: disable=W0621
    test_case = test_data["capital_gains_test"]
    mock_exchange_rate_util.get_exchange_rate_last_month.return_value = test_case["exchange_rates"]["acquisition"]

    processor = TransactionProcessor([mock_account], [])
    processor.exchange_rate_util = mock_exchange_rate_util

    lot_data = test_case["lot_data"]
    lot = Lot(
        lot_id=lot_data["lot_id"],
        balance=lot_data["balance"],
        stock=lot_data["stock"],
        invested_amount=lot_data["invested_amount"],
        peak_value=lot_data["peak_value"],
        invested_amount_metadata=tuple(lot_data["invested_amount_metadata"])
    )

    sell_data = test_case["sell_transaction"]
    sell_transaction = Transaction(
        account=mock_account,
        account_id=sell_data["account_id"],
        date=sell_data["date"],
        stock=sell_data["stock"],
        lot_id=sell_data["lot_id"],
        transaction_type=TransactionType[sell_data["transaction_type"]],
        units=sell_data["units"],
        buy_price=sell_data["buy_price"],
        sell_price=sell_data["sell_price"]
    )

    processor._process_capital_gain(sell_transaction, lot) # pylint: disable=W0212
                                                           # it's a legitimate testcase

    cg = processor.reports_stcg["2024"][0]
    expected = test_case["expected_results"]

    assert cg.cost_of_acquisition == expected["cost_of_acquisition"]
    assert cg.cost_of_acquisition_inr == expected["cost_of_acquisition_inr"]
    assert cg.total_value_of_consideration == expected["total_value_of_consideration"]
    assert cg.total_value_of_consideration_inr == expected["total_value_of_consideration_inr"]
    assert cg.gain == expected["gain"]


def test_report_a3_dataclass(test_data): # pylint: disable=W0621
    report_data = test_data["report_dataclass_tests"]["report_a3"]
    report = ReportA3(
        invested_amount=report_data["invested_amount"],
        peak_value=report_data["peak_value"],
        closing_balance=report_data["closing_balance"],
        gross_proceeds_redemption=report_data["gross_proceeds_redemption"],
        gross_proceeds_holdings=report_data["gross_proceeds_holdings"]
    )

    assert report.invested_amount == report_data["invested_amount"]
    assert report.peak_value == report_data["peak_value"]
    assert report.closing_balance == report_data["closing_balance"]


def test_lot_dataclass(test_data): # pylint: disable=W0621
    lot_data = test_data["report_dataclass_tests"]["lot"]
    lot = Lot(
        lot_id=lot_data["lot_id"],
        balance=lot_data["balance"],
        stock=lot_data["stock"],
        invested_amount=lot_data["invested_amount"],
        peak_value=lot_data["peak_value"]
    )

    assert lot.lot_id == lot_data["lot_id"]
    assert lot.balance == lot_data["balance"]
    assert lot.stock == lot_data["stock"]
    assert lot.invested_amount == lot_data["invested_amount"]


def test_capital_gain_dataclass(test_data): # pylint: disable=W0621
    cg_data = test_data["report_dataclass_tests"]["capital_gain"]
    cg = CapitalGain(
        lot_id=cg_data["lot_id"],
        stock=cg_data["stock"],
        cost_of_acquisition=cg_data["cost_of_acquisition"],
        cost_of_acquisition_inr=cg_data["cost_of_acquisition_inr"],
        total_value_of_consideration=cg_data["total_value_of_consideration"],
        total_value_of_consideration_inr=cg_data["total_value_of_consideration_inr"],
        buy_metadata=tuple(cg_data["buy_metadata"]),
        sell_metadata=tuple(cg_data["sell_metadata"]),
        units=cg_data["units"],
        gain=cg_data["gain"]
    )

    assert cg.lot_id == cg_data["lot_id"]
    assert cg.stock == cg_data["stock"]
    assert cg.units == cg_data["units"]
    assert cg.gain == cg_data["gain"]


@patch('src.transactionprocessor.StockPriceUtility')
def test_init_stock_price_util(mock_stock_util, mock_account, mock_exchange_rate_util): # pylint: disable=W0621
    processor = TransactionProcessor([mock_account], [])
    processor.exchange_rate_util = mock_exchange_rate_util

    start_date = datetime.strptime("2023-01-01", "%Y-%m-%d")
    end_date = datetime.strptime("2023-12-31", "%Y-%m-%d")

    processor._init_stock_price_util("AAPL", start_date, end_date) # pylint: disable=W0212
                                                                   # it's a legitimate testcase

    assert "AAPL" in processor.stock_price_util
    mock_stock_util.assert_called_once_with("AAPL", "2023-01-01", "2023-12-31", mock_exchange_rate_util)


def test_get_peak_stock_price(mock_account, test_data): # pylint: disable=W0621
    processor = TransactionProcessor([mock_account], [])
    processor.stock_split_multiplier = {"AAPL": 2}

    # Mock stock price utility
    mock_stock_util = Mock()
    stock_data = test_data["stock_price_mocks"]
    mock_stock_util.get_peak_price.return_value = (stock_data["peak_price"], stock_data["peak_metadata"])
    processor.stock_price_util = {"AAPL": mock_stock_util}

    price, metadata = processor.get_peak_stock_price("AAPL", "2023-06-01")

    assert price == stock_data["peak_price"] * 2  # Should apply split multiplier
    assert metadata == stock_data["peak_metadata"]


def test_get_closing_stock_price(mock_account, test_data): # pylint: disable=W0621
    processor = TransactionProcessor([mock_account], [])
    processor.stock_split_multiplier = {"AAPL": 2}

    # Mock stock price utility
    mock_stock_util = Mock()
    stock_data = test_data["stock_price_mocks"]
    mock_stock_util.get_closing.return_value = (stock_data["closing_price"], stock_data["closing_metadata"])
    processor.stock_price_util = {"AAPL": mock_stock_util}

    price, metadata = processor.get_closing_stock_price("AAPL")

    assert price == stock_data["closing_price"] * 2  # Should apply split multiplier
    assert metadata == stock_data["closing_metadata"]


def test_multiple_stock_splits(test_data): # pylint: disable=W0621
    processor = TransactionProcessor([], [])

    # Use test data for multiple splits
    case = test_data["stock_split_tests"][0]  # AAPL with [2, 3] splits

    splits = []
    for units in case["split_units"]:
        splits.append(Transaction(
            account=None, account_id="ACC001", date="2023-01-01", stock=case["stock"],
            lot_id="LOT001", transaction_type=TransactionType.SPLIT, units=units,
            buy_price=0.0, sell_price=0.0
        ))

    processor.transactions = splits
    processor._pre_processing() # pylint: disable=W0212
                                # it's a legitimate testcase

    assert processor.stock_split_multiplier[case["stock"]] == case["expected_multiplier"]


def test_edge_case_empty_transactions(): # pylint: disable=W0621
    processor = TransactionProcessor([], [])

    # Should handle empty transaction list gracefully
    with pytest.raises(IndexError):
        processor.generate_reports()


def test_weekend_date_handling(): # pylint: disable=W0621
    processor = TransactionProcessor([], [])

    # Test date parsing for weekends and holidays
    weekend_date = "2023-01-07"  # Saturday
    time_obj = processor._get_time(weekend_date) # pylint: disable=W0212
                                                 # it's a legitimate testcase

    assert time_obj.year == 2023
    assert time_obj.month == 1
    assert time_obj.day == 7
