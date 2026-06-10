# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tax Return Utility is a Python application that processes investment transaction records and generates tax-related capital gains reports. It calculates long-term and short-term capital gains (LTCG/STCG) for investments, factoring in currency exchange rates and stock splits.

### Key Features
- Loads investment accounts and transactions from CSV files
- Processes buy/sell transactions and stock splits
- Calculates capital gains using lot-based accounting
- Fetches real-time stock prices via yfinance
- Retrieves exchange rates from SBI rates data
- Generates three types of reports: A3 (annual holdings), LTCG (long-term gains), STCG (short-term gains)

## Architecture

### Core Components

**Ledger Module** (`src/ledger.py`)
- `LedgerLoader`: Reads accounts and transactions from CSV files in the `records/` directory
- `InvestmentAccount`: Dataclass representing a brokerage account
- `Transaction`: Dataclass for buy/sell/split events
- `TransactionType`: Enum for CREDIT (buy), DEBIT (sell), SPLIT

**Transaction Processor** (`src/transactionprocessor.py`)
- `TransactionProcessor`: Main orchestrator that processes transactions chronologically
  - Calculates invested amounts (in INR using exchange rates)
  - Tracks peak values for each lot
  - Generates capital gain records (CapitalGain dataclass)
  - Classifies gains as LTCG (>3 years) or STCG (≤3 years)
- `Lot`: Internal representation of a holdings lot tracking balance, invested amount, peak value
- `ReportA3`, `ReportFY`, `ReportA2`: Dataclasses for report outputs

**Stock Price Utility** (`src/stockpriceutility.py`)
- Fetches historical OHLC data via yfinance API
- Caches peak prices and opening prices
- Converts prices to INR using exchange rates
- Handles date lookups with fallback to prior trading days if date not available

**Exchange Rate Utility** (`src/exchangerateutility.py`)
- Fetches SBI USD exchange rates from GitHub repo (sahilgupta/sbi-fx-ratekeeper)
- Provides rates for specific dates or last trading day of previous month
- Used for converting USD stock prices and transaction amounts to INR

### Data Flow
```
CSV files (records/) 
  → LedgerLoader
    → accounts, transactions
      → TransactionProcessor
        → (with StockPriceUtility, ExchangeRateUtility)
          → reports_a3, reports_ltcg, reports_stcg
```

## Common Commands

### Running Tests
```bash
# Run all tests with verbose output
pytest tests -vvv

# Run a specific test file
pytest tests/test_transaction_processor.py -vvv

# Run a specific test function
pytest tests/test_transaction_processor.py::test_process_single_buy -vvv

# Run with test report generation
pytest tests --junitxml=report.xml -vvv
```

### Linting
```bash
# Run pylint on all Python files
export PYTHONPATH=$(pwd)
pylint --rcfile=.pylintrc $(git ls-files '*.py')

# Run pylint on a specific file
pylint --rcfile=.pylintrc src/transactionprocessor.py
```

### Running the Application
```bash
# Execute the main script (processes records/ and generates reports)
python main.py
```

## Testing

- Tests use `unittest.mock` to patch external dependencies (yfinance, pandas, GitHub API calls)
- Test data is stored as JSON files in `tests/` directory
- Each module has a corresponding test file with fixture-based setup
- The `test_transaction_processor_data.json` contains mock accounts and transaction records

### Key Test Files
- `test_transaction_processor.py`: Main processing logic, lot tracking, capital gains calculation
- `test_ledger.py`: CSV loading and parsing
- `test_stock_price_utility.py`: Price fetching and caching
- `test_exchange_rate_utility.py`: Exchange rate lookups

## Data Input Format

### CSV Files in `records/` Directory

**Accounts CSV** (columns: account_id, account_no, broker, address, zip_code, country, currency)
```
account_id,account_no,broker,address,zip_code,country,currency
ACC001,123456789,BrokerX,123 Main St,12345,USA,USD
```

**Transactions CSV** (columns: account_id, date, stock, lot_id, transaction_type, units, buy_price, sell_price)
```
account_id,date,stock,lot_id,transaction_type,units,buy_price,sell_price
ACC001,2023-01-15,AAPL,LOT1,CREDIT,10,150.00,0.00
ACC001,2024-03-20,AAPL,LOT1,DEBIT,10,0.00,195.00
```

## Important Notes

- **Lot-Based Accounting**: Transactions reference specific lots by lot_id. The user must manage lot assignments for tax planning.
- **Fiscal Year Identification**: Dates from Jan-Mar belong to the previous FY (e.g., 2024-01-15 → FY2023)
- **Stock Splits**: Split transactions multiply all holdings of that stock. The stock_split_multiplier tracks cumulative splits for price adjustments.
- **Exchange Rates**: Uses the last available trading day before the requested date. Requires working internet access to fetch SBI rates on first run.
- **3-Year Threshold**: Gains are LTCG if holding period > 3 years (calculated via relativedelta), otherwise STCG.

## Development Workflow

1. Update test data JSON files when modifying fixtures
2. Update .pylintrc if changing code style rules
3. Ensure new functions have type hints in docstrings for dataclass fields
4. Use dataclasses for structured data (Transaction, Lot, CapitalGain, Report*)
5. Keep CSV parsing logic in LedgerLoader._process_* methods
6. Sort transactions chronologically in _link_transactions_to_accounts
