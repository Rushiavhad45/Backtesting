"""
FastAPI app. Run with:  uvicorn app:app --reload --port 8000
"""

from datetime import date
import io
import csv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

from database import get_session, Company, init_db
from backtest_engine import BacktestParams, run_backtest

app = FastAPI(title="Qode Backtesting API")

# allow the React dev server to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


# ---------- request/response schemas ----------

class RankMetric(BaseModel):
    metric: str
    direction: str = "desc"  # "asc" or "desc"


class BacktestRequest(BaseModel):
    start_date: date
    end_date: date
    rebalance_freq: str             # monthly | quarterly | yearly
    portfolio_size: int = 20
    position_sizing: str = "equal"  # equal | market_cap | metric
    sizing_metric: str = "roce"
    min_market_cap: float = 0
    max_market_cap: float = 10_000_000
    min_roce: float = -100
    require_positive_pat: bool = True
    rank_metrics: List[RankMetric] = [RankMetric(metric="roe", direction="desc")]
    initial_capital: float = 1_000_000


# ---------- routes ----------

@app.get("/")
def root():
    return {"status": "ok", "message": "Qode Backtesting API"}


@app.get("/companies")
def list_companies():
    session = get_session()
    try:
        companies = session.query(Company).all()
        return [{"symbol": c.symbol, "name": c.name, "sector": c.sector} for c in companies]
    finally:
        session.close()


@app.post("/run_backtest")
def run_backtest_endpoint(req: BacktestRequest):
    if req.start_date >= req.end_date:
        raise HTTPException(400, "start_date must be before end_date")

    params = BacktestParams(
        start_date=req.start_date,
        end_date=req.end_date,
        rebalance_freq=req.rebalance_freq,
        portfolio_size=req.portfolio_size,
        position_sizing=req.position_sizing,
        sizing_metric=req.sizing_metric,
        min_market_cap=req.min_market_cap,
        max_market_cap=req.max_market_cap,
        min_roce=req.min_roce,
        require_positive_pat=req.require_positive_pat,
        rank_metrics=[m.dict() for m in req.rank_metrics],
        initial_capital=req.initial_capital,
    )
    try:
        result = run_backtest(params)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


@app.post("/export_csv")
def export_csv(req: BacktestRequest):
    """Re-runs the backtest and streams the portfolio logs as a CSV download."""
    params = BacktestParams(
        start_date=req.start_date, end_date=req.end_date,
        rebalance_freq=req.rebalance_freq, portfolio_size=req.portfolio_size,
        position_sizing=req.position_sizing, sizing_metric=req.sizing_metric,
        min_market_cap=req.min_market_cap, max_market_cap=req.max_market_cap,
        min_roce=req.min_roce, require_positive_pat=req.require_positive_pat,
        rank_metrics=[m.dict() for m in req.rank_metrics],
        initial_capital=req.initial_capital,
    )
    result = run_backtest(params)
    logs = result["portfolio_logs"]

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[
        "rebalance_date", "symbol", "name", "weight", "entry_price", "exit_price", "return_pct"
    ])
    writer.writeheader()
    writer.writerows(logs)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=portfolio_logs.csv"},
    )
