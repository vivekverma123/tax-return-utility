import csv
import os

from dataclasses import dataclass
from enum import Enum
from typing import List

class TransactionType(Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    SPLIT = "split"

@dataclass
class Transaction:
    account: "InvestmentAccount"
    # Same as InvestmentAccount.unique_id
    account_id: str
    """
    Uniquely determines a lot of stocks, it's on the user to assign/maintain appropriate value here, the code will only
    perform minimal validation
    """
    date: str
    stock: str
    # Assign unique lot id, lot id's across different stocks shouldn't conflict under the same account
    lot_id: str
    transaction_type: TransactionType
    units: int
    buy_price: float
    sell_price: float

@dataclass
class InvestmentAccount:
    """
    Not same as account number, but a unique ID within this system in case multiple security accounts held by the
    individual. It's on the user to ensure that this ID is unique and all the transactions refer this ID in the
    separate CSV file
    """
    account_id: str
    account_no: str
    broker: str
    address: str
    zip_code: str
    country: str
    currency: str

class LedgerLoader:

    def __init__(self, path):
        self.path = path
        self.accounts = []
        self.transactions = []
        self.id_to_account = {}
        self._initialize()

    def _detect_format(self, header: List[str]) -> str:
        if header == ['account_id', 'account_no', 'broker', 'address', 'zip_code', 'country', 'currency']:
            return 'account'
        if header == ['account_id', 'date', 'stock', 'lot_id', 'transaction_type', 'units', 'buy_price',
                        'sell_price']:
            return 'transaction'
        return 'unknown'

    def _process_account(self, reader, id_to_account):
        for row in reader:
            account = InvestmentAccount(
                account_id=row['account_id'],
                account_no=row['account_no'],
                broker=row['broker'],
                address=row['address'],
                zip_code=row['zip_code'],
                country=row['country'],
                currency=row['currency'],
            )
            id_to_account[account.account_id] = account
            self.accounts.append(account)

    def _process_transaction(self, reader):
        for row in reader:
            transaction = Transaction(
                account=None,
                account_id=row.get('account_id') or -1,
                date=row['date'],
                stock=row['stock'],
                lot_id=row.get('lot_id') or -1,
                transaction_type=TransactionType[row['transaction_type'].upper()],
                units=int(row['units']),
                buy_price=float(row.get('buy_price') or 0.0),
                sell_price=float(row.get('sell_price') or 0.0)
            )
            self.transactions.append(transaction)

    def _link_transactions_to_accounts(self, id_to_account):
        for transaction in self.transactions:
            if transaction.account_id in id_to_account:
                transaction.account = id_to_account[transaction.account_id]
        transaction_type_to_key = {
            TransactionType.SPLIT: 0,
            TransactionType.CREDIT: 1,
            TransactionType.DEBIT: 2
        }
        self.transactions.sort(
            key=lambda x: (
                x.date,
                x.stock,
                transaction_type_to_key[x.transaction_type]
            )
        )

    def _initialize(self):
        id_to_account = {}
        for filename in os.listdir(self.path):
            if not filename.endswith('.csv'):
                continue
            path = os.path.join(self.path, filename)
            with open(path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fmt = self._detect_format(reader.fieldnames)
                if fmt == 'account':
                    self._process_account(reader, id_to_account)
                elif fmt == 'transaction':
                    self._process_transaction(reader)
                else:
                    print(f"Skipping unknown format file: {filename}")
        self._link_transactions_to_accounts(id_to_account)

    def get_accounts(self):
        return self.accounts

    def get_transactions(self):
        return self.transactions
