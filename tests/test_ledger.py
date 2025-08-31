import csv
import json
import os
import tempfile
from unittest.mock import patch

import pytest
from src.ledger import LedgerLoader, InvestmentAccount, Transaction, TransactionType


@pytest.fixture
def test_data():
    test_file = os.path.join(os.path.dirname(__file__), "test_ledger_data.json")
    with open(test_file, "r", encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_account_csv(temp_dir, test_data): # pylint: disable=W0621
    csv_path = os.path.join(temp_dir, "accounts.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['account_id', 'account_no', 'broker', 'address', 'zip_code', 'country', 'currency'])
        for account in test_data["sample_accounts"]:
            writer.writerow([
                account["account_id"], account["account_no"], account["broker"],
                account["address"], account["zip_code"], account["country"], account["currency"]
            ])
    return csv_path


@pytest.fixture
def sample_transaction_csv(temp_dir, test_data): # pylint: disable=W0621
    csv_path = os.path.join(temp_dir, "transactions.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['account_id', 'date', 'stock', 'lot_id', 'transaction_type', \
            'units', 'buy_price', 'sell_price'])
        for transaction in test_data["sample_transactions"]:
            writer.writerow([
                transaction["account_id"], transaction["date"], transaction["stock"],
                transaction["lot_id"], transaction["transaction_type"], transaction["units"],
                transaction["buy_price"], transaction["sell_price"]
            ])
    return csv_path


def test_ledger_loader_initialization(temp_dir, sample_transaction_csv, # pylint: disable=W0621, W0613
                                      sample_account_csv, test_data): # pylint: disable=W0621, W0613
    loader = LedgerLoader(temp_dir)

    assert len(loader.accounts) == len(test_data["sample_accounts"])
    assert len(loader.transactions) == len(test_data["sample_transactions"])

    # Check accounts loaded correctly
    account_ids = [acc.account_id for acc in loader.accounts]
    for account in test_data["sample_accounts"]:
        assert account["account_id"] in account_ids


def test_account_format_detection(temp_dir, test_data): # pylint: disable=W0621
    loader = LedgerLoader(temp_dir)

    for case in test_data["format_detection_cases"]:
        result = loader._detect_format(case["header"]) # pylint: disable=W0212
                                                       # it's a legitimate testcase
        assert result == case["expected_format"]


def test_transaction_linking(temp_dir, sample_transaction_csv, # pylint: disable=W0621, W0613
                             sample_account_csv, test_data): # pylint: disable=W0621, W0613
    loader = LedgerLoader(temp_dir)

    # Check transactions are linked to correct accounts
    aapl_transactions = [t for t in loader.transactions if t.stock == 'AAPL']
    aapl_count = len([t for t in test_data["sample_transactions"] if t["stock"] == "AAPL"])
    assert len(aapl_transactions) == aapl_count
    assert all(t.account.account_id == 'ACC001' for t in aapl_transactions)

    msft_transactions = [t for t in loader.transactions if t.stock == 'MSFT']
    msft_count = len([t for t in test_data["sample_transactions"] if t["stock"] == "MSFT"])
    assert len(msft_transactions) == msft_count
    if msft_transactions:
        assert msft_transactions[0].account.account_id == 'ACC002'


def test_transaction_sorting(temp_dir): # pylint: disable=W0621
    loader = LedgerLoader(temp_dir)

    # Transactions should be sorted by date, stock, transaction_type
    dates = [t.date for t in loader.transactions]
    assert dates == sorted(dates)


def test_transaction_type_parsing(temp_dir, test_data): # pylint: disable=W0621
    csv_path = os.path.join(temp_dir, "transactions.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['account_id', 'date', 'stock', 'lot_id', 'transaction_type', \
            'units', 'buy_price', 'sell_price'])
        for case in test_data["transaction_type_test_cases"]:
            writer.writerow([
                case["account_id"], case["date"], case["stock"], case["lot_id"],
                case["transaction_type"], case["units"], case["buy_price"], case["sell_price"]
            ])

    loader = LedgerLoader(temp_dir)

    for i, case in enumerate(test_data["transaction_type_test_cases"]):
        expected_type = TransactionType[case["expected_type"]]
        assert loader.transactions[i].transaction_type == expected_type


def test_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = LedgerLoader(tmpdir)
        assert len(loader.accounts) == 0
        assert len(loader.transactions) == 0


def test_non_csv_files_ignored(temp_dir): # pylint: disable=W0621
    # Create a non-CSV file
    with open(os.path.join(temp_dir, "readme.txt"), 'w', encoding='utf-8') as f:
        f.write("This should be ignored")

    loader = LedgerLoader(temp_dir)
    assert len(loader.accounts) == 0
    assert len(loader.transactions) == 0


def test_invalid_csv_format_skipped(temp_dir): # pylint: disable=W0621
    csv_path = os.path.join(temp_dir, "invalid.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['invalid', 'header', 'format'])
        writer.writerow(['data1', 'data2', 'data3'])

    with patch('builtins.print') as mock_print:
        loader = LedgerLoader(temp_dir)
        mock_print.assert_called_with("Skipping unknown format file: invalid.csv")

    assert len(loader.accounts) == 0
    assert len(loader.transactions) == 0


def test_investment_account_creation(test_data): # pylint: disable=W0621
    account_data = test_data["sample_accounts"][0]
    account = InvestmentAccount(
        account_id=account_data["account_id"],
        account_no=account_data["account_no"],
        broker=account_data["broker"],
        address=account_data["address"],
        zip_code=account_data["zip_code"],
        country=account_data["country"],
        currency=account_data["currency"]
    )

    assert account.account_id == account_data["account_id"]
    assert account.broker == account_data["broker"]
    assert account.currency == account_data["currency"]


def test_transaction_creation(test_data): # pylint: disable=W0621
    transaction_data = test_data["sample_transactions"][0]
    transaction = Transaction(
        account=None,
        account_id=transaction_data["account_id"],
        date=transaction_data["date"],
        stock=transaction_data["stock"],
        lot_id=transaction_data["lot_id"],
        transaction_type=TransactionType[transaction_data["transaction_type"].upper()],
        units=int(transaction_data["units"]),
        buy_price=float(transaction_data["buy_price"]),
        sell_price=float(transaction_data["sell_price"])
    )

    assert transaction.stock == transaction_data["stock"]
    assert transaction.units == int(transaction_data["units"])
    assert transaction.transaction_type == TransactionType[transaction_data["transaction_type"].upper()]
