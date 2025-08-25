from dataclasses import dataclass
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from exchangerateutility import ExchangeRateUtility
from ledger import TransactionType
from stockpriceutility import StockPriceUtility

@dataclass
class Report_A3:
    invested_amount: float
    peak_value: float
    closing_balance: float
    invested_amount_metadata: tuple[float, float, float, float] = (0.0, 0,0, 0.0, 0.0)
    peak_value_metadata: tuple[float, float, float, float] = (0.0, 0,0, 0.0, 0.0)
    closing_balance_metadata: tuple[float, float, float, float] = (0.0, 0,0, 0.0, 0.0)
    gross_proceeds_redemption: float = 0.0
    gross_proceeds_holdings: float = 0.0

DEBUG_DATE = ""

# Intermediate class for processing transactions
@dataclass
class Lot:
    lot_id: str
    balance: int
    stock: str
    invested_amount: float
    peak_value: float
    invested_amount_metadata: tuple[float, float, float, float] = (0.0, 0,0, 0.0, 0.0)
    peak_value_metadata: tuple[float, float, float, float] = (0.0, 0,0, 0.0, 0.0)
    gross_proceeds_holdings: float = 0.0

class TransactionProcessor:

    def __init__(self, accounts, transactions):
        self.accounts = accounts
        self.transactions = transactions
        self.reports = {}
        self.stock_split_multiplier = {}
        self.stock_price_util = {}
        self.exchange_rate_util = ExchangeRateUtility()
        self.lots = {}

    def _identify_fy(self, date):
        year, month, _ = date.split("-")
        if int(month) in range(1, 4):
            return year
        else:
            return str(int(year) + 1)

    def _pre_processing(self):
        self.stock_split_multiplier = {}
        for transaction in self.transactions:
            self.stock_split_multiplier.setdefault(transaction.stock, 1)
            if transaction.transaction_type == TransactionType.SPLIT:
                self.stock_split_multiplier[transaction.stock] *= transaction.units

    def get_peak_stock_price(self, stock, date):
        price = self.stock_price_util[stock].get_peak_price(date)
        return price[0] * self.stock_split_multiplier[stock], price

    def get_closing_stock_price(self, stock):
        price = self.stock_price_util[stock].get_closing()
        return price[0] * self.stock_split_multiplier[stock], price

    def _identify_cy(self, date):
        return date.split("-")[0]

    def _get_time(self, date):
        return datetime.strptime(date, "%Y-%m-%d")

    def _process_credit_transaction(self, t1, curr_date):
        exchange_rate, exchange_rate_date = self.exchange_rate_util.get_exchange_rate(str(curr_date.date()))
        invested_amount = round(t1.units * t1.buy_price * exchange_rate, 2)
        self.lots[t1.stock + "_" + t1.lot_id] = Lot(
            lot_id=t1.lot_id,
            balance=t1.units,
            stock=t1.stock,
            invested_amount=invested_amount,
            invested_amount_metadata = (t1.buy_price, str(curr_date.date()), exchange_rate, exchange_rate_date),
            peak_value=invested_amount,
            peak_value_metadata = (t1.buy_price, str(curr_date.date()), exchange_rate, exchange_rate_date)
        )

    def _process_debit_transaction(self, t1, curr_date):
        exchange_rate, exchange_rate_date = self.exchange_rate_util.get_exchange_rate(str(curr_date.date()))
        lot = self.lots[t1.stock + "_" + t1.lot_id]
        gross_proceeds_holdings = round(t1.units * t1.sell_price * exchange_rate, 2)
        lot.balance -= t1.units
        lot.gross_proceeds_holdings += gross_proceeds_holdings

    def _init_stock_price_util(self, stock, start_date, end_date):
        if stock in self.stock_price_util:
            return
        self.stock_price_util[stock] = StockPriceUtility(stock, str(start_date.date()), \
                                    str(end_date.date()), self.exchange_rate_util)

    def generate_a3(self):
        # Get CY from the first transaction
        self._pre_processing()
        year = int(self._identify_cy(self.transactions[0].date))
        current_year = int(datetime.now().year)
        current_year = year
        transaction_idx = 0
        while(year <= current_year):
            curr_date = start_date = self._get_time(f"{year}-01-01")
            end_date = self._get_time(f"{year}-12-31")
            self.stock_price_util = {}
            while(curr_date <= end_date):
                # Process transactions on this date
                while(transaction_idx < len(self.transactions) and \
                    self._get_time(self.transactions[transaction_idx].date) == curr_date):
                    t1 = self.transactions[transaction_idx]
                    if t1.transaction_type==TransactionType.CREDIT:
                        self._process_credit_transaction(t1, curr_date)
                    if t1.transaction_type==TransactionType.DEBIT:
                        self._process_debit_transaction(t1, curr_date)
                    transaction_idx += 1

                # Update peak value
                for _, lot in self.lots.items():
                    self._init_stock_price_util(lot.stock, start_date, end_date)
                    price, meta_data = self.get_peak_stock_price(lot.stock, str(curr_date.date()))
                    todays_peak = lot.balance * price
                    if todays_peak > lot.peak_value:
                        lot.peak_value = todays_peak
                        lot.peak_value_metadata = meta_data
                curr_date += timedelta(days=1)

            # Generate A3
            self.reports[year] = {}
            for _, lot in self.lots.items():
                price, meta_data = self.get_closing_stock_price(lot.stock)
                self.reports[year][lot.lot_id] = Report_A3(
                    invested_amount=lot.invested_amount,
                    peak_value=lot.peak_value,
                    gross_proceeds_holdings=lot.gross_proceeds_holdings,
                    closing_balance=round(lot.balance * price, 2),
                    closing_balance_metadata=meta_data,
                    peak_value_metadata=lot.peak_value_metadata,
                    invested_amount_metadata=lot.invested_amount_metadata
                )
                # Reset lot for next CY
                lot.peak_value = -1
                lot.gross_proceeds_holdings = 0
            year += 1
        return self.reports

