import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

class StockPriceUtility:

    def __init__(self, stock, startDate, endDate, exchngRtUtil):

        self.ticker = yf.Ticker(stock)
        self.stock = stock
        self.startDate = startDate
        self.endDate = endDate
        self.cutOff = None
        self.closingPrice = None
        self.exchngRtUtil = exchngRtUtil
        self.date_to_peak_price = {}
        self.date_to_open_price = {}
        self._initialize()

    def _initialize(self):
        # Query 30 days prior data, in case data for self.startDate and prior isn't available for some reason
        self.cutOff = datetime.strptime(self.startDate, "%Y-%m-%d") - timedelta(days=30)
        end_date_excluded = datetime.strptime(self.endDate, "%Y-%m-%d") + timedelta(days=1)
        history = self.ticker.history(
            start=str(self.cutOff.date()),
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
            exchngRt, date_exchange_rate = self.exchngRtUtil.get_exchange_rate(date)
            priceLocalCurrency = row['High'] * exchngRt
            self.date_to_peak_price[date] = (priceLocalCurrency, row['High'], exchngRt, date_exchange_rate)
            self.date_to_open_price[date] = (row['Open'] * exchngRt, row['Open'], exchngRt, date)

        exchngRt, date_exchange_rate = self.exchngRtUtil.get_exchange_rate(self.endDate)
        self.closingPrice = (rows[-1]['Close'] * exchngRt, rows[-1]['Close'], str(rows[-1]['Date'].date()), \
                                exchngRt, date_exchange_rate)

    def get_closing(self):
        price = self.closingPrice
        return self.closingPrice[0], self.closingPrice[1:]

    def get_peak_price(self, date):
        rate = None
        dateStamp = datetime.strptime(date, "%Y-%m-%d")
        if dateStamp < datetime.strptime(self.startDate, "%Y-%m-%d") or \
            dateStamp > datetime.strptime(self.endDate, "%Y-%m-%d"):
            assert 0, f"For stock {self.ticker} requested date is out of range, reinitialize the class"
        while(rate is None and dateStamp>=self.cutOff):
            temp_date = str(dateStamp.date())
            if temp_date in self.date_to_peak_price:
                rate = self.date_to_peak_price[temp_date]
                break
            dateStamp = dateStamp - timedelta(days=1)
        if rate is None:
            assert 0, f"Stock {self.ticker} data not available for the requested date {date}"
        return rate[0], (rate[1], str(dateStamp.date()), rate[2], rate[3])

    def get_open_price(self, date):
        price = self.date_to_open_price[date]
        return price[0], (price[1], date, price[2], price[3])

