"""
Backtest engine.

Given user parameters, this:
  1. Builds a rebalance date schedule (monthly/quarterly/yearly).
  2. At each rebalance date, filters the universe using only fundamentals
     known as of that date (report_date <= rebalance_date) — no future leakage.
  3. Ranks the filtered stocks by the chosen metric(s).
  4. Picks the top N and assigns weights via the chosen position sizing method.
  5. Carries the portfolio forward, marking to market with daily closing
     prices, and rebalances again at the next date (compounding).
  6. Computes equity curve, drawdown, and summary performance metrics.
"""

from dataclasses import dataclass, field
from datetime import date
from dateutil.relativedelta import relativedelta
import math

from sqlalchemy import and_
from database import Company, Price, Fundamental, get_session


# ---------- Parameter container ----------

@dataclass
class BacktestParams:
    start_date: date
    end_date: date
    rebalance_freq: str            # "monthly" | "quarterly" | "yearly"
    portfolio_size: int            # e.g. 20
    position_sizing: str           # "equal" | "market_cap" | "metric"
    sizing_metric: str = "roce"    # used only if position_sizing == "metric"
    min_market_cap: float = 0      # INR Cr
    max_market_cap: float = math.inf
    min_roce: float = -math.inf
    require_positive_pat: bool = True
    rank_metrics: list = field(default_factory=lambda: [{"metric": "roe", "direction": "desc"}])
    initial_capital: float = 1_000_000.0


# ---------- Helpers ----------

def _rebalance_dates(start, end, freq):
    step = {"monthly": 1, "quarterly": 3, "yearly": 12}[freq]
    dates = []
    d = start
    while d <= end:
        dates.append(d)
        d = d + relativedelta(months=step)
    return dates


def _latest_fundamentals_asof(session, as_of_date):
    """
    For every company, get the most recent fundamental row whose report_date
    is <= as_of_date. This is the core no-future-leakage guard: a rebalance
    on a given date can only ever see fundamentals published on/before it.
    """
    rows = (
        session.query(Fundamental)
        .filter(Fundamental.report_date <= as_of_date)
        .order_by(Fundamental.company_id, Fundamental.report_date.desc())
        .all()
    )
    latest = {}
    for r in rows:
        if r.company_id not in latest:
            latest[r.company_id] = r
    return latest


def _price_on_or_before(session, company_id, target_date):
    row = (
        session.query(Price)
        .filter(Price.company_id == company_id, Price.date <= target_date)
        .order_by(Price.date.desc())
        .first()
    )
    return row.close if row else None


def _apply_filters(fundamentals_map, params):
    passed = []
    for cid, f in fundamentals_map.items():
        if f.market_cap_cr is None:
            continue
        if not (params.min_market_cap <= f.market_cap_cr <= params.max_market_cap):
            continue
        if f.roce is None or f.roce < params.min_roce:
            continue
        if params.require_positive_pat and (f.pat_cr is None or f.pat_cr <= 0):
            continue
        passed.append(f)
    return passed


def _rank_and_select(candidates, params):
    """
    Composite ranking: for each metric, rank ascending or descending,
    then average the ranks across metrics. Lower average rank = better.
    """
    if not candidates:
        return []

    rank_scores = {f.company_id: [] for f in candidates}
    for spec in params.rank_metrics:
        metric, direction = spec["metric"], spec.get("direction", "desc")
        values = [(f.company_id, getattr(f, metric)) for f in candidates if getattr(f, metric) is not None]
        values.sort(key=lambda x: x[1], reverse=(direction == "desc"))
        for rank, (cid, _) in enumerate(values, start=1):
            rank_scores[cid].append(rank)

    composite = []
    for f in candidates:
        ranks = rank_scores.get(f.company_id, [])
        if not ranks:
            continue
        composite.append((f, sum(ranks) / len(ranks)))

    composite.sort(key=lambda x: x[1])
    selected = [f for f, _ in composite[: params.portfolio_size]]
    return selected


def _assign_weights(selected, params, session, as_of_date):
    if not selected:
        return {}

    if params.position_sizing == "equal":
        w = 1.0 / len(selected)
        return {f.company_id: w for f in selected}

    if params.position_sizing == "market_cap":
        total = sum(f.market_cap_cr for f in selected if f.market_cap_cr)
        return {f.company_id: (f.market_cap_cr / total) for f in selected if f.market_cap_cr}

    if params.position_sizing == "metric":
        metric = params.sizing_metric
        vals = {f.company_id: max(getattr(f, metric) or 0, 0.0001) for f in selected}
        total = sum(vals.values())
        return {cid: v / total for cid, v in vals.items()}

    raise ValueError(f"Unknown position sizing method: {params.position_sizing}")


# ---------- Main engine ----------

