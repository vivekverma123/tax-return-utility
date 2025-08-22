import yfinance as yf
from datetime import datetime, timedelta
    
class StockPriceUtility:

    def __init__(self, stock, startDate, endDate, exchngRtUtil):

        self.ticker = yf.Ticker(stock)
        self.startDate = startDate
        self.endDate = endDate
        self.cutOff = None
        self.peakPrice = None
        self.peakedOn = None
        self.closingPrice = None
        self.closedOn = None
        self.exchngRtUtil = exchngRtUtil
        self.date_to_price = {}
        self._initialize()

    def _initialize(self):
        # Query 30 days prior data, in case data for self.startDate and prior isn't available for some reason
        self.cutOff = datetime.strptime(self.startDate, "%Y-%m-%d") - timedelta(days=30)
        history = self.ticker.history(
            start=str(self.cutOff.date()),
            end=self.endDate,
            interval="1d"
        )
        self.peakPrice = -1
        rows = history.reset_index().to_dict(orient='records')

        if len(rows) == 0:
            assert 0, f"Stock {self.ticker} data not available for the given date range"

        for row in rows:
            date = str(row['Date'].date())
            exchngRt, _ = self.exchngRtUtil.getExchangeRate(date, self.endDate) 
            priceLocalCurrency = row['High'] * exchngRt
            self.date_to_price[date] = (priceLocalCurrency, row['High'])
            if self.peakPrice < priceLocalCurrency:
                self.peakPrice = priceLocalCurrency
                self.peakedOn = date

        exchngRt, _ = self.exchngRtUtil.getExchangeRate(str(rows[-1]['Date'].date()), self.endDate)  
        self.closingPrice = rows[-1]['Close'] * exchngRt
        self.closedOn = str(rows[-1]['Date'].date())

    def getPeak(self):
        return self.peakedOn, self.peakPrice

    def getClosing(self):
        return self.closedOn, self.closingPrice

    def getPrice(self, date):
        rate = None
        dateStamp = datetime.strptime(date, "%Y-%m-%d")
        if dateStamp < datetime.strptime(self.startDate, "%Y-%m-%d") or dateStamp > datetime.strptime(self.endDate, "%Y-%m-%d"):
            assert 0, f"For stock {self.ticker} requested date is out of range, reinitialize the class"
        while(rate is None and dateStamp>=self.cutOff):
            temp_date = str(dateStamp.date())
            if temp_date in self.date_to_price:
                rate = self.date_to_price[temp_date]
                break
            dateStamp = dateStamp - timedelta(days=1)
        if rate is None:
            assert 0, f"Stock {self.ticker} data not available for the requested date {date}"
        return rate

