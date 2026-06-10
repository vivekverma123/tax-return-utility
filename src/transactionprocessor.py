from dataclasses import dataclass
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from src.exchangerateutility import ExchangeRateUtility
from src.ledger import TransactionType
from src.stockpriceutility import StockPriceUtility

@dataclass
class ReportA3:
    invested_amount: float
    peak_value: float
    closing_balance: float
    invested_amount_metadata: tuple[float, float, float, float] = (0.0, 0,0, 0.0, 0.0)
    peak_value_metadata: tuple[float, float, float, float] = (0.0, 0,0, 0.0, 0.0)
    closing_balance_metadata: tuple[float, float, float, float] = (0.0, 0,0, 0.0, 0.0)
    gross_proceeds_redemption: float = 0.0
    gross_proceeds_holdings: float = 0.0

@dataclass
class ReportFY(ReportA3):
    opening_units: int = 0
    opening_cost: float = 0.0
    units_acquired: int = 0
    acquisition_cost_total: float = 0.0
    avg_cost_per_share_acquired: float = 0.0
    units_sold: int = 0
    total_consideration: float = 0.0
    closing_units: int = 0
    closing_value: float = 0.0

@dataclass
class ReportA2(ReportA3):
    pass

# Intermediate class for processing transactions
@dataclass
class Lot:
    lot_id: str
    balance: int
    stock: str
    account_id: str
    invested_amount: float
    peak_value: float
    invested_amount_metadata: tuple[float, float, float, float] = (0.0, 0,0, 0.0, 0.0)
    peak_value_metadata: tuple[float, float, float, float] = (0.0, 0,0, 0.0, 0.0)
    gross_proceeds_holdings: float = 0.0

@dataclass
class CapitalGain:
    lot_id: str
    stock: str
    cost_of_acquisition: float
    cost_of_acquisition_inr: float
    total_value_of_consideration: float
    total_value_of_consideration_inr: float
    buy_metadata: tuple[float, str, float, str]
    sell_metadata: tuple[float, str, float, str]
    units: int = 0
    gain: float = 0.0

