# Qode Backtesting Framework

A full-stack backtesting platform for fundamental, equity-based strategies on Indian stocks. Configure filters, ranking rules, position sizing, and a rebalance schedule — the system simulates the strategy historically and shows equity curve, drawdown, performance metrics, and trade logs.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** SQLite (swap to Postgres/MySQL by changing one line in `database.py`)
- **Frontend:** React, Recharts
- **Data:** 109 NSE-listed companies, daily OHLCV + quarterly fundamentals (synthetically generated — see note below)

## Folder Structure

```
qode-backtest/
├── backend/
│   ├── app.py              # FastAPI routes
│   ├── database.py         # table definitions
│   ├── data_generator.py   # populates the database (run once)
│   ├── backtest_engine.py  # core simulation logic
│   └── requirements.txt
├── frontend/
│   ├── public/index.html
│   └── src/
│       ├── App.jsx
│       └── components/     # ConfigForm, charts, tables
└── README.md
```

## Architecture

```
React (port 3000) → POST /run_backtest → FastAPI (port 8000)
→ backtest_engine.py → SQLite database → JSON result → charts/tables
```

`backtest_engine.py` is plain Python with no web code — it can be run and tested directly from a terminal. `app.py` just translates JSON in/out.

## Setup

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python data_generator.py        # populates backtest.db, run once
uvicorn app:app --reload --port 8000
```
API: `http://localhost:8000` | Docs: `http://localhost:8000/docs`

### Frontend
```bash
cd frontend
npm install
npm start
```
App: `http://localhost:3000` (run backend first; both must be running together)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/companies` | List all companies |
| POST | `/run_backtest` | Run backtest, returns curves/metrics/logs |
| POST | `/export_csv` | Returns portfolio log as CSV |

## Notes

- **No look-ahead bias:** fundamentals are filtered by `report_date <= rebalance_date`, so the engine never uses data that wouldn't have been publicly known yet.
- **Data is synthetic**, not live-scraped, since the build environment had no internet access to Yahoo Finance/Screener. Schema matches real scraped data, so `data_generator.py` can be swapped for a real scraper without touching anything else.
- No transaction costs/slippage modeled; returns are gross.
- Not implemented (optional/bonus): Nifty 50 benchmark comparison, prebuilt strategies, strategy comparison view.
