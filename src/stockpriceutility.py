from datetime import datetime, timedelta

import yfinance as yf

class StockPriceUtility:

    def __init__(self, stock, start_date, end_date, exchange_rate_util):

        self.ticker = yf.Ticker(stock)
        self.stock = stock
        self.start_date = start_date
        self.end_date = end_date
        self.cut_off = None
        self.closing_price = None
        self.exchange_rate_util = exchange_rate_util
        self.date_to_peak_price = {}
        self.date_to_open_price = {}
        self._initialize()

    def _initialize(self):
        # Query 30 days prior data, in case data for self.start_date and prior isn't available for some reason
        self.cut_off = datetime.strptime(self.start_date, "%Y-%m-%d") - timedelta(days=30)
        end_date_excluded = datetime.strptime(self.end_date, "%Y-%m-%d") + timedelta(days=1)
        history = self.ticker.history(
            start=str(self.cut_off.date()),
            end=str(end_date_excluded.date()),
            interval="1d"
        )
        rows = history.reset_index().to_dict(orient='records')
        if len(rows) == 0:
            assert 0, f"Stock {self.ticker} data not available for the given date range"

        for row in rows:
            date = str(row['Date'].date())
            row['High'] = row['High']
            row['Open'] = row['Open']
            row['Close'] = row['Close']
            exchange_rate, date_exchange_rate = self.exchange_rate_util.get_exchange_rate(date)
            price_inr = row['High'] * exchange_rate
            self.date_to_peak_price[date] = (price_inr, row['High'], exchange_rate, date_exchange_rate)
            self.date_to_open_price[date] = (row['Open'] * exchange_rate, row['Open'], exchange_rate, date)

        exchange_rate, date_exchange_rate = self.exchange_rate_util.get_exchange_rate(self.end_date)
        self.closing_price = (rows[-1]['Close'] * exchange_rate, rows[-1]['Close'], str(rows[-1]['Date'].date()), \
                                exchange_rate, date_exchange_rate)

    def get_closing(self):
        return self.closing_price[0], self.closing_price[1:]

    def get_peak_price(self, date):
        rate = None
        date_stamp = datetime.strptime(date, "%Y-%m-%d")
        if date_stamp < datetime.strptime(self.start_date, "%Y-%m-%d") or \
            date_stamp > datetime.strptime(self.end_date, "%Y-%m-%d"):
            assert 0, f"For stock {self.ticker} requested date is out of range, reinitialize the class"
        while(rate is None and date_stamp>=self.cut_off):
            temp_date = str(date_stamp.date())
            if temp_date in self.date_to_peak_price:
                rate = self.date_to_peak_price[temp_date]
                break
            date_stamp = date_stamp - timedelta(days=1)
        if rate is None:
            assert 0, f"Stock {self.ticker} data not available for the requested date {date}"
        return rate[0], (rate[1], str(date_stamp.date()), rate[2], rate[3])

    def get_open_price(self, date):
        price = self.date_to_open_price[date]
        return price[0], (price[1], date, price[2], price[3])
