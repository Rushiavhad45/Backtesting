import React, { useState } from "react";
import ConfigForm from "./components/ConfigForm";
import EquityCurveChart from "./components/EquityCurveChart";
import DrawdownChart from "./components/DrawdownChart";
import MetricsPanel from "./components/MetricsPanel";
import WinnersLosers from "./components/WinnersLosers";
import PortfolioLogTable from "./components/PortfolioLogTable";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

const DEFAULT_CONFIG = {
  start_date: "2020-01-01",
  end_date: "2023-12-31",
  rebalance_freq: "quarterly",
  portfolio_size: 20,
  position_sizing: "equal",
  sizing_metric: "roce",
  min_market_cap: 1000,
  max_market_cap: 10000000,
  min_roce: 5,
  require_positive_pat: true,
  rank_metrics: [{ metric: "roe", direction: "desc" }],
  initial_capital: 1000000,
};

function App() {
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runBacktest = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/run_backtest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!res.ok) {
        const errBody = await res.json();
        throw new Error(errBody.detail || "Backtest failed");
      }
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const exportCsv = async () => {
    const res = await fetch(`${API_BASE}/export_csv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "portfolio_logs.csv";
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="app">
      <div className="header">
        <div>
          <h1>Qode Backtesting Platform</h1>
          <div className="subtitle">Fundamental strategy backtesting for Indian equities</div>
        </div>
      </div>

      <div className="layout">
        <div className="sidebar">
          <ConfigForm config={config} setConfig={setConfig} onRun={runBacktest} loading={loading} />
        </div>

        <div className="main">
          {error && <div className="error-box">{error}</div>}

          {!result && !loading && (
            <div className="empty-state">
              <div>Configure your strategy on the left and click "Run Backtest"</div>
              <div style={{ fontSize: 12 }}>Results will appear here</div>
            </div>
          )}

          {loading && (
            <div className="empty-state">
              <div>Running backtest...</div>
            </div>
          )}

          {result && !loading && (
            <>
              <MetricsPanel metrics={result.metrics} />
              <EquityCurveChart data={result.equity_curve} />
              <DrawdownChart data={result.drawdown_curve} />
              <WinnersLosers winners={result.top_winners} losers={result.top_losers} />
              <PortfolioLogTable logs={result.portfolio_logs} onExport={exportCsv} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
