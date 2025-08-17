import pandas as pd
from datetime import datetime, timedelta

PATH_PREFIX = "https://raw.githubusercontent.com"
REPO_PATH = "sahilgupta/sbi-fx-ratekeeper"
FILE_PATH = "main/csv_files/SBI_REFERENCE_RATES_USD.csv"

class ExchangeRateUtility:

    def __init__(self):
        self.path = f"{PATH_PREFIX}/{REPO_PATH}/{FILE_PATH}"
        self.date_to_rate = {}
        self.lower_limit = datetime.strptime("2020-01-04", "%Y-%m-%d")
        self._initialize()
        
    def _initialize(self):
        df = pd.read_csv(self.path)
        for row in df.itertuples():
            if row is None:
                continue
            # DATE PDF_FILE TT_BUY TT_SELL BILL_BUY	BILL_SELL FOREX_TRAVEL_CARD BUY_FOREX_TRAVEL CARD_SELL CN_BUY CN_SELL
            # For inward remittance TT_BUY is taken into account as the bank will buy foreign currency from you at that exchange rate
            self.date_to_rate[row.DATE.split(" ")[0]] = row._3
            
    def _traverse(self, check, update, temp):
        rate = None
        while(rate is None and check(temp)):
            temp_date = str(temp.date())
            if temp_date in self.date_to_rate and self.date_to_rate[temp_date] != 0:
                rate = self.date_to_rate[temp_date]
                break
            temp = update(temp)
        return rate, temp_date
        
    def getExchangeRate(self, date, cutOff=str(datetime.now().date())):
        rate = None
        dateStamp = datetime.strptime(date, "%Y-%m-%d")
        temp = dateStamp
        cutOff = datetime.strptime(cutOff, "%Y-%m-%d")
        rate, temp_date = self._traverse(lambda temp: temp <= cutOff, lambda temp: temp + timedelta(days=1), temp)
        # No published exchange rate data upto the cutOff, look for the last available data prior to the date requested
        if rate is not None:
            return rate, temp_date
            
        temp = dateStamp - timedelta(days=1)
        rate, temp_date = self._traverse(lambda temp: temp >= self.lower_limit, lambda temp: temp - timedelta(days=1), temp)
        
        if rate is None:
            assert 0, f"Data not available for the requested date {date}"

        return rate, temp_date