def run_backtest(params: BacktestParams):
    session = get_session()
    try:
        dates = _rebalance_dates(params.start_date, params.end_date, params.rebalance_freq)
        if len(dates) < 2:
            raise ValueError("Date range too short for the chosen rebalance frequency")

        capital = params.initial_capital
        equity_curve = []   # list of {date, equity}
        portfolio_logs = [] # list of {rebalance_date, symbol, weight, entry_price, exit_price, return_pct}
        company_lookup = {c.id: c for c in session.query(Company).all()}

        for i in range(len(dates) - 1):
            reb_date = dates[i]
            next_reb_date = dates[i + 1]

            fundamentals_map = _latest_fundamentals_asof(session, reb_date)
            candidates = _apply_filters(fundamentals_map, params)
            selected = _rank_and_select(candidates, params)
            weights = _assign_weights(selected, params, session, reb_date)

            if not weights:
                # nothing passed filters this period; carry capital flat
                equity_curve.append({"date": reb_date.isoformat(), "equity": round(capital, 2)})
                continue

            period_return = 0.0
            for f in selected:
                cid = f.company_id
                w = weights.get(cid)
                if not w:
                    continue
                entry_price = _price_on_or_before(session, cid, reb_date)
                exit_price = _price_on_or_before(session, cid, next_reb_date)
                if not entry_price or not exit_price:
                    continue
                stock_return = (exit_price - entry_price) / entry_price
                period_return += w * stock_return

                portfolio_logs.append({
                    "rebalance_date": reb_date.isoformat(),
                    "symbol": company_lookup[cid].symbol,
                    "name": company_lookup[cid].name,
                    "weight": round(w * 100, 2),
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(exit_price, 2),
                    "return_pct": round(stock_return * 100, 2),
                })

            capital = capital * (1 + period_return)
            equity_curve.append({"date": reb_date.isoformat(), "equity": round(capital, 2)})

        # final point
        equity_curve.append({"date": dates[-1].isoformat(), "equity": round(capital, 2)})

        metrics = _compute_metrics(equity_curve, params.initial_capital, params.start_date, params.end_date)
        drawdown_curve = _compute_drawdown(equity_curve)
        winners, losers = _top_winners_losers(portfolio_logs)

        return {
            "equity_curve": equity_curve,
            "drawdown_curve": drawdown_curve,
            "metrics": metrics,
            "portfolio_logs": portfolio_logs,
            "top_winners": winners,
            "top_losers": losers,
        }
    finally:
        session.close()


def _compute_metrics(equity_curve, initial_capital, start_date, end_date):
    final_equity = equity_curve[-1]["equity"]
    years = max((end_date - start_date).days / 365.25, 0.01)
    cagr = ((final_equity / initial_capital) ** (1 / years) - 1) * 100 if final_equity > 0 else -100

    # period returns for sharpe (per rebalance period, annualized roughly)
    rets = []
    for a, b in zip(equity_curve, equity_curve[1:]):
        if a["equity"] > 0:
            rets.append((b["equity"] - a["equity"]) / a["equity"])
    if rets:
        mean_r = sum(rets) / len(rets)
        var = sum((r - mean_r) ** 2 for r in rets) / max(len(rets) - 1, 1)
        std_r = math.sqrt(var)
        periods_per_year = max(len(rets) / years, 1)
        sharpe = (mean_r / std_r) * math.sqrt(periods_per_year) if std_r > 0 else 0
    else:
        sharpe = 0

    equities = [p["equity"] for p in equity_curve]
    peak = equities[0]
    max_dd = 0
    for e in equities:
        peak = max(peak, e)
        dd = (e - peak) / peak if peak > 0 else 0
        max_dd = min(max_dd, dd)

    return {
        "final_equity": round(final_equity, 2),
        "total_return_pct": round((final_equity / initial_capital - 1) * 100, 2),
        "cagr_pct": round(cagr, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "num_rebalances": len(equity_curve) - 1,
    }


def _compute_drawdown(equity_curve):
    out = []
    peak = equity_curve[0]["equity"]
    for p in equity_curve:
        peak = max(peak, p["equity"])
        dd = (p["equity"] - peak) / peak * 100 if peak > 0 else 0
        out.append({"date": p["date"], "drawdown": round(dd, 2)})
    return out


def _top_winners_losers(portfolio_logs, n=10):
    if not portfolio_logs:
        return [], []
    # aggregate average return per symbol across all periods held
    agg = {}
    for row in portfolio_logs:
        agg.setdefault(row["symbol"], {"symbol": row["symbol"], "name": row["name"], "returns": []})
        agg[row["symbol"]]["returns"].append(row["return_pct"])
    summary = []
    for sym, d in agg.items():
        avg_ret = sum(d["returns"]) / len(d["returns"])
        summary.append({"symbol": sym, "name": d["name"], "avg_return_pct": round(avg_ret, 2)})
    summary.sort(key=lambda x: x["avg_return_pct"], reverse=True)
    return summary[:n], summary[-n:][::-1]
