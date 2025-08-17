import yfinance as yf
    
class StockPriceUtility:

    def __init__(self, stock, startDate, endDate, exchngRtUtil):

        self.ticker = yf.Ticker(stock)
        self.startDate = startDate
        self.endDate = endDate
        self.peakPrice = None
        self.peakedOn = None
        self.closingPrice = None
        self.closedOn = None
        self.exchngRtUtil = exchngRtUtil
        self._initialize()

    def _initialize(self):

        history = self.ticker.history(
            start=self.startDate,
            end=self.endDate,
            interval="1d"
        )
        self.peakPrice = -1
        rows = history.reset_index().to_dict(orient='records')
        for row in rows:
            date = str(row['Date'].date())
            exchngRt, _ = self.exchngRtUtil.getExchangeRate(date, self.endDate) 
            if self.peakPrice < row['High'] * exchngRt:
                self.peakPrice = row['High'] * exchngRt
                self.peakedOn = date

        exchngRt, _ = self.exchngRtUtil.getExchangeRate(str(rows[-1]['Date'].date()), self.endDate)  
        self.closingPrice = rows[-1]['Close'] * exchngRt
        self.closedOn = str(rows[-1]['Date'].date())

    def getPeak(self):
        return self.peakedOn, self.peakPrice

    def getClosing(self):
        return self.closedOn, self.closingPrice