class TransactionProcessor:

    def __init__(self, accounts, transactions):
        self.accounts = accounts
        self.transactions = transactions
        self.reports_a3 = {}
        self.reports_a2 = {}
        self.reports_fy = {}
        self.reports_ltcg = {}
        self.reports_stcg = {}
        self.stock_split_multiplier = {}
        self.stock_price_util = {}
        self.exchange_rate_util = ExchangeRateUtility()
        self.lots = {}
        self.lot_a2 = {}

    def _identify_fy(self, date):
        year, month, _ = date.split("-")
        if int(month) in range(1, 4):
            return year
        return str(int(year) + 1)

    def _pre_processing(self):
        self.stock_split_multiplier = {}
        for transaction in self.transactions:
            self.stock_split_multiplier.setdefault(transaction.stock, 1)
            if transaction.transaction_type == TransactionType.SPLIT:
                self.stock_split_multiplier[transaction.stock] *= transaction.units

    def get_peak_stock_price(self, stock, date):
        price, meta_data = self.stock_price_util[stock].get_peak_price(date)
        return price * self.stock_split_multiplier[stock], meta_data

    def get_closing_stock_price(self, stock):
        price, meta_data = self.stock_price_util[stock].get_closing()
        return price * self.stock_split_multiplier[stock], meta_data

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
            account_id=t1.account_id,
            invested_amount=invested_amount,
            invested_amount_metadata = (t1.buy_price, str(curr_date.date()), exchange_rate, exchange_rate_date),
            peak_value=invested_amount,
            peak_value_metadata = (t1.buy_price, str(curr_date.date()), exchange_rate, exchange_rate_date)
        )

    def _process_capital_gain(self, t1, lot):
        cost_of_acquisition = lot.invested_amount_metadata[0] * t1.units
        total_value_of_consideration = t1.sell_price * t1.units
        exchange_rate_acquisition = self.exchange_rate_util.get_exchange_rate_last_month(
            lot.invested_amount_metadata[1])
        exchange_rate_sale = self.exchange_rate_util.get_exchange_rate_last_month(t1.date)
        cg = CapitalGain(
            lot_id=lot.lot_id,
            stock=t1.stock,
            units=t1.units,
            cost_of_acquisition=cost_of_acquisition,
            cost_of_acquisition_inr=cost_of_acquisition * exchange_rate_acquisition[0],
            total_value_of_consideration=total_value_of_consideration,
            total_value_of_consideration_inr=total_value_of_consideration * exchange_rate_sale[0],
            buy_metadata=lot.invested_amount_metadata[0:2] + tuple(exchange_rate_acquisition),
            sell_metadata=(t1.sell_price, t1.date) + tuple(exchange_rate_sale)
        )
        cg.gain = round(cg.total_value_of_consideration_inr - cg.cost_of_acquisition_inr, 2)
        difference = relativedelta(
            datetime.strptime(t1.date, "%Y-%m-%d"),
            datetime.strptime(lot.invested_amount_metadata[1], "%Y-%m-%d")
        )
        fy = self._identify_fy(t1.date)
        if difference.years > 3:
            self.reports_ltcg.setdefault(fy, []).append(cg)
        else:
            self.reports_stcg.setdefault(fy, []).append(cg)

    def _process_debit_transaction(self, t1, curr_date):
        exchange_rate, _ = self.exchange_rate_util.get_exchange_rate(str(curr_date.date()))
        lot = self.lots[t1.stock + "_" + t1.lot_id]
        gross_proceeds_holdings = round(t1.units * t1.sell_price * exchange_rate, 2)
        lot.balance -= t1.units
        lot.gross_proceeds_holdings += gross_proceeds_holdings
        self._process_capital_gain(t1, lot)

    def _process_split_transaction(self, t1):
        for _, lot in self.lots.items():
            if lot.stock != t1.stock:
                continue
            lot.balance *= t1.units
        self.stock_split_multiplier[t1.stock] /= t1.units

    def _init_stock_price_util(self, stock, start_date, end_date):
        if stock in self.stock_price_util:
            return
        self.stock_price_util[stock] = StockPriceUtility(stock, str(start_date.date()), \
                                    str(end_date.date()), self.exchange_rate_util)

    def generate_reports(self):
        # Get CY from the first transaction
        self._pre_processing()
        year = int(self._identify_cy(self.transactions[0].date))
        fy = int(self._identify_fy(self.transactions[0].date))
        current_year = int(datetime.now().year)
        transaction_idx = 0

        fy_stock_state = {}
        fy_opening_snapshot = {}
        fy_acquisitions = {}
        fy_sales = {}

        while year <= current_year:
            curr_date = start_date = self._get_time(f"{year}-01-01")
            end_date = self._get_time(f"{year}-12-31")
            self.stock_price_util = {}
            account_peak_value = {}
            account_invested_amount = {}
            account_gross_proceeds = {}

            while curr_date <= end_date:
                # Hook 1: April 1 - reset FY tracking
                if curr_date.month == 4 and curr_date.day == 1:
                    fy_opening_snapshot = {s: {'units': state['units'], 'cost_inr': state['cost_inr']}
                                          for s, state in fy_stock_state.items()}
                    fy_acquisitions = {}
                    fy_sales = {}

                # Process transactions on this date
                while(transaction_idx < len(self.transactions) and \
                    self._get_time(self.transactions[transaction_idx].date) == curr_date):
                    t1 = self.transactions[transaction_idx]
                    if t1.transaction_type==TransactionType.CREDIT:
                        self._process_credit_transaction(t1, curr_date)
                        # Hook 2a: Mirror to FY tracking
                        exchange_rate, _ = self.exchange_rate_util.get_exchange_rate(t1.date)
                        cost = t1.units * t1.buy_price * exchange_rate
                        if t1.stock not in fy_stock_state:
                            fy_stock_state[t1.stock] = {'units': 0, 'cost_inr': 0.0}
                        fy_stock_state[t1.stock]['units'] += t1.units
                        fy_stock_state[t1.stock]['cost_inr'] += cost
                        if t1.stock not in fy_acquisitions:
                            fy_acquisitions[t1.stock] = {'units': 0, 'cost': 0.0}
                        fy_acquisitions[t1.stock]['units'] += t1.units
                        fy_acquisitions[t1.stock]['cost'] += cost

                    if t1.transaction_type==TransactionType.DEBIT:
                        self._process_debit_transaction(t1, curr_date)
                        # Hook 2b: Mirror to FY tracking
                        exchange_rate, _ = self.exchange_rate_util.get_exchange_rate(t1.date)
                        proceeds = t1.units * t1.sell_price * exchange_rate
                        if t1.stock in fy_stock_state and fy_stock_state[t1.stock]['units'] > 0:
                            cost_per_unit = fy_stock_state[t1.stock]['cost_inr'] / fy_stock_state[t1.stock]['units']
                            cost_removed = cost_per_unit * t1.units
                            fy_stock_state[t1.stock]['units'] -= t1.units
                            fy_stock_state[t1.stock]['cost_inr'] -= cost_removed
                        if t1.stock not in fy_sales:
                            fy_sales[t1.stock] = {'units': 0, 'proceeds': 0.0}
                        fy_sales[t1.stock]['units'] += t1.units
                        fy_sales[t1.stock]['proceeds'] += proceeds

                    if t1.transaction_type==TransactionType.SPLIT:
                        self._process_split_transaction(t1)
                        # Hook 2c: Mirror to FY tracking
                        if t1.stock in fy_stock_state:
                            fy_stock_state[t1.stock]['units'] *= t1.units

                    transaction_idx += 1

                # Update peak value for lots and accounts
                account_daily_value = {}
                for _, lot in self.lots.items():
                    self._init_stock_price_util(lot.stock, start_date, end_date)
                    price, meta_data = self.get_peak_stock_price(lot.stock, str(curr_date.date()))
                    todays_peak = round(lot.balance * price, 2)
                    if todays_peak > lot.peak_value:
                        lot.peak_value = todays_peak
                        lot.peak_value_metadata = meta_data

                    close_price, _ = self.stock_price_util[lot.stock].get_close_price(str(curr_date.date()))
                    todays_closing_value = round(lot.balance * close_price, 2)
                    if lot.account_id not in account_daily_value:
                        account_daily_value[lot.account_id] = 0.0
                    account_daily_value[lot.account_id] += todays_closing_value

                for account_id, daily_value in account_daily_value.items():
                    if account_id not in account_peak_value:
                        account_peak_value[account_id] = 0.0
                    if daily_value > account_peak_value[account_id]:
                        account_peak_value[account_id] = daily_value

                # Hook 3: March 31 - generate FY report
                if curr_date.month == 3 and curr_date.day == 31:
                    fy_num = int(self._identify_fy(str(curr_date.date())))
                    fy_label = f"{fy_num - 1}-{str(fy_num)[2:]}"
                    self.reports_fy[fy_label] = {}

                    all_stocks = set(fy_stock_state.keys()) | set(fy_opening_snapshot.keys()) | set(fy_acquisitions.keys()) | set(fy_sales.keys())

                    for stock in all_stocks:
                        opening_units = fy_opening_snapshot.get(stock, {}).get('units', 0)
                        opening_cost = fy_opening_snapshot.get(stock, {}).get('cost_inr', 0.0)

                        units_acquired = fy_acquisitions.get(stock, {}).get('units', 0)
                        acquisition_cost_total = fy_acquisitions.get(stock, {}).get('cost', 0.0)
                        avg_cost_per_share_acquired = acquisition_cost_total / units_acquired if units_acquired > 0 else 0.0

                        units_sold = fy_sales.get(stock, {}).get('units', 0)
                        total_consideration = fy_sales.get(stock, {}).get('proceeds', 0.0)

                        closing_units = fy_stock_state.get(stock, {}).get('units', 0)
                        closing_value = 0.0
                        if closing_units > 0 and stock in self.stock_price_util:
                            close_price, _ = self.stock_price_util[stock].get_close_price(str(curr_date.date()))
                            closing_value = round(closing_units * close_price, 2)

                        self.reports_fy[fy_label][stock] = ReportFY(
                            invested_amount=opening_cost + acquisition_cost_total,
                            peak_value=0.0,
                            closing_balance=closing_value,
                            opening_units=opening_units,
                            opening_cost=opening_cost,
                            units_acquired=units_acquired,
                            acquisition_cost_total=acquisition_cost_total,
                            avg_cost_per_share_acquired=avg_cost_per_share_acquired,
                            units_sold=units_sold,
                            total_consideration=total_consideration,
                            closing_units=closing_units,
                            closing_value=closing_value
                        )

                curr_date += timedelta(days=1)

            # Aggregate account-level data
            for _, lot in self.lots.items():
                account_id = lot.account_id
                if account_id not in account_invested_amount:
                    account_invested_amount[account_id] = 0.0
                    account_gross_proceeds[account_id] = 0.0
                account_invested_amount[account_id] += lot.invested_amount
                account_gross_proceeds[account_id] += lot.gross_proceeds_holdings

            # Generate A3
            self.reports_a3[year] = {}
            for _, lot in self.lots.items():
                price, meta_data = self.get_closing_stock_price(lot.stock)
                self.reports_a3[year][lot.lot_id] = ReportA3(
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

            # Generate A2 (account-wise consolidated)
            self.reports_a2[year] = {}
            account_closing_balance = {}
            for _, lot in self.lots.items():
                account_id = lot.account_id
                if account_id not in account_closing_balance:
                    account_closing_balance[account_id] = 0.0
                price, _ = self.get_closing_stock_price(lot.stock)
                account_closing_balance[account_id] += round(lot.balance * price, 2)

            for account_id in account_invested_amount.keys():
                self.reports_a2[year][account_id] = ReportA2(
                    invested_amount=account_invested_amount[account_id],
                    peak_value=account_peak_value.get(account_id, 0.0),
                    closing_balance=account_closing_balance.get(account_id, 0.0),
                    gross_proceeds_holdings=account_gross_proceeds[account_id]
                )

            year += 1

        return self.reports_a3, self.reports_a2, self.reports_fy, self.reports_ltcg, self.reports_stcg
